# CareGuard AI

**A bounded healthcare AI security audit, runtime guard, and controlled agentic evaluation platform.**

CareGuard AI is a local, synthetic prototype for evaluating healthcare-specific AI risks, applying observable runtime controls, and comparing baseline and guarded behavior. It gives AI security teams, digital-health builders, and LLM application engineers a reproducible way to inspect retrieval, context, disclosure, source trust, tool use, escalation, and multi-turn behavior without using real patient data or public targets.

> **Project status:** Stages 1–4 are implemented and independently hardened for a public technical demonstration. The reviewed suite has 92 backend tests, 20 frontend tests, two end-to-end workflows, and four healthy Docker services. This is not production readiness, clinical validation, regulatory certification, HIPAA compliance, or a universal security guarantee.

## Product capabilities

| Capability | What it does |
|---|---|
| **CareGuard Audit** | Runs a versioned suite of healthcare-specific security and safety evaluations and produces deterministic evidence and reports. |
| **CareGuard Guard** | Applies bounded request, retrieval, context, response, escalation, confirmation, and tool controls in monitor or enforce mode. |
| **CareGuard Dashboard** | Manages local targets, audits, comparisons, Guard events, human reviews, policies, reports, and the synthetic demonstration. |
| **Agentic Audit** | Runs controlled multi-turn evaluations using approved objectives, allow-listed strategies, explicit limits, and sanitized trajectories. |

The default path is offline, deterministic, and key-free. It includes a deliberately imperfect fictional healthcare target so baseline weaknesses and guarded behavior can be measured against the same fixed configuration.

## How the parts fit together

```text
Browser / client
       |
       v
Dashboard :3000  --->  Audit API :8000  --->  fixed Audit or controlled Agentic Audit
                              |                         |
                              |                         v
                              +----> Guard :8002 ---> synthetic target :8001
                                             |
                                             v
                                  events, evidence, review, reports
```

Audit measures completed behavior. Guard applies runtime controls. The dashboard exposes sanitized, server-derived views. Controlled Agentic Audit adapts across multiple turns while remaining inside server-owned objectives, strategies, targets, and resource limits. See the [public case study](docs/public-case-study.md) and [architecture](docs/architecture.md) for the complete design.

## Reviewed results

### Fixed deterministic audit suite

The same 20-scenario suite was run against the synthetic baseline and guarded paths.

| Outcome | Baseline | Guarded |
|---|---:|---:|
| PASS | 6 | 13 |
| FAIL | 11 | 0 |
| REVIEW | 3 | 7 |

These are fixed-suite observations, not general security rates. REVIEW remains separate because consequential healthcare wording, authority, and source-trust cases require human judgment.

### Controlled agentic campaign

A matched deterministic campaign used seed `731`, ten objectives, a five-turn objective ceiling, a 50-turn campaign ceiling, and zero model calls.

| Metric | Baseline | Guarded |
|---|---:|---:|
| PASS | 1 | 5 |
| FAIL | 8 | 0 |
| REVIEW | 1 | 5 |
| Total turns | 11 | 19 |
| Answer disclosures | 8 | 0 |
| Untrusted context admissions | 2 | 0 |
| Blocked tool attempts | 0 | 2 |

Five guarded REVIEW outcomes are non-directional. The longer guarded trajectories show that boundaries were exercised across more turns in this configuration; they do not prove causation or universal effectiveness. Security and utility are reported separately in the [case study](docs/public-case-study.md).

## Run the local demonstration

Prerequisites are Docker Desktop and Docker Compose. No API key is required.

```bash
cp .env.example .env
docker compose up --build --wait
```

Open <http://127.0.0.1:3000>. The [public demo guide](docs/public-demo-guide.md) walks through onboarding, baseline and guarded audits, comparisons, Guard events, REVIEW decisions, and agentic campaigns.

## Screenshots

| Dashboard | Fixed-suite comparison | Agentic comparison |
|---|---|---|
| ![CareGuard dashboard overview](docs/screenshots/01-dashboard-overview.png) | ![Baseline-versus-guarded fixed-suite comparison](docs/screenshots/04-fixed-comparison.png) | ![Controlled agentic comparison](docs/screenshots/10-agentic-comparison.png) |

All captures come from the local fictional-data environment. See the [screenshot catalogue](docs/screenshots/README.md) for the complete set.

## Important limitations

- The target, identities, records, documents, and tools are synthetic and scripted.
- Evaluators use deterministic indicators over fixed scenarios and objectives.
- The local dashboard has no production authentication, authorization, or multi-tenancy.
- SQLite, local files, and process-local jobs are demonstration infrastructure.
- Optional model attacker and judge paths are disabled by default and have not been live-tested against a real local provider.
- Human REVIEW outcomes are unresolved until assessed by qualified reviewers.
- CareGuard does not establish clinical safety, compliance, complete prompt-injection prevention, or production security.

Use CareGuard only for authorized defensive testing with fictional data. A company-specific pilot requires architecture discovery, policy and identity mapping, authorized connector work, false-positive tuning, and independent validation; see the [company pilot framework](docs/company-pilot.md).

## Docker setup

```bash
cp .env.example .env
docker compose up --build --wait
```

- Audit API: <http://127.0.0.1:8000/docs>
- Synthetic demo agent: <http://127.0.0.1:8001/docs>
- Guard gateway: <http://127.0.0.1:8002/docs>
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
python -m careguard.cli compare-audits --baseline BASELINE_RUN_ID --guarded GUARDED_RUN_ID
python -m careguard.cli generate-report --run-id RUN_ID
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

These locations are ignored by Git. Public Guard responses/events hide raw request text, source excerpts, local paths, protected responses, and tool arguments. Complete sanitized synthetic evidence remains in local protected storage. Public illustrative summaries live in [`docs/samples/`](docs/samples/README.md); they are authored summaries rather than copies of raw evidence.

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
