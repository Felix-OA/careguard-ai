# Connector guide

A Stage 1-compatible connector implements asynchronous `send(NormalizedRequest) -> NormalizedResponse` and keeps credentials in private server-side state. Normalize answers, source trust/admission, active proposals, blocked/failed/executed tools, latency, provider/model, and sanitized error categories. Never copy headers, full exceptions, local paths, or credentials into evidence.

## External proxy control

A generic REST or OpenAI-compatible proxy can inspect the incoming request, final response, and surfaced tool metadata. It cannot reliably distinguish raw retrieval from admitted context, prevent hidden target-side tool execution, or refill context unless the target exposes authenticated control points. Guard must document this reduced visibility rather than claim context filtering.

## Deep retrieval integration

The synthetic demo exposes loopback, test-client, and Docker-network-only `/internal/retrieve` and `/internal/generate` endpoints. Guard fetches candidates, applies trust/scope controls, then supplies admitted context to generation with tool execution disabled. These demo hooks have no production authentication and must not be copied as a recommended design. A real integration needs authenticated, mutually authorized server-to-server hooks and server-derived identity/scope; production integration is outside Stage 2.

## Audit and runtime connectors

`DemoConnector` measures the baseline. `GuardConnector` adapts Guard output back to the Stage 1 normalized schema so the fixed suite can assess `demo-guarded`. The CLI runs this adapter in process; Docker’s audit API calls the separate Guard service.

Endpoint validation permits HTTP(S) only, rejects URL credentials, and restricts targets to configured local/Docker hosts. Test new connectors against a local fake target; tests must not call public or paid APIs. The normalized `error` field should contain a bounded category such as an exception type, never an exception message or stack trace.
