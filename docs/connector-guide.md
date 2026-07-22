# Connector guide

A Stage 1-compatible connector implements asynchronous `send(NormalizedRequest) -> NormalizedResponse` and keeps credentials in private server-side state. Normalize answers, source trust/admission, active proposals, blocked/failed/executed tools, latency, provider/model, and sanitized error categories. Never copy headers, full exceptions, local paths, or credentials into evidence.

## External proxy control

A generic REST or OpenAI-compatible proxy can inspect the incoming request, final response, and surfaced tool metadata. It cannot reliably distinguish raw retrieval from admitted context, prevent hidden target-side tool execution, or refill context unless the target exposes authenticated control points. Guard must document this reduced visibility rather than claim context filtering.

## Deep retrieval integration

The synthetic demo exposes loopback, test-client, and Docker-network-only `/internal/retrieve` and `/internal/generate` endpoints. Guard fetches candidates, applies trust/scope controls, then supplies admitted context to generation with tool execution disabled. These demo hooks have no production authentication and must not be copied as a recommended design. A real integration needs authenticated, mutually authorized server-to-server hooks and server-derived identity/scope; production integration is outside Stage 2.

## Audit and runtime connectors

`DemoConnector` measures the baseline. `GuardConnector` adapts Guard output back to the Stage 1 normalized schema so the fixed suite can assess `demo-guarded`. The CLI runs this adapter in process; Docker’s audit API calls the separate Guard service.

Stage 3 endpoint validation accepts only exact HTTP origins on local synthetic service ports `8001` and `8002`, rejects URL credentials, queries, fragments, redirects, alternate ports, unsupported schemes, and public hosts, and allowlists connector chat paths. Calls use configured bounded timeouts, do not follow redirects, and accept at most one megabyte of JSON. Test new connectors against a local fake target; tests must not call public or paid APIs. The normalized `error` field should contain a bounded category such as an exception type, never an exception message or stack trace. Production connectors additionally require network-layer egress policy and DNS/IP revalidation.

Stage 3 onboarding stores only non-secret mappings plus an optional environment-variable reference name. The browser never submits the referenced value and dashboard responses never return the reference name after configuration. Target updates that omit the credential field preserve the existing server-side reference. The harmless connection check uses synthetic clinic text and returns only `reachable`, `unavailable`, or `disabled`, a sanitized category, and latency.

Declare capability honestly: `proxy_only` sees surfaced requests/responses, `deep_retrieval` requires an authorized pre-context hook, and `tool_control` requires surfaced proposal/authorization/confirmation boundaries. The label is a declared integration property, not proof that the control exists.
