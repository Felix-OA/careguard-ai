from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from careguard import __version__
from careguard.audit.evaluators import evaluate, final_result
from careguard.config import load_policy_pack, load_scenario_pack
from careguard.connectors.base import TargetConnector
from careguard.evidence import EvidenceStore
from careguard.models.schemas import (
    AuditSummary, ChatTurn, EvidenceRecord, NormalizedRequest, NormalizedResponse, Result, Scenario,
)


class AuditRunner:
    def __init__(self, connector: TargetConnector, evidence_directory: Path) -> None:
        self.connector = connector
        self.evidence_store = EvidenceStore(evidence_directory)

    async def run(self, target_id: str = "demo", scenario_ids: list[str] | None = None) -> AuditSummary:
        policy_pack = load_policy_pack()
        scenario_pack = load_scenario_pack()
        scenarios = [item for item in scenario_pack.scenarios if item.enabled]
        if scenario_ids is not None:
            requested = set(scenario_ids)
            scenarios = [item for item in scenarios if item.scenario_id in requested]
            missing = requested - {item.scenario_id for item in scenarios}
            if missing:
                raise ValueError(f"unknown or disabled scenario IDs: {sorted(missing)}")
        started = datetime.now(timezone.utc)
        run_id = f"cg-{started.strftime('%Y%m%dT%H%M%SZ')}-{uuid4().hex[:8]}"
        counts: Counter[str] = Counter({result.value: 0 for result in Result})
        for scenario in scenarios:
            record = await self._run_scenario(run_id, target_id, scenario, scenario_pack.version, policy_pack.version)
            self.evidence_store.write(record)
            counts[record.final_result.value] += 1
        completed = datetime.now(timezone.utc)
        return AuditSummary(
            run_id=run_id,
            target_id=target_id,
            started_at=started,
            completed_at=completed,
            counts=dict(counts),
            evidence_path=str(self.evidence_store.path_for(run_id)),
        )

    async def _run_scenario(
        self, run_id: str, target_id: str, scenario: Scenario, scenario_version: str, policy_version: str
    ) -> EvidenceRecord:
        history: list[ChatTurn] = []
        sources, proposed, executed = [], [], []
        latency = 0.0
        last = NormalizedResponse(target_id=target_id, conversation_id=scenario.scenario_id)
        for turn in scenario.conversation_turns:
            request = NormalizedRequest(
                target_id=target_id,
                conversation_id=f"{run_id}:{scenario.scenario_id}",
                user_message=turn.user,
                conversation_history=list(history),
                role_metadata={"role": scenario.initial_role, "synthetic": "true"},
            )
            history.append(ChatTurn(role="user", content=turn.user))
            last = await self.connector.send(request)
            history.append(ChatTurn(role="assistant", content=last.answer or ""))
            sources.extend(last.retrieved_sources)
            proposed.extend(last.proposed_tool_calls)
            executed.extend(last.executed_tool_calls)
            latency += last.latency_ms
            if last.error:
                break
        combined = last.model_copy(
            update={
                "retrieved_sources": sources,
                "proposed_tool_calls": proposed,
                "executed_tool_calls": executed,
                "latency_ms": latency,
            }
        )
        evaluator_results = evaluate(combined, scenario)
        result = final_result(evaluator_results, scenario.human_review_required)
        failed_dimensions = {
            item.dimension for item in evaluator_results if item.result in {Result.FAIL, Result.REVIEW}
        }
        flags = {
            "retrieval_exposure": "retrieval_exposure" in failed_dimensions,
            "context_admission": "context_admission" in failed_dimensions,
            "answer_disclosure": "answer_disclosure" in failed_dimensions,
            "tool_proposal": "tool_proposal" in failed_dimensions,
            "tool_execution": "tool_execution" in failed_dimensions,
            "refusal_correctness": "refusal_correctness" in failed_dimensions,
            "grounding": "grounding" in failed_dimensions,
            "utility": "utility" in failed_dimensions,
        }
        return EvidenceRecord(
            run_id=run_id,
            timestamp=datetime.now(timezone.utc),
            product_version=__version__,
            scenario_version=scenario_version,
            policy_pack_version=policy_version,
            scenario_id=scenario.scenario_id,
            target_id=target_id,
            provider=last.provider,
            model=last.model,
            conversation_turns=history,
            expected_behavior=scenario.expected_behavior,
            raw_answer=last.answer,
            retrieved_sources=sources,
            proposed_tool_calls=proposed,
            executed_tool_calls=executed,
            evaluator_results=evaluator_results,
            final_result=result,
            severity=scenario.severity,
            likelihood=scenario.likelihood,
            impact=scenario.impact,
            evidence_flags=flags,
            manual_review_notes="Scenario requires qualified human review." if scenario.human_review_required else None,
            latency_ms=latency,
            error=last.error,
        )

