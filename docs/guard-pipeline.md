# Guard pipeline

Every `/v1/chat` request receives an event ID and passes through request inspection, retrieval admission, response inspection, tool control, and event storage.

Request rules emit a stable reason code, mapped policy ID, strength, safe explanation, and separate monitor/enforce actions. Emergency indicators short-circuit enforce mode to a predefined non-diagnostic escalation response and human review.

For deep demo requests, raw candidates remain unchanged. Guard records raw, rejected, and admitted metadata separately. Confidential synthetic chunks need role and matching patient scope; untrusted chunks are rejected; trusted clinical/operational chunks are preferred. After rejection Guard asks for eligible trusted refill candidates and records `CG_TRUSTED_CONTEXT_REFILLED`.

Generation receives only admitted context in enforce mode and cannot execute tools. The response guard redacts controlled synthetic values and withholds unsupported certainty, controlled system content, or source claims absent from admitted context. Public output never contains the protected raw target response.

Monitor mode sends raw context and allows baseline tool execution. It records `would_enforce_decision`, rejected candidates, redactions, and tool controls without changing visible traffic.

Events are stored in `.careguard-data/guard/guard-events.db`; sanitized protected responses are file references under `.careguard-data/guard/protected/` and are not returned by the public response model.
