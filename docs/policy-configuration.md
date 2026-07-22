# Guard policy configuration

`configs/careguard-guard.example.yaml` is validated with Pydantic. Invalid modes, bounds, trust types, missing required controls/reason mappings/tools, conflicting trusted/prohibited types, fallback omissions, or unknown policy mappings fail startup/reload clearly.

Configuration covers mode, enabled controls, reason-to-policy mappings, role/tool permissions, patient-scope rules, trusted and prohibited source types, redaction patterns, emergency response, confirmation tools/TTL, event retention, and safe fallbacks. It must never contain credentials.

Environment variable `CAREGUARD_GUARD_MODE=monitor|enforce` overrides the file mode. `CAREGUARD_GUARD_CONFIG` selects a local YAML path. `POST /v1/config/reload` applies only a newly validated configuration and returns `422` for rejected files without exposing local paths. A successful reload clears process-local confirmation and conversation-identity state; clients must start or reconfirm the affected workflow.

Stable reason codes are evidence interfaces. Add new codes with a healthcare policy mapping and tests; do not repurpose an existing code to mean a different decision.

Configuration version is copied into Guard responses, evidence, and comparisons. Stage 3 also records local policy enablement with an immutable policy ID, a generated configuration version, and a timestamp. The backend validates every requested ID and derives reason/scenario/control coverage; the frontend cannot invent mappings or rewrite IDs.

Validation is not configuration signing or change approval. Deployment access control, dependency validation beyond the current fixed pack, integrity monitoring, history, rollback, approvals, and signed governance remain production concerns. See [policy coverage](policy-coverage.md).
