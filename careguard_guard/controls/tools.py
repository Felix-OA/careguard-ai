from __future__ import annotations

from dataclasses import dataclass, field
import re

from careguard.models.schemas import ToolCall
from careguard_guard.config import GuardConfig
from careguard_guard.controls.common import role, verified_patient_id
from careguard_guard.controls.confirmations import ConfirmationStore
from careguard_guard.models import GuardChatRequest
from demo_health_agent.data.synthetic import PATIENTS
from demo_health_agent.tools import book_appointment, find_appointment, lookup_patient_record, request_clinician_escalation


@dataclass
class ToolGuardResult:
    proposed: list[ToolCall] = field(default_factory=list)
    authorized: list[ToolCall] = field(default_factory=list)
    blocked: list[ToolCall] = field(default_factory=list)
    executed: list[ToolCall] = field(default_factory=list)
    confirmation_status: str = "not_required"
    confirmation_token: str | None = None
    confirmation_summary: str | None = None
    reason_codes: list[str] = field(default_factory=list)
    policy_ids: list[str] = field(default_factory=list)


def _appointment_patient(reference: str | None) -> str | None:
    for patient_id, record in PATIENTS.items():
        if record.get("appointment_reference") == reference:
            return patient_id
    return None


class ToolGuard:
    def __init__(self, config: GuardConfig, confirmations: ConfirmationStore | None = None) -> None:
        self.config = config
        self.confirmations = confirmations or ConfirmationStore()

    def _authorized(self, call: ToolCall, request: GuardChatRequest) -> bool:
        current_role = role(request)
        if current_role not in self.config.tool_permissions.get(call.name, []):
            return False
        if current_role == "staff":
            return request.role_metadata.get("authorized") == "true"
        if call.name == "request_clinician_escalation":
            return True
        if current_role != "patient":
            return False
        verified = verified_patient_id(request)
        if not verified:
            return False
        action_patient = call.arguments.get("patient_id")
        if call.name == "find_appointment":
            action_patient = _appointment_patient(call.arguments.get("reference"))
        return action_patient == verified

    def evaluate(self, calls: list[ToolCall], request: GuardChatRequest, execute: bool) -> ToolGuardResult:
        result = ToolGuardResult(proposed=list(calls))
        for original in calls:
            authorized = self._authorized(original, request)
            call = original.model_copy(update={"authorized": authorized})
            if not authorized:
                result.blocked.append(call)
                result.reason_codes.append("CG_TOOL_AUTHORIZATION_DENIED")
                result.policy_ids.append(self.config.policy_mappings["CG_TOOL_AUTHORIZATION_DENIED"])
                continue
            result.authorized.append(call)
            if self.config.enabled_controls.get("confirmation", True) and call.name in self.config.confirmation.required_tools:
                status = self.confirmations.verify(request.confirmation_token, request.conversation_id, call)
                if status != "confirmed":
                    result.confirmation_status = status if request.confirmation_token else "required"
                    result.reason_codes.append("CG_TOOL_CONFIRMATION_REQUIRED" if status == "missing" else "CG_CONFIRMATION_INVALID")
                    result.policy_ids.append(self.config.policy_mappings[result.reason_codes[-1]])
                    result.confirmation_token = self.confirmations.create(
                        request.conversation_id, call, self.config.confirmation.ttl_seconds
                    )
                    result.confirmation_summary = self._safe_summary(call)
                    continue
                result.confirmation_status = "confirmed"
                call = call.model_copy(update={"confirmed": True})
            else:
                call = call.model_copy(update={"confirmed": True})
            if execute:
                self._execute(call)
                result.executed.append(call)
        return result

    @staticmethod
    def _execute(call: ToolCall) -> dict:
        if call.name == "lookup_patient_record":
            return lookup_patient_record(**call.arguments)
        if call.name == "find_appointment":
            return find_appointment(**call.arguments)
        if call.name == "request_clinician_escalation":
            return request_clinician_escalation(**call.arguments)
        if call.name == "book_appointment":
            return book_appointment(**call.arguments)
        raise ValueError(f"unsupported simulated tool: {call.name}")

    @staticmethod
    def _safe_summary(call: ToolCall) -> str:
        text = f"Synthetic action: {call.name} with {call.arguments}"
        text = re.sub(r"(?i)\bPAT-CG-\d{4}\b", "[VERIFIED_SYNTHETIC_PATIENT]", text)
        text = re.sub(r"(?i)\bAPPT-CG-[A-Z0-9-]+\b", "[SYNTHETIC_APPOINTMENT]", text)
        return text
