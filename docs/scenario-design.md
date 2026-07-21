# Scenario design

The versioned YAML pack contains safe, deterministic objectives. Every scenario declares its role, turns, expected behavior, failure indicators, evaluators, risk attributes, tags, policies, and human-review requirement.

Scenario authors should:

- Use only unmistakably fictional names, `example.test` emails, `PAT-CG-*` identifiers, and synthetic canaries.
- Describe the security property being tested without operational jailbreak or harmful medical content.
- Attach evaluators that measure the relevant layer: retrieval exposure, context admission, answer disclosure, tool proposal, tool execution, refusal correctness, grounding, or utility.
- Use `REVIEW` where a deterministic rule cannot establish correctness. A valid safe alternative should be `PASS`, not automatically `PARTIAL`.
- Include benign controls so a target that refuses everything does not appear safe.

Run `python -m careguard.cli check-config` after changes. It rejects duplicate IDs and unknown policy references.

