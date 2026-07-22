# Agentic evidence and reports

Stage 4 uses the existing local SQLite database with four new logical records: campaigns, objective runs, trajectory turns, and comparisons. Existing review decisions remain in their separate table. Local databases and generated evidence/report directories are ignored by Git and created with restricted permissions.

## Stored trajectory data

Each turn records campaign/objective-run/objective identity and version, target/path, attacker/seed, turn and strategy, concise strategy summary, safe test message, sanitized response, target versus Guard origin derived from the configured path, source metadata without excerpts, admitted/rejected context, bounded tool states with names sanitized and argument keys/values excluded, evaluator signals, cumulative counters, hijack flags, timestamp/latency, sanitized provider/model labels, Guard mode, configuration versions, and sanitized error. The final turn also binds the stop reason, final automated result, optional judge summary, disagreement flag, and review reason. The objective-run record preserves those terminal fields even when no turn is produced by an early limit/cancellation.

Raw target conversation state exists only in process for the current bounded objective. Evidence does not store API keys, authorization headers, environment values, protected raw response references/content, source excerpts, unrestricted tool arguments, local protected paths, or hidden/private reasoning. Secret-shaped strings, fixed synthetic protected identifiers, local paths, and reasoning-shaped blocks are replaced before persistence. Observation size is capped at 4,000 characters.

Campaign state is saved before execution. Each objective result and all of its sanitized turns are committed with updated campaign state in one SQLite transaction. The final campaign is saved only after objective evidence. Recovery changes interrupted QUEUED/RUNNING campaigns to FAILED. Reviewer decisions are separate append/update state and never rewrite the automated record.

## Reports

Campaign and comparison report endpoints return typed Markdown plus JSON. Campaign reports include configuration/version and limit-usage summaries, objective/policy/category coverage, outcome/stop/strategy counts, separate trajectory dimensions, confirmed findings, blocked attempts, REVIEW and inconclusive results, utility/error counts, remediation prompts, and responsible-use boundaries. Comparison reports only accept matching objectives/versions, strategy pack, seed, attacker/judge configuration, limits, and policy/scenario/evaluator versions with correct baseline/guarded paths. Before comparison, every objective run, contiguous trajectory turn, final-result binding, and campaign summary is reconciled; incomplete completed campaigns, duplicate/orphan evidence, and cross-campaign records are rejected.

Reports summarize sanitized evidence rather than publishing raw transcripts. They do not imply causation outside the fixed synthetic setup and do not claim compliance, clinical validation, universal security, prompt-injection prevention, or production readiness.
