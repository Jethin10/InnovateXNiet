from __future__ import annotations

import json

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.security import sign_payload, verify_payload_signature
from app.db.models import AssessmentSessionRecord, TrustScoreRecord, TrustStampProfileRecord
from app.services.roadmap_service import RoadmapService
from trust_ml.schemas import TrustScoreCard
from trust_ml.surfaces import build_trust_stamp_payload


class TrustStampService:
    def __init__(self, session: Session, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings

    def get_public_stamp(self, slug: str) -> dict:
        stamp = (
            self.session.query(TrustStampProfileRecord)
            .filter_by(public_slug=slug, consent_public=True)
            .one_or_none()
        )
        if stamp is None or stamp.latest_score_id is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trust stamp not found")

        score = self.session.get(TrustScoreRecord, stamp.latest_score_id)
        assessment = (
            self.session.query(AssessmentSessionRecord)
            .filter_by(score_id=stamp.latest_score_id)
            .one_or_none()
        )
        if score is None or assessment is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trust stamp not found")

        payload = build_trust_stamp_payload(
            self._to_assessment_session(assessment),
            self._to_scorecard(score),
        )
        payload["public_profile_url"] = f"https://truststamp.local/profile/{slug}"
        payload["verified_milestones"] = RoadmapService(self.session).get_verified_milestones(
            stamp.student_profile_id
        )
        if self.settings is not None:
            payload["signature"] = sign_payload(payload, secret_key=self.settings.auth_secret_key)
        return payload

    def verify_signature(self, payload: dict) -> dict[str, bool]:
        signature = payload.get("signature")
        if self.settings is None or not signature:
            return {"valid": False}
        unsigned_payload = dict(payload)
        unsigned_payload.pop("signature", None)
        return {
            "valid": verify_payload_signature(
                unsigned_payload,
                str(signature),
                secret_key=self.settings.auth_secret_key,
            )
        }

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

    def _to_assessment_session(self, assessment: AssessmentSessionRecord):
        from app.services.scoring_service import ScoringService

        return ScoringService(self.session)._to_trust_ml_session(assessment)
