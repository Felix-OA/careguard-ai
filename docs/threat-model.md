# Threat model

## Assets and trust boundaries

Assets are fictional records and identifiers, system/policy instructions, admitted context, simulated tool state, Guard decisions, protected raw responses, audit evidence, and optional connector credentials. User input, claimed roles, retrieved documents, target output, and tool arguments are untrusted until the applicable control succeeds. Authorization must come from server metadata, not message text.

## Modeled threats

- Cross-patient access, record requests without verified scope, and fake authority.
- Confidential retrieval, untrusted instruction admission, and top-k loss after filtering.
- Synthetic canary, email, patient, appointment, insurance, or fixture-name disclosure.
- System-instruction extraction, poison markers, unsupported certainty, and ungrounded claims.
- Missing emergency escalation or required human review.
- Unauthorized simulated tools, confirmation bypass, changed actions, and expired confirmations.
- Credentials or authorization material accidentally copied into events/evidence.

## Guard limitations

Deterministic indicators can miss paraphrases and can produce false positives. Monitor mode intentionally permits target behavior. External proxy-only integrations cannot inspect or filter target context. Process-local confirmation state is a bounded demonstration and not authentication. Protected local files still require host access control.

## Out of scope

Real patients or clinical systems, public targets, dangerous medical content, malware, denial of service, production identity, compliance certification, clinical validation, regulatory approval, and broad autonomous jailbreak activity are excluded.
