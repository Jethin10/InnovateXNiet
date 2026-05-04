from __future__ import annotations

import json

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.repositories.student_repository import StudentRepository
from app.schemas import (
    IntakeRequest,
    IntakeResponse,
    StoredAssessmentPlanResponse,
    TrustStampResponse,
    VerificationPlanResponse,
    VerificationStageResponse,
)
from trust_ml.intake import ResumeIntakeService
from trust_ml.verification import VerificationPlanner


class IntakeService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = StudentRepository(session)
        self.resume_service = ResumeIntakeService()
        self.verification_planner = VerificationPlanner()

    def process(self, student_id: int, request: IntakeRequest) -> IntakeResponse:
        student = self.repository.get_student(student_id)
        if student is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")

        if request.resume_text:
            profile = self.resume_service.from_resume_text(request.resume_text)
            self.repository.add_resume_artifact(
                student,
                raw_text=request.resume_text,
                extracted_claims=profile.claimed_skills,
            )
        else:
            profile = self.resume_service.from_manual_skills(
                target_role=student.target_role,
                skills=request.manual_skills,
            )

        student.target_role = profile.inferred_target_role or student.target_role
        student.preferred_resource_style = request.preferred_resource_style
        self.session.add(student)
        self.session.commit()
        self.session.refresh(student)

        plan = self.verification_planner.build(profile)
        self.repository.create_assessment_plan(
            student,
            target_role=plan.target_role,
            claimed_skills=plan.claimed_skills,
            stages=[
                {
                    "stage_id": stage.stage_id,
                    "difficulty": stage.difficulty,
                    "time_limit_minutes": stage.time_limit_minutes,
                    "focus_skills": list(stage.focus_skills),
                    "objective": stage.objective,
                    "pass_rule": stage.pass_rule,
                }
                for stage in plan.stages
            ],
        )
        trust_stamp = self.repository.upsert_trust_stamp(
            student,
            consent_public=request.consent_public,
        )

        return IntakeResponse(
            student_id=student.id,
            inferred_target_role=plan.target_role,
            claimed_skills=list(plan.claimed_skills),
            assessment_plan=VerificationPlanResponse(
                target_role=plan.target_role,
                claimed_skills=list(plan.claimed_skills),
                stages=[
                    VerificationStageResponse(
                        stage_id=stage.stage_id,
                        difficulty=stage.difficulty,
                        time_limit_minutes=stage.time_limit_minutes,
                        focus_skills=list(stage.focus_skills),
                        objective=stage.objective,
                        pass_rule=stage.pass_rule,
                    )
                    for stage in plan.stages
                ],
            ),
            trust_stamp=TrustStampResponse(
                slug=trust_stamp.public_slug,
                consent_public=trust_stamp.consent_public,
            ),
        )

    def get_latest_plan(self, student_id: int) -> StoredAssessmentPlanResponse:
        student = self.repository.get_student(student_id)
        if student is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")

        plan = self.repository.get_latest_assessment_plan(student_id)
        if plan is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment plan not found")

        return StoredAssessmentPlanResponse(
            student_id=student_id,
            target_role=plan.target_role,
            claimed_skills=list(json.loads(plan.claimed_skills_json)),
            stages=[
                VerificationStageResponse(**stage)
                for stage in json.loads(plan.stages_json)
            ],
        )
