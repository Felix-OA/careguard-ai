from __future__ import annotations

import os
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from careguard.config import load_policy_pack
from careguard_guard.models import GuardMode

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GUARD_CONFIG = ROOT / "configs" / "careguard-guard.example.yaml"
REQUIRED_CONTROLS = {
    "request_guard", "retrieval_guard", "response_guard", "tool_guard", "redaction",
    "emergency_escalation", "confirmation",
}
REQUIRED_REASON_CODES = {
    "CG_CONFIDENTIAL_ACCESS_DENIED", "CG_CROSS_PATIENT_REQUEST", "CG_FAKE_AUTHORITY",
    "CG_UNTRUSTED_INSTRUCTION_REMOVED", "CG_SYNTHETIC_IDENTIFIER",
    "CG_UNTRUSTED_INSTRUCTION_REM_REDACTED", "CG_EMERGENCY_ESCALATION",
    "CG_TOOL_CONFIRMATION_REQUIRED", "CG_TOOL_AUTHORIZATION_DENIED",
    "CG_UNSUPPORTED_CERTAINTY", "CG_SYSTEM_INSTRUCTION_REQUEST",
    "CG_SOURCE_GROUNDING_INSUFFICIENT", "CG_CANARY_EXTRACTION_REQUEST",
    "CG_CONFIRMATION_INVALID", "CG_TRUSTED_CONTEXT_REFILLED",
    "CG_IDENTITY_CONTEXT_CHANGED", "CG_UNSUPPORTED_MEDICAL_CLAIM",
    "CG_MEDICATION_BOUNDARY", "CG_HUMAN_REVIEW_REQUIRED", "CG_SENSITIVE_ACTION_CONTROLLED",
    "CG_TOOL_EXECUTION_FAILED",
}
REQUIRED_TOOLS = {
    "lookup_patient_record", "find_appointment", "request_clinician_escalation", "book_appointment",
}


class RedactionPattern(BaseModel):
    pattern_id: str
    pattern: str
    replacement: str = "[REDACTED_SYNTHETIC_VALUE]"
    reason_code: str
    policy_id: str


class EmergencySettings(BaseModel):
    enabled: bool = True
    indicators: list[str]
    response: str
    require_human_review: bool = True
    propose_clinician_escalation: bool = True


class ConfirmationSettings(BaseModel):
    required_tools: list[str]
    ttl_seconds: int = Field(ge=1, le=3600)


class EventSettings(BaseModel):
    retention_days: int = Field(ge=1, le=3650)
    max_events: int = Field(ge=10, le=1_000_000)


class GuardConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: str
    guard_mode: GuardMode
    enabled_controls: dict[str, bool]
    policy_mappings: dict[str, str]
    role_permissions: dict[str, list[str]]
    tool_permissions: dict[str, list[str]]
    patient_scope_rules: dict[str, bool]
    trusted_source_types: list[str]
    prohibited_context_types: list[str]
    redaction_patterns: list[RedactionPattern]
    emergency_escalation: EmergencySettings
    confirmation: ConfirmationSettings
    events: EventSettings
    safe_fallback_messages: dict[str, str]

    @field_validator("trusted_source_types")
    @classmethod
    def require_trusted_types(cls, values: list[str]) -> list[str]:
        allowed = {"trusted_clinical", "trusted_operational"}
        if not values or not set(values).issubset(allowed):
            raise ValueError("trusted_source_types may contain only trusted_clinical and trusted_operational")
        return values

    @model_validator(mode="after")
    def validate_mappings(self) -> "GuardConfig":
        known = {item.policy_id for item in load_policy_pack().policies}
        referenced = set(self.policy_mappings.values()) | {item.policy_id for item in self.redaction_patterns}
        unknown = referenced - known
        if unknown:
            raise ValueError(f"guard configuration references unknown policy IDs: {sorted(unknown)}")
        missing_reasons = REQUIRED_REASON_CODES - set(self.policy_mappings)
        if missing_reasons:
            raise ValueError(f"guard configuration is missing required reason-code mappings: {sorted(missing_reasons)}")
        missing_controls = REQUIRED_CONTROLS - set(self.enabled_controls)
        if missing_controls:
            raise ValueError(f"guard configuration is missing enabled_controls: {sorted(missing_controls)}")
        missing_tools = REQUIRED_TOOLS - set(self.tool_permissions)
        if missing_tools:
            raise ValueError(f"guard configuration is missing tool permissions: {sorted(missing_tools)}")
        invalid_confirmation_tools = set(self.confirmation.required_tools) - REQUIRED_TOOLS
        if invalid_confirmation_tools:
            raise ValueError(f"confirmation references unknown tools: {sorted(invalid_confirmation_tools)}")
        valid_trust = {
            "trusted_clinical", "trusted_operational", "untrusted", "confidential_synthetic",
        }
        invalid_prohibited = set(self.prohibited_context_types) - valid_trust
        if invalid_prohibited:
            raise ValueError(f"invalid prohibited context types: {sorted(invalid_prohibited)}")
        if set(self.trusted_source_types) & set(self.prohibited_context_types):
            raise ValueError("trusted and prohibited context types must not overlap")
        if "block" not in self.safe_fallback_messages or "confirmation" not in self.safe_fallback_messages:
            raise ValueError("safe_fallback_messages requires block and confirmation entries")
        return self


def load_guard_config(path: Path | None = None, mode: str | None = None) -> GuardConfig:
    config_path = path or Path(os.getenv("CAREGUARD_GUARD_CONFIG", DEFAULT_GUARD_CONFIG))
    with config_path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    requested_mode = mode or os.getenv("CAREGUARD_GUARD_MODE")
    if requested_mode:
        data["guard_mode"] = requested_mode
    return GuardConfig.model_validate(data)
