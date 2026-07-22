# Guard policy configuration

`configs/careguard-guard.example.yaml` is validated with Pydantic. Invalid modes, bounds, trusted source types, fallback omissions, or unknown healthcare policy mappings fail startup/reload clearly.

Configuration covers mode, enabled controls, reason-to-policy mappings, role/tool permissions, patient-scope rules, trusted and prohibited source types, redaction patterns, emergency response, confirmation tools/TTL, event retention, and safe fallbacks. It must never contain credentials.

Environment variable `CAREGUARD_GUARD_MODE=monitor|enforce` overrides the file mode. `CAREGUARD_GUARD_CONFIG` selects a local YAML path. `POST /v1/config/reload` applies a newly validated configuration; invalid configuration leaves the current process unable to reload and returns an API validation error.

Stable reason codes are evidence interfaces. Add new codes with a healthcare policy mapping and tests; do not repurpose an existing code to mean a different decision.
