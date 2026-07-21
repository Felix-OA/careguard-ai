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
summary = request("http://localhost:8000/audits", {"target_id": "demo", "scenario_ids": ["CG-S006", "CG-S010"]})
assert summary["counts"]["FAIL"] >= 1
print(json.dumps(summary, indent=2))

