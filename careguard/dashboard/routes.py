from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path as FilePath
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Path, Query

from careguard.audit import AuditRunner
from careguard.config import load_policy_pack, load_scenario_pack
from careguard.evidence import sanitize_for_evidence
from careguard.models.schemas import AuditSummary, ComparisonRequest, TargetCreate
from careguard.reports import compare_audits

from .schemas import (
    AuditDetail, AuditJob, AuditJobRequest, ConnectionTestResponse, DashboardSummary,
    DashboardTarget, DemoChatRequest, DemoChatResponse, JobStatus, OnboardingRequest,
    OnboardingResponse, OrganizationProfile, PaginatedEvents, PolicyCoverageItem,
    PolicyUpdateRequest, ReviewDecision, ReviewDecisionInput, ReviewQueueItem, SafeGuardEvent,
    SafeAuditSummary, SafeComparisonSummary, SafeReport, SafeReportMetadata, SystemStatus,
    TargetConfigurationInput, TargetUpdateRequest,
)
from .service import DashboardService, validate_target_endpoint


router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@lru_cache
def dashboard_service() -> DashboardService:
    from careguard.api.app import data_root, database

    return DashboardService(database(), data_root())


@router.get("/summary", response_model=DashboardSummary)
async def summary() -> DashboardSummary:
    return await dashboard_service().summary()


@router.get("/system-status", response_model=SystemStatus)
async def system_status() -> SystemStatus:
    return await dashboard_service().system_status()


@router.get("/onboarding", response_model=OrganizationProfile | None)
def onboarding_profile() -> OrganizationProfile | None:
    return dashboard_service().organization()


@router.post("/onboarding", response_model=OnboardingResponse)
def save_onboarding(request: OnboardingRequest) -> OnboardingResponse:
    service = dashboard_service()
    target_input = request.target
    target_create = TargetCreate(
        target_id=target_input.target_id,
        name=target_input.name,
        connector_type=target_input.connector_type,
        endpoint=target_input.endpoint,
        model=target_input.model,
    )
    try:
        validate_target_endpoint(target_create, target_input.configuration)
        known_policies = {item.policy_id for item in load_policy_pack().policies}
        requested_policies = set(request.enabled_policy_ids) if request.enabled_policy_ids is not None else known_policies
        unknown_policies = requested_policies - known_policies
        if unknown_policies:
            raise ValueError(f"unknown policy IDs: {sorted(unknown_policies)}")
        profile = service.save_organization(request.organization)
        target = service.database.add_target(target_create)
        service.save_target_configuration(target.target_id, target_input.configuration)
        version = service.save_policy_settings(request.enabled_policy_ids)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return OnboardingResponse(
        organization=profile,
        target=service.dashboard_target(target),
        policy_configuration_version=version,
        next_actions=["Test the target connection", "Run a baseline audit", "Run a guarded audit"],
    )


@router.get("/targets", response_model=list[DashboardTarget])
def targets() -> list[DashboardTarget]:
    return dashboard_service().dashboard_targets()


def _target_or_404(target_id: str):
    target = dashboard_service().database.get_target(target_id)
    if not target:
        raise HTTPException(404, "target not found")
    return target


@router.get("/targets/{target_id}", response_model=DashboardTarget)
def target(target_id: str = Path(pattern=r"^[A-Za-z0-9._-]+$", max_length=80)) -> DashboardTarget:
    return dashboard_service().dashboard_target(_target_or_404(target_id))


