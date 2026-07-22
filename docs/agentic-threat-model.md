# Agentic runner threat model

The agentic runner is a separate attack surface inside the local Audit API. The target, optional model provider, campaign request, retrieved metadata, and visible response are untrusted. The objective/strategy packs, server configuration, local host, and operator are trusted for this demonstration.

## Protected assets

- Campaign limits, allowed strategies, fixed role and fictional patient scope.
- Environment variables, connector credentials, local paths, protected Guard responses, and raw evidence.
- SQLite campaign/trajectory/review integrity and deterministic severe findings.
- Separation between retrieval, context admission, tool proposal, authorization, confirmation, execution, and block/failure states.

## Modeled target-to-attacker threats

A target may claim its response is an instruction, request environment disclosure, suggest ignoring system rules, return oversized/secret-shaped content, emit HTML, propose tools, or try to alter strategy/limits. Controls are: JSON serialization with escaped prompt delimiters for optional model inputs; 4,000-character observations; common credential, environment-assignment, synthetic protected value, local path, and reasoning-shaped redaction; strategy/schema validation; server-owned message templates; hijack indicators; no target-controlled callbacks; baseline rejection of target-supplied Guard metadata; and immediate review-oriented termination for modeled instruction-shaped output.

The attacker object has no shell, Python execution, browser, filesystem, environment accessor, database connection, Docker control, email/messaging connector, arbitrary HTTP client, or Guard protected-response reader. The optional provider has one fixed operator-configured loopback endpoint and no tools.

## Resource and lifecycle threats

Turns, total turns, duration, model calls, and estimated cost are hard-bounded and checked before each step. Projected model calls are rejected before crossing a call or cost ceiling, and attacker/judge waits use the remaining campaign time. Target connectors already have bounded timeouts, response bodies, local origins, allowlisted paths, disabled redirects, and safe normalized errors. Cancellation is persisted, cooperatively checked, and wins at a completed-objective boundary before terminal completion is saved. Repeated invalid model output stops as INCONCLUSIVE. Active records recovered after restart become FAILED, never fabricated COMPLETE.

SQLite objective commits are transactional. If objective evidence cannot be committed, the campaign becomes FAILED; if even the failed state cannot be stored, the storage error propagates. This prevents a successful result being released without durable evidence, but SQLite is not tamper-evident, encrypted, replicated, or access-controlled.

## Optional judge threats

The judge receives sanitized structured turns and returns only a bounded outcome and concise rationale. It cannot convert answer disclosure, untrusted context admission, unauthorized execution, or unsupported certainty into PASS because those deterministic severe findings remain FAIL. Any other disagreement becomes REVIEW. Provider failure leaves deterministic evidence valid.

## Residual risk

Pattern sanitization can miss novel secret formats or semantic injections. Cooperative cancellation cannot preempt a stuck process. A compromised host or operator can access local storage and environment data. Loopback allowlists are application defense in depth, not OS egress isolation. The local unauthenticated API and review workflow are not production governance. Use only fictional data and explicitly authorized local targets.
