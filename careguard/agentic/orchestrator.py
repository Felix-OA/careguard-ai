from __future__ import annotations

import asyncio
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
from time import monotonic
from typing import Callable, Protocol

from careguard.connectors.base import TargetConnector
from careguard.models.schemas import ChatTurn, NormalizedRequest, NormalizedResponse

from .attacker import AttackerAgent
from .evaluator import TrajectoryEvaluator
from .evidence import EvidenceWriter, safe_sources, safe_text, safe_tools
from .models import (
    AgentDecision, AgenticCampaign, AgenticObjective, AgenticOutcome, CampaignStatus,
    ObjectiveRun, StopReason, TrajectoryTurn,
)
from .judge import TrajectoryJudge
from .stop_conditions import (
    MODEL_CALL_COST_USD, LimitState, campaign_limit_reason, model_call_preflight_reason,
    objective_stop_reason,
)


class TargetAdapter(Protocol):
    async def send(self, request: NormalizedRequest): ...


class StopCondition(Protocol):
    def __call__(self, turns: list[TrajectoryTurn], maximum_turns: int) -> StopReason | None: ...


class CampaignRunner:
    """Bounded orchestrator. Target responses are data and never executable instructions."""

    def __init__(
        self,
        target: TargetConnector,
        attacker: AttackerAgent,
        evaluator: TrajectoryEvaluator,
        evidence_writer: EvidenceWriter,
        *,
        is_cancelled: Callable[[str], bool] | None = None,
        judge: TrajectoryJudge | None = None,
    ) -> None:
        self.target = target
        self.attacker = attacker
        self.evaluator = evaluator
        self.evidence_writer = evidence_writer
        self.is_cancelled = is_cancelled or (lambda _campaign_id: False)
        self.judge = judge

    async def run(self, campaign: AgenticCampaign, objectives: list[AgenticObjective]) -> AgenticCampaign:
        started_clock = monotonic()
        campaign = campaign.model_copy(update={
            "status": CampaignStatus.RUNNING, "started_at": datetime.now(timezone.utc),
            "provider_model_display_name": safe_text(self.attacker.provider_display_name, 160),
        })
        self.evidence_writer.save_campaign(campaign)
        total_turns = 0
        model_calls = 0
        estimated_cost = 0.0
        objective_runs: list[ObjectiveRun] = []
        try:
            for objective_index, objective in enumerate(objectives):
                limit = campaign_limit_reason(LimitState(
                    started_monotonic=started_clock, total_turns=total_turns,
                    maximum_total_turns=campaign.maximum_total_turns,
                    maximum_duration_seconds=campaign.maximum_duration_seconds,
                    model_calls=model_calls, maximum_model_calls=campaign.maximum_model_calls,
                    estimated_cost_usd=estimated_cost, cost_ceiling_usd=campaign.cost_ceiling_usd,
                ), self.is_cancelled(campaign.campaign_id))
                if limit:
                    campaign = self._terminal_for_limit(campaign, limit, total_turns, model_calls, objective_runs)
                    self.evidence_writer.save_campaign(campaign)
                    return campaign
                objective_run, turns, model_call_count = await self._run_objective(
                    campaign, objective, objective_index, total_turns, model_calls, started_clock,
                )
                total_turns += len(turns)
                model_calls += model_call_count
                estimated_cost = model_calls * MODEL_CALL_COST_USD
                objective_runs.append(objective_run)
                interim = campaign.model_copy(update={
                    "result_summary": self._summary(objective_runs, total_turns, model_calls),
                })
                self.evidence_writer.commit_objective(interim, objective_run, turns)
                if self.is_cancelled(campaign.campaign_id):
                    campaign = self._terminal_for_limit(
                        interim, StopReason.CANCELLED, total_turns, model_calls, objective_runs,
                    )
                    self.evidence_writer.save_campaign(campaign)
                    return campaign
                if objective_run.stop_reason in {
                    StopReason.CANCELLED, StopReason.MAX_TOTAL_TURNS_REACHED,
                    StopReason.TIME_LIMIT_REACHED, StopReason.MODEL_CALL_LIMIT_REACHED,
                    StopReason.COST_LIMIT_REACHED,
                }:
                    campaign = self._terminal_for_limit(
                        interim, objective_run.stop_reason, total_turns, model_calls, objective_runs,
                    )
                    self.evidence_writer.save_campaign(campaign)
                    return campaign
            if self.is_cancelled(campaign.campaign_id):
                campaign = self._terminal_for_limit(
                    campaign, StopReason.CANCELLED, total_turns, model_calls, objective_runs,
                )
                self.evidence_writer.save_campaign(campaign)
                return campaign
            status = CampaignStatus.LIMIT_REACHED if any(
                item.automated_result == AgenticOutcome.LIMIT_REACHED for item in objective_runs
            ) else CampaignStatus.COMPLETED
            campaign = campaign.model_copy(update={
                "status": status, "completed_at": datetime.now(timezone.utc),
                "result_summary": self._summary(objective_runs, total_turns, model_calls),
            })
            self.evidence_writer.save_campaign(campaign)
            return campaign
        except Exception as exc:
            failed = campaign.model_copy(update={
                "status": CampaignStatus.FAILED, "completed_at": datetime.now(timezone.utc),
                "error": f"Agentic campaign failed: {type(exc).__name__}",
                "result_summary": self._summary(objective_runs, total_turns, model_calls),
            })
            # A failed campaign is useful only if its terminal state is durable. If this write
            # also fails, propagate the storage error rather than reporting false completion.
            self.evidence_writer.save_campaign(failed)
            return failed

    async def _run_objective(
        self, campaign: AgenticCampaign, objective: AgenticObjective, objective_index: int,
        prior_total_turns: int, prior_model_calls: int, started_clock: float,
    ) -> tuple[ObjectiveRun, list[TrajectoryTurn], int]:
        started_at = datetime.now(timezone.utc)
        digest = sha256(f"{campaign.campaign_id}:{objective.objective_id}:{objective_index}".encode()).hexdigest()[:24]
        objective_run_id = f"aor-{digest}"
        conversation_id = f"agentic:{campaign.campaign_id}:{objective.objective_id}"
        turns: list[TrajectoryTurn] = []
        target_history: list[ChatTurn] = []
        stop_reason: StopReason | None = None
        invalid_outputs = 0
        model_calls = 0
        maximum_turns = min(campaign.maximum_turns_per_objective, objective.maximum_turns)
        while stop_reason is None:
            external_limit = campaign_limit_reason(LimitState(
                started_monotonic=started_clock, total_turns=prior_total_turns + len(turns),
                maximum_total_turns=campaign.maximum_total_turns,
                maximum_duration_seconds=campaign.maximum_duration_seconds,
                model_calls=prior_model_calls + model_calls,
                maximum_model_calls=campaign.maximum_model_calls,
                estimated_cost_usd=(prior_model_calls + model_calls) * MODEL_CALL_COST_USD,
                cost_ceiling_usd=campaign.cost_ceiling_usd,
            ), self.is_cancelled(campaign.campaign_id))
            if external_limit:
                stop_reason = external_limit
                break
            if not turns:
                decision = AgentDecision(
                    strategy_id="direct_request", decision_summary="Used the objective's approved starting message.",
                    test_message=objective.safe_starting_message, validation_result="approved",
                )
            else:
                if campaign.attacker_type == "model":
                    projected = model_call_preflight_reason(LimitState(
                        started_monotonic=started_clock,
                        total_turns=prior_total_turns + len(turns),
                        maximum_total_turns=campaign.maximum_total_turns,
                        maximum_duration_seconds=campaign.maximum_duration_seconds,
                        model_calls=prior_model_calls + model_calls,
                        maximum_model_calls=campaign.maximum_model_calls,
                        estimated_cost_usd=(prior_model_calls + model_calls) * MODEL_CALL_COST_USD,
                        cost_ceiling_usd=campaign.cost_ceiling_usd,
                    ))
                    if projected:
                        stop_reason = projected
                        break
                    remaining_seconds = campaign.maximum_duration_seconds - (monotonic() - started_clock)
                    if remaining_seconds <= 0:
                        stop_reason = StopReason.TIME_LIMIT_REACHED
                        break
                    model_calls += 1
                else:
                    remaining_seconds = campaign.maximum_duration_seconds - (monotonic() - started_clock)
                try:
                    decision = await asyncio.wait_for(
                        self.attacker.decide(objective, turns, campaign.seed),
                        timeout=max(0.001, remaining_seconds),
                    )
                except asyncio.TimeoutError:
                    stop_reason = StopReason.TIME_LIMIT_REACHED
                    break
                if decision.validation_result == "fallback":
                    invalid_outputs += 1
                    if invalid_outputs >= 2:
                        stop_reason = StopReason.INVALID_AGENT_OUTPUT
                        break
            if decision.strategy_id not in objective.permitted_strategy_ids:
                stop_reason = StopReason.INVALID_AGENT_OUTPUT
                break
            request = NormalizedRequest(
                target_id=campaign.target_id, conversation_id=conversation_id,
                user_message=decision.test_message, conversation_history=list(target_history),
                role_metadata={
                    "role": objective.initial_role, "synthetic": "true",
                    "agentic_objective_id": objective.objective_id,
                },
            )
            target_history.append(ChatTurn(role="user", content=decision.test_message))
            remaining_seconds = campaign.maximum_duration_seconds - (monotonic() - started_clock)
            try:
                response = await asyncio.wait_for(
                    self.target.send(request), timeout=max(0.001, remaining_seconds),
                )
            except asyncio.TimeoutError:
                stop_reason = StopReason.TIME_LIMIT_REACHED
                break
            except Exception as exc:
                response = NormalizedResponse(
                    target_id=campaign.target_id, conversation_id=conversation_id,
                    error=f"target adapter error: {type(exc).__name__}",
                )
            target_history.append(ChatTurn(role="assistant", content=response.answer or ""))
            evaluation_response = response if campaign.target_path == "guarded" else response.model_copy(
                update={"guard_metadata": {}}
            )
            signals, hijack = self.evaluator.evaluate_turn(objective, evaluation_response)
            sources, admitted, rejected = safe_sources(evaluation_response)
            finding_count = sum(
                1 for prior in turns for signal in prior.evaluator_signals if signal.status == "finding"
            ) + sum(1 for signal in signals if signal.status == "finding")
            safe_count = sum(
                1 for prior in turns for signal in prior.evaluator_signals if signal.status == "safe"
            ) + sum(1 for signal in signals if signal.status == "safe")
            turn = TrajectoryTurn(
                campaign_id=campaign.campaign_id, objective_run_id=objective_run_id,
                objective_id=objective.objective_id, objective_version=objective.version,
                target_id=campaign.target_id, target_path=campaign.target_path,
                attacker_type=campaign.attacker_type, seed=campaign.seed,
                turn_number=len(turns) + 1, strategy_id=decision.strategy_id,
                strategy_summary=safe_text(decision.decision_summary, 300),
                user_test_message=safe_text(decision.test_message, 1200),
                sanitized_target_response=safe_text(response.answer),
                response_origin="guard" if campaign.target_path == "guarded" else "target",
                retrieved_sources=sources, admitted_context=admitted, rejected_context=rejected,
                proposed_tools=safe_tools(evaluation_response.proposed_tool_calls),
                blocked_tools=safe_tools(evaluation_response.blocked_tool_calls),
                executed_tools=safe_tools(evaluation_response.executed_tool_calls),
                evaluator_signals=signals,
                cumulative_state={
                    "turns": len(turns) + 1, "findings": finding_count, "safe_signals": safe_count,
                    "invalid_agent_outputs": invalid_outputs,
                },
                agent_hijack_indicators=hijack, timestamp=datetime.now(timezone.utc),
                latency_ms=(
                    response.latency_ms if 0 <= response.latency_ms <= 600_000 else 0
                ),
                provider=safe_text(response.provider, 120), model=safe_text(response.model, 120),
                guard_mode=(
                    safe_text(str(response.guard_metadata.get("guard_mode", "")), 20) or None
                    if campaign.target_path == "guarded" else None
                ),
                policy_pack_version=campaign.policy_pack_version,
                scenario_version=campaign.scenario_version,
                evaluator_version=campaign.evaluator_version,
                error=safe_text(response.error, 300) or None,
            )
            turns.append(turn)
            stop_reason = objective_stop_reason(
                turns, maximum_turns=maximum_turns,
                emergency_objective=objective.risk_category == "emergency_escalation",
                human_review_required=objective.human_review_required,
                allowed_stop_reasons=set(objective.stop_conditions),
            )
        stop_reason = stop_reason or StopReason.MAX_TURNS_REACHED
        judge_result = None
        if self.judge and stop_reason not in {
            StopReason.CANCELLED, StopReason.TIME_LIMIT_REACHED, StopReason.MODEL_CALL_LIMIT_REACHED,
            StopReason.COST_LIMIT_REACHED, StopReason.TARGET_ERROR, StopReason.INVALID_AGENT_OUTPUT,
        }:
            projected = model_call_preflight_reason(LimitState(
                started_monotonic=started_clock,
                total_turns=prior_total_turns + len(turns),
                maximum_total_turns=campaign.maximum_total_turns,
                maximum_duration_seconds=campaign.maximum_duration_seconds,
                model_calls=prior_model_calls + model_calls,
                maximum_model_calls=campaign.maximum_model_calls,
                estimated_cost_usd=(prior_model_calls + model_calls) * MODEL_CALL_COST_USD,
                cost_ceiling_usd=campaign.cost_ceiling_usd,
            ))
            if projected:
                stop_reason = projected
            else:
                remaining_seconds = campaign.maximum_duration_seconds - (monotonic() - started_clock)
                if remaining_seconds <= 0:
                    stop_reason = StopReason.TIME_LIMIT_REACHED
                else:
                    model_calls += 1
                    try:
                        judge_result = await asyncio.wait_for(
                            self.judge.evaluate(objective, turns), timeout=remaining_seconds,
                        )
                    except asyncio.TimeoutError:
                        stop_reason = StopReason.TIME_LIMIT_REACHED
        final, deterministic, disagreement, evaluator_summary = self.evaluator.final_result(
            objective, turns, stop_reason, judge_result,
        )
        review_reason = None
        if final == AgenticOutcome.REVIEW or disagreement:
            review_reason = objective.human_review_reason or (
                "The optional secondary judge disagreed with the deterministic evaluator; human review is required."
            )
        if turns:
            turns[-1] = turns[-1].model_copy(update={
                "stop_reason": stop_reason, "final_automated_result": final,
                "judge_result": judge_result, "disagreement": disagreement,
                "human_review_reason": review_reason,
            })
        return ObjectiveRun(
            objective_run_id=objective_run_id, campaign_id=campaign.campaign_id,
            objective_id=objective.objective_id, objective_version=objective.version,
            target_id=campaign.target_id, target_path=campaign.target_path,
            started_at=started_at, completed_at=datetime.now(timezone.utc), turn_count=len(turns),
            stop_reason=stop_reason, automated_result=final, deterministic_result=deterministic,
            judge_result=judge_result, disagreement=disagreement, human_review_reason=review_reason,
            evaluator_summary=evaluator_summary,
        ), turns, model_calls

    @staticmethod
    def _summary(runs: list[ObjectiveRun], turns: int, model_calls: int) -> dict:
        counts = Counter(item.automated_result.value for item in runs)
        stops = Counter(item.stop_reason.value for item in runs)
        return {
            "objective_count": len(runs), "turn_count": turns, "model_calls": model_calls,
            "outcomes": dict(counts), "stop_reasons": dict(stops),
            "review_count": counts[AgenticOutcome.REVIEW.value],
            "estimated_cost_usd": round(model_calls * MODEL_CALL_COST_USD, 6),
        }

    @classmethod
    def _terminal_for_limit(
        cls, campaign: AgenticCampaign, reason: StopReason, total_turns: int,
        model_calls: int, runs: list[ObjectiveRun],
    ) -> AgenticCampaign:
        status = CampaignStatus.CANCELLED if reason == StopReason.CANCELLED else CampaignStatus.LIMIT_REACHED
        return campaign.model_copy(update={
            "status": status, "completed_at": datetime.now(timezone.utc),
            "cancellation_requested": reason == StopReason.CANCELLED or campaign.cancellation_requested,
            "result_summary": cls._summary(runs, total_turns, model_calls) | {
                "campaign_stop_reason": reason.value,
            },
        })
