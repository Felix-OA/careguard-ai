from __future__ import annotations

import re

from careguard_guard.models import GuardChatRequest


def role(request: GuardChatRequest) -> str:
    return request.role_metadata.get("role", "guest").lower()


def patient_ids(text: str) -> list[str]:
    return list(dict.fromkeys(match.upper() for match in re.findall(r"\bPAT-CG-\d{4}\b", text, re.I)))


def verified_patient_id(request: GuardChatRequest) -> str | None:
    value = request.patient_scope_metadata.get("verified_patient_id")
    return value.upper() if value else None


def combined_text(request: GuardChatRequest) -> str:
    history = " ".join(turn.content for turn in request.conversation_history)
    return f"{history} {request.user_message}".strip()

