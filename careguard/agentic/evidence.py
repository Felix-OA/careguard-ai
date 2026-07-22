from __future__ import annotations

import re
from typing import Any

from careguard.evidence import sanitize_for_evidence
from careguard.models.schemas import NormalizedResponse, SourceMetadata, ToolCall

from .models import AgenticCampaign, ObjectiveRun, TrajectoryTurn


MAX_OBSERVATION_CHARACTERS = 4_000
PROTECTED_PATTERNS = [
    (re.compile(r"<think>.*?</think>", re.I | re.S), "[HIDDEN_REASONING_REMOVED]"),
    (re.compile(
        r"(?:chain[- ]of[- ]thought|private reasoning|hidden reasoning)\s*:\s*[^\n]*",
        re.I,
    ), "[HIDDEN_REASONING_REMOVED]"),
    (re.compile(r"[A-Za-z0-9._%+-]+@example\.test", re.I), "[SYNTHETIC_EMAIL]"),
    (re.compile(r"SYN-?CANARY-?CG-?ALPHA-?731", re.I), "[SYNTHETIC_CANARY]"),
    (re.compile(r"\bPAT-CG-[0-9]{4}\b", re.I), "[SYNTHETIC_PATIENT_ID]"),
    (re.compile(r"\bAPPT-CG-[A-Z0-9-]+\b", re.I), "[SYNTHETIC_APPOINTMENT_REFERENCE]"),
    (re.compile(r"protected://[^\s]+", re.I), "[PROTECTED_REFERENCE]"),
    (re.compile(r"(?:/Users|/home|/private|/var|/tmp)/[^\s]+"), "[LOCAL_PATH]"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "[REDACTED]"),
    (re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b"), "[REDACTED]"),
    (re.compile(
        r"\b[A-Z][A-Z0-9_]*(?:SECRET|TOKEN|PASSWORD|API_KEY|AUTHORIZATION)[A-Z0-9_]*\s*=\s*[^\s]+",
        re.I,
    ), "[REDACTED_ENV_VALUE]"),
]


def safe_text(value: str | None, limit: int = MAX_OBSERVATION_CHARACTERS) -> str:
    text = str(sanitize_for_evidence(value or ""))
    for pattern, replacement in PROTECTED_PATTERNS:
        text = pattern.sub(replacement, text)
    text = "".join(character for character in text if character in "\n\t" or ord(character) >= 32)
    return text[:limit]


def safe_sources(response: NormalizedResponse) -> tuple[list[SourceMetadata], list[SourceMetadata], list[SourceMetadata]]:
    all_sources = [item.model_copy(update={
        "source_id": safe_text(item.source_id, 120), "title": safe_text(item.title, 200), "excerpt": None,
    }) for item in response.retrieved_sources[:100]]
    admitted = [item for item in all_sources if item.admitted_to_context]
    rejected = [item for item in all_sources if not item.admitted_to_context]
    return all_sources, admitted, rejected


def safe_tools(items: list[ToolCall]) -> list[ToolCall]:
    return [item.model_copy(update={
        "name": safe_text(item.name, 120),
        "arguments": {"_redacted": f"{len(item.arguments)} field(s) excluded"},
    }) for item in items[:100]]


class EvidenceWriter:
    """Durably writes only sanitized agentic records through the existing database."""

    def __init__(self, database: Any) -> None:
        self.database = database

    def save_campaign(self, campaign: AgenticCampaign) -> None:
        self.database.save_agentic_campaign(campaign.campaign_id, campaign.submitted_at, campaign.model_dump_json())

    def commit_objective(
        self, campaign: AgenticCampaign, objective_run: ObjectiveRun, turns: list[TrajectoryTurn],
    ) -> None:
        self.database.save_agentic_evidence(
            campaign.campaign_id,
            campaign.submitted_at,
            campaign.model_dump_json(),
            objective_run.objective_run_id,
            objective_run.completed_at,
            objective_run.model_dump_json(),
            {f"{turn.objective_run_id}:{turn.turn_number:03d}": turn.model_dump_json() for turn in turns},
        )
