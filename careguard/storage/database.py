from __future__ import annotations

from pathlib import Path

from sqlalchemy import DateTime, String, Text, create_engine, delete, select
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


class OrganizationRow(Base):
    __tablename__ = "organization_profile"
    profile_id: Mapped[str] = mapped_column(String, primary_key=True)
    payload: Mapped[str] = mapped_column(Text)


class TargetConfigRow(Base):
    __tablename__ = "target_configs"
    target_id: Mapped[str] = mapped_column(String, primary_key=True)
    payload: Mapped[str] = mapped_column(Text)


class AuditJobRow(Base):
    __tablename__ = "audit_jobs"
    job_id: Mapped[str] = mapped_column(String, primary_key=True)
    submitted_at: Mapped[object] = mapped_column(DateTime(timezone=True), index=True)
    payload: Mapped[str] = mapped_column(Text)


class ReviewRow(Base):
    __tablename__ = "review_decisions"
    review_id: Mapped[str] = mapped_column(String, primary_key=True)
    payload: Mapped[str] = mapped_column(Text)


class PolicySettingRow(Base):
    __tablename__ = "policy_settings"
    policy_id: Mapped[str] = mapped_column(String, primary_key=True)
    payload: Mapped[str] = mapped_column(Text)


class Database:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.parent.chmod(0o700)
        self.engine = create_engine(f"sqlite:///{path}")
        Base.metadata.create_all(self.engine)
        path.chmod(0o600)
        if not self.get_target("demo"):
            self.add_target(TargetCreate(target_id="demo", name="Synthetic Demo Agent", connector_type="demo"))
        if not self.get_target("demo-guarded"):
            self.add_target(TargetCreate(
                target_id="demo-guarded", name="Synthetic Demo Agent through CareGuard Guard",
                connector_type="guard",
            ))

    def add_target(self, target: TargetCreate) -> Target:
        with Session(self.engine) as session:
            existing = session.get(TargetRow, target.target_id)
            existing_model = Target.model_validate_json(existing.payload) if existing else None
            model = Target(
                **target.model_dump(),
                **({"created_at": existing_model.created_at} if existing_model else {}),
            )
            payload = model.model_dump_json()
            if existing:
                existing.payload = payload
            else:
                session.add(TargetRow(target_id=target.target_id, payload=payload))
            session.commit()
        return model

    def delete_target(self, target_id: str) -> bool:
        with Session(self.engine) as session:
            existing = session.get(TargetRow, target_id)
            if not existing:
                return False
            session.delete(existing)
            session.execute(delete(TargetConfigRow).where(TargetConfigRow.target_id == target_id))
            session.commit()
        return True

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

    def save_organization(self, payload: str) -> None:
        with Session(self.engine) as session:
            session.merge(OrganizationRow(profile_id="local", payload=payload))
            session.commit()

    def get_organization_payload(self) -> str | None:
        with Session(self.engine) as session:
            row = session.get(OrganizationRow, "local")
            return row.payload if row else None

    def save_target_config(self, target_id: str, payload: str) -> None:
        with Session(self.engine) as session:
            session.merge(TargetConfigRow(target_id=target_id, payload=payload))
            session.commit()

    def get_target_config_payload(self, target_id: str) -> str | None:
        with Session(self.engine) as session:
            row = session.get(TargetConfigRow, target_id)
            return row.payload if row else None

    def save_audit_job(self, job_id: str, submitted_at: object, payload: str) -> None:
        with Session(self.engine) as session:
            session.merge(AuditJobRow(job_id=job_id, submitted_at=submitted_at, payload=payload))
            session.commit()

    def get_audit_job_payload(self, job_id: str) -> str | None:
        with Session(self.engine) as session:
            row = session.get(AuditJobRow, job_id)
            return row.payload if row else None

    def list_audit_job_payloads(self) -> list[str]:
        with Session(self.engine) as session:
            rows = session.scalars(select(AuditJobRow).order_by(AuditJobRow.submitted_at.desc())).all()
            return [row.payload for row in rows]

    def save_review(self, review_id: str, payload: str) -> None:
        with Session(self.engine) as session:
            session.merge(ReviewRow(review_id=review_id, payload=payload))
            session.commit()

    def get_review_payload(self, review_id: str) -> str | None:
        with Session(self.engine) as session:
            row = session.get(ReviewRow, review_id)
            return row.payload if row else None

    def list_review_payloads(self) -> list[str]:
        with Session(self.engine) as session:
            return [row.payload for row in session.scalars(select(ReviewRow)).all()]

    def save_policy_setting(self, policy_id: str, payload: str) -> None:
        with Session(self.engine) as session:
            session.merge(PolicySettingRow(policy_id=policy_id, payload=payload))
            session.commit()

    def save_policy_settings(self, payloads: dict[str, str]) -> None:
        with Session(self.engine) as session:
            for policy_id, payload in payloads.items():
                session.merge(PolicySettingRow(policy_id=policy_id, payload=payload))
            session.commit()

    def get_policy_setting_payload(self, policy_id: str) -> str | None:
        with Session(self.engine) as session:
            row = session.get(PolicySettingRow, policy_id)
            return row.payload if row else None

    def list_policy_setting_payloads(self) -> list[str]:
        with Session(self.engine) as session:
            return [row.payload for row in session.scalars(select(PolicySettingRow)).all()]
