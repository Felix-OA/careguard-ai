# Architecture

CareGuard has two complementary execution planes.

The **audit plane** loads the fixed policy/scenario catalogs, invokes a normalized target connector, applies deterministic evaluators, writes backward-compatible JSONL evidence, indexes runs in SQLite, and derives audit/comparison reports. Targets `demo` and `demo-guarded` use the same scenario IDs and expected behavior.

The **runtime plane** is the separate CareGuard Guard service. Its pipeline is:

1. Inspect normalized request, history, role, and verified synthetic patient scope.
2. Fetch raw candidates through the demo’s local-only retrieval hook.
3. classify candidates as rejected or eligible, refill with trusted candidates when exclusions reduce context, and record every state.
4. Ask the deterministic target to generate with admitted context while tool execution is disabled.
5. Inspect/redact or withhold the response.
6. Authorize proposed tools and apply conversation/action-bound confirmation.
7. Store a sanitized security event and a protected raw response reference.

Monitor mode generates through raw target context and permits baseline tool behavior while computing the enforce-mode decisions. Enforce mode applies the guarded context and controls.

Docker runs three services: audit API `8000`, demo agent `8001`, and Guard `8002`. All default providers and tools are local and deterministic.

Audit-time testing scores fixed evidence after a scenario. Runtime protection makes and records an immediate decision for each request. Neither is a substitute for qualified review.
