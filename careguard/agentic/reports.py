from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any

from .comparison import trajectory_metrics
from .models import AgenticCampaign, AgenticComparison, AgenticReport, ObjectiveRun, TrajectoryTurn
from .objectives import load_objective_pack


BOUNDARIES = [
    "Synthetic local evaluation only.",
    "Protected raw responses and unrestricted tool arguments are excluded.",
    "No hidden reasoning or chain of thought is stored.",
    "Not a production security, clinical, or compliance guarantee.",
]


def markdown_inline(value: object) -> str:
    """Keep dynamic values on one Markdown line and neutralize raw HTML/backticks."""
    return " ".join(str(value).split()).replace("\\", "\\\\").replace("`", "\\`").replace("<", "&lt;").replace(">", "&gt;")


def campaign_report(campaign: AgenticCampaign, runs: list[ObjectiveRun], turns: list[TrajectoryTurn]) -> AgenticReport:
    outcomes = Counter(item.automated_result.value for item in runs)
    stops = Counter(item.stop_reason.value for item in runs)
    strategies = Counter(item.strategy_id for item in turns)
    objectives = {item.objective_id: item for item in load_objective_pack().objectives}
    rows = []
    for run in runs:
        objective = objectives.get(run.objective_id)
        objective_turns = [turn for turn in turns if turn.objective_run_id == run.objective_run_id]
        rows.append({
            "objective_id": run.objective_id, "result": run.automated_result.value,
            "stop_reason": run.stop_reason.value, "turn_count": run.turn_count,
            "human_review_reason": run.human_review_reason,
            "risk_category": objective.risk_category if objective else "unknown",
            "policy_ids": objective.applicable_policy_ids if objective else [],
            "severity": objective.severity if objective else "unknown",
            "metrics": trajectory_metrics(objective_turns),
            "remediation": (
                "Review the mapped policy controls and server-side authorization, context-admission, "
                "and tool-confirmation boundaries for this synthetic objective."
                if run.automated_result.value in {"FAIL", "PARTIAL", "REVIEW"} else None
            ),
        })
    aggregate_metrics = trajectory_metrics(turns)
    confirmed_findings = [row for row in rows if row["result"] == "FAIL"]
    review_items = [row for row in rows if row["result"] == "REVIEW"]
    inconclusive_items = [row for row in rows if row["result"] in {"INCONCLUSIVE", "LIMIT_REACHED"}]
    by_category = Counter(row["risk_category"] for row in rows)
    by_policy = Counter(policy for row in rows for policy in row["policy_ids"])
    disagreements = [
        {
            "objective_id": run.objective_id,
            "deterministic_result": run.deterministic_result.value,
            "judge_result": run.judge_result.outcome.value if run.judge_result else None,
        }
        for run in runs if run.disagreement
    ]
    content: dict[str, Any] = {
        "campaign": {
            "campaign_id": campaign.campaign_id, "label": campaign.label, "target_id": campaign.target_id,
            "target_path": campaign.target_path, "attacker_type": campaign.attacker_type,
            "seed": campaign.seed, "objective_pack_version": campaign.objective_pack_version,
            "strategy_pack_version": campaign.strategy_pack_version,
            "policy_pack_version": campaign.policy_pack_version, "scenario_version": campaign.scenario_version,
            "evaluator_version": campaign.evaluator_version, "status": campaign.status.value,
            "guard_mode": campaign.guard_mode,
        },
        "limits": {
            "maximum_turns_per_objective": campaign.maximum_turns_per_objective,
            "maximum_total_turns": campaign.maximum_total_turns,
            "maximum_duration_seconds": campaign.maximum_duration_seconds,
            "maximum_model_calls": campaign.maximum_model_calls,
            "cost_ceiling_usd": campaign.cost_ceiling_usd,
            "turns_used": len(turns),
            "model_calls_used": campaign.result_summary.get("model_calls", 0),
            "estimated_cost_usd": campaign.result_summary.get("estimated_cost_usd", 0),
        },
        "outcomes": dict(outcomes), "stop_reasons": dict(stops), "strategy_usage": dict(strategies),
        "results_by_category": dict(by_category), "results_by_policy": dict(by_policy),
        "trajectory_metrics": aggregate_metrics, "confirmed_findings": confirmed_findings,
        "blocked_attempts": aggregate_metrics["blocked_tool_attempts"],
        "inconclusive_or_limited": inconclusive_items, "review_required": review_items,
        "utility": {"safe_turns": aggregate_metrics["utility_safe_turns"], "total_turns": len(turns)},
        "errors": aggregate_metrics["target_errors"], "deterministic_judge_disagreements": disagreements,
        "objectives": rows,
        "turns_used": len(turns), "boundaries": BOUNDARIES,
    }
    lines = [
        f"# Controlled agentic campaign — {markdown_inline(campaign.label)}", "", "## Campaign summary", "",
        f"- Campaign: `{campaign.campaign_id}`", f"- Target path: `{campaign.target_path}`",
        f"- Attacker: `{campaign.attacker_type}`", f"- Seed: `{campaign.seed}`",
        f"- Objective pack: `{campaign.objective_pack_version}`",
        f"- Strategy pack: `{campaign.strategy_pack_version}`",
        f"- Evaluator: `{campaign.evaluator_version}`",
        f"- Turns used: `{len(turns)} / {campaign.maximum_total_turns}`",
        f"- Model calls used: `{campaign.result_summary.get('model_calls', 0)} / {campaign.maximum_model_calls}`",
        f"- Duration ceiling: `{campaign.maximum_duration_seconds} seconds`",
        f"- Cost ceiling: `{campaign.cost_ceiling_usd if campaign.cost_ceiling_usd is not None else 'not configured'}`",
        "", "## Automated outcomes", "",
    ]
    lines.extend(f"- {key}: {value}" for key, value in sorted(outcomes.items()))
    lines.extend(["", "## Objective coverage", ""])
    lines.extend(f"- Category `{key}`: {value}" for key, value in sorted(by_category.items()))
    lines.extend(f"- Policy `{key}`: {value}" for key, value in sorted(by_policy.items()))
    lines.extend(["", "## Sanitized trajectory dimensions", ""])
    lines.extend(f"- {key.replace('_', ' ').title()}: {value}" for key, value in aggregate_metrics.items())
    lines.extend(["", "## Sanitized objective summaries", ""])
    lines.extend(
        f"- `{row['objective_id']}` — {row['risk_category']} — {row['result']} — "
        f"{row['stop_reason']} — {row['turn_count']} turns"
        for row in rows
    )
    lines.extend(["", "## Review and remediation", ""])
    if not confirmed_findings and not review_items and not inconclusive_items:
        lines.append("- No confirmed, review-required, or inconclusive objective result was recorded.")
    lines.extend(
        f"- `{row['objective_id']}` — {row['result']}: {row['remediation']}"
        for row in rows if row["remediation"]
    )
    lines.extend([
        "", "## Evidence classes", "",
        f"- Confirmed FAIL findings: {len(confirmed_findings)}",
        f"- Blocked tool attempts: {aggregate_metrics['blocked_tool_attempts']}",
        f"- REVIEW outcomes: {len(review_items)}",
        f"- INCONCLUSIVE or LIMIT_REACHED outcomes: {len(inconclusive_items)}",
    ])
    lines.extend(["", "## Responsible-use boundaries", ""] + [f"- {item}" for item in BOUNDARIES])
    return AgenticReport(
        report_id=campaign.campaign_id, report_type="campaign",
        title=f"Agentic campaign — {markdown_inline(campaign.label)}",
        created_at=campaign.completed_at or datetime.now(timezone.utc), markdown="\n".join(lines),
        json_content=content, boundaries=BOUNDARIES,
    )


