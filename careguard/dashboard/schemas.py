from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from careguard.models.schemas import (
    EvaluatorResult, Policy, Result, SourceMetadata, Target, ToolCall,
)


class CredentialStatus(StrEnum):
    NOT_CONFIGURED = "Not configured"
    CONFIGURED = "Configured server-side"
    UNAVAILABLE = "Unavailable"


class IntegrationCapability(StrEnum):
    PROXY_ONLY = "proxy_only"
    DEEP_RETRIEVAL = "deep_retrieval"
    TOOL_CONTROL = "tool_control"


class ReviewStatus(StrEnum):
    UNREVIEWED = "UNREVIEWED"
    CONFIRMED_SAFE = "CONFIRMED_SAFE"
    CONFIRMED_FINDING = "CONFIRMED_FINDING"
    NEEDS_MORE_CONTEXT = "NEEDS_MORE_CONTEXT"


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class SafeAuditSummary(BaseModel):
    run_id: str
    target_id: str
    started_at: datetime
    completed_at: datetime
    counts: dict[str, int]


class SafeComparisonSummary(BaseModel):
    comparison_id: str
    created_at: datetime
    baseline_run_id: str
    guarded_run_id: str
    baseline_target_id: str
    guarded_target_id: str
    identical_scope: bool
    scenario_ids: list[str]
    scope_validation: dict[str, Any] = Field(default_factory=dict)
    policy_configuration: dict[str, Any] = Field(default_factory=dict)
    baseline_metrics: dict[str, Any]
    guarded_metrics: dict[str, Any]
    security_improvements: list[str]
    unchanged_risks: list[str]
    regressions: list[str]
    false_positives: list[str]
    utility_tradeoffs: list[str]
    scenario_results: list[dict[str, Any]] = Field(default_factory=list)
    manual_review_notes: list[str]


class OrganizationProfile(BaseModel):
    organization_name: str = Field(min_length=1, max_length=120)
    product_name: str = Field(min_length=1, max_length=120)
    environment_label: str = Field(min_length=1, max_length=80)
    healthcare_use_case: str = Field(min_length=1, max_length=300)
    technical_contact_name: str | None = Field(default=None, max_length=120)
    synthetic_data_confirmed: bool
    updated_at: datetime


class OrganizationProfileInput(BaseModel):
    organization_name: str = Field(min_length=1, max_length=120)
    product_name: str = Field(min_length=1, max_length=120)
    environment_label: str = Field(min_length=1, max_length=80)
    healthcare_use_case: str = Field(min_length=1, max_length=300)
    technical_contact_name: str | None = Field(default=None, max_length=120)
    synthetic_data_confirmed: bool

    @model_validator(mode="after")
    def require_synthetic_confirmation(self) -> "OrganizationProfileInput":
        if not self.synthetic_data_confirmed:
            raise ValueError("synthetic or explicitly authorized test-data confirmation is required")
        return self


class TargetConfigurationInput(BaseModel):
    integration_capability: IntegrationCapability = IntegrationCapability.PROXY_ONLY
    chat_path: str = Field(default="/chat", min_length=1, max_length=160, pattern=r"^/[A-Za-z0-9_./{}-]*$")
    request_message_field: str = Field(default="user_message", min_length=1, max_length=80, pattern=r"^[A-Za-z0-9_.-]+$")
    response_answer_field: str = Field(default="answer", min_length=1, max_length=80, pattern=r"^[A-Za-z0-9_.-]+$")
    conversation_field: str | None = Field(default="conversation_id", max_length=80, pattern=r"^[A-Za-z0-9_.-]+$")
    retrieval_metadata_field: str | None = Field(default="retrieved_sources", max_length=80, pattern=r"^[A-Za-z0-9_.-]+$")
    timeout_seconds: int = Field(default=15, ge=1, le=60)
    provider_label: str | None = Field(default=None, max_length=120)
    credential_env_reference: str | None = Field(default=None, max_length=80, pattern=r"^[A-Z][A-Z0-9_]{2,79}$")
    enabled: bool = True

    @field_validator("credential_env_reference")
    @classmethod
    def allow_known_credential_reference(cls, value: str | None) -> str | None:
        if value not in {None, "OPENAI_COMPATIBLE_API_KEY"}:
            raise ValueError("credential reference is not approved for the local dashboard")
        return value


