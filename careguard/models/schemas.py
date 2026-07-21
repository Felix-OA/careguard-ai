from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Result(StrEnum):
    PASS = "PASS"
    PARTIAL = "PARTIAL"
    FAIL = "FAIL"
    REVIEW = "REVIEW"


class ChatTurn(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str


class SourceMetadata(BaseModel):
    source_id: str
    title: str
    trust_level: Literal[
        "trusted_clinical", "trusted_operational", "untrusted", "confidential_synthetic"
    ]
    admitted_to_context: bool = True
    excerpt: str | None = None


class ToolCall(BaseModel):
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    authorized: bool = False
    confirmed: bool = False


class NormalizedRequest(BaseModel):
    target_id: str
    conversation_id: str
    user_message: str
    conversation_history: list[ChatTurn] = Field(default_factory=list)
    role_metadata: dict[str, str] = Field(default_factory=dict)


class NormalizedResponse(BaseModel):
    target_id: str
    conversation_id: str
    answer: str = ""
    retrieved_sources: list[SourceMetadata] = Field(default_factory=list)
    proposed_tool_calls: list[ToolCall] = Field(default_factory=list)
    executed_tool_calls: list[ToolCall] = Field(default_factory=list)
    latency_ms: float = 0
    provider: str = "deterministic-local"
    model: str = "careguard-demo-v1"
    error: str | None = None


class Policy(BaseModel):
    policy_id: str
    title: str
    description: str
    category: str
    severity: Literal["low", "medium", "high", "critical"]
    expected_behavior: str
    failure_indicators: list[str]
    applicable_roles: list[str]
    enabled: bool = True
    references: list[str] = Field(default_factory=list)
    remediation_guidance: str


class PolicyPack(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: str
    name: str
    disclaimer: str
    policies: list[Policy]

    @field_validator("policies")
    @classmethod
    def unique_policy_ids(cls, value: list[Policy]) -> list[Policy]:
        ids = [item.policy_id for item in value]
        if len(ids) != len(set(ids)):
            raise ValueError("policy IDs must be unique")
        return value


class ScenarioTurn(BaseModel):
    user: str


class Scenario(BaseModel):
    scenario_id: str
    title: str
    category: str
    description: str
    initial_role: str
    conversation_turns: list[ScenarioTurn]
    expected_behavior: str
    failure_indicators: list[str]
    evaluator_ids: list[str]
    severity: Literal["low", "medium", "high", "critical"]
    likelihood: Literal["unlikely", "possible", "likely"]
    impact: Literal["low", "medium", "high", "critical"]
    tags: list[str]
    applicable_policy_ids: list[str]
    human_review_required: bool = False
    enabled: bool = True


class ScenarioPack(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: str
    scenarios: list[Scenario]

    @field_validator("scenarios")
    @classmethod
    def unique_scenario_ids(cls, value: list[Scenario]) -> list[Scenario]:
        ids = [item.scenario_id for item in value]
        if len(ids) != len(set(ids)):
            raise ValueError("scenario IDs must be unique")
        return value


class TargetCreate(BaseModel):
    target_id: str
    name: str
    connector_type: Literal["demo", "rest", "openai_compatible"] = "demo"
    endpoint: str | None = None
    model: str | None = None


class Target(TargetCreate):
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class EvaluatorResult(BaseModel):
    evaluator_id: str
    result: Result
    dimension: Literal[
        "retrieval_exposure", "context_admission", "answer_disclosure", "tool_proposal",
        "tool_execution", "refusal_correctness", "grounding", "utility"
    ]
    detail: str


class EvidenceRecord(BaseModel):
    run_id: str
    timestamp: datetime
    product_version: str
    scenario_version: str
    policy_pack_version: str
    scenario_id: str
    target_id: str
    provider: str
    model: str
    conversation_turns: list[ChatTurn]
    expected_behavior: str
    raw_answer: str
    retrieved_sources: list[SourceMetadata]
    proposed_tool_calls: list[ToolCall]
    executed_tool_calls: list[ToolCall]
    evaluator_results: list[EvaluatorResult]
    final_result: Result
    severity: str
    likelihood: str
    impact: str
    evidence_flags: dict[str, bool]
    manual_review_notes: str | None = None
    latency_ms: float
    error: str | None = None


class AuditRequest(BaseModel):
    target_id: str = "demo"
    scenario_ids: list[str] | None = None


class AuditSummary(BaseModel):
    run_id: str
    target_id: str
    started_at: datetime
    completed_at: datetime
    counts: dict[str, int]
    evidence_path: str

