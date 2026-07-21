# Connector guide

A connector implements the asynchronous `TargetConnector.send` method. Input includes target and conversation IDs, the current user message, prior normalized turns, and role metadata. Output includes the answer, retrieved sources and trust levels, proposed and executed tools, latency, provider/model identity, and a sanitized error category.

Rules for new connectors:

1. Keep keys and authorization headers in private connector fields populated from server environment state.
2. Never copy headers, full exception messages, or request clients into evidence.
3. Enforce an explicit authorized-target allowlist before connecting.
4. Normalize retrieved and tool metadata even when the upstream field names differ.
5. Return an error category rather than raising target internals into evidence.
6. Test with a local fake server; tests must not call paid or public APIs.

Register a custom local target through `POST /targets` using `rest` or `openai_compatible`. Stage 1's endpoint guard permits localhost and named Compose services only.

