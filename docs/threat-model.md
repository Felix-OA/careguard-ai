# Threat model

## Assets

- Synthetic patient records, identifiers, appointment references, and canaries.
- System instructions and policy boundaries.
- Target authorization state and simulated tool controls.
- Assessment evidence and optional connector credentials.

## Modeled threats

- Cross-patient access and authority claimed only in natural language.
- Over-broad retrieval and confidential-source admission.
- Retrieved untrusted instructions and conflicting sources.
- System-instruction extraction and synthetic canary disclosure.
- Unsupported diagnostic certainty or personalized medication direction.
- Missing emergency escalation, grounding, confirmation, or human review.
- Unauthorized simulated tool proposals or executions.
- Secrets accidentally copied into evidence.

## Trust boundaries

User input, retrieved documents, connector responses, and tool arguments are untrusted until policy checks succeed. Authorization must come from server-managed identity metadata, not prompt assertions. Simulated tools never contact external services.

## Out of scope

Real patients and clinical systems, public targets, dangerous medical content, malware, denial-of-service testing, regulatory certification, clinical validation, and broad autonomous jailbreak activity are excluded.

