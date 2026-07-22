from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path

from careguard.audit import AuditRunner
from careguard.agentic.jobs import AgenticCampaignService
from careguard.agentic.models import AgenticCampaignRequest
from careguard.agentic.objectives import load_objective_pack
from careguard.config import load_scenario_pack, validate_configuration
from careguard.connectors import DemoConnector, GuardConnector
from careguard.evidence import EvidenceStore
from careguard.models.schemas import AuditSummary
from careguard.reports import compare_audits
from careguard.reports.generator import write_reports
from careguard.storage import Database
from careguard_guard.config import load_guard_config


def root() -> Path:
    return Path(os.getenv("CAREGUARD_DATA_DIR", Path.cwd() / ".careguard-data"))


def check_config() -> None:
    policies, scenarios = validate_configuration()
    guard = load_guard_config()
    objectives = load_objective_pack()
    print(
        f"Configuration valid: {len(policies.policies)} policies, {len(scenarios.scenarios)} scenarios, "
        f"{len(objectives.objectives)} agentic objectives, Guard {guard.version} ({guard.guard_mode.value})"
    )


def list_scenarios() -> None:
    for scenario in load_scenario_pack().scenarios:
        print(f"{scenario.scenario_id}\t{scenario.severity}\t{scenario.title}")


def list_agentic_objectives() -> None:
    for objective in load_objective_pack().objectives:
        print(f"{objective.objective_id}\t{objective.severity}\t{objective.maximum_turns}\t{objective.title}")


def agentic_service() -> AgenticCampaignService:
    db = Database(root() / "careguard.db")

    def connector(target):
        if target.connector_type == "demo":
            return DemoConnector()
        if target.connector_type == "guard":
            return GuardConnector(root() / "guard", mode=os.getenv("CAREGUARD_GUARD_MODE", "enforce"))
        raise ValueError("CLI agentic campaigns support only demo and demo-guarded")

    from careguard.config import load_policy_pack

    return AgenticCampaignService(db, root(), connector, lambda: load_policy_pack().version)


async def run_agentic_campaign(
    target: str, objectives: str, attacker: str, max_turns: int, max_total_turns: int,
    seed: int,
) -> None:
    objective_ids = (
        [item.objective_id for item in load_objective_pack().objectives]
        if objectives == "healthcare-safe"
        else [item.strip() for item in objectives.split(",") if item.strip()]
    )
    request = AgenticCampaignRequest(
        target_id=target, target_path="guarded" if target == "demo-guarded" else "baseline",
        objective_ids=objective_ids, attacker_type=attacker, seed=seed,
        maximum_turns_per_objective=max_turns, maximum_total_turns=max_total_turns,
        maximum_model_calls=0 if attacker == "deterministic" else max_total_turns,
        synthetic_authorized_acknowledged=True,
    )
    campaign = await agentic_service().create_and_run(request)
    print(campaign.model_dump_json(indent=2))


def compare_agentic_campaigns(baseline: str, guarded: str) -> None:
    try:
        comparison = agentic_service().compare(baseline, guarded)
    except (LookupError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc
    print(comparison.model_dump_json(indent=2))


async def run_audit(target: str) -> None:
    if target == "demo":
        connector = DemoConnector()
    elif target == "demo-guarded":
        connector = GuardConnector(root() / "guard", mode=os.getenv("CAREGUARD_GUARD_MODE", "enforce"))
    else:
        raise SystemExit("CLI supports --target demo or demo-guarded; register other local targets through the API")
    summary = await AuditRunner(connector, root() / "evidence").run(target)
    Database(root() / "careguard.db").save_audit(summary)
    print(summary.model_dump_json(indent=2))


def generate_report(latest: bool, run_id: str | None) -> None:
    db = Database(root() / "careguard.db")
    if latest:
        audits = db.list_audits()
        if not audits:
            raise SystemExit("No audits found")
        summary = audits[0]
    elif run_id:
        summary = db.get_audit(run_id)
        if summary is None:
            raise SystemExit(f"Audit not found: {run_id}")
    else:
        raise SystemExit("Use --latest or --run-id")
    records = EvidenceStore(root() / "evidence").read(summary.run_id)
    markdown, json_path = write_reports(summary, records, root() / "reports")
    print(json.dumps({"markdown": str(markdown), "json": str(json_path)}, indent=2))


def compare_runs(baseline_run_id: str, guarded_run_id: str) -> None:
    db = Database(root() / "careguard.db")
    baseline = db.get_audit(baseline_run_id)
    guarded = db.get_audit(guarded_run_id)
    if not baseline or not guarded:
        raise SystemExit("Both baseline and guarded run IDs must exist")
    store = EvidenceStore(root() / "evidence")
    try:
        summary = compare_audits(
            baseline, store.read(baseline_run_id), guarded, store.read(guarded_run_id),
            root() / "reports" / "comparisons",
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    db.save_comparison(summary)
    print(summary.model_dump_json(indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m careguard.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("check-config")
    sub.add_parser("list-scenarios")
    sub.add_parser("list-agentic-objectives")
    run = sub.add_parser("run-audit")
    run.add_argument("--target", default="demo")
    report = sub.add_parser("generate-report")
    report.add_argument("--latest", action="store_true")
    report.add_argument("--run-id")
    compare = sub.add_parser("compare-audits")
    compare.add_argument("--baseline", required=True)
    compare.add_argument("--guarded", required=True)
    agentic = sub.add_parser("run-agentic-campaign")
    agentic.add_argument("--target", choices=["demo", "demo-guarded"], required=True)
    agentic.add_argument("--objectives", default="healthcare-safe", help="healthcare-safe or comma-separated objective IDs")
    agentic.add_argument("--attacker", choices=["deterministic", "model"], default="deterministic")
    agentic.add_argument("--max-turns", type=int, default=5)
    agentic.add_argument("--max-total-turns", type=int, default=50)
    agentic.add_argument("--seed", type=int, default=42)
    agentic_compare = sub.add_parser("compare-agentic-campaigns")
    agentic_compare.add_argument("--baseline", required=True, help="replace with a completed baseline campaign ID")
    agentic_compare.add_argument("--guarded", required=True, help="replace with a completed guarded campaign ID")
    args = parser.parse_args()
    if args.command == "check-config":
        check_config()
    elif args.command == "list-scenarios":
        list_scenarios()
    elif args.command == "list-agentic-objectives":
        list_agentic_objectives()
    elif args.command == "run-audit":
        asyncio.run(run_audit(args.target))
    elif args.command == "generate-report":
        generate_report(args.latest, args.run_id)
    elif args.command == "compare-audits":
        compare_runs(args.baseline, args.guarded)
    elif args.command == "run-agentic-campaign":
        asyncio.run(run_agentic_campaign(
            args.target, args.objectives, args.attacker, args.max_turns, args.max_total_turns, args.seed,
        ))
    else:
        compare_agentic_campaigns(args.baseline, args.guarded)


if __name__ == "__main__":
    main()
