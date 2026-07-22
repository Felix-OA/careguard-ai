# Architecture

CareGuard separates the deliberately imperfect synthetic target from two defensive execution planes.

## Stage 1: Audit plane

The audit plane loads versioned policies and fixed scenarios, invokes a normalized connector, applies deterministic evaluators, appends sanitized JSONL evidence, indexes run metadata in SQLite, and derives audit/comparison reports. `demo` measures the unchanged baseline endpoint; `demo-guarded` measures the same target through Guard with identical scenario order, versions, expected behavior, and evaluator definitions.

Audit controls score completed scenario evidence. They do not make runtime authorization decisions.

## Stage 2: runtime Guard plane

The separate Guard service sits between its client and the target:

1. Normalize and validate the request.
2. Inspect policy, role, verified synthetic patient scope, and conversation identity.
3. Retrieve raw candidates through the demo's restricted deep-integration hook.
4. Classify candidates, exclude prohibited context, and perform query-relevant trusted refill.
5. Generate with admitted context and target-side tool execution disabled.
6. Inspect, redact, withhold, or replace the response.
7. Classify tool states as proposed, authorized, confirmation-required, confirmed, executed, blocked, or failed.
8. Persist the protected response and sanitized security decision before releasing enforce output.

Monitor mode uses raw target context and behavior, then records the enforce decision without changing visible traffic. It is observation only and can expose the baseline's intentional weaknesses. Enforce mode applies the guarded context and controls.

The demo's `/chat` endpoint remains the Stage 1 baseline. `/internal/retrieve` and `/internal/generate` are loopback/Compose-only test hooks; they demonstrate the visibility a deep integration needs and are not a production design. A proxy-only integration can inspect only what the target exposes and cannot claim context admission.

## Stage 3: dashboard plane

The React/TypeScript application is a presentation client, not a security decision engine. In Docker, nginx serves it on loopback port `3000` and proxies same-origin `/api/` requests only to the Audit API. The browser does not combine Guard, demo-agent, evidence, or environment data.

The Audit API's `careguard.dashboard` package is the sanitized aggregation boundary. Explicit Pydantic models expose organization state, target capability and credential status, audit-job state, path-free audit/comparison summaries, protected-content-free finding details, paginated public Guard events, independent review decisions, policy coverage, safe report summaries, health, and evidence-validated dashboard summaries. SQLite remains authoritative for local onboarding, configuration, job, and review records. Jobs run synchronously in-process but persist honest queued/running/completed/failed transitions, recover interrupted active records as failed, and do not fabricate progress. This is not a durable queue.

Dashboard policy enablement is a local audit-scope configuration, not Guard policy governance. Updates are transactional and monotonically versioned; future dashboard audit evidence binds the effective version. Comparisons reject different scenario, policy, product, expected-behavior, evaluator, or ordering scope.

```text
Browser :3000
  -> nginx /api/*
    -> Audit API :8000
       -> dashboard aggregation -> SQLite / sanitized evidence / public events
       -> demo-agent :8001 and Guard :8002 (server-to-server only)
```

## Dependencies and Stage 4 boundary

Shared schemas, catalogs, evidence, and reports live in `careguard`; runtime controls live in `careguard_guard`; intentional target behavior lives in `demo_health_agent`. The Guard imports shared models, while the Audit package includes a Guard connector and comparison helper because both stages ship together. Decoupling the comparison's legacy configuration fallback is minor architectural debt if these become separately deployed packages.

Docker runs Dashboard `3000`, Audit API `8000`, demo agent `8001`, and Guard `8002`, bound to host loopback. Default providers and tools are offline and deterministic.

Stage 4 may add explicitly approved agentic or scheduled regression work, but it must not treat Stage 3's local UI, unauthenticated APIs, SQLite job state, or demonstration review workflow as production identity/governance. Durable identity, authorization, migrations, tamper-evident event storage, secret-vault integration, signed policy governance, and distributed work remain productization requirements.
