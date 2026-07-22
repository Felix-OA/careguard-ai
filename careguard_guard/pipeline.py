from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from threading import RLock
from uuid import uuid4

from careguard.models.schemas import NormalizedRequest, NormalizedResponse, SourceMetadata, ToolCall
from careguard_guard.config import GuardConfig
from careguard_guard.controls import ToolGuard, guard_retrieval, inspect_request, inspect_response
from careguard_guard.events import GuardEventStore
from careguard_guard.integration import DemoDeepIntegration
from careguard_guard.models import (
    Decision, GuardChatRequest, GuardChatResponse, GuardMode, RuleDecision, SecurityEvent,
)


DECISION_PRIORITY = {
    Decision.ALLOW: 0,
    Decision.ALLOW_WITH_WARNING: 1,
    Decision.REDACT: 2,
    Decision.REQUIRE_HUMAN_REVIEW: 3,
    Decision.REQUIRE_CONFIRMATION: 4,
    Decision.ESCALATE: 7,
    Decision.BLOCK: 6,
}


class GuardPersistenceError(RuntimeError):
    """Raised when a Guard decision cannot be durably recorded."""


def strongest(decisions: list[Decision]) -> Decision:
    return max(decisions or [Decision.ALLOW], key=lambda item: DECISION_PRIORITY[item])


def _hash_message(message: str) -> str:
    normalized = " ".join(message.lower().split())
    return hashlib.sha256(normalized.encode()).hexdigest()


def _public_sources(raw: list[SourceMetadata]) -> list[SourceMetadata]:
    return [item.model_copy(update={"excerpt": None}) for item in raw]


def _public_tools(raw: list[ToolCall]) -> list[ToolCall]:
    return [item.model_copy(update={"arguments": {key: "[REDACTED]" for key in item.arguments}}) for item in raw]


