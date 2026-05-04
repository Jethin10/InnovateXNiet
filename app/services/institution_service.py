from __future__ import annotations

import json

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.db.models import (
    AssessmentSessionRecord,
    CohortMembership,
    Institution,
    TrustScoreRecord,
)
from app.repositories.institution_repository import InstitutionRepository
from app.schemas import (
    AddCohortMemberRequest,
    CohortAnalyticsResponse,
    CohortResponse,
    InstitutionCreateRequest,
    InstitutionResponse,
)
from trust_ml.schemas import TrustScoreCard
from trust_ml.surfaces import build_college_dashboard


class InstitutionService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = InstitutionRepository(session)

    def create_institution(self, request: InstitutionCreateRequest) -> InstitutionResponse:
        institution = self.repository.create_institution(request.name)
        return InstitutionResponse(institution_id=institution.id, name=institution.name)

    def create_cohort(self, institution_id: int, name: str) -> CohortResponse:
        institution = self.session.get(Institution, institution_id)
        if institution is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Institution not found")
        cohort = self.repository.create_cohort(institution_id, name)
        return CohortResponse(cohort_id=cohort.id, institution_id=cohort.institution_id, name=cohort.name)

    def add_member(self, cohort_id: int, request: AddCohortMemberRequest) -> dict[str, int]:
        cohort = self.repository.get_cohort(cohort_id)
        if cohort is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cohort not found")
        membership = self.repository.add_member(cohort_id, request.student_id)
        return {"membership_id": membership.id}

    def get_analytics(self, cohort_id: int) -> CohortAnalyticsResponse:
        cohort = self.repository.get_cohort(cohort_id)
        if cohort is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cohort not found")

        memberships = (
            self.session.query(CohortMembership)
            .filter_by(cohort_id=cohort_id)
            .all()
        )
        entries: list[tuple[str, TrustScoreCard]] = []
        for membership in memberships:
            student = membership.student_profile
            latest_assessment = (
                self.session.query(AssessmentSessionRecord)
                .filter_by(student_profile_id=student.id)
                .filter(AssessmentSessionRecord.score_id.is_not(None))
                .order_by(AssessmentSessionRecord.id.desc())
                .first()
            )
            if latest_assessment is None or latest_assessment.score_id is None:
                continue
            score = self.session.get(TrustScoreRecord, latest_assessment.score_id)
            if score is None:
                continue
            entries.append((f"student-{student.id}", self._to_scorecard(score)))

        dashboard = build_college_dashboard(entries)
        return CohortAnalyticsResponse(
            cohort_id=cohort.id,
            cohort_name=cohort.name,
            total_students=dashboard["total_students"],
            average_trust_score=dashboard["average_trust_score"],
            average_bluff_index=dashboard["average_bluff_index"],
            risk_buckets=dashboard["risk_buckets"],
            skill_gap_heatmap=dashboard["skill_gap_heatmap"],
            flagged_students=dashboard["flagged_students"],
        )

    def _to_scorecard(self, score: TrustScoreRecord) -> TrustScoreCard:
        return TrustScoreCard(
            overall_readiness=score.overall_readiness,
            model_probability=score.model_probability,
            raw_accuracy=score.raw_accuracy,
            skill_scores=json.loads(score.skill_scores_json),
            confidence_reliability=score.confidence_reliability,
            evidence_alignment=score.evidence_alignment,
            calibration_gap=score.calibration_gap,
            bluff_index=score.bluff_index,
            readiness_band=score.readiness_band,
            risk_band=score.risk_band,
            feature_snapshot=json.loads(score.feature_snapshot_json),
            explanations=tuple(json.loads(score.explanations_json)),
        )
