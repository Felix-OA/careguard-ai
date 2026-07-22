from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import DateTime, String, Text, create_engine, delete, func, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from careguard.evidence import sanitize_for_evidence
from careguard.models.schemas import NormalizedResponse
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
        self.engine = create_engine(f"sqlite:///{root / 'guard-events.db'}")
        Base.metadata.create_all(self.engine)

    def protect_raw_response(self, event_id: str, response: NormalizedResponse) -> str:
        path = self.protected / f"{event_id}.json"
        payload = sanitize_for_evidence(response.model_dump(mode="json"))
        path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
        path.chmod(0o600)
        return str(path)

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
