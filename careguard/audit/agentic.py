"""Interfaces for a future controlled agentic audit runner; no autonomous runner is implemented."""

from dataclasses import dataclass
from typing import Protocol

from careguard.connectors.base import TargetConnector
from careguard.models.schemas import EvaluatorResult, NormalizedResponse, Scenario


class AttackerAgentAdapter(Protocol):
    async def next_message(self, objective: str, evidence: list[NormalizedResponse]) -> str: ...


class ControlledEvaluator(Protocol):
    def evaluate(self, response: NormalizedResponse, scenario: Scenario) -> list[EvaluatorResult]: ...


@dataclass(frozen=True)
class AgenticAuditLimits:
    turn_limit: int
    cost_limit_usd: float
    approved_scenario_ids: tuple[str, ...]
    authorized_hosts: tuple[str, ...] = ("localhost", "127.0.0.1")


@dataclass(frozen=True)
class FutureAgenticAuditContract:
    attacker: AttackerAgentAdapter
    target: TargetConnector
    evaluator: ControlledEvaluator
    limits: AgenticAuditLimits

