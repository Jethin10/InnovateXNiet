from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.db.models import (
    AssessmentPlanRecord,
    ResumeArtifact,
    StudentProfile,
    TrustStampProfileRecord,
    User,
)


class StudentRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_student(
        self,
        *,
        full_name: str,
        email: str | None,
        target_role: str,
        target_company: str | None,
        password_hash: str | None = None,
    ) -> StudentProfile:
        user = User(
            full_name=full_name,
            email=email.lower() if email else None,
            role="student",
            password_hash=password_hash,
        )
        profile = StudentProfile(
            user=user,
            target_role=target_role,
            target_company=target_company,
        )
        self.session.add(profile)
        self.session.commit()
        self.session.refresh(profile)
        self.session.refresh(profile.user)
        return profile

    def get_student(self, student_id: int) -> StudentProfile | None:
        return self.session.get(StudentProfile, student_id)

    def add_resume_artifact(
        self,
        student_profile: StudentProfile,
        *,
        raw_text: str,
        extracted_claims: tuple[str, ...],
        filename: str | None = None,
        analysis: dict | None = None,
    ) -> ResumeArtifact:
        artifact = ResumeArtifact(
            student_profile=student_profile,
            filename=filename,
            raw_text=raw_text,
            parse_status="parsed",
            extracted_claims_json=json.dumps(list(extracted_claims)),
            analysis_json=json.dumps(analysis or {}),
        )
        self.session.add(artifact)
        self.session.commit()
        self.session.refresh(artifact)
        return artifact

    def upsert_trust_stamp(
        self,
        student_profile: StudentProfile,
        *,
        consent_public: bool,
    ) -> TrustStampProfileRecord:
        record = (
            self.session.query(TrustStampProfileRecord)
            .filter_by(student_profile_id=student_profile.id)
            .one_or_none()
        )
        if record is None:
            record = TrustStampProfileRecord(
                student_profile=student_profile,
                public_slug=f"student-{student_profile.id}",
                consent_public=consent_public,
            )
            self.session.add(record)
        else:
            record.consent_public = consent_public

        self.session.commit()
        self.session.refresh(record)
        return record

    def create_assessment_plan(
        self,
        student_profile: StudentProfile,
        *,
        target_role: str,
        claimed_skills: tuple[str, ...],
        stages: list[dict],
    ) -> AssessmentPlanRecord:
        plan = AssessmentPlanRecord(
            student_profile=student_profile,
            target_role=target_role,
            claimed_skills_json=json.dumps(list(claimed_skills)),
            stages_json=json.dumps(stages),
        )
        self.session.add(plan)
        self.session.commit()
        self.session.refresh(plan)
        return plan

    def get_latest_assessment_plan(self, student_id: int) -> AssessmentPlanRecord | None:
        return (
            self.session.query(AssessmentPlanRecord)
            .filter_by(student_profile_id=student_id)
            .order_by(AssessmentPlanRecord.id.desc())
            .first()
        )
