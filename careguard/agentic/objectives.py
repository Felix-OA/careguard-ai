from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

from careguard.config import load_policy_pack

from .models import AgenticObjectivePack
from .strategies import STRATEGY_IDS


KNOWN_EVALUATOR_IDS = {
    "agent_hijack_indicator", "answer_disclosure", "confirmation_handling",
    "emergency_escalation", "exact_canary_detection", "grounding",
    "patient_scope_stability", "refusal_consistency", "refusal_correctness",
    "role_stability", "source_trust", "system_disclosure", "tool_authorization",
    "tool_execution", "tool_proposal", "transformed_canary_detection",
    "unsupported_certainty", "untrusted_context_admission", "utility",
    "strategy_effectiveness",
}


@lru_cache
def load_objective_pack(path: str | Path | None = None) -> AgenticObjectivePack:
    source = Path(path) if path else Path(__file__).resolve().parents[2] / "configs" / "agentic-healthcare-objectives.yaml"
    with source.open(encoding="utf-8") as handle:
        pack = AgenticObjectivePack.model_validate(yaml.safe_load(handle))
    policy_ids = {item.policy_id for item in load_policy_pack().policies}
    for objective in pack.objectives:
        unknown = set(objective.permitted_strategy_ids) - STRATEGY_IDS
        if unknown:
            raise ValueError(f"objective {objective.objective_id} uses unknown strategies: {sorted(unknown)}")
        unknown_policies = set(objective.applicable_policy_ids) - policy_ids
        if unknown_policies:
            raise ValueError(
                f"objective {objective.objective_id} uses unknown policies: {sorted(unknown_policies)}"
            )
        unknown_evaluators = set(objective.evaluator_ids) - KNOWN_EVALUATOR_IDS
        if unknown_evaluators:
            raise ValueError(
                f"objective {objective.objective_id} uses unknown evaluators: {sorted(unknown_evaluators)}"
            )
    return pack
