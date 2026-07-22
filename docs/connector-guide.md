# Connector guide

A Stage 1-compatible connector implements asynchronous `send(NormalizedRequest) -> NormalizedResponse` and keeps credentials in private server-side state. Normalize answers, source trust/admission, proposed and executed tools, latency, provider/model, and sanitized error categories. Never copy headers, full exceptions, or credentials into evidence.

## External proxy control

A generic REST or OpenAI-compatible proxy can inspect the incoming request, final response, and surfaced tool metadata. It cannot reliably distinguish raw retrieval from admitted context unless the target exposes that information. Guard must document this reduced visibility rather than claim context filtering.

## Deep retrieval integration

The synthetic demo exposes local/private-network-only `/internal/retrieve` and `/internal/generate` endpoints. Guard fetches candidates, applies trust/scope controls, then supplies admitted context to generation with tool execution disabled. A real custom integration should provide equivalent authenticated, authorized server-to-server hooks; production integration is outside Stage 2.

## Audit and runtime connectors

`DemoConnector` measures the baseline. `GuardConnector` adapts Guard output back to the Stage 1 normalized schema so the fixed suite can assess `demo-guarded`. The CLI runs this adapter in process; Docker’s audit API calls the separate Guard service.

All Stage 2 endpoints remain restricted to localhost and named Compose services. Test new connectors against a local fake target; tests must not call public or paid APIs.
