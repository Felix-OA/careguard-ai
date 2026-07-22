# CareGuard AI

CareGuard AI is a defensive, local-first system for assessing and applying bounded runtime controls to healthcare patient-support and healthcare-information AI applications. Stage 1 provides **Audit**, Stage 2 adds the functional **CareGuard Guard** gateway, Stage 3 adds a working dashboard and local company-onboarding workflow, and Stage 4 adds **controlled multi-turn agentic auditing**. Regression scheduling remains future work.

CareGuard is intended for authorized AI security and application teams. It uses only fictional data, provides no diagnosis or personalized treatment, and does not claim HIPAA compliance, clinical validation, regulatory approval, complete prompt-injection prevention, production readiness, or a production security guarantee.

## Implemented capabilities

- A deliberately imperfect synthetic healthcare target with four local simulated tools.
- A versioned 15-policy pack, 20 safe scenarios, deterministic evaluators, JSONL evidence, SQLite metadata, reports, API, and CLI.
- A separate Guard FastAPI gateway with request, retrieval/context, response, tool, redaction, escalation, and confirmation controls.
- `monitor` mode that preserves traffic while recording what enforce mode would do.
- `enforce` mode that applies blocks, context filtering/refill, redaction, policy escalation, tool authorization, and bounded confirmation.
- Protected raw target responses and structured Guard events with stable reason codes and distinct proposed/authorized/confirmed/executed/blocked/failed tool states.
- Baseline `demo` and guarded `demo-guarded` audits using the identical scenario suite, plus Markdown/JSON comparisons.
- A React/TypeScript dashboard with server-persisted onboarding, target configuration, audit jobs, comparisons, sanitized Guard events, a separate human-review workflow, policies, safe reports, and a guided synthetic demo.
- A versioned 10-objective agentic pack, versioned 10-strategy safe template pack, deterministic seeded campaigns, sanitized trajectory evidence, explicit limits/stops, REVIEW routing, and evidence-reconciled baseline-versus-guarded comparison.
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

Browser -> Dashboard :3000 -> same-origin /api -> Audit API :8000
                                            -> sanitized dashboard aggregation
                                            -> bounded in-process agentic runner
                                            -> baseline/guarded evidence and reports
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
- Dashboard: <http://127.0.0.1:3000>
- Health endpoints: `:8000/health`, `:8001/health`, and `:8002/health`

Restart after changing `.env` or Guard configuration:

```bash
docker compose down
docker compose up --build
```

Set `CAREGUARD_GUARD_MODE=monitor` or `enforce` in `.env`. Monitor observes and intentionally preserves unsafe baseline traffic; it is not protection. `POST /v1/config/reload` reloads validated YAML and the environment-selected mode, and clears process-local confirmation/conversation state.

The browser talks only to `/api/` on the dashboard origin; nginx proxies that path to the Audit API. It never contacts Guard or the demo agent directly. API and static responses are marked `no-store`. Complete `/onboarding` first, then use `/audits/new` to run baseline and guarded suites, `/comparisons` to compare equivalent fixed-suite runs, and `/agentic/new` for a bounded deterministic multi-turn campaign. Credential values are never accepted by the UI: onboarding may select only the allowlisted server-side reference `OPENAI_COMPATIBLE_API_KEY`, and dashboard responses expose only `Not configured`, `Configured server-side`, or `Unavailable`.

