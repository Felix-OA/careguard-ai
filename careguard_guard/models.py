from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from careguard.models.schemas import ChatTurn, SourceMetadata, ToolCall


class GuardMode(StrEnum):
    MONITOR = "monitor"
    ENFORCE = "enforce"


class Decision(StrEnum):
    ALLOW = "ALLOW"
    ALLOW_WITH_WARNING = "ALLOW_WITH_WARNING"
    BLOCK = "BLOCK"
    REDACT = "REDACT"
    ESCALATE = "ESCALATE"
    REQUIRE_CONFIRMATION = "REQUIRE_CONFIRMATION"
    REQUIRE_HUMAN_REVIEW = "REQUIRE_HUMAN_REVIEW"


class RuleDecision(BaseModel):
    rule_id: str
    matched_category: str
    policy_id: str
    reason_code: str
    decision: Decision
    rule_strength: Literal["low", "medium", "high"]
    safe_explanation: str
    monitor_action: str
    enforce_action: str


class Redaction(BaseModel):
    pattern_id: str
    reason_code: str
    policy_id: str
    replacement: str
    count: int


class GuardChatRequest(BaseModel):
    target_id: str = "demo"
    conversation_id: str
    request_id: str = Field(default_factory=lambda: f"req-{uuid4().hex}")
    user_message: str
    conversation_history: list[ChatTurn] = Field(default_factory=list)
    role_metadata: dict[str, str] = Field(default_factory=dict)
    patient_scope_metadata: dict[str, str] = Field(default_factory=dict)
    confirmation_token: str | None = None


class GuardChatResponse(BaseModel):
    target_id: str
    conversation_id: str
    answer: str
    retrieved_sources: list[SourceMetadata] = Field(default_factory=list)
    proposed_tool_calls: list[ToolCall] = Field(default_factory=list)
    executed_tool_calls: list[ToolCall] = Field(default_factory=list)
    blocked_tool_calls: list[ToolCall] = Field(default_factory=list)
    guard_mode: GuardMode
    final_decision: Decision
    would_enforce_decision: Decision
    triggered_policies: list[str] = Field(default_factory=list)
    reason_codes: list[str] = Field(default_factory=list)
    request_decisions: list[RuleDecision] = Field(default_factory=list)
    blocked: bool = False
    filtered: bool = False
    redacted: bool = False
    escalated: bool = False
    allowed: bool = True
    human_review_required: bool = False
    policy_generated: bool = False
    redactions: list[Redaction] = Field(default_factory=list)
    confirmation_status: str = "not_required"
    confirmation_token: str | None = None
    confirmation_summary: str | None = None
    event_id: str
    latency_ms: float
    provider: str = "careguard-guard"
    model: str = "guard-deterministic-v1"
    error: str | None = None


class SecurityEvent(BaseModel):
    event_id: str
    timestamp: datetime
    conversation_id: str
    request_id: str
    guard_mode: GuardMode
    target_id: str
    role_metadata: dict[str, str]
    patient_scope_metadata: dict[str, str]
    original_user_message: str
    normalized_message_hash: str
    request_policy_decisions: list[RuleDecision]
    raw_retrieval_metadata: list[SourceMetadata]
    rejected_retrieval_metadata: list[SourceMetadata]
    admitted_context_metadata: list[SourceMetadata]
    raw_target_response_reference: str | None
    final_response: str
    redactions: list[Redaction]
    proposed_tools: list[ToolCall]
    authorized_tools: list[ToolCall]
    blocked_tools: list[ToolCall]
    executed_tools: list[ToolCall]
    confirmation_status: str
    final_decision: Decision
    would_enforce_decision: Decision
    triggered_policies: list[str]
    reason_codes: list[str]
    human_review_required: bool
    latency_ms: float
    error: str | None = None

