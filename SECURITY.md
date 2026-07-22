# Security policy

CareGuard is for controlled defensive testing. Do not submit real patient data, medical records, credentials, secrets, or reports containing them.

## Supported scope

Stages 1 and 2 permit localhost and explicit Docker service hosts only. Do not modify the allowlist to test a public or third-party system unless you own it and have written authorization; production targeting is outside this design.

## Reporting a vulnerability

Privately report the affected version, reproduction using synthetic data, security impact, and a suggested mitigation to the project maintainer. Do not include live credentials or patient information. Rotate any credential accidentally exposed and remove it from history using your organization's incident process.

## Design safeguards

- Connector credentials remain server-side and are not part of normalized evidence models.
- Evidence serialization redacts authorization/secret-like keys and common bearer/key patterns.
- Guard events apply the same sanitizer; public event views remove request text, excerpts, scope values, and tool arguments, while protected raw target responses use opaque references.
- Deep demo integration endpoints accept only loopback, test clients, and the Compose subnet. They are unauthenticated fixtures and are not a production integration pattern.
- Confirmation state is one-time, short-lived, conversation/action/argument/patient-scope-bound, and explicitly not production authentication.
- Enforce responses are withheld if the Guard decision cannot be persisted.
- `.env`, databases, raw evidence, indexes, tool state, and generated reports are ignored.
- The default provider is deterministic and needs no network access or key.

`normalized_message_hash` supports local correlation/integrity checks. It does not anonymize input and must be handled as potentially sensitive metadata. Monitor mode preserves unsafe target behavior and must not be treated as an enforcement boundary.