class GuardPipeline:
    def __init__(
        self, config: GuardConfig, event_root: Path,
        integration: DemoDeepIntegration | None = None,
    ) -> None:
        self.config = config
        self.integration = integration or DemoDeepIntegration()
        self.events = GuardEventStore(event_root, config.events)
        self.tool_guard = ToolGuard(config)
        self._conversation_identity: dict[str, tuple[str, str | None]] = {}
        self._identity_lock = RLock()

    def reload(self, config: GuardConfig) -> None:
        self.config = config
        self.events.settings = config.events
        self.tool_guard = ToolGuard(config)
        with self._identity_lock:
            self._conversation_identity.clear()

    def _conversation_rule(self, request: GuardChatRequest) -> RuleDecision | None:
        identity = (
            request.role_metadata.get("role", "guest").lower(),
            request.patient_scope_metadata.get("verified_patient_id", "").upper() or None,
        )
        with self._identity_lock:
            existing = self._conversation_identity.get(request.conversation_id)
            if existing is None:
                self._conversation_identity[request.conversation_id] = identity
                return None
            if existing == identity:
                return None
        return RuleDecision(
            rule_id="request.conversation_identity_change",
            matched_category="authorization",
            policy_id=self.config.policy_mappings["CG_IDENTITY_CONTEXT_CHANGED"],
            reason_code="CG_IDENTITY_CONTEXT_CHANGED",
            decision=Decision.BLOCK,
            rule_strength="high",
            safe_explanation="Role or verified synthetic patient scope changed within the conversation.",
            monitor_action="Record that enforce mode would block the changed conversation identity.",
            enforce_action="block and require a new conversation after identity or scope changes",
        )

    async def process(self, request: GuardChatRequest) -> GuardChatResponse:
        started = perf_counter()
        event_id = f"evt-{uuid4().hex}"
        request_rules = inspect_request(request, self.config)
        conversation_rule = self._conversation_rule(request)
        if conversation_rule:
            request_rules.append(conversation_rule)
        request_enforcement = strongest([item.decision for item in request_rules])
        mode = self.config.guard_mode
        raw_candidates: list[dict] = []
        raw_metadata: list[SourceMetadata] = []
        rejected_metadata: list[SourceMetadata] = []
        refill_metadata: list[SourceMetadata] = []
        admitted_metadata: list[SourceMetadata] = []
        response_rules = []
        redactions = []
        target_response: NormalizedResponse | None = None
        final_answer = ""
        proposed: list[ToolCall] = []
        authorized: list[ToolCall] = []
        blocked_tools: list[ToolCall] = []
        failed_tools: list[ToolCall] = []
        executed: list[ToolCall] = []
        confirmation_status = "not_required"
        confirmation_token = None
        confirmation_summary = None
        filtered = False
        redacted = False
        escalated = False
        blocked = False
        policy_generated = False
        human_review = False
        insufficient_context = False
        reason_codes = [item.reason_code for item in request_rules]
        policy_ids = [item.policy_id for item in request_rules]
        error = None
        would_decisions = [item.decision for item in request_rules]

        normalized_request = NormalizedRequest(
            target_id=request.target_id,
            conversation_id=request.conversation_id,
            user_message=request.user_message,
            conversation_history=request.conversation_history,
            role_metadata=request.role_metadata,
        )

        try:
            if mode == GuardMode.ENFORCE and request_enforcement == Decision.BLOCK:
                final_answer = self.config.safe_fallback_messages["block"]
                blocked = True
            elif mode == GuardMode.ENFORCE and request_enforcement == Decision.ESCALATE:
                final_answer = self.config.emergency_escalation.response
                call = ToolCall(
                    name="request_clinician_escalation",
                    arguments={"patient_id": request.patient_scope_metadata.get("verified_patient_id"), "priority": "urgent_review"},
                    authorized=True,
                    confirmed=False,
                )
                proposed = [call] if self.config.emergency_escalation.propose_clinician_escalation else []
                authorized = list(proposed)
                escalated = True
                policy_generated = True
                human_review = self.config.emergency_escalation.require_human_review
                if human_review:
                    reason_codes.append("CG_HUMAN_REVIEW_REQUIRED")
                    policy_ids.append(self.config.policy_mappings["CG_HUMAN_REVIEW_REQUIRED"])
            else:
                raw_candidates = await self.integration.retrieve(normalized_request)
                refill = await self.integration.refill(normalized_request)
                if self.config.enabled_controls.get("retrieval_guard", True):
                    admitted_docs, raw_metadata, rejected_metadata, refill_metadata, would_admitted, refilled = guard_retrieval(
                        raw_candidates, request, self.config, refill_candidates=refill
                    )
                else:
                    admitted_docs = raw_candidates
                    raw_metadata = [
                        SourceMetadata(
                            source_id=doc["source_id"], title=doc["title"], trust_level=doc["trust_level"],
                            admitted_to_context=True, excerpt=doc.get("content", "")[:180],
                        ) for doc in raw_candidates
                    ]
                    rejected_metadata, refill_metadata, would_admitted, refilled = [], [], list(raw_metadata), False
                filtered = bool(rejected_metadata)
                if refilled:
                    reason_codes.append("CG_TRUSTED_CONTEXT_REFILLED")
                    policy_ids.append(self.config.policy_mappings["CG_TRUSTED_CONTEXT_REFILLED"])
                for item in rejected_metadata:
                    if item.trust_level == "untrusted":
                        reason_codes.append("CG_UNTRUSTED_INSTRUCTION_REMOVED")
                        policy_ids.append(self.config.policy_mappings["CG_UNTRUSTED_INSTRUCTION_REMOVED"])
                    elif item.trust_level == "confidential_synthetic":
                        reason_codes.append("CG_CONFIDENTIAL_ACCESS_DENIED")
                        policy_ids.append(self.config.policy_mappings["CG_CONFIDENTIAL_ACCESS_DENIED"])
                if filtered:
                    would_decisions.append(Decision.ALLOW_WITH_WARNING)

                if mode == GuardMode.MONITOR:
                    admitted_docs = raw_candidates
                    admitted_metadata = [
                        SourceMetadata(
                            source_id=doc["source_id"], title=doc["title"], trust_level=doc["trust_level"],
                            admitted_to_context=True, excerpt=doc.get("content", "")[:180],
                        ) for doc in raw_candidates
                    ]
                    target_response = await self.integration.generate(
                        normalized_request, admitted_docs, execute_tools=True
                    )
                else:
                    admitted_metadata = would_admitted
                    if not admitted_docs and raw_candidates:
                        reason_codes.append("CG_SOURCE_GROUNDING_INSUFFICIENT")
                        policy_ids.append(self.config.policy_mappings["CG_SOURCE_GROUNDING_INSUFFICIENT"])
                        would_decisions.append(Decision.BLOCK)
                        insufficient_context = True
                    target_response = await self.integration.generate(
                        normalized_request, admitted_docs,
                        execute_tools=not self.config.enabled_controls.get("tool_guard", True),
                    )

                protected_ref = self.events.protect_raw_response(event_id, target_response)
                guarded_answer, redactions, response_rules, response_decision = inspect_response(
                    target_response.answer, admitted_metadata, self.config,
                    apply_redaction=self.config.enabled_controls.get("redaction", True),
                    apply_safety=self.config.enabled_controls.get("response_guard", True),
                    emergency_required=any(item.reason_code == "CG_EMERGENCY_ESCALATION" for item in request_rules),
                )
                reason_codes.extend(item.reason_code for item in response_rules)
                policy_ids.extend(item.policy_id for item in response_rules)
                reason_codes.extend(item.reason_code for item in redactions)
                policy_ids.extend(item.policy_id for item in redactions)
                would_decisions.append(response_decision)
                redacted = bool(redactions)

                if mode == GuardMode.MONITOR:
                    final_answer = target_response.answer
                    proposed = target_response.proposed_tool_calls
                    executed = target_response.executed_tool_calls
                    if self.config.enabled_controls.get("tool_guard", True):
                        preview = self.tool_guard.evaluate(
                            proposed, request, execute=False, issue_confirmation=False
                        )
                        authorized, blocked_tools = preview.authorized, preview.blocked
                        reason_codes.extend(preview.reason_codes)
                        policy_ids.extend(preview.policy_ids)
                        if preview.blocked:
                            would_decisions.append(Decision.BLOCK)
                        if preview.confirmation_status != "not_required":
                            would_decisions.append(Decision.REQUIRE_CONFIRMATION)
                            confirmation_status = "would_require_confirmation"
                    else:
                        authorized = proposed
                else:
                    if self.config.enabled_controls.get("tool_guard", True):
                        tool_result = self.tool_guard.evaluate(
                            target_response.proposed_tool_calls, request, execute=True
                        )
                        proposed = tool_result.proposed
                        authorized = tool_result.authorized
                        blocked_tools = tool_result.blocked
                        failed_tools = tool_result.failed
                        executed = tool_result.executed
                        confirmation_status = tool_result.confirmation_status
                        confirmation_token = tool_result.confirmation_token
                        confirmation_summary = tool_result.confirmation_summary
                        reason_codes.extend(tool_result.reason_codes)
                        policy_ids.extend(tool_result.policy_ids)
                        if blocked_tools:
                            would_decisions.append(Decision.BLOCK)
                        if failed_tools:
                            would_decisions.append(Decision.REQUIRE_HUMAN_REVIEW)
                            human_review = True
                        if confirmation_status in {
                            "required", "missing", "expired", "changed_action",
                            "changed_scope", "changed_conversation",
                        }:
                            would_decisions.append(Decision.REQUIRE_CONFIRMATION)
                    else:
                        proposed = target_response.proposed_tool_calls
                        authorized = proposed
                        executed = target_response.executed_tool_calls
                    if any(item.decision == Decision.BLOCK for item in response_rules):
                        final_answer = self.config.safe_fallback_messages["response_block"]
                        blocked = True
                    elif failed_tools:
                        final_answer = self.config.safe_fallback_messages["response_block"]
                        blocked = True
                    elif insufficient_context:
                        final_answer = self.config.safe_fallback_messages["insufficient_context"]
                        blocked = True
                    elif blocked_tools:
                        final_answer = self.config.safe_fallback_messages["block"]
                        blocked = True
                    elif confirmation_token:
                        final_answer = f"{self.config.safe_fallback_messages['confirmation']} {confirmation_summary}"
                    elif executed:
                        final_answer = f"Confirmed synthetic action executed: {executed[0].name}."
                    else:
                        final_answer = guarded_answer
        except Exception as exc:
            error = f"guard pipeline error: {type(exc).__name__}"
            final_answer = self.config.safe_fallback_messages["response_block"]
            blocked = mode == GuardMode.ENFORCE
            would_decisions.append(Decision.REQUIRE_HUMAN_REVIEW)
            human_review = True
            protected_ref = None
        else:
            protected_ref = locals().get("protected_ref")

        would_decision = strongest(would_decisions)
        if mode == GuardMode.MONITOR:
            final_decision = Decision.ALLOW_WITH_WARNING if would_decision != Decision.ALLOW else Decision.ALLOW
            blocked = filtered = redacted = escalated = False
        elif escalated:
            final_decision = Decision.ESCALATE
        elif failed_tools:
            final_decision = Decision.REQUIRE_HUMAN_REVIEW
        elif blocked:
            final_decision = Decision.BLOCK
        elif confirmation_token:
            final_decision = Decision.REQUIRE_CONFIRMATION
        elif blocked_tools:
            final_decision = Decision.BLOCK
            blocked = True
        elif redacted:
            final_decision = Decision.REDACT
        elif filtered or request_enforcement == Decision.ALLOW_WITH_WARNING:
            final_decision = Decision.ALLOW_WITH_WARNING
        else:
            final_decision = Decision.ALLOW

        reason_codes = list(dict.fromkeys(reason_codes))
        policy_ids = list(dict.fromkeys(policy_ids))
        latency = (perf_counter() - started) * 1000
        public_raw = raw_metadata + refill_metadata
        if mode == GuardMode.MONITOR and raw_candidates:
            public_raw = admitted_metadata
        event = SecurityEvent(
            event_id=event_id,
            timestamp=datetime.now(timezone.utc),
            conversation_id=request.conversation_id,
            request_id=request.request_id,
            guard_mode=mode,
            guard_config_version=self.config.version,
            target_id=request.target_id,
            role_metadata=request.role_metadata,
            patient_scope_metadata=request.patient_scope_metadata,
            original_user_message=request.user_message,
            normalized_message_hash=_hash_message(request.user_message),
            request_policy_decisions=request_rules + response_rules,
            raw_retrieval_metadata=raw_metadata,
            rejected_retrieval_metadata=rejected_metadata,
            refill_context_metadata=refill_metadata,
            admitted_context_metadata=admitted_metadata,
            context_refill_performed=bool(refill_metadata),
            insufficient_trusted_context=insufficient_context,
            raw_target_response_reference=protected_ref,
            final_response=final_answer,
            redactions=redactions,
            proposed_tools=proposed,
            authorized_tools=authorized,
            blocked_tools=blocked_tools,
            failed_tools=failed_tools,
            executed_tools=executed,
            confirmation_status=confirmation_status,
            final_decision=final_decision,
            would_enforce_decision=would_decision,
            triggered_policies=policy_ids,
            reason_codes=reason_codes,
            human_review_required=human_review,
            latency_ms=latency,
            error=error,
        )
        try:
            self.events.save(event)
        except Exception as exc:
            self.events.delete_protected(event_id)
            raise GuardPersistenceError("Guard decision persistence failed; response was not released") from exc
        public_proposed = proposed if mode == GuardMode.MONITOR else authorized
        return GuardChatResponse(
            target_id="demo-guarded" if request.target_id == "demo" else request.target_id,
            conversation_id=request.conversation_id,
            answer=final_answer,
            retrieved_sources=_public_sources(public_raw),
            proposed_tool_calls=_public_tools(public_proposed),
            executed_tool_calls=_public_tools(executed),
            blocked_tool_calls=_public_tools(blocked_tools),
            failed_tool_calls=_public_tools(failed_tools),
            guard_mode=mode,
            guard_config_version=self.config.version,
            final_decision=final_decision,
            would_enforce_decision=would_decision,
            triggered_policies=policy_ids,
            reason_codes=reason_codes,
            request_decisions=request_rules + response_rules,
            blocked=blocked,
            filtered=filtered,
            redacted=redacted,
            escalated=escalated,
            allowed=not blocked,
            human_review_required=human_review,
            policy_generated=policy_generated,
            redactions=redactions,
            confirmation_status=confirmation_status,
            confirmation_token=confirmation_token,
            confirmation_summary=confirmation_summary,
            event_id=event_id,
            latency_ms=latency,
            error=error,
        )