class TargetConfiguration(BaseModel):
    integration_capability: IntegrationCapability
    chat_path: str
    request_message_field: str
    response_answer_field: str
    conversation_field: str | None
    retrieval_metadata_field: str | None
    timeout_seconds: int
    provider_label: str | None
    enabled: bool
    credential_status: CredentialStatus
    updated_at: datetime


class DashboardTarget(BaseModel):
    target: Target
    configuration: TargetConfiguration
    recent_audits: list[SafeAuditSummary] = Field(default_factory=list)
    guard_mode: str | None = None


class OnboardingTargetInput(BaseModel):
    target_id: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9._-]+$")
    name: str = Field(min_length=1, max_length=160)
    connector_type: Literal["demo", "guard", "rest", "openai_compatible"]
    endpoint: str | None = Field(default=None, max_length=500)
    model: str | None = Field(default=None, max_length=160)
    authorized_target_confirmed: bool = False
    configuration: TargetConfigurationInput

    @model_validator(mode="after")
    def require_target_authorization(self) -> "OnboardingTargetInput":
        if self.connector_type != "demo" and not self.authorized_target_confirmed:
            raise ValueError("explicit authorized-target confirmation is required")
        return self


class TargetUpdateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    endpoint: str | None = Field(default=None, max_length=500)
    model: str | None = Field(default=None, max_length=160)
    authorized_target_confirmed: bool = False
    configuration: TargetConfigurationInput


class OnboardingRequest(BaseModel):
    organization: OrganizationProfileInput
    target: OnboardingTargetInput
    enabled_policy_ids: list[str] | None = Field(default=None, max_length=15)


class OnboardingResponse(BaseModel):
    organization: OrganizationProfile
    target: DashboardTarget
    policy_configuration_version: str
    next_actions: list[str]


class ConnectionTestResponse(BaseModel):
    target_id: str
    status: Literal["reachable", "unavailable", "disabled"]
    detail: str
    latency_ms: float | None = None


class AuditJobRequest(BaseModel):
    target_id: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9._-]+$")
    scenario_ids: list[str] | None = Field(default=None, max_length=100)
    policy_ids: list[str] | None = Field(default=None, max_length=15)
    run_label: str | None = Field(default=None, max_length=120)
    notes: str | None = Field(default=None, max_length=500)


class AuditJob(BaseModel):
    job_id: str
    run_id: str | None = None
    status: JobStatus
    submitted_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    target_id: str
    progress_count: int = 0
    total_scenarios: int
    policy_configuration_version: str = "policy-pack-1.0"
    run_label: str | None = None
    notes: str | None = None
    error: str | None = None


class ReviewDecisionInput(BaseModel):
    status: ReviewStatus
    note: str | None = Field(default=None, max_length=500)


class ReviewDecision(BaseModel):
    review_id: str
    status: ReviewStatus
    note: str | None = None
    reviewed_at: datetime | None = None


class ReviewQueueItem(BaseModel):
    review_id: str
    source_type: Literal["audit", "guard_event", "agentic"]
    source_id: str
    scenario_id: str | None = None
    campaign_id: str | None = None
    objective_run_id: str | None = None
    objective_id: str | None = None
    review_reason: str
    policy_categories: list[str]
    automated_dimensions: list[EvaluatorResult] = Field(default_factory=list)
    agentic_signal_summary: dict[str, int] = Field(default_factory=dict)
    evidence_summary: str
    target_id: str
    timestamp: datetime
    automated_result: str
    is_stale: bool = False
    superseded_by: str | None = None
    decision: ReviewDecision


class SafeFinding(BaseModel):
    scenario_id: str
    title: str
    category: str
    result: Result
    severity: str
    expected_behavior: str
    observed_behavior: str
    policies: list[str]
    evidence_flags: dict[str, bool]
    retrieved_sources: list[SourceMetadata]
    proposed_tools: list[ToolCall]
    blocked_tools: list[ToolCall]
    failed_tools: list[ToolCall]
    executed_tools: list[ToolCall]
    evaluator_results: list[EvaluatorResult]
    human_review_reason: str | None
    guard_final_decision: str | None
    timestamp: datetime


