from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from secrets import token_urlsafe
from threading import RLock

from careguard.models.schemas import ToolCall


def action_digest(call: ToolCall) -> str:
    payload = json.dumps({"name": call.name, "arguments": call.arguments}, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()


def scope_digest(patient_scope: dict[str, str] | None) -> str:
    payload = json.dumps(patient_scope or {}, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()


@dataclass
class PendingConfirmation:
    conversation_id: str
    action_hash: str
    patient_scope_hash: str
    expires_at: datetime


class ConfirmationStore:
    """Process-local, short-lived synthetic confirmation state; not production authentication."""

    def __init__(self) -> None:
        self._pending: dict[str, PendingConfirmation] = {}
        self._lock = RLock()

    def create(
        self, conversation_id: str, call: ToolCall, ttl_seconds: int,
        patient_scope: dict[str, str] | None = None, now: datetime | None = None,
    ) -> str:
        current = now or datetime.now(timezone.utc)
        with self._lock:
            token = f"cg-confirm-{token_urlsafe(12)}"
            self._pending[token] = PendingConfirmation(
                conversation_id=conversation_id,
                action_hash=action_digest(call),
                patient_scope_hash=scope_digest(patient_scope),
                expires_at=current + timedelta(seconds=ttl_seconds),
            )
        return token

    def verify(
        self, token: str | None, conversation_id: str, call: ToolCall,
        patient_scope: dict[str, str] | None = None, now: datetime | None = None,
    ) -> str:
        with self._lock:
            if not token or token not in self._pending:
                return "missing"
            pending = self._pending[token]
            current = now or datetime.now(timezone.utc)
            if current > pending.expires_at:
                self._pending.pop(token, None)
                return "expired"
            if pending.conversation_id != conversation_id:
                self._pending.pop(token, None)
                return "changed_conversation"
            if pending.patient_scope_hash != scope_digest(patient_scope):
                self._pending.pop(token, None)
                return "changed_scope"
            if pending.action_hash != action_digest(call):
                self._pending.pop(token, None)
                return "changed_action"
            self._pending.pop(token, None)
            return "confirmed"
