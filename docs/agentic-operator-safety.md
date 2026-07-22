# Agentic operator safety

Use Stage 4 only on the built-in fictional demo, the local CareGuard-protected demo, or another explicitly configured and authorized connector already accepted by CareGuard's local target validation. Never enter patient information, real staff identities, production URLs, credentials, authentication headers, clinical questions, or live appointment references.

## Before a campaign

- Confirm the target is local, synthetic, enabled, and authorized.
- Choose the correct baseline or protected path; the API rejects mismatches.
- Keep the deterministic attacker unless a specific loopback model test is necessary.
- Review objective scope, prohibited classes, seed, turn/total/duration/model-call limits, and optional cost ceiling.
- Confirm local storage is protected and excluded from Git.
- Do not widen connector/provider allowlists for convenience.

## Optional model configuration

Model attacker and judge switches are false by default. Configure only an exact `http://127.0.0.1:PORT` origin in the server environment. Provider keys, if a local provider unusually requires one, remain server-side and must never appear in prompts or evidence. The provider has no tools and is secondary to deterministic safety boundaries. Do not use public model endpoints in this stage.

## During and after a campaign

Cancellation is cooperative; use the dashboard campaign action or cancellation endpoint while the API remains responsive. A terminal `LIMIT_REACHED`, `FAILED`, `CANCELLED`, `INCONCLUSIVE`, or `REVIEW` is not PASS. Inspect sanitized objective trajectories, stop reasons, separate retrieval/context and tool states, agent-hijack flags, and reviewer decisions. Compare baseline and guarded runs only when the backend validates and reconciles identical scope. REVIEW, INCONCLUSIVE, and LIMIT_REACHED comparisons remain non-directional. Treat other directional changes as observations about that fixed setup, not proof of Guard causation or universal safety.

Do not publish local databases or protected raw evidence. Export only reviewed sanitized reports. Scan changes for secrets, token-shaped values, environment files, local paths, provider caches, protected trajectories, and generated Playwright artifacts before committing.

## Honest limitations

Stage 4 has no production authentication, multi-tenancy, formal reviewer identity, durable worker queue, hard process isolation, external egress policy, immutable audit log, formal compliance, clinical validation, or hosted deployment. It must not be exposed publicly or described as broad autonomous red teaming, a GOAT reproduction, a production security guarantee, or complete prompt-injection prevention.
