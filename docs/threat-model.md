# Threat model

This model covers the synthetic, local Stage 1 Audit, Stage 2 Guard, Stage 3 dashboard, and Stage 4 controlled agentic runner. It is not a clinical, privacy, legal, or compliance assessment.

## Assets

- Fictional records, controlled identifiers, appointment references, and canaries.
- System and policy instructions, source trust labels, admitted context, and target responses.
- Simulated tool proposals, authorization decisions, confirmations, and tool state.
- Guard configuration, reason codes, security events, protected raw responses, audit evidence, and reports.
- Optional connector credentials held in server-side connector state.
- Organization, target, policy, audit-job, and reviewer-decision metadata in the local dashboard database.
- Agentic objective definitions, campaign limits, sanitized observations, strategy selections, trajectories, stop reasons, evaluator/judge outcomes, and comparisons.

## Actors and capabilities

- An unauthenticated guest can send arbitrary bounded messages and claim a role or identity in text.
- A synthetic patient can attempt same-patient and cross-patient requests or manipulate conversation state.
- A claimed staff user can assert authority; only server-supplied role metadata is considered by the demonstration control.
- An untrusted document author can place indirect instructions in retrieved content.
- A target or connector can return malformed, unsafe, overconfident, tool-bearing, or secret-shaped output.
- A malicious synthetic target can try to hijack the attacker using instruction-like text, request environment access, inflate observations, or smuggle reasoning-, secret-, or path-shaped values into evidence.
- A local operator can change configuration, storage, environment variables, or service mode. A host administrator is trusted and can access local protected files.

Attackers may transform controlled strings, replay or mutate confirmation state, mix multiple policy triggers, manipulate tool arguments, exploit scope changes, or try to confuse raw retrieval with admitted context. Network denial of service, host compromise, and arbitrary code execution are outside this bounded model.

## Trust boundaries

1. Client to Audit or Guard API: request text and client-provided metadata are untrusted. The demo accepts role and patient-scope metadata only to exercise policy logic; production identity must come from an authenticated upstream identity adapter.
2. Guard to retrieval/generation integration: retrieved content and target output are untrusted. The local demo hooks are a deep-integration test fixture, not a recommended production API.
3. Retrieval candidates to model context: only explicitly admitted trusted sources cross this boundary in enforce mode. Raw retrieval and admitted context are recorded separately.
4. Model proposal to tool execution: proposal, authorization, confirmation, execution, failure, and blocking are separate states.
5. Runtime to storage/reporting: events and evidence are sanitized, permissions are restricted, and protected responses remain local. Storage success is required before an enforce response is released.
6. Configuration to runtime: validated configuration controls behavior. Configuration files and reload authority are trusted operational inputs and require deployment access controls outside this repository.
7. Browser to dashboard aggregation: all browser input is untrusted. nginx same-origin routing reaches only the Audit API; dashboard schemas must remove paths, secrets, protected references, raw authorization metadata, excerpts, and stack traces before rendering.
8. Dashboard API to configured target: only exact local synthetic origins and allowlisted chat paths are accepted with explicit operator acknowledgement. Redirects are disabled and timeouts/responses are bounded. Production DNS/IP rebinding defenses and egress policy remain out of scope.
9. Target output to agentic attacker: output is quoted untrusted observation data, size-limited, and sanitized. It cannot add strategies, change campaign limits, invoke tools, or become executable instructions.
10. Optional model attacker/judge: server-side only, disabled by default, no tools, exact loopback-IP HTTP origin, structured bounded output, sanitized inputs, deterministic fallback, and deterministic severe-finding authority.

## Modeled threats and controls

- Unauthorized or cross-patient synthetic record access, missing scope, fake authority, and identity/scope changes within a conversation.
- Direct prompt injection, indirect retrieved-document injection, system-instruction extraction, source-trust confusion, and trusted-context exhaustion.
- Synthetic identifier, canary, fixture-name, poison-marker, event, evidence, and protected-response leakage.
- Unsupported medical certainty or claims, personalized medication instructions, missing emergency escalation, and inappropriate reassurance.
- Unauthorized tool proposal or execution, confirmation omission, expiry, replay, changed conversation/action/arguments/scope, and execution failure.
- External connector overclaiming: proxy-only integrations cannot enforce context admission without an authorized retrieval/generation boundary.
- Configuration tampering or invalid reload: schema validation rejects missing controls/mappings and invalid values, but deployment-level file integrity is residual risk.
- Monitor-mode misunderstanding: monitor intentionally preserves unsafe baseline behavior and is never an enforcement control.
- Dashboard attacks: stored/reflected HTML, malicious Markdown, path traversal, unbounded queries, arbitrary targets, secret-shaped input, verbose errors, and confusion between automated results and reviewer decisions.
- Agentic attacks: strategy escape, prompt injection from target output, repeated malformed provider output, hidden-reasoning capture, resource exhaustion, cancellation races, target-path mismatch, scope-mismatched comparisons, and evidence-write failure.

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
- The dashboard is an unauthenticated single-operator local demonstration. Any process or user with loopback/host access may change local target, review, and policy state.
- The application target allowlist reduces the local demonstration's SSRF surface but cannot provide production network isolation or protect a compromised host.
- Audit jobs are synchronous and process-local; restart recovery marks unfinished records failed but does not provide leases, distributed locking, cancellation, or exactly-once execution.
- Agentic campaigns are synchronous and process-local. Cooperative cancellation, bounded target adapters, and restart recovery reduce risk but do not supply worker isolation, hard process preemption, or distributed coordination.
- Configuration validation does not provide signing, change approval, rollback, or tamper detection.
- Proxy-only connectors cannot see hidden retrieval or tools that a target does not surface.
