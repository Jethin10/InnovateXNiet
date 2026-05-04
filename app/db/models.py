from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    full_name: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(64), default="student")
    password_hash: Mapped[str | None] = mapped_column(Text, nullable=True)

    student_profile: Mapped["StudentProfile | None"] = relationship(
        back_populates="user",
        uselist=False,
    )


class StudentProfile(TimestampMixin, Base):
    __tablename__ = "student_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    target_role: Mapped[str] = mapped_column(String(120))
    target_company: Mapped[str | None] = mapped_column(String(120), nullable=True)
    preferred_resource_style: Mapped[str | None] = mapped_column(String(120), nullable=True)
    coding_handle: Mapped[str | None] = mapped_column(String(120), nullable=True)

    user: Mapped[User] = relationship(back_populates="student_profile")
    resumes: Mapped[list["ResumeArtifact"]] = relationship(back_populates="student_profile")
    assessments: Mapped[list["AssessmentSessionRecord"]] = relationship(back_populates="student_profile")
    assessment_plans: Mapped[list["AssessmentPlanRecord"]] = relationship(back_populates="student_profile")
    assessment_attempts: Mapped[list["AssessmentAttemptRecord"]] = relationship(back_populates="student_profile")
    roadmap_progress_entries: Mapped[list["RoadmapNodeProgressRecord"]] = relationship(back_populates="student_profile")
    roadmap_snapshots: Mapped[list["RoadmapSnapshot"]] = relationship(back_populates="student_profile")
    trust_stamps: Mapped[list["TrustStampProfileRecord"]] = relationship(back_populates="student_profile")
    cohort_memberships: Mapped[list["CohortMembership"]] = relationship(back_populates="student_profile")


class Institution(TimestampMixin, Base):
    __tablename__ = "institutions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)

    cohorts: Mapped[list["Cohort"]] = relationship(back_populates="institution")


class Cohort(TimestampMixin, Base):
    __tablename__ = "cohorts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    institution_id: Mapped[int] = mapped_column(ForeignKey("institutions.id"))
    name: Mapped[str] = mapped_column(String(255))

    institution: Mapped[Institution] = relationship(back_populates="cohorts")
    memberships: Mapped[list["CohortMembership"]] = relationship(back_populates="cohort")


class CohortMembership(TimestampMixin, Base):
    __tablename__ = "cohort_memberships"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cohort_id: Mapped[int] = mapped_column(ForeignKey("cohorts.id"))
    student_profile_id: Mapped[int] = mapped_column(ForeignKey("student_profiles.id"))

    cohort: Mapped[Cohort] = relationship(back_populates="memberships")
    student_profile: Mapped[StudentProfile] = relationship(back_populates="cohort_memberships")


class ResumeArtifact(TimestampMixin, Base):
    __tablename__ = "resume_artifacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_profile_id: Mapped[int] = mapped_column(ForeignKey("student_profiles.id"))
    filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    raw_text: Mapped[str] = mapped_column(Text)
    parse_status: Mapped[str] = mapped_column(String(64), default="parsed")
    extracted_claims_json: Mapped[str] = mapped_column(Text, default="[]")
    analysis_json: Mapped[str] = mapped_column(Text, default="{}")

    student_profile: Mapped[StudentProfile] = relationship(back_populates="resumes")


class AssessmentPlanRecord(TimestampMixin, Base):
    __tablename__ = "assessment_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_profile_id: Mapped[int] = mapped_column(ForeignKey("student_profiles.id"))
    target_role: Mapped[str] = mapped_column(String(120))
    claimed_skills_json: Mapped[str] = mapped_column(Text, default="[]")
    stages_json: Mapped[str] = mapped_column(Text, default="[]")

    student_profile: Mapped[StudentProfile] = relationship(back_populates="assessment_plans")


class AssessmentAttemptRecord(TimestampMixin, Base):
    __tablename__ = "assessment_attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_profile_id: Mapped[int] = mapped_column(ForeignKey("student_profiles.id"))
    status: Mapped[str] = mapped_column(String(64), default="started")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    question_ids_json: Mapped[str] = mapped_column(Text, default="[]")

    student_profile: Mapped[StudentProfile] = relationship(back_populates="assessment_attempts")
    audit_events: Mapped[list["AssessmentAuditEventRecord"]] = relationship(back_populates="attempt")


class AssessmentAuditEventRecord(TimestampMixin, Base):
    __tablename__ = "assessment_audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    attempt_id: Mapped[int] = mapped_column(ForeignKey("assessment_attempts.id"))
    student_profile_id: Mapped[int] = mapped_column(ForeignKey("student_profiles.id"))
    event_type: Mapped[str] = mapped_column(String(120))
    payload_json: Mapped[str] = mapped_column(Text, default="{}")

    attempt: Mapped[AssessmentAttemptRecord] = relationship(back_populates="audit_events")


