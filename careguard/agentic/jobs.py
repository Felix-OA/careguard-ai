from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

from careguard.config import load_policy_pack, load_scenario_pack
from careguard.models.schemas import Target
from careguard_guard.config import load_guard_config

from .attacker import DeterministicAttacker, ModelAttacker
from .comparison import compare_campaigns
from .evaluator import TrajectoryEvaluator
from .evidence import EvidenceWriter, safe_text
from .models import (
    AgenticCampaign, AgenticCampaignRequest, AgenticComparison, AgenticObjective,
    CampaignStatus, ObjectiveRun, TrajectoryTurn,
)
from .judge import ModelTrajectoryJudge
from .objectives import load_objective_pack
from .orchestrator import CampaignRunner
from .reports import campaign_report, comparison_report
from .strategies import STRATEGY_PACK_VERSION


ACTIVE_STATUSES = {CampaignStatus.QUEUED, CampaignStatus.RUNNING}


class AgenticCampaignService:
    def __init__(
        self,
        database: Any,
        data_root: Path,
        connector_factory: Callable[[Target], Any],
        policy_version: Callable[[], str],
    ) -> None:
        self.database = database
        self.data_root = data_root
        self.connector_factory = connector_factory
        self.policy_version = policy_version
        self._recover_interrupted_campaigns()

    def _recover_interrupted_campaigns(self) -> None:
        for campaign in self.campaigns():
            if campaign.status in ACTIVE_STATUSES:
                recovered = campaign.model_copy(update={
                    "status": CampaignStatus.FAILED,
                    "completed_at": datetime.now(timezone.utc),
                    "error": "Campaign interrupted before durable completion.",
                })
                self.database.save_agentic_campaign(
                    recovered.campaign_id, recovered.submitted_at, recovered.model_dump_json(),
                )

    def campaigns(self) -> list[AgenticCampaign]:
        output: list[AgenticCampaign] = []
        for payload in self.database.list_agentic_campaign_payloads():
            try:
                output.append(AgenticCampaign.model_validate_json(payload))
            except Exception:
                continue
        return output

    def campaign(self, campaign_id: str) -> AgenticCampaign | None:
        payload = self.database.get_agentic_campaign_payload(campaign_id)
        try:
            return AgenticCampaign.model_validate_json(payload) if payload else None
        except Exception:
            return None

    def objective_runs(self, campaign_id: str) -> list[ObjectiveRun]:
        return [
            ObjectiveRun.model_validate_json(payload)
            for payload in self.database.list_agentic_objective_payloads(campaign_id)
        ]

    def turns(self, campaign_id: str, objective_run_id: str | None = None) -> list[TrajectoryTurn]:
        return [
            TrajectoryTurn.model_validate_json(payload)
            for payload in self.database.list_agentic_turn_payloads(campaign_id, objective_run_id)
        ]

    def objectives(self, objective_ids: list[str]) -> list[AgenticObjective]:
        pack = load_objective_pack()
        mapping = {item.objective_id: item for item in pack.objectives}
        unknown = set(objective_ids) - mapping.keys()
        if unknown:
            raise ValueError(f"unknown agentic objective IDs: {sorted(unknown)}")
        if len(objective_ids) != len(set(objective_ids)):
            raise ValueError("agentic objective IDs must not be duplicated")
        return [mapping[item] for item in objective_ids]

    def _validate_target(self, request: AgenticCampaignRequest) -> Target:
        target = self.database.get_target(request.target_id)
        if not target:
            raise LookupError("target not found")
        is_guard = target.connector_type == "guard"
        if request.target_path == "guarded" and not is_guard:
            raise ValueError("guarded campaigns require an authorized Guard target")
        if request.target_path == "baseline" and is_guard:
            raise ValueError("baseline campaigns cannot use a Guard target")
        if target.target_id == "demo" and request.target_path != "baseline":
            raise ValueError("the demo target is baseline-only")
        if target.target_id == "demo-guarded" and request.target_path != "guarded":
            raise ValueError("the demo-guarded target is guarded-only")
        return target

    async def create_and_run(self, request: AgenticCampaignRequest) -> AgenticCampaign:
        request = request.model_copy(update={"label": safe_text(request.label, 120)})
        target = self._validate_target(request)
        objectives = self.objectives(request.objective_ids)
        signature = (
            request.target_id, request.target_path, tuple(request.objective_ids), request.attacker_type, request.seed,
            request.maximum_turns_per_objective, request.maximum_total_turns,
            request.maximum_duration_seconds, request.maximum_model_calls,
            request.cost_ceiling_usd, request.judge_enabled,
        )
        for item in self.campaigns():
            existing_signature = (
                item.target_id, item.target_path, tuple(item.objective_ids), item.attacker_type, item.seed,
                item.maximum_turns_per_objective, item.maximum_total_turns,
                item.maximum_duration_seconds, item.maximum_model_calls,
                item.cost_ceiling_usd, item.judge_enabled,
            )
            if item.status in ACTIVE_STATUSES and signature == existing_signature:
                raise RuntimeError("an equivalent agentic campaign is already active")
        pack = load_objective_pack()
        campaign = AgenticCampaign.queued(
            f"ac-{uuid4().hex[:24]}", request,
            guard_mode=load_guard_config().guard_mode.value if request.target_path == "guarded" else None,
            objective_pack_version=pack.version,
            strategy_pack_version=STRATEGY_PACK_VERSION,
            policy_pack_version=self.policy_version(),
            scenario_version=load_scenario_pack().version,
            evaluator_version=TrajectoryEvaluator.version,
        )
        attacker = DeterministicAttacker() if request.attacker_type == "deterministic" else ModelAttacker()
        judge = ModelTrajectoryJudge() if request.judge_enabled else None
        connector = self.connector_factory(target)
        writer = EvidenceWriter(self.database)
        # Validate every optional component and the configured connector before publishing QUEUED.
        # Initialization failures therefore cannot leave a campaign permanently active.
        writer.save_campaign(campaign)
        runner = CampaignRunner(
            connector, attacker, TrajectoryEvaluator(), writer,
            is_cancelled=lambda campaign_id: bool(
                (current := self.campaign(campaign_id)) and current.cancellation_requested
            ), judge=judge,
        )
        return await runner.run(campaign, objectives)

    def cancel(self, campaign_id: str) -> AgenticCampaign | None:
        campaign = self.campaign(campaign_id)
        if not campaign:
            return None
        if campaign.status not in ACTIVE_STATUSES:
            raise RuntimeError("only queued or running campaigns can be cancelled")
        updated = campaign.model_copy(update={"cancellation_requested": True})
        self.database.save_agentic_campaign(campaign_id, campaign.submitted_at, updated.model_dump_json())
        return updated

    def comparisons(self) -> list[AgenticComparison]:
        return [
            AgenticComparison.model_validate_json(payload)
            for payload in self.database.list_agentic_comparison_payloads()
        ]

    def comparison(self, comparison_id: str) -> AgenticComparison | None:
        payload = self.database.get_agentic_comparison_payload(comparison_id)
        return AgenticComparison.model_validate_json(payload) if payload else None

    def compare(self, baseline_id: str, guarded_id: str) -> AgenticComparison:
        baseline, guarded = self.campaign(baseline_id), self.campaign(guarded_id)
        if not baseline or not guarded:
            raise LookupError("both agentic campaigns must exist")
        comparison = compare_campaigns(
            baseline, self.objective_runs(baseline_id), guarded, self.objective_runs(guarded_id),
            self.turns(baseline_id), self.turns(guarded_id),
        )
        self.database.save_agentic_comparison(
            comparison.comparison_id, comparison.created_at, comparison.model_dump_json(),
        )
        return comparison

    def campaign_report(self, campaign_id: str):
        campaign = self.campaign(campaign_id)
        if not campaign:
            return None
        return campaign_report(campaign, self.objective_runs(campaign_id), self.turns(campaign_id))

    def comparison_report(self, comparison_id: str):
        comparison = self.comparison(comparison_id)
        return comparison_report(comparison) if comparison else None
