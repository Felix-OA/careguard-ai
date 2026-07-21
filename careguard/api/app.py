from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse, PlainTextResponse

from careguard import __version__
from careguard.audit import AuditRunner
from careguard.config import load_policy_pack, load_scenario_pack
from careguard.connectors import DemoConnector, OpenAICompatibleConnector, RestChatConnector
from careguard.evidence import EvidenceStore
from careguard.models.schemas import AuditRequest, AuditSummary, Target, TargetCreate
from careguard.reports import report_markdown
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
        ensure_authorized_endpoint(target.endpoint)
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

