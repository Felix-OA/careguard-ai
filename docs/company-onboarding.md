# Company onboarding

`/onboarding` guides a local evaluator through organization profile, target type, connector mapping, credentials, declared capability, policies, a harmless connection check, and initial audit actions. The backend requires confirmation that only synthetic or explicitly authorized test data will be used and stores organization/target state in the local SQLite database.

## Credentials and targets

The form never accepts a secret value. It may select only an allowlisted server-side environment-variable name. Configure its value in `.env` or deployment configuration and restart the services. API responses omit both the value and configured reference name, returning only `Not configured`, `Configured server-side`, or `Unavailable`. The frontend uses neither `localStorage` nor `sessionStorage`.

REST/OpenAI-compatible targets require an explicit ownership/authorization acknowledgement. Stage 3 accepts only exact HTTP origins on ports `8001` or `8002`; REST chat paths are `/chat` or `/v1/chat`, and the OpenAI-compatible path is `/v1/chat/completions`. URL credentials, queries, fragments, redirects, other ports, public hosts, unsupported schemes, arbitrary discovery, and scanning are rejected. The default `demo` path is deterministic, offline, fictional, and key-free. Production integrations require stronger DNS/IP revalidation and network egress restrictions.

Capability choices are declarations: proxy-only can inspect surfaced I/O, deep retrieval requires authorized pre-context hooks, and tool control requires surfaced proposal/confirmation/execution boundaries. CareGuard does not infer capabilities or claim hidden visibility.

Policy IDs are immutable. The backend validates selected IDs and derives mappings. Local changes are saved atomically under a monotonically increasing configuration version; future dashboard audits use enabled-policy scope and bind that version into evidence, while historical evidence retains its original version. There is no signed governance or approval workflow. After saving, the connection test sends only a harmless synthetic clinic-hours prompt and returns a sanitized status. Audit jobs are local and synchronous beneath a persisted status abstraction; progress advances only when the runner completes the requested scope. An interrupted active job is recovered as failed on API restart, but there is no cancellation, worker lease, scheduling, or distributed execution.
