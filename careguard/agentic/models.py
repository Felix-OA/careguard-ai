from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from careguard.models.schemas import SourceMetadata, ToolCall


class AgenticOutcome(StrEnum):
    PASS = "PASS"
    PARTIAL = "PARTIAL"
    FAIL = "FAIL"
    REVIEW = "REVIEW"
    INCONCLUSIVE = "INCONCLUSIVE"
    LIMIT_REACHED = "LIMIT_REACHED"


class CampaignStatus(StrEnum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    LIMIT_REACHED = "LIMIT_REACHED"


class StopReason(StrEnum):
    OBJECTIVE_CONFIRMED = "OBJECTIVE_CONFIRMED"
    SAFE_BOUNDARY_STABLE = "SAFE_BOUNDARY_STABLE"
    MAX_TURNS_REACHED = "MAX_TURNS_REACHED"
    MAX_TOTAL_TURNS_REACHED = "MAX_TOTAL_TURNS_REACHED"
    TIME_LIMIT_REACHED = "TIME_LIMIT_REACHED"
    MODEL_CALL_LIMIT_REACHED = "MODEL_CALL_LIMIT_REACHED"
    COST_LIMIT_REACHED = "COST_LIMIT_REACHED"
    TARGET_ERROR = "TARGET_ERROR"
    POLICY_BOUNDARY_REACHED = "POLICY_BOUNDARY_REACHED"
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"
    CANCELLED = "CANCELLED"
    INVALID_AGENT_OUTPUT = "INVALID_AGENT_OUTPUT"
    SAFETY_BOUNDARY_TRIGGERED = "SAFETY_BOUNDARY_TRIGGERED"


class AgenticStrategy(BaseModel):
    model_config = ConfigDict(extra="forbid")
    strategy_id: str = Field(pattern=r"^[a-z][a-z0-9_]{2,40}$")
    title: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1, max_length=300)
    safe_by_design: bool = True


class AgenticObjective(BaseModel):
    model_config = ConfigDict(extra="forbid")
    objective_id: str = Field(pattern=r"^CG-AO-[0-9]{3}$")
    version: str = Field(pattern=r"^[0-9]+\.[0-9]+$")
    title: str = Field(min_length=1, max_length=140)
    description: str = Field(min_length=1, max_length=500)
    risk_category: str = Field(pattern=r"^[a-z][a-z0-9_]{2,50}$")
    initial_role: Literal["guest", "patient"]
    synthetic_patient_scope: str | None = Field(default=None, pattern=r"^PAT-CG-[0-9]{4}$")
    permitted_strategy_ids: list[str] = Field(min_length=1, max_length=10)
    maximum_turns: int = Field(ge=1, le=10)
    success_indicators: list[str] = Field(min_length=1, max_length=12)
    safe_behavior_indicators: list[str] = Field(min_length=1, max_length=12)
    prohibited_content_classes: list[str] = Field(min_length=1, max_length=12)
    applicable_policy_ids: list[str] = Field(min_length=1, max_length=15)
    evaluator_ids: list[str] = Field(min_length=1, max_length=20)
    severity: Literal["low", "medium", "high", "critical"]
    likelihood: Literal["unlikely", "possible", "likely"]
    impact: Literal["low", "medium", "high", "critical"]
    human_review_required: bool = False
    human_review_reason: str | None = Field(default=None, max_length=500)
    stop_conditions: list[StopReason] = Field(min_length=1, max_length=10)
    safe_starting_message: str = Field(min_length=1, max_length=1200)
    expected_limitations: list[str] = Field(min_length=1, max_length=10)

    @model_validator(mode="after")
    def validate_review_reason(self) -> "AgenticObjective":
        if self.human_review_required != bool(self.human_review_reason):
            raise ValueError("human-review requirement and reason must be configured together")
        if len(self.permitted_strategy_ids) != len(set(self.permitted_strategy_ids)):
            raise ValueError("permitted strategy IDs must be unique")
        if "direct_request" not in self.permitted_strategy_ids:
            raise ValueError("the safe starting turn requires the direct_request strategy")
        if len(self.stop_conditions) != len(set(self.stop_conditions)):
            raise ValueError("stop conditions must be unique")
        if StopReason.MAX_TURNS_REACHED not in self.stop_conditions:
            raise ValueError("every objective must declare MAX_TURNS_REACHED")
        return self


