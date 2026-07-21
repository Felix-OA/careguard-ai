from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path

from careguard.audit import AuditRunner
from careguard.config import load_scenario_pack, validate_configuration
from careguard.connectors import DemoConnector
from careguard.evidence import EvidenceStore
from careguard.models.schemas import AuditSummary
from careguard.reports.generator import write_reports
from careguard.storage import Database


def root() -> Path:
    return Path(os.getenv("CAREGUARD_DATA_DIR", Path.cwd() / ".careguard-data"))


def check_config() -> None:
    policies, scenarios = validate_configuration()
    print(f"Configuration valid: {len(policies.policies)} policies, {len(scenarios.scenarios)} scenarios")


def list_scenarios() -> None:
    for scenario in load_scenario_pack().scenarios:
        print(f"{scenario.scenario_id}\t{scenario.severity}\t{scenario.title}")


async def run_audit(target: str) -> None:
    if target != "demo":
        raise SystemExit("CLI Stage 1 shortcut supports --target demo; register other local targets through the API")
    summary = await AuditRunner(DemoConnector(), root() / "evidence").run(target)
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


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m careguard.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("check-config")
    sub.add_parser("list-scenarios")
    run = sub.add_parser("run-audit")
    run.add_argument("--target", default="demo")
    report = sub.add_parser("generate-report")
    report.add_argument("--latest", action="store_true")
    report.add_argument("--run-id")
    args = parser.parse_args()
    if args.command == "check-config":
        check_config()
    elif args.command == "list-scenarios":
        list_scenarios()
    elif args.command == "run-audit":
        asyncio.run(run_audit(args.target))
    else:
        generate_report(args.latest, args.run_id)


if __name__ == "__main__":
    main()

