from __future__ import annotations

import re

from careguard.models.schemas import SourceMetadata
from careguard_guard.config import GuardConfig
from careguard_guard.models import Decision, Redaction, RuleDecision

CERTAINTY_PATTERN = re.compile(
    r"\b(?:definitely\s+have|guaranteed(?:\s+diagnosis)?|certain(?:ly)?\s+(?:have|diagnosis)|"
    r"double\s+your\s+dose|take\s+twice|must\s+be\s+diagnosed)\b",
    re.I,
)


def inspect_response(
    raw_answer: str, admitted: list[SourceMetadata], config: GuardConfig,
    apply_redaction: bool = True, apply_safety: bool = True, emergency_required: bool = False,
) -> tuple[str, list[Redaction], list[RuleDecision], Decision]:
    answer = raw_answer
    redactions: list[Redaction] = []
    rules: list[RuleDecision] = []
    for item in config.redaction_patterns if apply_redaction else []:
        answer, count = re.subn(item.pattern, item.replacement, answer)
        if count:
            redactions.append(Redaction(
                pattern_id=item.pattern_id,
                reason_code=item.reason_code,
                policy_id=item.policy_id,
                replacement=item.replacement,
                count=count,
            ))
    lowered = raw_answer.lower()
    if apply_safety and CERTAINTY_PATTERN.search(raw_answer):
        rules.append(RuleDecision(
            rule_id="response.unsupported_certainty", matched_category="diagnostic_certainty",
            policy_id=config.policy_mappings["CG_UNSUPPORTED_CERTAINTY"],
            reason_code="CG_UNSUPPORTED_CERTAINTY", decision=Decision.BLOCK, rule_strength="high",
            safe_explanation="The target response contains unsupported certainty language.",
            monitor_action="Record that enforce mode would withhold the response.",
            enforce_action="withhold the response and use the configured safe fallback",
        ))
        rules.append(RuleDecision(
            rule_id="response.unsupported_medical_claim", matched_category="unsupported_claims",
            policy_id=config.policy_mappings["CG_UNSUPPORTED_MEDICAL_CLAIM"],
            reason_code="CG_UNSUPPORTED_MEDICAL_CLAIM", decision=Decision.BLOCK, rule_strength="high",
            safe_explanation="The target response makes a medical claim without approved grounding.",
            monitor_action="Record that enforce mode would withhold the unsupported claim.",
            enforce_action="withhold the response and use the configured safe fallback",
        ))
    if apply_safety and "internal_system_rule" in lowered:
        rules.append(RuleDecision(
            rule_id="response.system_disclosure", matched_category="system_disclosure",
            policy_id=config.policy_mappings["CG_SYSTEM_INSTRUCTION_REQUEST"],
            reason_code="CG_SYSTEM_INSTRUCTION_REQUEST", decision=Decision.BLOCK, rule_strength="high",
            safe_explanation="Controlled system-instruction content was detected.",
            monitor_action="Record that enforce mode would withhold the response.",
            enforce_action="withhold the response",
        ))
    admitted_ids = {item.source_id.lower() for item in admitted}
    claimed_ids = {item.lower() for item in re.findall(r"\[Source:\s*([^\]]+)\]", raw_answer, re.I)}
    if apply_safety and claimed_ids and not claimed_ids.issubset(admitted_ids):
        rules.append(RuleDecision(
            rule_id="response.ungrounded_source", matched_category="grounding",
            policy_id=config.policy_mappings["CG_SOURCE_GROUNDING_INSUFFICIENT"],
            reason_code="CG_SOURCE_GROUNDING_INSUFFICIENT", decision=Decision.BLOCK, rule_strength="high",
            safe_explanation="A source claim is not present in admitted context.",
            monitor_action="Record that enforce mode would withhold the response.",
            enforce_action="withhold the ungrounded response",
        ))
    emergency_support = "emergency services" in lowered or "qualified clinical support" in lowered
    if apply_safety and emergency_required and (not emergency_support or CERTAINTY_PATTERN.search(raw_answer)):
        rules.append(RuleDecision(
            rule_id="response.emergency_missing", matched_category="emergency_escalation",
            policy_id=config.policy_mappings["CG_EMERGENCY_ESCALATION"],
            reason_code="CG_EMERGENCY_ESCALATION", decision=Decision.ESCALATE, rule_strength="high",
            safe_explanation="The target response omitted the configured emergency escalation.",
            monitor_action="Record that enforce mode would replace the response with the policy escalation.",
            enforce_action="replace the response and require human review",
        ))
    if any(rule.decision == Decision.BLOCK for rule in rules):
        decision = Decision.BLOCK
    elif any(rule.decision == Decision.ESCALATE for rule in rules):
        decision = Decision.ESCALATE
    elif redactions:
        decision = Decision.REDACT
    else:
        decision = Decision.ALLOW
    return answer, redactions, rules, decision
