from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse, PlainTextResponse

from careguard import __version__
from careguard.audit import AuditRunner
from careguard.config import load_policy_pack, load_scenario_pack
from careguard.connectors import DemoConnector, GuardConnector, OpenAICompatibleConnector, RestChatConnector
from careguard.evidence import EvidenceStore
from careguard.models.schemas import (
    AuditRequest, AuditSummary, ComparisonRequest, ComparisonSummary, Target, TargetCreate,
)
from careguard.reports import compare_audits, comparison_markdown, report_markdown
from careguard.reports.generator import build_report
from careguard.security import ensure_authorized_endpoint
from careguard.storage import Database

app = FastAPI(title="CareGuard AI API", version=__version__)


def data_root() -> Path:
    return Path(os.getenv("CAREGUARD_DATA_DIR", Path(__file__).resolve().parents[2] / ".careguard-data"))


@lru_cache
def database() -> Database:
    return Database(data_root() / "careguard.db")


def evidence_store() -> EvidenceStore:
    return EvidenceStore(data_root() / "evidence")


def connector_for(target: Target):
    if target.connector_type == "demo":
        return DemoConnector(target.endpoint)
    if target.connector_type == "guard":
        endpoint = target.endpoint or os.getenv("CAREGUARD_GUARD_URL")
        if endpoint:
            endpoint = f"{endpoint.rstrip('/')}/v1/chat" if not endpoint.rstrip('/').endswith("/v1/chat") else endpoint
        return GuardConnector(data_root() / "guard", endpoint=endpoint)
    if not target.endpoint:
        raise HTTPException(422, "connector endpoint is required")
    ensure_authorized_endpoint(target.endpoint)
    if target.connector_type == "rest":
        return RestChatConnector(target.endpoint)
    return OpenAICompatibleConnector(
        target.endpoint,
        target.model or os.getenv("OPENAI_COMPATIBLE_MODEL", "local-model"),
        os.getenv("OPENAI_COMPATIBLE_API_KEY"),
    )


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "version": __version__, "synthetic_data_only": True}


@app.get("/policies")
def policies() -> dict:
    return load_policy_pack().model_dump(mode="json")


@app.get("/scenarios")
def scenarios() -> dict:
    return load_scenario_pack().model_dump(mode="json")


@app.post("/targets", response_model=Target)
def create_target(target: TargetCreate) -> Target:
    if target.endpoint:
        try:
            ensure_authorized_endpoint(target.endpoint)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
    return database().add_target(target)


@app.get("/targets", response_model=list[Target])
def targets() -> list[Target]:
    return database().list_targets()


@app.post("/audits", response_model=AuditSummary)
async def create_audit(request: AuditRequest) -> AuditSummary:
    target = database().get_target(request.target_id)
    if not target:
        raise HTTPException(404, "target not found")
    try:
        summary = await AuditRunner(connector_for(target), data_root() / "evidence").run(
            request.target_id, request.scenario_ids
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    database().save_audit(summary)
    return summary


@app.get("/audits", response_model=list[AuditSummary])
def audits() -> list[AuditSummary]:
    return database().list_audits()


def _audit_or_404(run_id: str) -> AuditSummary:
    summary = database().get_audit(run_id)
    if not summary:
        raise HTTPException(404, "audit not found")
    return summary


@app.get("/audits/{run_id}", response_model=AuditSummary)
def audit(run_id: str) -> AuditSummary:
    return _audit_or_404(run_id)


@app.get("/audits/{run_id}/findings")
def findings(run_id: str) -> list[dict]:
    _audit_or_404(run_id)
    return [
        record.model_dump(mode="json")
        for record in evidence_store().read(run_id)
        if record.final_result.value != "PASS"
    ]


@app.get("/audits/{run_id}/report")
def report(run_id: str, format: str = Query("markdown", pattern="^(markdown|json)$")):
    summary = _audit_or_404(run_id)
    records = evidence_store().read(run_id)
    if format == "json":
        return JSONResponse(build_report(summary, records))
    return PlainTextResponse(report_markdown(summary, records), media_type="text/markdown")


@app.post("/audits/compare", response_model=ComparisonSummary)
def create_comparison(request: ComparisonRequest) -> ComparisonSummary:
    baseline = _audit_or_404(request.baseline_run_id)
    guarded = _audit_or_404(request.guarded_run_id)
    try:
        summary = compare_audits(
            baseline, evidence_store().read(baseline.run_id),
            guarded, evidence_store().read(guarded.run_id),
            data_root() / "reports" / "comparisons",
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    database().save_comparison(summary)
    return summary


@app.get("/comparisons", response_model=list[ComparisonSummary])
def comparisons() -> list[ComparisonSummary]:
    return database().list_comparisons()


def _comparison_or_404(comparison_id: str) -> ComparisonSummary:
    summary = database().get_comparison(comparison_id)
    if not summary:
        raise HTTPException(404, "comparison not found")
    return summary


@app.get("/comparisons/{comparison_id}", response_model=ComparisonSummary)
def comparison(comparison_id: str) -> ComparisonSummary:
    return _comparison_or_404(comparison_id)


@app.get("/comparisons/{comparison_id}/report")
def comparison_report(comparison_id: str, format: str = Query("markdown", pattern="^(markdown|json)$")):
    summary = _comparison_or_404(comparison_id)
    if format == "json":
        return JSONResponse(summary.model_dump(mode="json"))
    return PlainTextResponse(comparison_markdown(summary), media_type="text/markdown")
