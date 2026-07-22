# Threat model

This model covers the synthetic, local Stage 1 Audit and Stage 2 Guard implementation. It is not a clinical, privacy, legal, or compliance assessment.

## Assets

- Fictional records, controlled identifiers, appointment references, and canaries.
- System and policy instructions, source trust labels, admitted context, and target responses.
- Simulated tool proposals, authorization decisions, confirmations, and tool state.
- Guard configuration, reason codes, security events, protected raw responses, audit evidence, and reports.
- Optional connector credentials held in server-side connector state.

## Actors and capabilities

- An unauthenticated guest can send arbitrary bounded messages and claim a role or identity in text.
- A synthetic patient can attempt same-patient and cross-patient requests or manipulate conversation state.
- A claimed staff user can assert authority; only server-supplied role metadata is considered by the demonstration control.
- An untrusted document author can place indirect instructions in retrieved content.
- A target or connector can return malformed, unsafe, overconfident, tool-bearing, or secret-shaped output.
- A local operator can change configuration, storage, environment variables, or service mode. A host administrator is trusted and can access local protected files.

Attackers may transform controlled strings, replay or mutate confirmation state, mix multiple policy triggers, manipulate tool arguments, exploit scope changes, or try to confuse raw retrieval with admitted context. Network denial of service, host compromise, and arbitrary code execution are outside this bounded model.

## Trust boundaries

1. Client to Audit or Guard API: request text and client-provided metadata are untrusted. The demo accepts role and patient-scope metadata only to exercise policy logic; production identity must come from an authenticated upstream identity adapter.
2. Guard to retrieval/generation integration: retrieved content and target output are untrusted. The local demo hooks are a deep-integration test fixture, not a recommended production API.
3. Retrieval candidates to model context: only explicitly admitted trusted sources cross this boundary in enforce mode. Raw retrieval and admitted context are recorded separately.
4. Model proposal to tool execution: proposal, authorization, confirmation, execution, failure, and blocking are separate states.
5. Runtime to storage/reporting: events and evidence are sanitized, permissions are restricted, and protected responses remain local. Storage success is required before an enforce response is released.
6. Configuration to runtime: validated configuration controls behavior. Configuration files and reload authority are trusted operational inputs and require deployment access controls outside this repository.

## Modeled threats and controls

- Unauthorized or cross-patient synthetic record access, missing scope, fake authority, and identity/scope changes within a conversation.
- Direct prompt injection, indirect retrieved-document injection, system-instruction extraction, source-trust confusion, and trusted-context exhaustion.
- Synthetic identifier, canary, fixture-name, poison-marker, event, evidence, and protected-response leakage.
- Unsupported medical certainty or claims, personalized medication instructions, missing emergency escalation, and inappropriate reassurance.
- Unauthorized tool proposal or execution, confirmation omission, expiry, replay, changed conversation/action/arguments/scope, and execution failure.
- External connector overclaiming: proxy-only integrations cannot enforce context admission without an authorized retrieval/generation boundary.
- Configuration tampering or invalid reload: schema validation rejects missing controls/mappings and invalid values, but deployment-level file integrity is residual risk.
- Monitor-mode misunderstanding: monitor intentionally preserves unsafe baseline behavior and is never an enforcement control.

## Assumptions

- All records, identities, tools, and documents are synthetic and the default system stays offline.
- Local files, environment variables, configuration, service-to-service networking, and operator access are protected by the host/deployment.
- Role and patient-scope metadata is supplied by a trusted upstream adapter in any future real integration; message text is never identity proof.
- The deterministic target and fixed suite are repeatable demonstrations, not representative clinical validation.

## Non-goals

Real patients or clinical systems, production authentication/authorization, public target testing, dangerous medical instructions, malware, availability testing, broad autonomous red teaming, HIPAA compliance, clinical validation, regulatory approval, and complete prompt-injection prevention are out of scope.

## Residual risks

- Pattern rules can miss semantic paraphrases and produce false positives; qualified review remains necessary.
- Monitor mode permits the target's unsafe content and tool behavior. It must not be deployed or described as protection.
- Confirmation and conversation state are process-local and disappear on restart/reload; they are not transaction security.
- Public event metadata is minimized, but local event and protected-response stores intentionally retain sanitized synthetic evidence and remain sensitive to host access.
- The message hash supports deterministic correlation/integrity checks; it is not anonymization and can be vulnerable to guessing for low-entropy messages.
- The event store and SQLite indexes are single-node development components without production audit-log immutability, encryption, distributed locking, or access control.
- Configuration validation does not provide signing, change approval, rollback, or tamper detection.
- Proxy-only connectors cannot see hidden retrieval or tools that a target does not surface.
