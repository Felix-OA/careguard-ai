# Guard pipeline

Every `/v1/chat` request receives an event ID and passes through normalization, request inspection, authorization/scope checks, raw retrieval, classification, exclusion/refill, generation, response inspection, tool control, and event storage in that order.

Request rules emit a stable reason code, mapped policy ID, strength, safe explanation, and separate monitor/enforce actions. Emergency indicators short-circuit enforce mode to a predefined non-diagnostic escalation response and human review.

For deep demo requests, Guard records initial raw, rejected, refill, and admitted metadata separately. Confidential synthetic chunks need an allowed role and matching verified scope; untrusted chunks are rejected; trusted clinical/operational chunks are preferred. Refill is query-relevant and admits only eligible trusted candidates. If raw candidates exist but no trusted context remains, enforce mode reports `CG_SOURCE_GROUNDING_INSUFFICIENT` and fails closed.

Generation receives only admitted context in enforce mode and cannot execute tools. The response guard redacts exact and separator-transformed controlled values and withholds unsupported certainty, controlled system content, or source claims absent from admitted context. Emergency policy output has precedence over later block decisions. Public output never contains the protected raw target response, source excerpts, raw request, or unredacted tool arguments.

Monitor mode sends raw context and allows baseline tool execution. It records `would_enforce_decision`, rejected candidates, prospective redactions, and tool controls without changing visible traffic. `final_decision` describes what happened; `would_enforce_decision` describes the enforce result. Monitor mode is unsafe by design and must not be used as protection.

Events are stored in `.careguard-data/guard/guard-events.db`; sanitized protected responses are mode-`0600` files under `.careguard-data/guard/protected/`. Public references use opaque `protected://` identifiers. A response is withheld with `503` if the security decision cannot be persisted. The message hash is a correlation/integrity aid, not anonymization.