@router.put("/targets/{target_id}", response_model=DashboardTarget)
def update_target(
    request: TargetUpdateRequest,
    target_id: str = Path(pattern=r"^[A-Za-z0-9._-]+$", max_length=80),
) -> DashboardTarget:
    current = _target_or_404(target_id)
    replacement = TargetCreate(
        target_id=target_id,
        name=request.name,
        connector_type=current.connector_type,
        endpoint=request.endpoint,
        model=request.model,
    )
    try:
        if current.connector_type != "demo" and target_id != "demo-guarded" and not request.authorized_target_confirmed:
            raise ValueError("explicit authorized-target confirmation is required")
        validate_target_endpoint(replacement, request.configuration)
        updated = dashboard_service().database.add_target(replacement)
        if "credential_env_reference" not in request.configuration.model_fields_set:
            request.configuration.credential_env_reference = dashboard_service()._raw_target_configuration(
                target_id
            ).get("credential_env_reference")
        dashboard_service().save_target_configuration(target_id, request.configuration)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return dashboard_service().dashboard_target(updated)


@router.delete("/targets/{target_id}", status_code=204)
def delete_target(target_id: str = Path(pattern=r"^[A-Za-z0-9._-]+$", max_length=80)) -> None:
    if target_id in {"demo", "demo-guarded"}:
        raise HTTPException(409, "built-in synthetic targets cannot be deleted")
    if not dashboard_service().database.delete_target(target_id):
        raise HTTPException(404, "target not found")


@router.post("/targets/{target_id}/test", response_model=ConnectionTestResponse)
async def test_target(target_id: str = Path(pattern=r"^[A-Za-z0-9._-]+$", max_length=80)) -> ConnectionTestResponse:
    return await dashboard_service().test_connection(_target_or_404(target_id))


@router.post("/audit-jobs", response_model=AuditJob)
async def create_audit_job(request: AuditJobRequest) -> AuditJob:
    service = dashboard_service()
    target = _target_or_404(request.target_id)
    config = service.target_configuration(request.target_id)
    if not config.enabled:
        raise HTTPException(409, "target is disabled")
    active_jobs = service.audit_jobs()
    if any(job.target_id == request.target_id and job.status in {JobStatus.QUEUED, JobStatus.RUNNING} for job in active_jobs):
        raise HTTPException(409, "an audit job is already active for this target")
    scenario_pack = load_scenario_pack()
    selected = [item for item in scenario_pack.scenarios if item.enabled]
    enabled_policy_ids, policy_configuration_version = service.current_policy_settings()
    if request.policy_ids:
        known = {item.policy_id for item in load_policy_pack().policies}
        unknown = set(request.policy_ids) - known
        if unknown:
            raise HTTPException(422, f"unknown policy IDs: {sorted(unknown)}")
        disabled = set(request.policy_ids) - enabled_policy_ids
        if disabled:
            raise HTTPException(409, f"requested policies are disabled: {sorted(disabled)}")
        selected = [item for item in selected if set(item.applicable_policy_ids) & set(request.policy_ids)]
    else:
        selected = [item for item in selected if set(item.applicable_policy_ids) & enabled_policy_ids]
    if request.scenario_ids is not None:
        selected_ids = set(request.scenario_ids)
        known_ids = {item.scenario_id for item in scenario_pack.scenarios}
        if selected_ids - known_ids:
            raise HTTPException(422, f"unknown scenario IDs: {sorted(selected_ids - known_ids)}")
        selected = [item for item in selected if item.scenario_id in selected_ids]
    if not selected:
        raise HTTPException(422, "selected policy/scenario scope is empty")
    submitted = datetime.now(timezone.utc)
    safe_fields = sanitize_for_evidence({"label": request.run_label, "notes": request.notes})
    job = AuditJob(
        job_id=f"job-{uuid4().hex}",
        status=JobStatus.QUEUED,
        submitted_at=submitted,
        target_id=request.target_id,
        total_scenarios=len(selected),
        policy_configuration_version=policy_configuration_version,
        run_label=safe_fields["label"],
        notes=safe_fields["notes"],
    )
    service.database.save_audit_job(job.job_id, submitted, job.model_dump_json())
    job = job.model_copy(update={"status": JobStatus.RUNNING, "started_at": datetime.now(timezone.utc)})
    service.database.save_audit_job(job.job_id, submitted, job.model_dump_json())
    try:
        from careguard.api.app import connector_for

        raw_config = service._raw_target_configuration(request.target_id)
        audit = await AuditRunner(
            connector_for(
                target,
                chat_path=config.chat_path,
                timeout_seconds=config.timeout_seconds,
                credential_env_reference=raw_config.get("credential_env_reference"),
            ),
            service.data_root / "evidence",
        ).run(
            request.target_id,
            [item.scenario_id for item in selected],
            policy_version=service.effective_policy_version(),
        )
        service.database.save_audit(audit)
        job = job.model_copy(update={
            "status": JobStatus.COMPLETED,
            "run_id": audit.run_id,
            "completed_at": audit.completed_at,
            "progress_count": len(selected),
        })
    except Exception as exc:
        job = job.model_copy(update={
            "status": JobStatus.FAILED,
            "completed_at": datetime.now(timezone.utc),
            "error": f"Audit job failed: {type(exc).__name__}",
        })
    service.database.save_audit_job(job.job_id, submitted, job.model_dump_json())
    return job


