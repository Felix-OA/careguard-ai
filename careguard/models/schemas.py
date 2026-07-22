from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Result(StrEnum):
    PASS = "PASS"
    PARTIAL = "PARTIAL"
    FAIL = "FAIL"
    REVIEW = "REVIEW"


class ChatTurn(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str = Field(max_length=20_000)


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
    conversation_id: str = Field(min_length=1, max_length=160, pattern=r"^[A-Za-z0-9:._-]+$")
    user_message: str = Field(min_length=1, max_length=10_000)
    conversation_history: list[ChatTurn] = Field(default_factory=list, max_length=50)
    role_metadata: dict[str, str] = Field(default_factory=dict)


class NormalizedResponse(BaseModel):
    target_id: str
    conversation_id: str
    answer: str = ""
    retrieved_sources: list[SourceMetadata] = Field(default_factory=list)
    proposed_tool_calls: list[ToolCall] = Field(default_factory=list)
    blocked_tool_calls: list[ToolCall] = Field(default_factory=list)
    failed_tool_calls: list[ToolCall] = Field(default_factory=list)
    executed_tool_calls: list[ToolCall] = Field(default_factory=list)
    latency_ms: float = 0
    provider: str = "deterministic-local"
    model: str = "careguard-demo-v1"
    error: str | None = None
    guard_metadata: dict[str, Any] = Field(default_factory=dict)


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
    human_review_reason: str | None = None
    enabled: bool = True

    @model_validator(mode="after")
    def require_review_reason(self) -> "Scenario":
        if self.human_review_required and not self.human_review_reason:
            raise ValueError("human_review_reason is required when human_review_required is true")
        if not self.human_review_required and self.human_review_reason:
            raise ValueError("human_review_reason requires human_review_required=true")
        return self


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
    target_id: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9._-]+$")
    name: str = Field(min_length=1, max_length=160)
    connector_type: Literal["demo", "guard", "rest", "openai_compatible"] = "demo"
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
    blocked_tool_calls: list[ToolCall] = Field(default_factory=list)
    failed_tool_calls: list[ToolCall] = Field(default_factory=list)
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
    guard_mode: str | None = None
    guard_config_version: str | None = None
    guard_event_id: str | None = None
    guard_final_decision: str | None = None


class AuditRequest(BaseModel):
    target_id: str = Field(default="demo", min_length=1, max_length=80, pattern=r"^[A-Za-z0-9._-]+$")
    scenario_ids: list[str] | None = Field(default=None, max_length=100)


class AuditSummary(BaseModel):
    run_id: str
    target_id: str
    started_at: datetime
    completed_at: datetime
    counts: dict[str, int]
    evidence_path: str


class ComparisonRequest(BaseModel):
    baseline_run_id: str = Field(min_length=1, max_length=120, pattern=r"^[A-Za-z0-9._-]+$")
    guarded_run_id: str = Field(min_length=1, max_length=120, pattern=r"^[A-Za-z0-9._-]+$")


class ComparisonSummary(BaseModel):
    comparison_id: str
    created_at: datetime
    baseline_run_id: str
    guarded_run_id: str
    baseline_target_id: str
    guarded_target_id: str
    identical_scope: bool
    scenario_ids: list[str]
    scope_validation: dict[str, Any] = Field(default_factory=dict)
    policy_configuration: dict[str, Any] = Field(default_factory=dict)
    baseline_metrics: dict[str, Any]
    guarded_metrics: dict[str, Any]
    security_improvements: list[str]
    unchanged_risks: list[str]
    regressions: list[str]
    false_positives: list[str]
    utility_tradeoffs: list[str]
    scenario_results: list[dict[str, Any]] = Field(default_factory=list)
    manual_review_notes: list[str]
    markdown_report_path: str
    json_report_path: str
