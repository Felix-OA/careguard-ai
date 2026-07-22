# Dashboard security

The dashboard is designed for loopback-only synthetic evaluation. nginx binds host port `3000` to `127.0.0.1`, proxies same-origin `/api/` only to the Audit API, rejects the ambiguous bare `/api` route, marks responses `no-store`, and configures Content Security Policy, frame denial, MIME sniffing protection, no-referrer, and disabled camera/microphone/geolocation. Vite development also proxies `/api`; the API does not enable wildcard credentialed CORS.

## Data minimization

- Explicit dashboard Pydantic schemas omit evidence/report/database paths, environment configuration, protected-response references, authorization metadata, excerpts, and secret values.
- Credential values never enter the browser, URL, source, log, local storage, or frontend state.
- Guard events use the public sanitized representation and bounded pagination; tool arguments are redacted and proposal/block/failure/execution states remain separate.
- Reports are regenerated through validated database identifiers. Route patterns prevent traversal; report output omits raw prompts/responses, source excerpts, tool arguments, secret references, protected references, and local paths rather than reusing protected evidence exports.
- Markdown is rendered as plain React text with no arbitrary HTML or `dangerouslySetInnerHTML`.
- Connectivity and job failures return bounded categories, not exception messages or stack traces.
- Target URL validation accepts only exact HTTP origins for the two local synthetic service ports plus connector-specific chat paths. It rejects URL credentials, queries, fragments, redirects, alternate ports, public/unapproved hosts, and unsupported schemes; connector responses are capped at one megabyte and no discovery exists.

The production bundle should be checked for secret-shaped strings and protected local paths during release validation. Dependency audits are informational and must be triaged rather than treated as proof of safety.

## Residual risk

There is no authentication or production authorization. Any local process/user that can access loopback endpoints may change demonstration state. Application SSRF allowlists are defense in depth, not a replacement for production DNS/IP validation and network egress policy. SQLite/local files are not encrypted or tamper-evident, nginx does not provide TLS on loopback, CSP allows inline styles for the current component/chart implementation, and host compromise defeats these boundaries. Do not expose this stack publicly or use real patient information. It is not HIPAA compliance, clinical validation, regulatory approval, complete prompt-injection protection, or production readiness.