class EvidenceVerificationRecord(TimestampMixin, Base):
    __tablename__ = "evidence_verifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_profile_id: Mapped[int] = mapped_column(ForeignKey("student_profiles.id"))
    source: Mapped[str] = mapped_column(String(64))
    handle: Mapped[str | None] = mapped_column(String(120), nullable=True)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    payload_json: Mapped[str] = mapped_column(Text, default="{}")


class AssessmentSessionRecord(TimestampMixin, Base):
    __tablename__ = "assessment_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_profile_id: Mapped[int] = mapped_column(ForeignKey("student_profiles.id"))
    attempt_id: Mapped[int | None] = mapped_column(ForeignKey("assessment_attempts.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(64), default="draft")
    evidence_json: Mapped[str] = mapped_column(Text, default="{}")
    answers_json: Mapped[str] = mapped_column(Text, default="[]")
    score_id: Mapped[int | None] = mapped_column(ForeignKey("trust_scores.id"), nullable=True)

    student_profile: Mapped[StudentProfile] = relationship(back_populates="assessments")
    score: Mapped["TrustScoreRecord | None"] = relationship(back_populates="assessment", uselist=False)


class TrustScoreRecord(TimestampMixin, Base):
    __tablename__ = "trust_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    overall_readiness: Mapped[float] = mapped_column(Float)
    model_probability: Mapped[float] = mapped_column(Float)
    raw_accuracy: Mapped[float] = mapped_column(Float)
    confidence_reliability: Mapped[float] = mapped_column(Float)
    evidence_alignment: Mapped[float] = mapped_column(Float)
    calibration_gap: Mapped[float] = mapped_column(Float)
    bluff_index: Mapped[float] = mapped_column(Float)
    readiness_band: Mapped[str] = mapped_column(String(64))
    risk_band: Mapped[str] = mapped_column(String(64))
    skill_scores_json: Mapped[str] = mapped_column(Text, default="{}")
    feature_snapshot_json: Mapped[str] = mapped_column(Text, default="{}")
    explanations_json: Mapped[str] = mapped_column(Text, default="[]")
    model_version: Mapped[str] = mapped_column(String(64), default="v1")

    assessment: Mapped["AssessmentSessionRecord | None"] = relationship(back_populates="score")


class RoadmapSnapshot(TimestampMixin, Base):
    __tablename__ = "roadmap_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_profile_id: Mapped[int] = mapped_column(ForeignKey("student_profiles.id"))
    target_role: Mapped[str] = mapped_column(String(120))
    current_level: Mapped[str] = mapped_column(String(64))
    summary: Mapped[str] = mapped_column(Text)
    graph_json: Mapped[str] = mapped_column(Text, default="{}")

    student_profile: Mapped[StudentProfile] = relationship(back_populates="roadmap_snapshots")


class RoadmapNodeProgressRecord(TimestampMixin, Base):
    __tablename__ = "roadmap_node_progress"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_profile_id: Mapped[int] = mapped_column(ForeignKey("student_profiles.id"))
    node_id: Mapped[str] = mapped_column(String(120))
    node_title: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(64), default="completed")
    proof_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    student_profile: Mapped[StudentProfile] = relationship(back_populates="roadmap_progress_entries")


class SkillRoadmapSnapshot(TimestampMixin, Base):
    __tablename__ = "skill_roadmap_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_key: Mapped[str] = mapped_column(String(120), default="pipeline-demo")
    target_role: Mapped[str] = mapped_column(String(120))
    skill_gaps_json: Mapped[str] = mapped_column(Text, default="[]")
    roadmap_json: Mapped[str] = mapped_column(Text, default="[]")
    source_json: Mapped[str] = mapped_column(Text, default="{}")


class SkillRoadmapTaskProgressRecord(TimestampMixin, Base):
    __tablename__ = "skill_roadmap_task_progress"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_key: Mapped[str] = mapped_column(String(120), default="pipeline-demo")
    task_id: Mapped[str] = mapped_column(String(180))
    status: Mapped[str] = mapped_column(String(64), default="not_started")
    proof_summary: Mapped[str | None] = mapped_column(Text, nullable=True)


class PipelineResumeState(TimestampMixin, Base):
    __tablename__ = "pipeline_resume_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_key: Mapped[str] = mapped_column(String(120), default="pipeline-demo")
    target_role: Mapped[str] = mapped_column(String(120))
    raw_text: Mapped[str] = mapped_column(Text)
    analysis_json: Mapped[str] = mapped_column(Text, default="{}")


class TrustStampProfileRecord(TimestampMixin, Base):
    __tablename__ = "trust_stamp_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_profile_id: Mapped[int] = mapped_column(ForeignKey("student_profiles.id"))
    public_slug: Mapped[str] = mapped_column(String(255), unique=True)
    consent_public: Mapped[bool] = mapped_column(Boolean, default=False)
    latest_score_id: Mapped[int | None] = mapped_column(ForeignKey("trust_scores.id"), nullable=True)
    visible_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    student_profile: Mapped[StudentProfile] = relationship(back_populates="trust_stamps")
