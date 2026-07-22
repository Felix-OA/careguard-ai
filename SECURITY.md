# Security policy

CareGuard is for controlled defensive testing. Do not submit real patient data, medical records, credentials, secrets, or reports containing them.

## Supported scope

Stages 1 and 2 permit localhost and explicit Docker service hosts only. Do not modify the allowlist to test a public or third-party system unless you own it and have written authorization; production targeting is outside this design.

## Reporting a vulnerability

Privately report the affected version, reproduction using synthetic data, security impact, and a suggested mitigation to the project maintainer. Do not include live credentials or patient information. Rotate any credential accidentally exposed and remove it from history using your organization's incident process.

## Design safeguards

- Connector credentials remain server-side and are not part of normalized evidence models.
- Evidence serialization redacts authorization/secret-like keys and common bearer/key patterns.
- Guard events apply the same sanitizer; protected raw target responses are referenced rather than returned publicly.
- Deep demo integration endpoints reject non-private network clients.
- Confirmation state is short-lived, conversation/action-bound, and explicitly not production authentication.
- `.env`, databases, raw evidence, indexes, tool state, and generated reports are ignored.
- The default provider is deterministic and needs no network access or key.