class AgenticObjectivePack(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: str
    name: str
    disclaimer: str
    objectives: list[AgenticObjective]

    @field_validator("objectives")
    @classmethod
    def unique_objectives(cls, value: list[AgenticObjective]) -> list[AgenticObjective]:
        identities = [(item.objective_id, item.version) for item in value]
        if len(identities) != len(set(identities)):
            raise ValueError("agentic objective IDs and versions must be unique")
        return value


class AgentDecision(BaseModel):
    strategy_id: str
    decision_summary: str = Field(max_length=300)
    test_message: str = Field(min_length=1, max_length=1200)
    validation_result: Literal["approved", "fallback"]


class TrajectorySignal(BaseModel):
    evaluator_id: str
    dimension: str
    status: Literal["safe", "finding", "review", "inconclusive"]
    detail: str = Field(max_length=300)


class JudgeResult(BaseModel):
    outcome: AgenticOutcome
    rationale_summary: str = Field(max_length=500)
    provider: str
    model: str


class TrajectoryTurn(BaseModel):
    campaign_id: str
    objective_run_id: str
    objective_id: str
    objective_version: str
    target_id: str
    target_path: Literal["baseline", "guarded"]
    attacker_type: Literal["deterministic", "model"]
    seed: int
    turn_number: int = Field(ge=1, le=100)
    strategy_id: str
    strategy_summary: str
    user_test_message: str
    sanitized_target_response: str
    response_origin: Literal["target", "guard"]
    retrieved_sources: list[SourceMetadata] = Field(default_factory=list, max_length=100)
    admitted_context: list[SourceMetadata] = Field(default_factory=list, max_length=100)
    rejected_context: list[SourceMetadata] = Field(default_factory=list, max_length=100)
    proposed_tools: list[ToolCall] = Field(default_factory=list, max_length=100)
    blocked_tools: list[ToolCall] = Field(default_factory=list, max_length=100)
    executed_tools: list[ToolCall] = Field(default_factory=list, max_length=100)
    evaluator_signals: list[TrajectorySignal] = Field(default_factory=list, max_length=100)
    cumulative_state: dict[str, int | bool | str] = Field(default_factory=dict)
    agent_hijack_indicators: list[str] = Field(default_factory=list)
    timestamp: datetime
    latency_ms: float = 0
    provider: str
    model: str
    guard_mode: str | None = None
    policy_pack_version: str
    scenario_version: str
    evaluator_version: str
    error: str | None = None
    stop_reason: StopReason | None = None
    final_automated_result: AgenticOutcome | None = None
    judge_result: JudgeResult | None = None
    disagreement: bool = False
    human_review_reason: str | None = None


class ObjectiveRun(BaseModel):
    objective_run_id: str
    campaign_id: str
    objective_id: str
    objective_version: str
    target_id: str
    target_path: Literal["baseline", "guarded"]
    started_at: datetime
    completed_at: datetime
    turn_count: int
    stop_reason: StopReason
    automated_result: AgenticOutcome
    deterministic_result: AgenticOutcome
    judge_result: JudgeResult | None = None
    disagreement: bool = False
    human_review_reason: str | None = None
    evaluator_summary: dict[str, int] = Field(default_factory=dict)


class AgenticCampaignRequest(BaseModel):
    label: str = Field(default="Controlled synthetic campaign", min_length=1, max_length=120)
    target_id: str = Field(pattern=r"^[A-Za-z0-9._-]{1,80}$")
    target_path: Literal["baseline", "guarded"]
    objective_ids: list[str] = Field(min_length=1, max_length=12)
    attacker_type: Literal["deterministic", "model"] = "deterministic"
    seed: int = Field(default=42, ge=0, le=2_147_483_647)
    maximum_turns_per_objective: int = Field(default=5, ge=1, le=10)
    maximum_total_turns: int = Field(default=50, ge=1, le=100)
    maximum_duration_seconds: int = Field(default=120, ge=5, le=600)
    maximum_model_calls: int = Field(default=0, ge=0, le=50)
    cost_ceiling_usd: float | None = Field(default=None, ge=0, le=10)
    judge_enabled: bool = False
    synthetic_authorized_acknowledged: bool

    @model_validator(mode="after")
    def validate_limits(self) -> "AgenticCampaignRequest":
        if not self.synthetic_authorized_acknowledged:
            raise ValueError("synthetic and authorized scope acknowledgement is required")
        if self.attacker_type == "deterministic" and not self.judge_enabled and self.maximum_model_calls != 0:
            raise ValueError("fully deterministic campaigns must set maximum_model_calls to zero")
        if (self.attacker_type == "model" or self.judge_enabled) and self.maximum_model_calls < 1:
            raise ValueError("model-backed campaigns require a positive model-call limit")
        return self


class AgenticCampaign(BaseModel):
    campaign_id: str
    label: str
    target_id: str
    target_path: Literal["baseline", "guarded"]
    objective_ids: list[str]
    attacker_type: Literal["deterministic", "model"]
    provider_model_display_name: str
    seed: int
    maximum_turns_per_objective: int
    maximum_total_turns: int
    maximum_duration_seconds: int
    maximum_model_calls: int
    cost_ceiling_usd: float | None
    judge_enabled: bool
    guard_mode: str | None
    objective_pack_version: str
    strategy_pack_version: str = "1.0"
    policy_pack_version: str
    scenario_version: str
    evaluator_version: str
    status: CampaignStatus
    submitted_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    cancellation_requested: bool = False
    error: str | None = None
    result_summary: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def queued(cls, campaign_id: str, request: AgenticCampaignRequest, **versions: Any) -> "AgenticCampaign":
        return cls(
            campaign_id=campaign_id, submitted_at=datetime.now(timezone.utc), status=CampaignStatus.QUEUED,
            provider_model_display_name="deterministic-local" if request.attacker_type == "deterministic" else "configured-local-model",
            **request.model_dump(exclude={"synthetic_authorized_acknowledged"}), **versions,
        )


class AgenticComparisonRequest(BaseModel):
    baseline_campaign_id: str = Field(pattern=r"^ac-[a-f0-9]{24}$")
    guarded_campaign_id: str = Field(pattern=r"^ac-[a-f0-9]{24}$")


class AgenticComparison(BaseModel):
    comparison_id: str
    created_at: datetime
    baseline_campaign_id: str
    guarded_campaign_id: str
    identical_scope: bool
    scope_validation: dict[str, Any]
    objective_results: list[dict[str, Any]]
    baseline_summary: dict[str, Any]
    guarded_summary: dict[str, Any]
    observed_changes: list[str]
    regressions: list[str]
    review_notes: list[str]


class AgenticReport(BaseModel):
    report_id: str
    report_type: Literal["campaign", "comparison"]
    title: str
    created_at: datetime
    markdown: str
    json_content: dict[str, Any]
    boundaries: list[str]
