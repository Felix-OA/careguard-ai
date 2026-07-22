from __future__ import annotations

import os
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from careguard.config import load_policy_pack
from careguard_guard.models import GuardMode

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GUARD_CONFIG = ROOT / "configs" / "careguard-guard.example.yaml"


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