@router.get("/audit-jobs", response_model=list[AuditJob])
def audit_jobs() -> list[AuditJob]:
    return dashboard_service().audit_jobs()


@router.get("/audit-jobs/{job_id}", response_model=AuditJob)
def audit_job(job_id: str = Path(pattern=r"^job-[a-f0-9]{32}$")) -> AuditJob:
    payload = dashboard_service().database.get_audit_job_payload(job_id)
    if not payload:
        raise HTTPException(404, "audit job not found")
    return AuditJob.model_validate_json(payload)


@router.get("/audits", response_model=list[SafeAuditSummary])
def audit_summaries() -> list[SafeAuditSummary]:
    service = dashboard_service()
    return [service.safe_audit(item) for item in service.validated_audits()]


@router.get("/audits/{run_id}", response_model=AuditDetail)
def audit_detail(run_id: str = Path(pattern=r"^cg-[A-Za-z0-9-]+$", max_length=120)) -> AuditDetail:
    summary = dashboard_service().database.get_audit(run_id)
    if not summary:
        raise HTTPException(404, "audit not found")
    return dashboard_service().audit_detail(summary)


@router.post("/comparisons", response_model=SafeComparisonSummary)
def create_comparison(request: ComparisonRequest) -> SafeComparisonSummary:
    service = dashboard_service()
    baseline = service.database.get_audit(request.baseline_run_id)
    guarded = service.database.get_audit(request.guarded_run_id)
    if not baseline or not guarded:
        raise HTTPException(404, "audit not found")
    try:
        result = compare_audits(
            baseline, service.evidence.read(baseline.run_id),
            guarded, service.evidence.read(guarded.run_id),
            service.data_root / "reports" / "comparisons",
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    service.database.save_comparison(result)
    return service.safe_comparison(result)


@router.get("/comparisons", response_model=list[SafeComparisonSummary])
def comparisons() -> list[SafeComparisonSummary]:
    service = dashboard_service()
    return [service.safe_comparison(item) for item in service.validated_comparisons()]


@router.get("/comparisons/{comparison_id}", response_model=SafeComparisonSummary)
def comparison(
    comparison_id: str = Path(pattern=r"^cmp-[A-Za-z0-9-]+$", max_length=140),
) -> SafeComparisonSummary:
    service = dashboard_service()
    item = next(
        (value for value in service.validated_comparisons() if value.comparison_id == comparison_id), None,
    )
    if not item:
        raise HTTPException(404, "comparison not found")
    return service.safe_comparison(item)


@router.get("/events", response_model=PaginatedEvents)
async def events(
    page: int = Query(1, ge=1, le=10_000),
    page_size: int = Query(25, ge=1, le=100),
    decision: Literal[
        "ALLOW", "ALLOW_WITH_WARNING", "BLOCK", "REDACT", "ESCALATE",
        "REQUIRE_CONFIRMATION", "REQUIRE_HUMAN_REVIEW",
    ] | None = None,
    reason_code: str | None = Query(default=None, max_length=100),
    policy_id: str | None = Query(default=None, pattern=r"^CG-[A-Z]+-[0-9]{3}$"),
    human_review: bool | None = None,
    target_id: str | None = Query(default=None, max_length=80, pattern=r"^[A-Za-z0-9._-]+$"),
    guard_mode: Literal["monitor", "enforce"] | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> PaginatedEvents:
    if date_from and date_to and date_from > date_to:
        raise HTTPException(422, "date_from must be earlier than or equal to date_to")
    return await dashboard_service().events(
        page, page_size, decision, reason_code, policy_id, human_review,
        target_id, guard_mode, date_from, date_to,
    )


@router.get("/events/{event_id}", response_model=SafeGuardEvent)
async def event(event_id: str = Path(pattern=r"^evt-[a-f0-9]{32}$")) -> SafeGuardEvent:
    page = await dashboard_service().events(1, 1000)
    if page.source_status == "unavailable":
        raise HTTPException(503, "Guard event source is unavailable")
    item = next((value for value in page.items if value.event_id == event_id), None)
    if not item:
        raise HTTPException(404, "event not found")
    return item


@router.get("/reviews", response_model=list[ReviewQueueItem])
async def reviews() -> list[ReviewQueueItem]:
    return await dashboard_service().review_queue()


@router.put("/reviews/{review_id:path}", response_model=ReviewDecision)
async def update_review(review_id: str, request: ReviewDecisionInput) -> ReviewDecision:
    queue = await dashboard_service().review_queue()
    if review_id not in {item.review_id for item in queue}:
        raise HTTPException(404, "review item not found")
    return dashboard_service().save_review_decision(review_id, request.status, request.note)


@router.get("/policies", response_model=list[PolicyCoverageItem])
def policies() -> list[PolicyCoverageItem]:
    return dashboard_service().policy_coverage()


@router.get("/policies/{policy_id}", response_model=PolicyCoverageItem)
def policy(policy_id: str = Path(pattern=r"^CG-[A-Z]+-[0-9]{3}$")) -> PolicyCoverageItem:
    item = next((value for value in dashboard_service().policy_coverage() if value.policy.policy_id == policy_id), None)
    if not item:
        raise HTTPException(404, "policy not found")
    return item


@router.put("/policies/{policy_id}", response_model=PolicyCoverageItem)
def update_policy(
    request: PolicyUpdateRequest,
    policy_id: str = Path(pattern=r"^CG-[A-Z]+-[0-9]{3}$"),
) -> PolicyCoverageItem:
    service = dashboard_service()
    coverage = service.policy_coverage()
    if policy_id not in {item.policy.policy_id for item in coverage}:
        raise HTTPException(404, "policy not found")
    enabled = [item.policy.policy_id for item in coverage if item.enabled and item.policy.policy_id != policy_id]
    if request.enabled:
        enabled.append(policy_id)
    service.save_policy_settings(enabled)
    return next(item for item in service.policy_coverage() if item.policy.policy_id == policy_id)


@router.get("/reports", response_model=list[SafeReportMetadata])
def reports() -> list[SafeReportMetadata]:
    return dashboard_service().reports()


@router.get("/reports/{report_type}/{report_id}", response_model=SafeReport)
def report(
    report_type: str = Path(pattern=r"^(audit|comparison)$"),
    report_id: str = Path(pattern=r"^(cg|cmp)-[A-Za-z0-9-]+$", max_length=140),
) -> SafeReport:
    value = dashboard_service().report(report_type, report_id)
    if not value:
        raise HTTPException(404, "report not found")
    return value


@router.post("/demo/chat", response_model=DemoChatResponse)
async def demo_chat(request: DemoChatRequest) -> DemoChatResponse:
    return await dashboard_service().demo_chat(request)
