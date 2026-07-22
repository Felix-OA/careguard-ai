from __future__ import annotations

from pathlib import Path

from sqlalchemy import DateTime, String, Text, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from careguard.models.schemas import AuditSummary, ComparisonSummary, Target, TargetCreate


class Base(DeclarativeBase):
    pass


class TargetRow(Base):
    __tablename__ = "targets"
    target_id: Mapped[str] = mapped_column(String, primary_key=True)
    payload: Mapped[str] = mapped_column(Text)


class AuditRow(Base):
    __tablename__ = "audits"
    run_id: Mapped[str] = mapped_column(String, primary_key=True)
    target_id: Mapped[str] = mapped_column(String)
    completed_at: Mapped[object] = mapped_column(DateTime(timezone=True))
    payload: Mapped[str] = mapped_column(Text)


class ComparisonRow(Base):
    __tablename__ = "comparisons"
    comparison_id: Mapped[str] = mapped_column(String, primary_key=True)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True))
    payload: Mapped[str] = mapped_column(Text)


class Database:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.engine = create_engine(f"sqlite:///{path}")
        Base.metadata.create_all(self.engine)
        if not self.get_target("demo"):
            self.add_target(TargetCreate(target_id="demo", name="Synthetic Demo Agent", connector_type="demo"))
        if not self.get_target("demo-guarded"):
            self.add_target(TargetCreate(
                target_id="demo-guarded", name="Synthetic Demo Agent through CareGuard Guard",
                connector_type="guard",
            ))

    def add_target(self, target: TargetCreate) -> Target:
        model = Target(**target.model_dump())
        with Session(self.engine) as session:
            existing = session.get(TargetRow, target.target_id)
            payload = model.model_dump_json()
            if existing:
                existing.payload = payload
            else:
                session.add(TargetRow(target_id=target.target_id, payload=payload))
            session.commit()
        return model

    def get_target(self, target_id: str) -> Target | None:
        with Session(self.engine) as session:
            row = session.get(TargetRow, target_id)
            return Target.model_validate_json(row.payload) if row else None

    def list_targets(self) -> list[Target]:
        with Session(self.engine) as session:
            return [Target.model_validate_json(row.payload) for row in session.scalars(select(TargetRow))]

    def save_audit(self, summary: AuditSummary) -> None:
        with Session(self.engine) as session:
            session.merge(AuditRow(run_id=summary.run_id, target_id=summary.target_id, completed_at=summary.completed_at, payload=summary.model_dump_json()))
            session.commit()

    def list_audits(self) -> list[AuditSummary]:
        with Session(self.engine) as session:
            rows = session.scalars(select(AuditRow).order_by(AuditRow.completed_at.desc())).all()
            return [AuditSummary.model_validate_json(row.payload) for row in rows]

    def get_audit(self, run_id: str) -> AuditSummary | None:
        with Session(self.engine) as session:
            row = session.get(AuditRow, run_id)
            return AuditSummary.model_validate_json(row.payload) if row else None

    def save_comparison(self, summary: ComparisonSummary) -> None:
        with Session(self.engine) as session:
            session.merge(ComparisonRow(
                comparison_id=summary.comparison_id,
                created_at=summary.created_at,
                payload=summary.model_dump_json(),
            ))
            session.commit()

    def list_comparisons(self) -> list[ComparisonSummary]:
        with Session(self.engine) as session:
            rows = session.scalars(select(ComparisonRow).order_by(ComparisonRow.created_at.desc())).all()
            return [ComparisonSummary.model_validate_json(row.payload) for row in rows]

    def get_comparison(self, comparison_id: str) -> ComparisonSummary | None:
        with Session(self.engine) as session:
            row = session.get(ComparisonRow, comparison_id)
            return ComparisonSummary.model_validate_json(row.payload) if row else None
