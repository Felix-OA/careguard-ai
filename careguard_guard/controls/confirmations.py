from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from secrets import token_urlsafe

from careguard.models.schemas import ToolCall


def action_digest(call: ToolCall) -> str:
    payload = json.dumps({"name": call.name, "arguments": call.arguments}, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()


@dataclass
class PendingConfirmation:
    conversation_id: str
    action_hash: str
    expires_at: datetime


class ConfirmationStore:
    """Process-local, short-lived synthetic confirmation state; not production authentication."""

    def __init__(self) -> None:
        self._pending: dict[str, PendingConfirmation] = {}

    def create(self, conversation_id: str, call: ToolCall, ttl_seconds: int, now: datetime | None = None) -> str:
        token = f"cg-confirm-{token_urlsafe(12)}"
        current = now or datetime.now(timezone.utc)
        self._pending[token] = PendingConfirmation(
            conversation_id=conversation_id,
            action_hash=action_digest(call),
            expires_at=current + timedelta(seconds=ttl_seconds),
        )
        return token

    def verify(
        self, token: str | None, conversation_id: str, call: ToolCall, now: datetime | None = None
    ) -> str:
        if not token or token not in self._pending:
            return "missing"
        pending = self._pending[token]
        current = now or datetime.now(timezone.utc)
        if current > pending.expires_at:
            self._pending.pop(token, None)
            return "expired"
        if pending.conversation_id != conversation_id or pending.action_hash != action_digest(call):
            return "changed_action"
        self._pending.pop(token, None)
        return "confirmed"

