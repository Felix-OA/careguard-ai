# Security policy

CareGuard is for controlled defensive testing. Do not submit real patient data, medical records, credentials, secrets, or reports containing them.

## Supported scope

Stages 1–4 permit localhost and explicit Docker service hosts only. Stage 4 campaigns additionally require a synthetic/authorized acknowledgement and a baseline or Guard target-path match. Public or third-party testing is outside this design.

## Reporting a vulnerability

Privately report the affected version, reproduction using synthetic data, security impact, and a suggested mitigation to the project maintainer. Do not include live credentials or patient information. Rotate any credential accidentally exposed and remove it from history using your organization's incident process.

## Design safeguards

- Connector credentials remain server-side and are not part of normalized evidence models. The dashboard never renders secret-value inputs or stores configuration in browser persistence; it receives only credential status.
- Evidence serialization redacts authorization/secret-like keys and common bearer/key patterns.
- Guard events apply the same sanitizer; public event views remove request text, excerpts, scope values, and tool arguments, while protected raw target responses use opaque references.
- Deep demo integration endpoints accept only loopback, test clients, and the Compose subnet. They are unauthenticated fixtures and are not a production integration pattern.
- Confirmation state is one-time, short-lived, conversation/action/argument/patient-scope-bound, and explicitly not production authentication.
- Enforce responses are withheld if the Guard decision cannot be persisted.
- `.env`, databases, raw evidence, indexes, tool state, and generated reports are ignored.
- The default provider is deterministic and needs no network access or key.
- The Stage 4 attacker has no tools, shell, Python, browser, filesystem, Docker, messaging, environment, or arbitrary HTTP capability. It selects an allowlisted strategy and the server generates the message from a safe template.
- Target output is bounded; secret-, path-, and reasoning-shaped content is removed before persistence; instruction-shaped output is flagged; and repeated invalid optional-model output stops the objective. Optional model attacker/judge traffic is disabled by default and restricted to an exact allowlist of loopback-IP HTTP origins.
- Agentic evidence commits campaign state, objective outcome, and sanitized turns transactionally. A persistence failure produces a safe failed state; if that state cannot be persisted, the storage exception propagates instead of releasing false success.
- Dashboard API schemas omit raw prompts/responses, evidence paths, report paths, protected-response references, environment configuration, source excerpts, tool arguments, and raw authorization metadata. Event/report pagination and identifiers are bounded.
- nginx serves a restrictive Content Security Policy plus `nosniff`, frame denial, referrer, and permissions headers. Markdown is rendered as React text without arbitrary HTML.
- Target endpoints are validated server-side against exact local synthetic origins and allowlisted chat paths. URL credentials, queries, fragments, redirects, alternate ports, public hosts, and unsupported schemes are rejected; responses and timeouts are bounded. The UI requires an authorization acknowledgement and does not discover or scan targets.

`normalized_message_hash` supports local correlation/integrity checks. It does not anonymize input and must be handled as potentially sensitive metadata. Monitor mode preserves unsafe target behavior and must not be treated as an enforcement boundary.
