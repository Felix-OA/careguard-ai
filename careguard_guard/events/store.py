from __future__ import annotations

import json
import os
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import DateTime, String, Text, create_engine, delete, func, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from careguard.evidence import sanitize_for_evidence
from careguard.models.schemas import NormalizedResponse, ToolCall
from careguard_guard.config import EventSettings
from careguard_guard.models import SecurityEvent


class Base(DeclarativeBase):
    pass


class EventRow(Base):
    __tablename__ = "guard_events"
    event_id: Mapped[str] = mapped_column(String, primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    decision: Mapped[str] = mapped_column(String, index=True)
    payload: Mapped[str] = mapped_column(Text)


class GuardEventStore:
    def __init__(self, root: Path, settings: EventSettings) -> None:
        self.root = root
        self.settings = settings
        self.protected = root / "protected"
        self.protected.mkdir(parents=True, exist_ok=True)
        root.mkdir(parents=True, exist_ok=True)
        root.chmod(0o700)
        self.protected.chmod(0o700)
        database_path = root / "guard-events.db"
        self.engine = create_engine(f"sqlite:///{database_path}")
        Base.metadata.create_all(self.engine)
        database_path.chmod(0o600)

    def protect_raw_response(self, event_id: str, response: NormalizedResponse) -> str:
        path = self.protected / f"{event_id}.json"
        temporary_path = self.protected / f".{event_id}.tmp"
        payload = sanitize_for_evidence(response.model_dump(mode="json"))
        with temporary_path.open("w", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, sort_keys=True))
            handle.flush()
            os.fsync(handle.fileno())
        temporary_path.chmod(0o600)
        temporary_path.replace(path)
        path.chmod(0o600)
        return f"protected://guard-response/{event_id}"

    def delete_protected(self, event_id: str) -> None:
        (self.protected / f"{event_id}.json").unlink(missing_ok=True)

    def save(self, event: SecurityEvent) -> SecurityEvent:
        sanitized = SecurityEvent.model_validate(sanitize_for_evidence(event.model_dump(mode="json")))
        with Session(self.engine) as session:
            session.merge(EventRow(
                event_id=sanitized.event_id,
                timestamp=sanitized.timestamp,
                decision=sanitized.final_decision.value,
                payload=sanitized.model_dump_json(),
            ))
            session.commit()
        self.prune()
        return sanitized

    def get(self, event_id: str) -> SecurityEvent | None:
        with Session(self.engine) as session:
            row = session.get(EventRow, event_id)
            return SecurityEvent.model_validate_json(row.payload) if row else None

    def list(self, limit: int = 100) -> list[SecurityEvent]:
        limit = min(max(limit, 1), 1000)
        with Session(self.engine) as session:
            rows = session.scalars(select(EventRow).order_by(EventRow.timestamp.desc()).limit(limit)).all()
            return [SecurityEvent.model_validate_json(row.payload) for row in rows]

    @staticmethod
    def public_event(event: SecurityEvent) -> SecurityEvent:
        def without_excerpts(items: list) -> list:
            return [item.model_copy(update={"excerpt": None}) for item in items]

        def without_arguments(items: list[ToolCall]) -> list[ToolCall]:
            return [item.model_copy(update={
                "arguments": {key: "[REDACTED]" for key in item.arguments}
            }) for item in items]

        return event.model_copy(update={
            "original_user_message": "[REDACTED_FROM_PUBLIC_EVENT]",
            "role_metadata": {"role": event.role_metadata.get("role", "unknown")},
            "patient_scope_metadata": {
                key: "[REDACTED]" for key in event.patient_scope_metadata
            },
            "raw_retrieval_metadata": without_excerpts(event.raw_retrieval_metadata),
            "rejected_retrieval_metadata": without_excerpts(event.rejected_retrieval_metadata),
            "refill_context_metadata": without_excerpts(event.refill_context_metadata),
            "admitted_context_metadata": without_excerpts(event.admitted_context_metadata),
            "proposed_tools": without_arguments(event.proposed_tools),
            "authorized_tools": without_arguments(event.authorized_tools),
            "blocked_tools": without_arguments(event.blocked_tools),
            "failed_tools": without_arguments(event.failed_tools),
            "executed_tools": without_arguments(event.executed_tools),
        })

    def metrics(self) -> dict:
        with Session(self.engine) as session:
            rows = session.scalars(select(EventRow).order_by(EventRow.timestamp.desc())).all()
            events = [SecurityEvent.model_validate_json(row.payload) for row in rows]
        return {
            "event_count": len(events),
            "decisions": dict(Counter(event.final_decision.value for event in events)),
            "would_enforce_decisions": dict(Counter(event.would_enforce_decision.value for event in events)),
            "reason_codes": dict(Counter(code for event in events for code in event.reason_codes)),
            "human_review_required": sum(event.human_review_required for event in events),
        }

    def prune(self) -> None:
        cutoff = datetime.now(timezone.utc) - timedelta(days=self.settings.retention_days)
        remove_ids: list[str] = []
        with Session(self.engine) as session:
            remove_ids.extend(session.scalars(
                select(EventRow.event_id).where(EventRow.timestamp < cutoff)
            ).all())
            session.execute(delete(EventRow).where(EventRow.timestamp < cutoff))
            count = session.scalar(select(func.count()).select_from(EventRow)) or 0
            if count > self.settings.max_events:
                excess_ids = session.scalars(
                    select(EventRow.event_id).order_by(EventRow.timestamp.asc()).limit(count - self.settings.max_events)
                ).all()
                remove_ids.extend(excess_ids)
                session.execute(delete(EventRow).where(EventRow.event_id.in_(excess_ids)))
            session.commit()
        for event_id in set(remove_ids):
            (self.protected / f"{event_id}.json").unlink(missing_ok=True)
