from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.repositories.student_repository import StudentRepository
from app.schemas import ResumeAnalysisRequest, ResumeAnalysisResponse
from trust_ml.intake import ResumeIntakeService


SUPPORTED_EVIDENCE_SKILLS = {
    "python",
    "sql",
    "apis",
    "data_structures",
    "algorithms",
    "javascript",
    "react",
    "html",
    "css",
    "machine_learning",
    "statistics",
    "numpy",
    "pandas",
}


class ResumeAnalysisService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = StudentRepository(session)
        self.intake = ResumeIntakeService()

    def analyze(self, student_id: int, request: ResumeAnalysisRequest) -> ResumeAnalysisResponse:
        student = self.repository.get_student(student_id)
        if student is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")

        profile = self.intake.from_resume_text(request.resume_text)
        project_count = sum(
            1
            for line in request.resume_text.splitlines()
            if line.strip().lower().startswith("projects:")
        )
        unsupported_claims = [
            skill
            for skill in profile.claimed_skills
            if skill not in SUPPORTED_EVIDENCE_SKILLS
        ]
        risk_flags = []
        if unsupported_claims:
            risk_flags.append("Some resume claims need external proof before they increase trust.")
        if project_count == 0:
            risk_flags.append("No clearly marked project evidence was detected.")

        response = ResumeAnalysisResponse(
            inferred_target_role=profile.inferred_target_role,
            claimed_skills=list(profile.claimed_skills),
            project_count=project_count,
            unsupported_claims=unsupported_claims,
            risk_flags=risk_flags,
        )
        self.repository.add_resume_artifact(
            student,
            raw_text=request.resume_text,
            extracted_claims=profile.claimed_skills,
            filename=request.filename,
            analysis=response.model_dump(),
        )
        return response
