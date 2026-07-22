from __future__ import annotations

import re
from pathlib import Path
from threading import RLock

import httpx

from careguard.connectors.base import TargetConnector
from careguard.models.schemas import NormalizedRequest, NormalizedResponse
from careguard.security import ensure_authorized_endpoint
from careguard_guard.config import load_guard_config
from careguard_guard.models import GuardChatRequest
from careguard_guard.pipeline import GuardPipeline


class GuardConnector(TargetConnector):
    """In-process deterministic adapter used for fixed-suite guarded audits."""

    def __init__(self, event_root: Path, mode: str = "enforce", endpoint: str | None = None) -> None:
        self.endpoint = endpoint
        if endpoint:
            ensure_authorized_endpoint(endpoint)
            self.pipeline = None
        else:
            self.pipeline = GuardPipeline(load_guard_config(mode=mode), event_root)
        self._confirmation_tokens: dict[str, str] = {}
        self._patient_scopes: dict[str, dict[str, str]] = {}
        self._state_lock = RLock()

    async def send(self, request: NormalizedRequest) -> NormalizedResponse:
        scope: dict[str, str] = {}
        explicit = re.search(r"(?:\bI am|\bAs)\s+(PAT-CG-\d{4})", request.user_message, re.I)
        all_ids = list(dict.fromkeys(re.findall(r"\bPAT-CG-\d{4}\b", request.user_message, re.I)))
        synthetic_scope = explicit.group(1) if explicit else (all_ids[0] if len(all_ids) == 1 else None)
        if synthetic_scope and request.role_metadata.get("role") == "patient":
            scope["verified_patient_id"] = synthetic_scope.upper()
            scope["verification"] = "synthetic_audit_adapter"
            with self._state_lock:
                self._patient_scopes[request.conversation_id] = dict(scope)
        else:
            with self._state_lock:
                if request.conversation_id in self._patient_scopes:
                    scope = dict(self._patient_scopes[request.conversation_id])
        token = None
        if "confirm" in request.user_message.lower():
            with self._state_lock:
                token = self._confirmation_tokens.pop(request.conversation_id, None)
        guard_request = GuardChatRequest(
            target_id="demo",
            conversation_id=request.conversation_id,
            user_message=request.user_message,
            conversation_history=request.conversation_history,
            role_metadata=request.role_metadata,
            patient_scope_metadata=scope,
            confirmation_token=token,
        )
        if self.endpoint:
            try:
                async with httpx.AsyncClient(timeout=15) as client:
                    response = await client.post(
                        self.endpoint, json=guard_request.model_dump(mode="json")
                    )
                    response.raise_for_status()
                    from careguard_guard.models import GuardChatResponse

                    guarded = GuardChatResponse.model_validate(response.json())
            except Exception as exc:
                return NormalizedResponse(
                    target_id="demo-guarded", conversation_id=request.conversation_id,
                    provider="careguard-guard", model="guard-deterministic-v1",
                    error=f"guard connector error: {type(exc).__name__}",
                )
        else:
            try:
                guarded = await self.pipeline.process(guard_request)
            except Exception as exc:
                return NormalizedResponse(
                    target_id="demo-guarded", conversation_id=request.conversation_id,
                    provider="careguard-guard", model="guard-deterministic-v1",
                    error=f"guard connector error: {type(exc).__name__}",
                )
        if guarded.confirmation_token:
            with self._state_lock:
                self._confirmation_tokens[request.conversation_id] = guarded.confirmation_token
        return NormalizedResponse(
            target_id="demo-guarded",
            conversation_id=request.conversation_id,
            answer=guarded.answer,
            retrieved_sources=guarded.retrieved_sources,
            proposed_tool_calls=guarded.proposed_tool_calls,
            blocked_tool_calls=guarded.blocked_tool_calls,
            failed_tool_calls=guarded.failed_tool_calls,
            executed_tool_calls=guarded.executed_tool_calls,
            latency_ms=guarded.latency_ms,
            provider="careguard-guard",
            model="guard-deterministic-v1",
            error=guarded.error,
            guard_metadata={
                "guard_mode": guarded.guard_mode.value,
                "guard_config_version": guarded.guard_config_version,
                "event_id": guarded.event_id,
                "final_decision": guarded.final_decision.value,
            },
        )
