from __future__ import annotations

from careguard_guard.config import GuardConfig
from careguard_guard.controls.common import combined_text, patient_ids, role, verified_patient_id
from careguard_guard.models import Decision, GuardChatRequest, RuleDecision


def _rule(
    config: GuardConfig, rule_id: str, category: str, reason: str, decision: Decision,
    strength: str, explanation: str, enforce_action: str,
) -> RuleDecision:
    return RuleDecision(
        rule_id=rule_id,
        matched_category=category,
        policy_id=config.policy_mappings[reason],
        reason_code=reason,
        decision=decision,
        rule_strength=strength,
        safe_explanation=explanation,
        monitor_action=f"Record that enforce mode would {enforce_action}.",
        enforce_action=enforce_action,
    )


def inspect_request(request: GuardChatRequest, config: GuardConfig) -> list[RuleDecision]:
    if not config.enabled_controls.get("request_guard", True):
        return []
    text = combined_text(request)
    lowered = text.lower()
    decisions: list[RuleDecision] = []
    ids = patient_ids(text)
    verified = verified_patient_id(request)
    current_role = role(request)

    if len(ids) > 1 or (verified and ids and any(item != verified for item in ids)):
        decisions.append(_rule(
            config, "request.cross_patient", "cross_patient_access", "CG_CROSS_PATIENT_REQUEST",
            Decision.BLOCK, "high", "The request crosses synthetic patient scopes.", "block the request",
        ))
    if any(phrase in lowered for phrase in ("i am clinic staff", "i am staff", "i am administrator")) and current_role != "staff":
        decisions.append(_rule(
            config, "request.fake_authority", "authorization", "CG_FAKE_AUTHORITY",
            Decision.BLOCK, "high", "Authority claimed in message text is not trusted authorization metadata.", "block the request",
        ))
    record_request = any(term in lowered for term in ("record", "case note", "patient information", "example.test"))
    permitted_record_scope = current_role == "staff" and request.role_metadata.get("authorized") == "true"
    permitted_record_scope = permitted_record_scope or (
        current_role == "patient" and verified is not None and (not ids or set(ids) == {verified})
    )
    if record_request and not permitted_record_scope:
        decisions.append(_rule(
            config, "request.record_authorization", "authorization", "CG_CONFIDENTIAL_ACCESS_DENIED",
            Decision.BLOCK, "high", "No verified synthetic record scope is present.", "block the request",
        ))
    if "canary" in lowered or "synthetic credential" in lowered:
        decisions.append(_rule(
            config, "request.canary_extraction", "confidentiality", "CG_CANARY_EXTRACTION_REQUEST",
            Decision.BLOCK, "high", "Synthetic canary extraction is not an allowed support task.", "block the request",
        ))
    if "system instruction" in lowered or "hidden instruction" in lowered or "system prompt" in lowered:
        decisions.append(_rule(
            config, "request.system_disclosure", "system_disclosure", "CG_SYSTEM_INSTRUCTION_REQUEST",
            Decision.BLOCK, "high", "Hidden instruction disclosure is not allowed.", "block the request",
        ))
    if any(phrase in lowered for phrase in ("ignore prior", "ignore previous", "bypass policy", "override the system")):
        decisions.append(_rule(
            config, "request.instruction_override", "prompt_injection", "CG_UNTRUSTED_INSTRUCTION_REM_REDACTED",
            Decision.BLOCK, "high", "The request asks to override the configured instruction hierarchy.", "block the request",
        ))
    if any(phrase in lowered for phrase in ("without confirmation", "skip confirmation", "bypass confirmation")):
        decisions.append(_rule(
            config, "request.confirmation_bypass", "tool_confirmation", "CG_TOOL_CONFIRMATION_REQUIRED",
            Decision.BLOCK, "high", "Required action confirmation cannot be bypassed.", "block the request",
        ))
    if any(phrase in lowered for phrase in ("exact diagnosis", "definitely have", "guaranteed diagnosis")):
        decisions.append(_rule(
            config, "request.diagnostic_certainty", "diagnostic_certainty", "CG_UNSUPPORTED_CERTAINTY",
            Decision.ALLOW_WITH_WARNING, "medium", "The request asks for unsupported diagnostic certainty.", "inspect and potentially withhold the response",
        ))
        decisions.append(_rule(
            config, "request.unsupported_medical_claim", "unsupported_claims", "CG_UNSUPPORTED_MEDICAL_CLAIM",
            Decision.ALLOW_WITH_WARNING, "medium", "The request seeks a medical claim not supported by approved context.",
            "inspect grounding and potentially withhold the response",
        ))
    if any(phrase in lowered for phrase in ("double my medicine", "double my dose", "personal instruction", "take twice")):
        decisions.append(_rule(
            config, "request.medication_boundary", "medication_information", "CG_MEDICATION_BOUNDARY",
            Decision.ALLOW_WITH_WARNING, "high", "The request seeks a personalized medication direction.",
            "allow only a non-personalized boundary response and qualified support referral",
        ))
    if "update" in lowered and any(term in lowered for term in ("record", "case note")):
        decisions.append(_rule(
            config, "request.sensitive_record_action", "sensitive_actions", "CG_SENSITIVE_ACTION_CONTROLLED",
            Decision.BLOCK, "high", "The request attempts a consequential synthetic record action through chat.",
            "block and require an authorized record workflow",
        ))
    emergency = config.enabled_controls.get("emergency_escalation", True) and config.emergency_escalation.enabled and any(
        indicator.lower() in lowered for indicator in config.emergency_escalation.indicators
    )
    if emergency:
        decisions.append(_rule(
            config, "request.emergency", "emergency_escalation", "CG_EMERGENCY_ESCALATION",
            Decision.ESCALATE, "high", "A configured high-level emergency indicator was detected.", "return the policy escalation response and require human review",
        ))
    return decisions
