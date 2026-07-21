# CareGuard AI

CareGuard AI is a defensive, local-first foundation for auditing healthcare patient-support and healthcare-information AI applications. Stage 1 implements the **Audit** module against a deliberately imperfect synthetic demo target. Guard and Regression Monitor are documented future modules.

CareGuard is intended for AI security engineers, application teams, healthcare technology risk teams, and authorized assessors. It is not a medical service. It provides no diagnosis or personalized treatment and makes no claim of HIPAA compliance, regulatory approval, or medical-device status.

## What Stage 1 includes

- A separate FastAPI synthetic healthcare target with chat, retrieval debug, and health endpoints.
- Fictional records, appointments, `example.test` emails, canaries, trust-labeled documents, and four local simulated tools.
- A versioned 15-policy healthcare policy pack and 20 safe synthetic scenarios.
- Demo, generic REST, and optional OpenAI-compatible normalized connectors.
- Deterministic audit execution with multi-turn history and 14 evaluator types.
- Timestamped JSONL evidence, SQLite run metadata, Markdown/JSON reports, REST API, and CLI.
- Localhost/explicit-container-host target restriction and secret redaction.
- No paid provider or API key in the default path.

## Architecture

```text
scenarios + policy pack
          |
          v
  CareGuard audit runner ---> normalized connector ---> synthetic demo agent
          |                                             | retrieval + tools
          v
 deterministic evaluators
          |
          +--> JSONL evidence --> Markdown / JSON report
          +--> SQLite run and target index
```

The demo agent intentionally has over-broad retrieval, poor trust separation, weak synthetic-record authorization, occasional unsupported certainty, and weak action confirmation. Those are target findings, not recommended implementation patterns.

## One-command container setup

Requirements: Docker with Compose.

```bash
cp .env.example .env
docker compose up --build
```

- CareGuard API and docs: <http://localhost:8000/docs>
- Demo agent API and docs: <http://localhost:8001/docs>
- CareGuard health: <http://localhost:8000/health>
- Demo health: <http://localhost:8001/health>

Run a complete demo audit through the API:

```bash
curl -sS -X POST http://localhost:8000/audits \
  -H 'content-type: application/json' \
  -d '{"target_id":"demo"}'
```

Use the returned `run_id` with `/audits/{run_id}`, `/findings`, or `/report?format=markdown|json`.

## Local Python workflow

Use Python 3.11 or newer:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
python -m careguard.cli check-config
python -m careguard.cli list-scenarios
python -m careguard.cli run-audit --target demo
python -m careguard.cli generate-report --latest
```

Raw JSONL evidence is written under `.careguard-data/evidence/`; generated reports are under `.careguard-data/reports/`. Both are ignored by Git because even synthetic local evidence should be handled deliberately. A static, reviewed example is in `reports/samples/`.

Run validation:

```bash
pytest
python -m compileall careguard demo_health_agent
docker compose config
```

## Adding a custom connector

Implement `TargetConnector.send(NormalizedRequest) -> NormalizedResponse`, keep credentials inside the connector, and map source/tool/error information into the normalized schema. Stage 1 rejects non-local endpoints by default; extend the allowlist only for a target you own or are explicitly authorized to assess. See [docs/connector-guide.md](docs/connector-guide.md).

## Synthetic-data restrictions

Only fictional data may be used. Never place real patient information, identifiers, medical records, credentials, authorization headers, or API keys in scenarios, evidence, fixtures, or reports. The demo target does not call real healthcare services, book real visits, or escalate real cases.

## Known limitations

- Rules are deterministic and are not a substitute for expert clinical, security, privacy, or legal review.
- Stage 1 runs approved scenarios; it does not conduct broad autonomous red teaming.
- The demo target is intentionally vulnerable and must not be treated as production code.
- Local SQLite execution is intended for development, not distributed production workloads.
- The generic connector expects a documented normalized response shape.

See [architecture](docs/architecture.md), [threat model](docs/threat-model.md), [scenario design](docs/scenario-design.md), [connector guide](docs/connector-guide.md), and [roadmap](docs/product-roadmap.md).

## Responsible use

CareGuard Stage 1 is a synthetic local assessment tool. It is not a compliance certification, clinical validation, or production security guarantee. Test only localhost, container-local services, or targets you are explicitly authorized to assess.