class AuditDetail(BaseModel):
    summary: SafeAuditSummary
    scenario_version: str | None
    policy_pack_version: str | None
    product_version: str | None
    guard_mode: str | None
    severity_breakdown: dict[str, int]
    category_breakdown: dict[str, int]
    retrieval_metrics: dict[str, int]
    tool_metrics: dict[str, int]
    findings: list[SafeFinding]
    limitations: list[str]


class SafeGuardEvent(BaseModel):
    event_id: str
    timestamp: datetime
    conversation_id: str
    target_id: str
    guard_mode: str
    guard_config_version: str
    request_summary: str
    final_response: str
    final_decision: str
    would_enforce_decision: str
    reason_codes: list[str]
    triggered_policies: list[str]
    raw_retrieval_metadata: list[SourceMetadata]
    rejected_retrieval_metadata: list[SourceMetadata]
    refill_context_metadata: list[SourceMetadata]
    admitted_context_metadata: list[SourceMetadata]
    redaction_categories: list[str]
    proposed_tools: list[ToolCall]
    authorized_tools: list[ToolCall]
    blocked_tools: list[ToolCall]
    failed_tools: list[ToolCall]
    executed_tools: list[ToolCall]
    confirmation_status: str
    human_review_required: bool
    error: str | None = None


class PaginatedEvents(BaseModel):
    items: list[SafeGuardEvent]
    page: int
    page_size: int
    total: int
    source_status: Literal["available", "unavailable"] = "available"
    source_detail: str | None = None


class PolicyCoverageItem(BaseModel):
    policy: Policy
    enabled: bool
    mapped_reason_codes: list[str]
    scenario_ids: list[str]
    control_coverage: list[str]
    configuration_version: str
    configuration_updated_at: datetime | None


class PolicyUpdateRequest(BaseModel):
    enabled: bool


class SafeReportMetadata(BaseModel):
    report_id: str
    report_type: Literal["audit", "comparison"]
    title: str
    created_at: datetime
    target_id: str | None = None
    result_counts: dict[str, int] = Field(default_factory=dict)


class SafeReport(BaseModel):
    metadata: SafeReportMetadata
    markdown: str
    json_content: dict[str, Any]
    boundaries: list[str]


class ServiceHealth(BaseModel):
    service: str
    status: Literal["healthy", "degraded", "unavailable"]
    version: str | None = None
    detail: str


class SystemStatus(BaseModel):
    services: list[ServiceHealth]
    guard_mode: str | None
    policy_pack_version: str
    scenario_version: str
    product_version: str
    latest_successful_audit: SafeAuditSummary | None
    latest_comparison: SafeComparisonSummary | None


class DashboardSummary(BaseModel):
    generated_at: datetime
    disclaimer: str
    latest_baseline_audit: SafeAuditSummary | None
    latest_guarded_audit: SafeAuditSummary | None
    latest_comparison: SafeComparisonSummary | None
    guard_mode: str | None
    active_target_count: int
    result_counts: dict[str, int]
    unresolved_review_count: int
    event_decisions: dict[str, int]
    recent_events: list[SafeGuardEvent]
    finding_severity: dict[str, int]
    finding_categories: dict[str, int]
    retrieval_metrics: dict[str, int]
    tool_metrics: dict[str, int]
    recent_audits: list[SafeAuditSummary]
    services: list[ServiceHealth]


class DemoChatRequest(BaseModel):
    path: Literal["baseline", "guarded"]
    prompt_id: Literal["benign", "cross_patient", "fake_authority", "untrusted", "appointment", "emergency", "custom"]
    custom_message: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def require_custom_message(self) -> "DemoChatRequest":
        if self.prompt_id == "custom" and not self.custom_message:
            raise ValueError("custom_message is required for the custom synthetic prompt")
        return self


class DemoChatResponse(BaseModel):
    path: str
    prompt: str
    answer: str
    decision: str | None
    reason_codes: list[str]
    triggered_policies: list[str]
    retrieval_counts: dict[str, int]
    proposed_tools: list[ToolCall]
    blocked_tools: list[ToolCall]
    executed_tools: list[ToolCall]
    redaction_count: int
    human_review_required: bool