def comparison_report(comparison: AgenticComparison) -> AgenticReport:
    content = comparison.model_dump(mode="json")
    lines = [
        "# Controlled agentic baseline-versus-guarded comparison", "",
        f"- Comparison: `{comparison.comparison_id}`",
        f"- Identical scope: `{comparison.identical_scope}`", "", "## Objective outcomes", "",
    ]
    lines.extend(
        f"- `{row['objective_id']}` — baseline {row['baseline_result']} → guarded {row['guarded_result']} "
        f"— turns {row['baseline_turns']} → {row['guarded_turns']} "
        f"— security {row.get('security_change', 'not classified')} "
        f"— utility {row.get('utility_change', 'not classified')} — review {row['human_review_change']}"
        for row in comparison.objective_results
    )
    lines.extend(["", "## Sanitized trajectory metrics", ""])
    for label, summary in (("Baseline", comparison.baseline_summary), ("Guarded", comparison.guarded_summary)):
        lines.append(f"- {label} turns: {summary.get('turns', 0)}")
        for key, value in summary.get("trajectory_metrics", {}).items():
            lines.append(f"  - {key.replace('_', ' ')}: {value}")
    lines.extend(["", "## Observed changes", ""] + [f"- {item}" for item in comparison.observed_changes])
    lines.extend(["", "## Regressions and review", ""])
    lines.extend(f"- {item}" for item in [*comparison.regressions, *comparison.review_notes])
    lines.extend(["", "## Responsible-use boundaries", ""] + [f"- {item}" for item in BOUNDARIES])
    return AgenticReport(
        report_id=comparison.comparison_id, report_type="comparison",
        title="Controlled agentic baseline-versus-guarded comparison", created_at=comparison.created_at,
        markdown="\n".join(lines), json_content=content, boundaries=BOUNDARIES,
    )
