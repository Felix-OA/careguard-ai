from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

from careguard.config import load_scenario_pack
from careguard.models.schemas import AuditSummary, EvidenceRecord, Result


def build_report(summary: AuditSummary, records: list[EvidenceRecord]) -> dict:
    scenario_map = {item.scenario_id: item for item in load_scenario_pack().scenarios}
    findings = [record for record in records if record.final_result != Result.PASS]
    severity = Counter(record.severity for record in findings)
    dimensions = Counter(
        key for record in findings for key, enabled in record.evidence_flags.items() if enabled
    )
    affected_policies: dict[str, set[str]] = defaultdict(set)
    for record in findings:
        for policy_id in scenario_map[record.scenario_id].applicable_policy_ids:
            affected_policies[policy_id].add(record.scenario_id)
    return {
        "title": "CareGuard AI Synthetic Local Assessment",
        "executive_summary": {
            "run_id": summary.run_id,
            "target_id": summary.target_id,
            "counts": summary.counts,
            "finding_count": len(findings),
        },
        "scope": "Controlled local assessment using fictional healthcare data and deterministic scenarios.",
        "target": {"target_id": summary.target_id, "scenario_count": len(records)},
        "scenario_coverage": [record.scenario_id for record in records],
        "findings_by_severity": dict(severity),
        "findings_by_dimension": dict(dimensions),
        "retrieval_vs_answer": {
            "retrieval_exposure": dimensions.get("retrieval_exposure", 0),
            "context_admission": dimensions.get("context_admission", 0),
            "answer_disclosure": dimensions.get("answer_disclosure", 0),
        },
        "tool_findings": {
            "tool_proposal": dimensions.get("tool_proposal", 0),
            "tool_execution": dimensions.get("tool_execution", 0),
        },
        "affected_policies": {key: sorted(value) for key, value in affected_policies.items()},
        "findings": [
            {
                "scenario_id": record.scenario_id,
                "result": record.final_result.value,
                "severity": record.severity,
                "expected_behavior": record.expected_behavior,
                "answer": record.raw_answer,
                "evaluator_results": [item.model_dump(mode="json") for item in record.evaluator_results],
            }
            for record in findings
        ],
        "remediation_recommendations": [
            "Enforce server-side subject and role authorization before retrieval or tool use.",
            "Filter untrusted and confidential sources before context assembly.",
            "Require explicit confirmation immediately before sensitive tool execution.",
            "Constrain health information to approved sources and calibrated language.",
        ],
        "limitations": [
            "Synthetic local assessment only.",
            "Not a compliance certification.",
            "Not clinical validation.",
            "Not a production security guarantee.",
            "Deterministic evaluators may require qualified human review for context-sensitive cases.",
        ],
        "responsible_use": "Use only on localhost or targets you are explicitly authorized to assess. Do not use real patient data.",
    }


def report_json(summary: AuditSummary, records: list[EvidenceRecord]) -> str:
    return json.dumps(build_report(summary, records), indent=2, sort_keys=True)


def report_markdown(summary: AuditSummary, records: list[EvidenceRecord]) -> str:
    report = build_report(summary, records)
    counts = report["executive_summary"]["counts"]
    lines = [
        "# CareGuard AI Synthetic Local Assessment",
        "",
        "## Executive summary",
        "",
        f"Run `{summary.run_id}` assessed target `{summary.target_id}` across {len(records)} scenarios. "
        f"Results: PASS {counts.get('PASS', 0)}, PARTIAL {counts.get('PARTIAL', 0)}, "
        f"FAIL {counts.get('FAIL', 0)}, REVIEW {counts.get('REVIEW', 0)}.",
        "",
        "## Scope and target",
        "",
        report["scope"],
        f"Target: `{summary.target_id}`. Scenario coverage: {', '.join(report['scenario_coverage'])}.",
        "",
        "## Findings by severity",
        "",
    ]
    for severity, count in sorted(report["findings_by_severity"].items()):
        lines.append(f"- {severity}: {count}")
    lines += ["", "## Retrieval versus answer findings", ""]
    for key, count in report["retrieval_vs_answer"].items():
        lines.append(f"- {key.replace('_', ' ')}: {count}")
    lines += ["", "## Tool-related findings", ""]
    for key, count in report["tool_findings"].items():
        lines.append(f"- {key.replace('_', ' ')}: {count}")
    lines += ["", "## Affected policies", ""]
    for policy_id, scenario_ids in sorted(report["affected_policies"].items()):
        lines.append(f"- `{policy_id}`: {', '.join(scenario_ids)}")
    lines += ["", "## Reproducible evidence", ""]
    for finding in report["findings"]:
        lines += [
            f"### {finding['scenario_id']} — {finding['result']} ({finding['severity']})", "",
            f"Expected: {finding['expected_behavior']}", "",
            f"Observed synthetic answer: {finding['answer']}", "",
        ]
    lines += ["## Remediation recommendations", ""]
    lines.extend(f"- {item}" for item in report["remediation_recommendations"])
    lines += ["", "## Limitations", ""]
    lines.extend(f"- {item}" for item in report["limitations"])
    lines += ["", "## Responsible use", "", report["responsible_use"], ""]
    return "\n".join(lines)


def write_reports(summary: AuditSummary, records: list[EvidenceRecord], directory: Path) -> tuple[Path, Path]:
    directory.mkdir(parents=True, exist_ok=True)
    markdown_path = directory / f"{summary.run_id}.md"
    json_path = directory / f"{summary.run_id}.json"
    markdown_path.write_text(report_markdown(summary, records), encoding="utf-8")
    json_path.write_text(report_json(summary, records), encoding="utf-8")
    return markdown_path, json_path

