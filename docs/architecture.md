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

## Dependencies and Stage 3 boundary

Shared schemas, catalogs, evidence, and reports live in `careguard`; runtime controls live in `careguard_guard`; intentional target behavior lives in `demo_health_agent`. The Guard imports shared models, while the Audit package includes a Guard connector and comparison helper because both stages ship together. Decoupling the comparison's legacy configuration fallback is minor architectural debt if these become separately deployed packages.

Docker runs Audit API `8000`, demo agent `8001`, and Guard `8002`, bound to host loopback. Default providers and tools are offline and deterministic.

Stage 3 may add scheduling, review workflows, and views over these APIs. Scheduling, policy decisions, evaluation aggregation, and event/report logic must remain in backend services rather than the UI. Stage 3 must also add durable identity, access control, migrations, and production event-store design before any real deployment claim.
