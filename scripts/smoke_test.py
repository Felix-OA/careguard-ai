"""Run after Docker Compose is healthy: python scripts/smoke_test.py."""

import json
import urllib.request


def request(url: str, payload: dict | None = None) -> dict:
    data = json.dumps(payload).encode() if payload else None
    headers = {"content-type": "application/json"} if data else {}
    with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=headers), timeout=60) as response:
        return json.load(response)


assert request("http://localhost:8001/health")["status"] == "ok"
assert request("http://localhost:8000/health")["status"] == "ok"
assert request("http://localhost:8002/health")["status"] == "ok"
guarded_chat = request("http://localhost:8002/v1/chat", {
    "conversation_id": "docker-smoke",
    "user_message": "What are the clinic opening hours?",
    "role_metadata": {"role": "guest"},
})
assert guarded_chat["final_decision"] == "ALLOW"
scenarios = ["CG-S006", "CG-S010", "CG-S018"]
baseline = request("http://localhost:8000/audits", {"target_id": "demo", "scenario_ids": scenarios})
guarded = request("http://localhost:8000/audits", {"target_id": "demo-guarded", "scenario_ids": scenarios})
comparison = request("http://localhost:8000/audits/compare", {
    "baseline_run_id": baseline["run_id"], "guarded_run_id": guarded["run_id"],
})
assert comparison["identical_scope"] is True
assert request("http://localhost:8002/v1/metrics")["event_count"] >= 1
print(json.dumps({"baseline": baseline, "guarded": guarded, "comparison": comparison}, indent=2))
