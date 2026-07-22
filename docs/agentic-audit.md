# Controlled agentic audit

Stage 4 adds a local, synthetic, authorized, bounded, observable, reproducible, and interruptible multi-turn evaluation loop. It is inspired by the high-level objective/attacker/target/evaluator pattern associated with GOAT. It is not an official GOAT implementation, reproduction, certification, benchmark, or claim of research equivalence.

## Execution loop

1. Validate the acknowledged campaign, enabled local target, baseline/guarded path, objective IDs, and hard limits.
2. Persist `QUEUED`, then `RUNNING` state.
3. Send the objective's server-owned safe starting message with fixed synthetic role/scope metadata.
4. Normalize the target response and evaluate deterministic signals.
5. Sanitize and size-limit the observation before an attacker can see it.
6. Stop, or select one approved strategy and generate the next message from a server-owned template.
7. Evaluate the complete trajectory, optionally obtain secondary judge evidence, and route ambiguity to REVIEW.
8. Atomically persist the objective outcome and sanitized turns before advancing or releasing the terminal campaign result.

The default deterministic attacker requires no network, API key, model, or paid service. Given the same objective version, seed, and prior sanitized trajectory, its selection order is reproducible. The campaign records objective, strategy, policy, scenario, and evaluator versions so comparisons can reject mismatched scope.

## Limits and stops

Campaign input bounds turns per objective (1–10), total turns (1–100), duration (5–600 seconds), model calls (0–50), and optional estimated cost (0–10 USD). Model calls are preflighted so the configured call or estimated-cost ceiling is not crossed, and provider/target/judge waits share the campaign duration ceiling. Objective maxima can only reduce the campaign turn limit. Explicit stops cover confirmed objectives, stable safety, objective/campaign limits, target errors, policy boundaries, human review, cancellation, repeated invalid agent output, and target-output safety indicators.

The cost value is a conservative local per-call estimate for budget control, not provider billing telemetry or a financial record.

Emergency objectives stop after the first expected safe escalation. REVIEW is never counted as PASS. A blocked tool proposal is not an execution, raw retrieval is not admitted context, a redacted answer is not visible disclosure, and a useful safe alternative can PASS.

## Optional model components

The attacker and judge are independently disabled by default. When deliberately enabled, they use a configured OpenAI-compatible endpoint whose exact origin must be listed and must be an unauthenticated HTTP loopback IP. Inputs contain only the objective rubric and sanitized bounded trajectory. There are no tools. Output is structured and bounded. The model attacker may select only an objective-approved strategy; the server replaces its message with the safe template. Invalid/provider output uses deterministic fallback and repeated invalid output stops. The judge stores a concise outcome/rationale only, cannot override deterministic severe findings, and disagreement becomes REVIEW.

## Interfaces

The API exposes objective/strategy catalogs, campaign creation/history/detail/cancellation, objective runs, trajectories, reports, comparisons, and comparison reports under `/agentic`. The CLI exposes `list-agentic-objectives`, `run-agentic-campaign`, and `compare-agentic-campaigns`. The dashboard exposes history, wizard, detail, trajectory, comparison, report, and review-queue flows.

There is no separate worker in Stage 4. Synchronous execution avoids a new port/service/secret boundary but is not a durable queue. Cancellation is cooperative and requires another API request to set the persisted flag. Restart recovery marks unfinished records failed.

## Limitations

Deterministic patterns and fixed safe templates do not establish general adversarial coverage, prompt-injection prevention, clinical validity, compliance, or production security. No public targets, real patient data, autonomous hacking, unrestricted prompts, arbitrary tools, shell/code execution, browser/computer use, messaging, filesystem access, hosted execution, or cloud deployment is supported.
