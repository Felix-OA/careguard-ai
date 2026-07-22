# CareGuard AI

CareGuard AI is a defensive, local-first system for assessing and applying bounded runtime controls to healthcare patient-support and healthcare-information AI applications. Stage 1 provides **Audit**; Stage 2 adds the functional **CareGuard Guard** gateway. Regression Monitor and a dashboard remain future work.

CareGuard is intended for authorized AI security and application teams. It uses only fictional data, provides no diagnosis or personalized treatment, and does not claim HIPAA compliance, clinical validation, regulatory approval, complete prompt-injection prevention, production readiness, or a production security guarantee.

## Implemented capabilities

- A deliberately imperfect synthetic healthcare target with four local simulated tools.
- A versioned 15-policy pack, 20 safe scenarios, deterministic evaluators, JSONL evidence, SQLite metadata, reports, API, and CLI.
- A separate Guard FastAPI gateway with request, retrieval/context, response, tool, redaction, escalation, and confirmation controls.
- `monitor` mode that preserves traffic while recording what enforce mode would do.
- `enforce` mode that applies blocks, context filtering/refill, redaction, policy escalation, tool authorization, and bounded confirmation.
- Protected raw target responses and structured Guard events with stable reason codes and distinct proposed/authorized/confirmed/executed/blocked/failed tool states.
- Baseline `demo` and guarded `demo-guarded` audits using the identical scenario suite, plus Markdown/JSON comparisons.
- No paid provider or API key in the default path.

## Architecture

```text
Client / fixed audit suite
          |
          v
CareGuard Guard :8002
  request policy -> raw retrieval -> context admission/refill
  -> deterministic target generation -> response/redaction
  -> tool authorization/confirmation -> security event
          |
          v
Synthetic demo agent :8001

CareGuard Audit API :8000 -> baseline or guarded connector -> evidence/reports
```

The demo’s `/internal/retrieve` and `/internal/generate` hooks are restricted to loopback, test, and Docker-network clients and let Guard inspect candidates before generation. They are unauthenticated test fixtures, not a recommended production interface. The original `/chat` remains the intentionally weak Stage 1 baseline.

## Docker setup

```bash
cp .env.example .env
docker compose up --build
```

- Audit API: <http://localhost:8000/docs>
- Synthetic demo agent: <http://localhost:8001/docs>
- Guard gateway: <http://localhost:8002/docs>
- Health endpoints: `:8000/health`, `:8001/health`, and `:8002/health`

Restart after changing `.env` or Guard configuration:

```bash
docker compose down
docker compose up --build
```

Set `CAREGUARD_GUARD_MODE=monitor` or `enforce` in `.env`. Monitor observes and intentionally preserves unsafe baseline traffic; it is not protection. `POST /v1/config/reload` reloads validated YAML and the environment-selected mode, and clears process-local confirmation/conversation state.

## Local CLI workflow

Use Python 3.11 or newer:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
python -m careguard.cli check-config
python -m careguard.cli run-audit --target demo
python -m careguard.cli run-audit --target demo-guarded
python -m careguard.cli compare-audits --baseline <baseline_run_id> --guarded <guarded_run_id>
python -m careguard.cli generate-report --run-id <run_id>
```

The CLI’s guarded connector is an in-process adapter to the same Guard pipeline. In Docker, the audit API uses the separate `careguard-guard` service.

## API workflows

Guard a synthetic request:

```bash
curl -sS -X POST http://localhost:8002/v1/chat \
  -H 'content-type: application/json' \
  -d '{"conversation_id":"example","user_message":"What are the clinic hours?","role_metadata":{"role":"guest"}}'
```

Run baseline and guarded audits:

```bash
curl -sS -X POST http://localhost:8000/audits -H 'content-type: application/json' -d '{"target_id":"demo"}'
curl -sS -X POST http://localhost:8000/audits -H 'content-type: application/json' -d '{"target_id":"demo-guarded"}'
curl -sS -X POST http://localhost:8000/audits/compare -H 'content-type: application/json' \
  -d '{"baseline_run_id":"<baseline>","guarded_run_id":"<guarded>"}'
```

Guard endpoints include `/v1/policies`, `/v1/events`, `/v1/events/{event_id}`, `/v1/metrics`, and `/v1/config/reload`. Audit comparison endpoints include `/comparisons`, `/comparisons/{id}`, and `/comparisons/{id}/report?format=markdown|json`.

## Local data locations

- Audit evidence: `.careguard-data/evidence/*.jsonl`
- Audit reports: `.careguard-data/reports/`
- Guard events: `.careguard-data/guard/guard-events.db`
- Protected raw target responses: `.careguard-data/guard/protected/`
- Comparison reports: `.careguard-data/reports/comparisons/`

These locations are ignored by Git. Public Guard responses/events hide raw request text, source excerpts, local paths, protected responses, and tool arguments. Complete sanitized synthetic evidence remains in local protected storage. Reviewed samples live in `reports/samples/`.

## Integration boundaries

Deep integration exposes retrieval candidates to Guard and supports context admission before generation. An external proxy-only connector can inspect requests, responses, and proposed tools, but it cannot filter model context unless the target supplies an authorized retrieval/generation hook. Audit-time testing replays fixed scenarios and scores evidence; runtime protection evaluates each live local request and records a Guard event.

See the [architecture](docs/architecture.md), [Guard pipeline](docs/guard-pipeline.md), [policy configuration](docs/policy-configuration.md), [policy coverage](docs/policy-coverage.md), [tool controls](docs/tool-control.md), [connector guide](docs/connector-guide.md), [threat model](docs/threat-model.md), [pre-Stage-3 validation](docs/pre-stage-3-validation.md), and [roadmap](docs/product-roadmap.md).

## Validation

```bash
pytest
python -m compileall careguard demo_health_agent careguard_guard
docker compose config
python scripts/smoke_test.py  # after the Compose stack is healthy
```

## Known limitations and responsible use

- Controls are transparent deterministic rules, not complete semantic security.
- Process-local confirmation tokens demonstrate binding and expiry; they are not production authentication.
- SQLite and local files are development storage, not a distributed security event platform.
- Client-supplied role/scope metadata demonstrates policy behavior; production identity must be authenticated and server-derived.
- Message hashes aid correlation/integrity checking and are not anonymization.
- Generic external connectors lack deep context admission unless they implement the integration hook.
- Qualified clinical, security, privacy, and legal review remains necessary.

Use only synthetic data and localhost, container-local services, or targets you are explicitly authorized to assess. The demo does not contact healthcare or booking services.
