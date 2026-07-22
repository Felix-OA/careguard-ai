# Public demonstration guide

This guide runs the CareGuard AI demonstration locally with fictional healthcare data. It does not require an API key and must not be exposed to a public network.

## Prerequisites

- Docker Desktop with Docker Compose
- At least 4 GB of available memory
- Ports `3000`, `8000`, `8001`, and `8002` available on loopback
- A modern browser

## Start the demonstration

From the repository root:

```bash
cp .env.example .env
docker compose up --build --wait
```

Open the dashboard at <http://127.0.0.1:3000>.

Service URLs:

| Service | Local URL |
|---|---|
| Dashboard | <http://127.0.0.1:3000> |
| Audit API documentation | <http://127.0.0.1:8000/docs> |
| Synthetic target documentation | <http://127.0.0.1:8001/docs> |
| Guard API documentation | <http://127.0.0.1:8002/docs> |

## Synthetic-data warning

Use only the built-in fictional records and prompts. Do not enter patient information, credentials, internal documents, private URLs, or production data. The stack has no production authentication or multi-tenancy and is intended only for a local authorized demonstration.

## Onboarding walkthrough

1. Open **Onboarding**.
2. Enter a fictional organization name and confirm the synthetic-data boundary.
3. Select the built-in synthetic target.
4. Keep the local connector mapping and default key-free configuration.
5. Review the declared integration capability and enabled policy scope.
6. Run the harmless clinic-hours connection check.
7. Save the local configuration.

The browser never asks for an API key. Optional credentials are configured only as server-side environment references; their values are not sent to or displayed by the dashboard. See [company onboarding](company-onboarding.md).

## Baseline audit walkthrough

1. Open **Audits** and choose **Run audit**.
2. Select the **Baseline** path and the complete enabled scenario set.
3. Use a label such as “Public demo baseline”.
4. Start the audit and open the persisted result.
5. Inspect PASS, PARTIAL, FAIL, and REVIEW separately.
6. Expand a scenario to view sanitized evaluator, retrieval/context, and tool-state evidence.

The baseline is intentionally imperfect. FAIL results are expected in the synthetic demonstration and should not be hidden.

## Guarded audit walkthrough

1. Run another audit with the **Guarded** path.
2. Use the same scenario and policy scope as the baseline.
3. Open the result and inspect the same evidence dimensions.
4. Confirm that blocked tool proposals are not reported as executions and that REVIEW remains separate from PASS.

Guard runs in `enforce` mode by default. `monitor` mode preserves baseline behavior and is observation only.

## Comparison walkthrough

1. Open **Comparisons**.
2. Select the baseline and guarded runs created above.
3. Generate the comparison.
4. Verify the **Identical scope** banner.
5. Review outcome counts, security metrics, utility metrics, scenario-level changes, regressions, and human-review reasons.

Do not interpret the comparison as a universal security rate or causal proof. It describes only the matched synthetic suite.

## Guard-event walkthrough

1. Open **Guard events**.
2. Select a recent BLOCK, REDACT, ESCALATE, or confirmation-related event.
3. Inspect reason codes, policy mappings, source counts, tool states, and the safe decision summary.

Public event views do not contain the raw request, protected response, source excerpts, patient scope, or tool arguments.

## REVIEW queue walkthrough

1. Open **Human review**.
2. Filter to **UNREVIEWED**.
3. Inspect the automated outcome, bounded reason, evidence link, and category.
4. Open the review dialog to see how a reviewer decision and note would be stored separately.
5. Close without recording a decision unless you are intentionally demonstrating the workflow.

Reviewer decisions never rewrite the automated evidence.

## Agentic campaign walkthrough

1. Open **Agentic audit** and choose **New campaign**.
2. Select **Baseline**, the deterministic attacker, seed `731`, all ten objectives, five turns per objective, 50 total turns, 120 seconds, and zero model calls.
3. Confirm the authorized synthetic-target acknowledgement and run the campaign.
4. Repeat with the **CareGuard-protected** path using identical settings.
5. Open each campaign to inspect outcomes, explicit stop reasons, and sanitized trajectories.
6. Generate a comparison from the two matching campaigns.
7. Treat every REVIEW outcome as non-directional.

The deterministic attacker uses only server-owned strategy templates and has no shell, filesystem, browser, arbitrary network, or tool access.

## Reports

Use **Reports** or the report links on audit, campaign, and comparison pages. Dashboard reports are sanitized summaries, not protected raw-evidence downloads. Illustrative static examples are in [samples](samples/README.md).

## Clean shutdown

```bash
docker compose down
```

This preserves the named Docker data volume. Use `docker compose down -v` only when you deliberately want to delete the local demonstration data.

## Troubleshooting

- **A port is in use:** stop the conflicting local process or change the Compose mapping for local testing.
- **A service is unhealthy:** run `docker compose ps` and `docker compose logs --since=10m`.
- **Dashboard shows unavailable data:** confirm all four services are healthy and reload the page.
- **No comparison candidates appear:** complete both baseline and guarded runs with matching scope first.
- **Comparison is rejected:** align scenario/objective order, versions, seed, attacker, limits, and target paths.
- **Campaign launch is disabled:** accept the synthetic authorized-target acknowledgement.
- **Old review records appear:** current counts exclude superseded items; history remains available and labelled.
- **Configuration changed:** restart with `docker compose down` followed by `docker compose up --build --wait`.

For deeper setup details, see the main [README](../README.md), [dashboard guide](dashboard-guide.md), and [operator safety guide](agentic-operator-safety.md).

