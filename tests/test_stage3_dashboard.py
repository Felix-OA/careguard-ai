from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone

import pytest

from fastapi.testclient import TestClient

from careguard.api import app as api_module
from careguard.api.app import app
from careguard.dashboard.routes import dashboard_service
from careguard_guard.config import load_guard_config
from careguard_guard.pipeline import GuardPipeline
from careguard_guard.models import GuardChatRequest


def reset_state(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("CAREGUARD_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("CAREGUARD_GUARD_URL", raising=False)
    monkeypatch.delenv("CAREGUARD_DEMO_URL", raising=False)
    api_module.database.cache_clear()
    dashboard_service.cache_clear()


def onboarding_payload(target_id: str = "company-demo") -> dict:
    return {
        "organization": {
            "organization_name": "Northstar Digital Health",
            "product_name": "Northstar Support",
            "environment_label": "Local synthetic evaluation",
            "healthcare_use_case": "Synthetic patient-support testing",
            "technical_contact_name": "Synthetic Operator",
            "synthetic_data_confirmed": True,
        },
        "target": {
            "target_id": target_id,
            "name": "Company synthetic demo",
            "connector_type": "demo",
            "endpoint": None,
            "model": None,
            "configuration": {
                "integration_capability": "deep_retrieval",
                "chat_path": "/chat",
                "request_message_field": "user_message",
                "response_answer_field": "answer",
                "conversation_field": "conversation_id",
                "retrieval_metadata_field": "retrieved_sources",
                "timeout_seconds": 15,
                "provider_label": "deterministic-local",
                "credential_env_reference": "OPENAI_COMPATIBLE_API_KEY",
                "enabled": True,
            },
        },
        "enabled_policy_ids": [],
    }


def test_onboarding_is_persistent_and_never_returns_secret(tmp_path, monkeypatch):
    reset_state(tmp_path, monkeypatch)
    monkeypatch.setenv("OPENAI_COMPATIBLE_API_KEY", "sk-synthetic-dashboard-secret-value")
    with TestClient(app) as client:
        response = client.post("/dashboard/onboarding", json=onboarding_payload())
        assert response.status_code == 200
        body = response.json()
        serialized = response.text
        assert body["target"]["configuration"]["credential_status"] == "Configured server-side"
        assert "synthetic-dashboard-secret" not in serialized
        assert "OPENAI_COMPATIBLE_API_KEY" not in serialized
        assert client.get("/dashboard/onboarding").json()["organization_name"] == "Northstar Digital Health"


def test_target_update_delete_and_built_in_protection(tmp_path, monkeypatch):
    reset_state(tmp_path, monkeypatch)
    with TestClient(app) as client:
        assert client.post("/dashboard/onboarding", json=onboarding_payload("delete-me")).status_code == 200
        target = client.get("/dashboard/targets/delete-me").json()
        update = client.put("/dashboard/targets/delete-me", json={
            "name": "Updated local demo", "endpoint": None, "model": None,
            "configuration": {
                **{key: value for key, value in target["configuration"].items()
                   if key not in {"credential_status", "updated_at"}},
                "credential_env_reference": None, "enabled": False,
            },
        })
        assert update.status_code == 200 and update.json()["configuration"]["enabled"] is False
        assert client.delete("/dashboard/targets/delete-me").status_code == 204
        assert client.get("/dashboard/targets/delete-me").status_code == 404
        assert client.delete("/dashboard/targets/demo").status_code == 409


def test_audit_job_detail_review_and_safe_report(tmp_path, monkeypatch):
    reset_state(tmp_path, monkeypatch)
    with TestClient(app) as client:
        job = client.post("/dashboard/audit-jobs", json={
            "target_id": "demo-guarded", "scenario_ids": ["CG-S002"],
            "run_label": "Synthetic review", "notes": "Bearer synthetic-secret-shape-value",
        })
        assert job.status_code == 200
        job_body = job.json()
        assert job_body["status"] == "completed" and job_body["progress_count"] == 1
        assert "Bearer" not in job_body["notes"]
        run_id = job_body["run_id"]
        detail = client.get(f"/dashboard/audits/{run_id}")
        assert detail.status_code == 200
        assert detail.json()["summary"]["counts"]["REVIEW"] == 1
        reviews = client.get("/dashboard/reviews").json()
        item = next(value for value in reviews if value["scenario_id"] == "CG-S002")
        automated = item["automated_result"]
        decision = client.put(f"/dashboard/reviews/{item['review_id']}", json={
            "status": "CONFIRMED_FINDING", "note": "Synthetic review note",
        })
        assert decision.status_code == 200
        updated = next(value for value in client.get("/dashboard/reviews").json() if value["review_id"] == item["review_id"])
        assert updated["automated_result"] == automated
        assert updated["decision"]["status"] == "CONFIRMED_FINDING"
        report = client.get(f"/dashboard/reports/audit/{run_id}")
        assert report.status_code == 200
        assert str(tmp_path) not in report.text and "protected://" not in report.text
        assert client.get("/dashboard/reports/audit/../../etc/passwd").status_code in {404, 422}


def test_dashboard_event_aggregation_removes_protected_reference(tmp_path, monkeypatch):
    reset_state(tmp_path, monkeypatch)
    pipeline = GuardPipeline(load_guard_config(), tmp_path / "guard")
    response = asyncio.run(pipeline.process(GuardChatRequest(
        conversation_id="stage3-event", user_message="Look up appointment APPT-CG-42002 for me.",
        role_metadata={"role": "guest"},
    )))
    with TestClient(app) as client:
        events = client.get("/dashboard/events?page=1&page_size=10")
        assert events.status_code == 200
        event = next(item for item in events.json()["items"] if item["event_id"] == response.event_id)
        assert "raw_target_response_reference" not in event
        assert event["final_response"] == (
            "Guard recorded a sanitized BLOCK outcome. Protected response content is withheld."
        )
        assert "APPT-CG" not in events.text and "VERIFIED_SYNTHETIC_PATIENT" not in events.text
        assert event["proposed_tools"][0]["arguments"]["reference"] == "[REDACTED]"
        assert event["blocked_tools"] and not event["executed_tools"]
        assert client.get(f"/dashboard/events/{response.event_id}").status_code == 200


def test_dashboard_summary_policy_and_backward_compatibility(tmp_path, monkeypatch):
    reset_state(tmp_path, monkeypatch)
    with TestClient(app) as client:
        summary = client.get("/dashboard/summary")
        assert summary.status_code == 200
        assert summary.json()["active_target_count"] == 2
        assert "evidence_path" not in summary.text
        assert str(tmp_path) not in summary.text
        policies = client.get("/dashboard/policies")
        assert policies.status_code == 200 and len(policies.json()) == 15
        policy_id = policies.json()[0]["policy"]["policy_id"]
        disabled = client.put(f"/dashboard/policies/{policy_id}", json={"enabled": False})
        assert disabled.status_code == 200 and disabled.json()["enabled"] is False
        assert client.get("/health").status_code == 200
        assert client.get("/policies").status_code == 200
        assert client.get("/scenarios").status_code == 200
        assert client.post("/audits", json={"target_id": "demo", "scenario_ids": ["CG-S018"]}).status_code == 200


def test_dashboard_comparisons_are_path_free(tmp_path, monkeypatch):
    reset_state(tmp_path, monkeypatch)
    with TestClient(app) as client:
        baseline = client.post("/dashboard/audit-jobs", json={
            "target_id": "demo", "scenario_ids": ["CG-S001", "CG-S002"],
        }).json()
        guarded = client.post("/dashboard/audit-jobs", json={
            "target_id": "demo-guarded", "scenario_ids": ["CG-S001", "CG-S002"],
        }).json()
        response = client.post("/dashboard/comparisons", json={
            "baseline_run_id": baseline["run_id"], "guarded_run_id": guarded["run_id"],
        })
        assert response.status_code == 200
        assert "report_path" not in response.text
        assert str(tmp_path) not in response.text
        review_row = next(item for item in response.json()["scenario_results"] if item["guarded_result"] == "REVIEW")
        assert review_row["security_change"] == "Review required — no directional claim"
        comparison_id = response.json()["comparison_id"]
        assert client.get(f"/dashboard/comparisons/{comparison_id}").json() == response.json()


def test_target_update_preserves_server_secret_reference_when_omitted(tmp_path, monkeypatch):
    reset_state(tmp_path, monkeypatch)
    monkeypatch.setenv("OPENAI_COMPATIBLE_API_KEY", "synthetic-private-value")
    with TestClient(app) as client:
        created = client.post("/dashboard/onboarding", json=onboarding_payload("preserve-reference")).json()["target"]
        configuration = created["configuration"]
        configuration.pop("credential_status")
        configuration.pop("updated_at")
        response = client.put("/dashboard/targets/preserve-reference", json={
            "name": "Updated", "endpoint": None, "model": None,
            "configuration": {**configuration, "enabled": False},
        })
        assert response.status_code == 200
        assert response.json()["configuration"]["credential_status"] == "Configured server-side"
        assert "synthetic-private-value" not in response.text


def test_connection_error_and_pagination_are_bounded_and_sanitized(tmp_path, monkeypatch):
    reset_state(tmp_path, monkeypatch)
    with TestClient(app) as client:
        payload = onboarding_payload("offline-local")
        payload["target"].update({
            "connector_type": "rest",
            "endpoint": "http://127.0.0.1:8001",
            "authorized_target_confirmed": True,
        })
        assert client.post("/dashboard/onboarding", json=payload).status_code == 200
        result = client.post("/dashboard/targets/offline-local/test")
        assert result.status_code == 200
        assert result.json()["status"] == "unavailable"
        assert "Traceback" not in result.text and "127.0.0.1:8001" not in result.text
        assert client.get("/dashboard/events?page_size=101").status_code == 422
        assert client.get("/dashboard/events?page=0").status_code == 422
        assert client.get("/dashboard/events?page=1&page_size=1").status_code == 200


def test_dashboard_has_no_wildcard_cors_or_html_report_execution_boundary(tmp_path, monkeypatch):
    reset_state(tmp_path, monkeypatch)
    with TestClient(app) as client:
        preflight = client.options("/dashboard/summary", headers={
            "Origin": "https://public.example", "Access-Control-Request-Method": "GET",
        })
        assert preflight.headers.get("access-control-allow-origin") != "*"
        job = client.post("/dashboard/audit-jobs", json={
            "target_id": "demo", "scenario_ids": ["CG-S018"],
        }).json()
        report = client.get(f"/dashboard/reports/audit/{job['run_id']}")
        assert report.status_code == 200
        assert report.headers["content-type"].startswith("application/json")


def test_onboarding_rejects_public_endpoint_and_missing_synthetic_confirmation(tmp_path, monkeypatch):
    reset_state(tmp_path, monkeypatch)
    payload = onboarding_payload("unsafe")
    payload["target"].update({"connector_type": "rest", "endpoint": "https://public.example/chat"})
    payload["target"]["authorized_target_confirmed"] = True
    with TestClient(app) as client:
        assert client.post("/dashboard/onboarding", json=payload).status_code == 422
        payload = onboarding_payload("not-confirmed")
        payload["organization"]["synthetic_data_confirmed"] = False
        assert client.post("/dashboard/onboarding", json=payload).status_code == 422


@pytest.mark.parametrize("endpoint", [
    "file:///tmp/target", "ftp://127.0.0.1:8001", "gopher://127.0.0.1:8001",
    "http://user:password@127.0.0.1:8001", "http://127.0.0.1:8001?token=synthetic",
    "http://127.0.0.1:8001/#fragment", "http://127.0.0.1:9000",
    "https://127.0.0.1:8001", "http://127.0.0.1:8001/internal/retrieve",
])
def test_onboarding_strictly_rejects_ssrf_shapes(endpoint, tmp_path, monkeypatch):
    reset_state(tmp_path, monkeypatch)
    payload = onboarding_payload("ssrf-shape")
    payload["target"].update({
        "connector_type": "rest", "endpoint": endpoint, "authorized_target_confirmed": True,
    })
    with TestClient(app) as client:
        response = client.post("/dashboard/onboarding", json=payload)
        assert response.status_code == 422
        assert "Traceback" not in response.text and str(tmp_path) not in response.text


def test_external_target_requires_explicit_authorization_and_known_credential_reference(tmp_path, monkeypatch):
    reset_state(tmp_path, monkeypatch)
    payload = onboarding_payload("authorized-local")
    payload["target"].update({"connector_type": "rest", "endpoint": "http://127.0.0.1:8001"})
    with TestClient(app) as client:
        assert client.post("/dashboard/onboarding", json=payload).status_code == 422
        payload["target"]["authorized_target_confirmed"] = True
        payload["target"]["configuration"]["credential_env_reference"] = "UNAPPROVED_SECRET_NAME"
        response = client.post("/dashboard/onboarding", json=payload)
        assert response.status_code == 422
        assert "UNAPPROVED_SECRET_NAME" not in client.get("/dashboard/targets").text


def test_summary_uses_only_current_matching_comparison_metrics(tmp_path, monkeypatch):
    reset_state(tmp_path, monkeypatch)
    with TestClient(app) as client:
        baseline = client.post("/dashboard/audit-jobs", json={
            "target_id": "demo", "scenario_ids": ["CG-S001", "CG-S002"],
        }).json()
        guarded = client.post("/dashboard/audit-jobs", json={
            "target_id": "demo-guarded", "scenario_ids": ["CG-S001", "CG-S002"],
        }).json()
        assert client.post("/dashboard/comparisons", json={
            "baseline_run_id": baseline["run_id"], "guarded_run_id": guarded["run_id"],
        }).status_code == 200
        latest = client.post("/dashboard/audit-jobs", json={
            "target_id": "demo-guarded", "scenario_ids": ["CG-S018"],
        }).json()
        detail = client.get(f"/dashboard/audits/{latest['run_id']}").json()
        summary = client.get("/dashboard/summary").json()
        assert summary["latest_guarded_audit"]["run_id"] == latest["run_id"]
        assert summary["latest_comparison"] is None
        assert summary["result_counts"] == detail["summary"]["counts"]
        assert summary["retrieval_metrics"] == detail["retrieval_metrics"]
        assert summary["tool_metrics"] == detail["tool_metrics"]


def test_repeated_review_runs_mark_history_without_inflating_current_count(tmp_path, monkeypatch):
    reset_state(tmp_path, monkeypatch)
    with TestClient(app) as client:
        runs = [client.post("/dashboard/audit-jobs", json={
            "target_id": "demo-guarded", "scenario_ids": ["CG-S002"],
        }).json()["run_id"] for _ in range(2)]
        audit_items = [item for item in client.get("/dashboard/reviews").json()
                       if item["source_type"] == "audit" and item["scenario_id"] == "CG-S002"]
        assert len(audit_items) == 2
        assert sum(not item["is_stale"] for item in audit_items) == 1
        stale = next(item for item in audit_items if item["is_stale"])
        assert stale["superseded_by"] == runs[-1]
        assert client.get("/dashboard/summary").json()["unresolved_review_count"] == 1


def test_all_guarded_catalogue_review_reasons_are_preserved(tmp_path, monkeypatch):
    reset_state(tmp_path, monkeypatch)
    expected = {
        item.scenario_id: item.human_review_reason
        for item in api_module.load_scenario_pack().scenarios if item.human_review_required
    }
    assert len(expected) == 7
    with TestClient(app) as client:
        run = client.post("/dashboard/audit-jobs", json={"target_id": "demo-guarded"}).json()
        actual = {
            item["scenario_id"]: item["review_reason"]
            for item in client.get("/dashboard/reviews").json()
            if item["source_type"] == "audit" and item["source_id"] == run["run_id"]
        }
        assert actual == expected


def test_policy_versions_increment_apply_to_future_evidence_and_prevent_mismatch(tmp_path, monkeypatch):
    reset_state(tmp_path, monkeypatch)
    with TestClient(app) as client:
        policies = client.get("/dashboard/policies").json()
        policy_id = policies[0]["policy"]["policy_id"]
        scenarios = client.get("/scenarios").json()["scenarios"]
        scenario_id = next(
            item["scenario_id"] for item in scenarios
            if item["enabled"] and policy_id not in item["applicable_policy_ids"]
        )
        baseline = client.post("/dashboard/audit-jobs", json={
            "target_id": "demo", "scenario_ids": [scenario_id],
        }).json()
        baseline_version = client.get(f"/dashboard/audits/{baseline['run_id']}").json()["policy_pack_version"]
        first = client.put(f"/dashboard/policies/{policy_id}", json={"enabled": False}).json()
        guarded = client.post("/dashboard/audit-jobs", json={
            "target_id": "demo-guarded", "scenario_ids": [scenario_id],
        }).json()
        guarded_version = client.get(f"/dashboard/audits/{guarded['run_id']}").json()["policy_pack_version"]
        second = client.put(f"/dashboard/policies/{policy_id}", json={"enabled": True}).json()
        assert first["configuration_version"] != second["configuration_version"]
        assert baseline_version != guarded_version
        assert client.get(f"/dashboard/audits/{baseline['run_id']}").json()["policy_pack_version"] == baseline_version
        mismatch = client.post("/dashboard/comparisons", json={
            "baseline_run_id": baseline["run_id"], "guarded_run_id": guarded["run_id"],
        })
        assert mismatch.status_code == 422
        assert "versions are not equivalent" in mismatch.json()["detail"]


def test_dashboard_report_excludes_raw_response_and_markdown_payloads(tmp_path, monkeypatch):
    reset_state(tmp_path, monkeypatch)
    with TestClient(app) as client:
        job = client.post("/dashboard/audit-jobs", json={
            "target_id": "demo-guarded", "scenario_ids": ["CG-S002"],
        }).json()
        report = client.get(f"/dashboard/reports/audit/{job['run_id']}")
        assert report.status_code == 200
        assert "raw_answer" not in report.text and '"answer"' not in report.text
        safe_json = json.dumps(report.json()["json_content"])
        assert "conversation_turns" not in safe_json and '"arguments"' not in safe_json
        assert "protected://" not in report.text and str(tmp_path) not in report.text
        for traversal in ("%2e%2e%2fetc%2fpasswd", "%252e%252e%252fetc%252fpasswd"):
            assert client.get(f"/dashboard/reports/audit/{traversal}").status_code in {404, 422}


def test_audit_job_failure_is_terminal_and_sanitized(tmp_path, monkeypatch):
    reset_state(tmp_path, monkeypatch)

    class FailingConnector:
        async def send(self, request):
            raise RuntimeError("Bearer synthetic-secret /Users/tbt/protected")

    monkeypatch.setattr(api_module, "connector_for", lambda *args, **kwargs: FailingConnector())
    with TestClient(app) as client:
        response = client.post("/dashboard/audit-jobs", json={
            "target_id": "demo", "scenario_ids": ["CG-S018"],
        })
        assert response.status_code == 200
        job = response.json()
        assert job["status"] == "failed" and job["completed_at"]
        assert job["run_id"] is None and job["error"] == "Audit job failed: RuntimeError"
        assert "synthetic-secret" not in response.text and "/Users/" not in response.text
        assert client.get(f"/dashboard/audit-jobs/{job['job_id']}").json()["status"] == "failed"


def test_interrupted_jobs_recover_as_failed(tmp_path, monkeypatch):
    reset_state(tmp_path, monkeypatch)
    submitted = datetime.now(timezone.utc)
    job_id = "job-" + "a" * 32
    api_module.database().save_audit_job(job_id, submitted, json.dumps({
        "job_id": job_id, "run_id": None, "status": "running",
        "submitted_at": submitted.isoformat(), "started_at": submitted.isoformat(),
        "completed_at": None, "target_id": "demo", "progress_count": 0,
        "total_scenarios": 1,
        "run_label": None, "notes": None, "error": None,
    }))
    dashboard_service.cache_clear()
    with TestClient(app) as client:
        recovered = client.get(f"/dashboard/audit-jobs/{job_id}").json()
        assert recovered["status"] == "failed" and recovered["completed_at"]
        assert recovered["error"] == "Audit job was interrupted before completion."


def test_event_degradation_and_filter_validation_are_explicit(tmp_path, monkeypatch):
    reset_state(tmp_path, monkeypatch)

    async def unavailable(limit=1000):
        raise RuntimeError("private upstream detail")

    service = dashboard_service()
    monkeypatch.setattr(service, "_guard_events", unavailable)
    with TestClient(app) as client:
        events = client.get("/dashboard/events")
        assert events.status_code == 200
        assert events.json()["source_status"] == "unavailable"
        assert "private upstream detail" not in events.text
        assert client.get("/dashboard/events/evt-" + "a" * 32).status_code == 503
        assert client.get("/dashboard/events?decision=NOT_A_DECISION").status_code == 422
        assert client.get("/dashboard/events?guard_mode=unsafe").status_code == 422
        assert client.get("/dashboard/events?policy_id=not-a-policy").status_code == 422
        assert client.get("/dashboard/events?date_from=2026-07-23T00:00:00Z&date_to=2026-07-22T00:00:00Z").status_code == 422


def test_deleted_target_history_does_not_become_current_dashboard_posture(tmp_path, monkeypatch):
    reset_state(tmp_path, monkeypatch)
    with TestClient(app) as client:
        assert client.post("/targets", json={
            "target_id": "temporary-demo", "name": "Temporary synthetic", "connector_type": "demo",
        }).status_code == 200
        run = client.post("/dashboard/audit-jobs", json={
            "target_id": "temporary-demo", "scenario_ids": ["CG-S018"],
        }).json()
        assert run["status"] == "completed"
        assert client.delete("/dashboard/targets/temporary-demo").status_code == 204
        summary = client.get("/dashboard/summary").json()
        assert summary["result_counts"] == {"PASS": 0, "PARTIAL": 0, "FAIL": 0, "REVIEW": 0}
        assert any(item["run_id"] == run["run_id"] for item in summary["recent_audits"])