Stage 3 external-target onboarding requires an explicit authorization acknowledgement and accepts only exact HTTP origins on the two synthetic service ports (`8001` and `8002`) with allowlisted chat paths. Public hosts, alternate ports, URL credentials, query strings, fragments, redirects, and unsupported schemes are rejected. Connector timeouts are bounded and connector JSON responses are capped at one megabyte. These application checks do not replace production network egress controls.

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
python -m careguard.cli list-agentic-objectives
python -m careguard.cli run-agentic-campaign --target demo --objectives healthcare-safe --attacker deterministic --max-turns 5 --seed 42
python -m careguard.cli run-agentic-campaign --target demo-guarded --objectives healthcare-safe --attacker deterministic --max-turns 5 --seed 42
python -m careguard.cli compare-agentic-campaigns --baseline BASELINE_CAMPAIGN_ID --guarded GUARDED_CAMPAIGN_ID
```

Replace `BASELINE_CAMPAIGN_ID` and `GUARDED_CAMPAIGN_ID` with completed campaign IDs printed by the preceding commands. The default attacker is deterministic, needs no API key, has no tools, and generates messages only from server-owned templates. An optional OpenAI-compatible attacker and secondary judge can be enabled server-side for an exact `127.0.0.1` HTTP origin; both are disabled by default.

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
- Agentic campaigns, objective runs, sanitized turns, comparisons, and reviews: `.careguard-data/careguard.db`

These locations are ignored by Git. Public Guard responses/events hide raw request text, source excerpts, local paths, protected responses, and tool arguments. Complete sanitized synthetic evidence remains in local protected storage. Reviewed samples live in `reports/samples/`.

## Integration boundaries

Deep integration exposes retrieval candidates to Guard and supports context admission before generation. An external proxy-only connector can inspect requests, responses, and proposed tools, but it cannot filter model context unless the target supplies an authorized retrieval/generation hook. Audit-time testing replays fixed scenarios and scores evidence; runtime protection evaluates each live local request and records a Guard event.

See the [agentic audit guide](docs/agentic-audit.md), [agentic threat model](docs/agentic-threat-model.md), [agentic objectives](docs/agentic-objectives.md), [agentic evidence](docs/agentic-evidence.md), [operator safety](docs/agentic-operator-safety.md), [dashboard guide](docs/dashboard-guide.md), [human-review workflow](docs/human-review-workflow.md), [dashboard security](docs/dashboard-security.md), [architecture](docs/architecture.md), [Guard pipeline](docs/guard-pipeline.md), [connector guide](docs/connector-guide.md), [threat model](docs/threat-model.md), and [roadmap](docs/product-roadmap.md).

## Validation

```bash
pytest
python -m compileall careguard demo_health_agent careguard_guard
docker compose config
python scripts/smoke_test.py  # after the Compose stack is healthy
cd frontend && npm ci && npm run typecheck && npm run lint && npm test -- --run && npm run build
```

## Known limitations and responsible use

- Controls are transparent deterministic rules, not complete semantic security.
- Process-local confirmation tokens demonstrate binding and expiry; they are not production authentication.
- SQLite and local files are development storage, not a distributed security event platform.
- The dashboard has no production authentication, authorization, multi-tenancy, policy approval, or distributed job queue.
- Dashboard audit jobs execute synchronously in one API process. Persisted active jobs are marked failed after process restart; there is no cancellation, worker lease, scheduling, or cross-process coordination.
- Agentic campaigns also execute synchronously inside the Audit API. They use a persisted cooperative cancellation flag but have no separate worker, lease, distributed queue, live progress stream, or exactly-once guarantee.
- Stage 4 is inspired only by the high-level objective/attacker/target/evaluator loop associated with GOAT. It is not an official GOAT implementation, reproduction, certification, or research-equivalence claim.
- Dashboard reports are deliberately less detailed than protected local evidence: raw prompts/responses, source excerpts, tool arguments, secret references, and local paths are excluded.
- Superseded audit review items remain available as history but are excluded from the current unresolved count.
- Client-supplied role/scope metadata demonstrates policy behavior; production identity must be authenticated and server-derived.
- Message hashes aid correlation/integrity checking and are not anonymization.
- Generic external connectors lack deep context admission unless they implement the integration hook.
- Qualified clinical, security, privacy, and legal review remains necessary.

Use only synthetic data and localhost, container-local services, or targets you are explicitly authorized to assess. The demo does not contact healthcare or booking services.
