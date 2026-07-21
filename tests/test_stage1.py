from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from careguard.api import app as api_module
from careguard.api.app import app
from careguard.audit import AuditRunner
from careguard.audit.evaluators import evaluate
from careguard.config import load_policy_pack, load_scenario_pack, validate_configuration
from careguard.connectors import DemoConnector
from careguard.evidence import EvidenceStore, sanitize_for_evidence
from careguard.models.schemas import (
    AuditSummary, ChatTurn, EvidenceRecord, NormalizedRequest, Result,
)
from careguard.reports import report_json, report_markdown
from demo_health_agent.engine import respond


def test_policy_and_scenario_validation():
    policies, scenarios = validate_configuration()
    assert len(policies.policies) >= 14
    assert len(scenarios.scenarios) >= 18
    assert all(s.applicable_policy_ids for s in scenarios.scenarios)


def test_connector_normalization():
    request = NormalizedRequest(
        target_id="demo", conversation_id="test", user_message="What are the clinic hours?"
    )
    response = asyncio.run(DemoConnector().send(request))
    assert response.target_id == "demo"
    assert response.provider == "deterministic-local"
    assert response.retrieved_sources[0].trust_level == "trusted_operational"


def test_deterministic_evaluators_detect_canary():
    scenario = next(item for item in load_scenario_pack().scenarios if item.scenario_id == "CG-S006")
    response = respond(NormalizedRequest(target_id="demo", conversation_id="x", user_message=scenario.conversation_turns[0].user))
    results = evaluate(response, scenario)
    assert any(item.evaluator_id == "exact_canary_detection" and item.result == Result.FAIL for item in results)


def test_evidence_serialization_and_secret_redaction(tmp_path):
    assert sanitize_for_evidence({"Authorization": "Bearer placeholder", "error": "Bearer placeholder"}) == {
        "Authorization": "[REDACTED]", "error": "[REDACTED]"
    }
    record = EvidenceRecord(
        run_id="run", timestamp=datetime.now(timezone.utc), product_version="0.1.0",
        scenario_version="1", policy_pack_version="1", scenario_id="CG-S000", target_id="demo",
        provider="local", model="test", conversation_turns=[ChatTurn(role="user", content="safe")],
        expected_behavior="safe", raw_answer="safe", retrieved_sources=[], proposed_tool_calls=[],
        executed_tool_calls=[], evaluator_results=[], final_result=Result.PASS, severity="low",
        likelihood="unlikely", impact="low", evidence_flags={}, latency_ms=1,
    )
    store = EvidenceStore(tmp_path)
    path = store.write(record)
    assert json.loads(path.read_text())["scenario_id"] == "CG-S000"
    assert store.read("run")[0].final_result == Result.PASS


def test_report_generation():
    summary = AuditSummary(
        run_id="run", target_id="demo", started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc), counts={"PASS": 0, "PARTIAL": 0, "FAIL": 0, "REVIEW": 0},
        evidence_path="safe.jsonl",
    )
    assert "not a compliance certification" in report_markdown(summary, []).lower()
    assert json.loads(report_json(summary, []))["target"]["target_id"] == "demo"


def test_api_health_and_catalog(tmp_path, monkeypatch):
    monkeypatch.setenv("CAREGUARD_DATA_DIR", str(tmp_path))
    api_module.database.cache_clear()
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        assert len(client.get("/scenarios").json()["scenarios"]) >= 18
        assert client.get("/targets").json()[0]["target_id"] == "demo"


def test_local_demo_audit_end_to_end(tmp_path):
    runner = AuditRunner(DemoConnector(), tmp_path / "evidence")
    summary = asyncio.run(runner.run("demo", ["CG-S006", "CG-S010", "CG-S018"]))
    records = EvidenceStore(tmp_path / "evidence").read(summary.run_id)
    assert len(records) == 3
    assert summary.counts["FAIL"] >= 1
    assert summary.counts["PASS"] >= 1
    assert all(record.target_id == "demo" for record in records)
