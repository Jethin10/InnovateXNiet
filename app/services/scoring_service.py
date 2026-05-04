from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.assessment.question_bank import DEFAULT_QUESTION_BANK, AssessmentQuestion
from app.db.models import (
    AssessmentAttemptRecord,
    AssessmentAuditEventRecord,
    AssessmentSessionRecord,
    EvidenceVerificationRecord,
    ResumeArtifact,
    RoadmapSnapshot,
    StudentProfile,
    TrustScoreRecord,
    TrustStampProfileRecord,
)
from app.ml.service import load_trust_model
from app.schemas import (
    AssessmentAnswerInput,
    AssessmentAttemptStartResponse,
    AssessmentCreateRequest,
    AssessmentQuestionResponse,
    AssessmentResponse,
    RoadmapResponse,
    ScoreResponse,
    TrustScoreResponse,
)
from app.services.roadmap_service import RoadmapService
from trust_ml.roadmap import PersonalizedRoadmapBuilder
from trust_ml.schemas import AnswerEvent, AssessmentSession, EvidenceProfile, QuestionStage, ResumeProfile


class ScoringService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.model = load_trust_model()
        self.roadmap_builder = PersonalizedRoadmapBuilder()

    def start_attempt(self, student_id: int) -> AssessmentAttemptStartResponse:
        student = self.session.get(StudentProfile, student_id)
        if student is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")

        question_ids = DEFAULT_QUESTION_BANK.list_question_ids()
        expires_at = datetime.now(UTC) + timedelta(minutes=45)
        attempt = AssessmentAttemptRecord(
            student_profile=student,
            status="started",
            expires_at=expires_at,
            question_ids_json=json.dumps(question_ids),
        )
        self.session.add(attempt)
        self.session.flush()
        self._add_audit_event(
            attempt.id,
            student_id,
            "attempt_started",
            {"question_count": len(question_ids)},
        )
        self.session.commit()
        self.session.refresh(attempt)
        return AssessmentAttemptStartResponse(
            attempt_id=attempt.id,
            status=attempt.status,
            expires_at=attempt.expires_at.isoformat(),
            questions=[
                AssessmentQuestionResponse(**question)
                for question in DEFAULT_QUESTION_BANK.list_public_by_ids(question_ids)
            ],
        )

    def create_assessment(
        self,
        student_id: int,
        request: AssessmentCreateRequest,
    ) -> AssessmentResponse:
        student = self.session.get(StudentProfile, student_id)
        if student is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")
        attempt = self._validate_attempt(student_id, request.attempt_id)

        record = AssessmentSessionRecord(
            student_profile=student,
            attempt_id=attempt.id if attempt is not None else None,
            status="submitted",
            evidence_json=request.evidence.model_dump_json(),
            answers_json=json.dumps(
                self._validated_answer_payloads(
                    request.answers,
                    allowed_question_ids=self._attempt_question_ids(attempt),
                )
            ),
        )
        self.session.add(record)
        if attempt is not None:
            attempt.status = "submitted"
            attempt.completed_at = datetime.now(UTC)
            self._add_audit_event(
                attempt.id,
                student_id,
                "assessment_submitted",
                {"answer_count": len(request.answers)},
            )
        self.session.commit()
        self.session.refresh(record)

        return AssessmentResponse(assessment_id=record.id, status=record.status)

    def _validated_answer_payloads(
        self,
        answers: list[AssessmentAnswerInput],
        *,
        allowed_question_ids: set[str] | None = None,
    ) -> list[dict]:
        if not answers:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Assessment must contain at least one answer",
            )

        payloads: list[dict] = []
        seen_question_ids: set[str] = set()
        for answer in answers:
            if answer.question_id in seen_question_ids:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Duplicate assessment question: {answer.question_id}",
                )
            seen_question_ids.add(answer.question_id)

            try:
                question = DEFAULT_QUESTION_BANK.require(answer.question_id)
            except KeyError as exc:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Unknown assessment question: {answer.question_id}",
                ) from exc
            if allowed_question_ids is not None and answer.question_id not in allowed_question_ids:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Question {answer.question_id} was not assigned to this attempt",
                )

            self._validate_client_metadata(answer, question)
            if answer.submitted_answer is None or not answer.submitted_answer.strip():
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"submitted_answer is required for {answer.question_id}",
                )
            if answer.elapsed_seconds < 0:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Negative elapsed time for {answer.question_id}",
                )
            if answer.elapsed_seconds > question.max_time_seconds:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Answer for {answer.question_id} exceeded time limit",
                )
            if not 0.0 <= answer.confidence <= 1.0:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Confidence must be between 0 and 1 for {answer.question_id}",
                )

            payloads.append(
                {
                    "question_id": question.question_id,
                    "stage_id": question.stage_id,
                    "difficulty_band": question.difficulty_band,
                    "skill_tag": question.skill_tag,
                    "submitted_answer": answer.submitted_answer,
                    "correct": DEFAULT_QUESTION_BANK.is_correct(
                        question.question_id,
                        answer.submitted_answer,
                    ),
                    "elapsed_seconds": answer.elapsed_seconds,
                    "confidence": answer.confidence,
                    "answer_changes": answer.answer_changes,
                    "max_time_seconds": question.max_time_seconds,
                    "client_correct_ignored": answer.correct,
                }
            )

        return payloads

    def _validate_attempt(
        self,
        student_id: int,
        attempt_id: int | None,
    ) -> AssessmentAttemptRecord | None:
        if attempt_id is None:
            return None

        attempt = self.session.get(AssessmentAttemptRecord, attempt_id)
        if attempt is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment attempt not found")
        if attempt.student_profile_id != student_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Assessment attempt does not belong to this student",
            )
        if attempt.status != "started":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Assessment attempt is not active")
        expires_at = attempt.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if datetime.now(UTC) > expires_at:
            attempt.status = "expired"
            self.session.add(attempt)
            self.session.commit()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Assessment attempt has expired")
        return attempt

    def _attempt_question_ids(self, attempt: AssessmentAttemptRecord | None) -> set[str] | None:
        if attempt is None:
            return None
        return set(json.loads(attempt.question_ids_json))

    def _add_audit_event(
        self,
        attempt_id: int,
        student_id: int,
        event_type: str,
        payload: dict,
    ) -> None:
        self.session.add(
            AssessmentAuditEventRecord(
                attempt_id=attempt_id,
                student_profile_id=student_id,
                event_type=event_type,
                payload_json=json.dumps(payload),
            )
        )

    def _validate_client_metadata(
        self,
        answer: AssessmentAnswerInput,
        question: AssessmentQuestion,
    ) -> None:
        expected = {
            "stage_id": question.stage_id,
            "difficulty_band": question.difficulty_band,
            "skill_tag": question.skill_tag,
        }
        submitted = {
            "stage_id": answer.stage_id,
            "difficulty_band": answer.difficulty_band,
            "skill_tag": answer.skill_tag,
        }
        if submitted != expected:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Question metadata mismatch for {answer.question_id}",
            )

    def score_assessment(self, assessment_id: int) -> ScoreResponse:
        record = self.session.get(AssessmentSessionRecord, assessment_id)
        if record is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")

        if record.status not in {"submitted", "scored"}:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Assessment is not ready for scoring")

        assessment_session = self._to_trust_ml_session(record)
        scorecard = self.model.score_session(assessment_session)
        score_record = TrustScoreRecord(
            overall_readiness=scorecard.overall_readiness,
            model_probability=scorecard.model_probability,
            raw_accuracy=scorecard.raw_accuracy,
            confidence_reliability=scorecard.confidence_reliability,
            evidence_alignment=scorecard.evidence_alignment,
            calibration_gap=scorecard.calibration_gap,
            bluff_index=scorecard.bluff_index,
            readiness_band=scorecard.readiness_band,
            risk_band=scorecard.risk_band,
            skill_scores_json=json.dumps(scorecard.skill_scores),
            feature_snapshot_json=json.dumps(scorecard.feature_snapshot),
            explanations_json=json.dumps(list(scorecard.explanations)),
            model_version=self.model.training_summary.get("selected_model", "v1"),
        )
        self.session.add(score_record)
        self.session.flush()

        record.score = score_record
        record.score_id = score_record.id
        record.status = "scored"
        if record.attempt_id is not None:
            attempt = self.session.get(AssessmentAttemptRecord, record.attempt_id)
            if attempt is not None:
                attempt.status = "scored"
                self._add_audit_event(
                    attempt.id,
                    record.student_profile_id,
                    "assessment_scored",
                    {"score_id": score_record.id},
                )

        roadmap_graph = self.roadmap_builder.build(
            self._resume_profile(record),
            scorecard,
        )
        snapshot = RoadmapSnapshot(
            student_profile=record.student_profile,
            target_role=roadmap_graph.target_role,
            current_level=roadmap_graph.current_level,
            summary=roadmap_graph.summary,
            graph_json=RoadmapResponse.from_graph(roadmap_graph).model_dump_json(),
        )
        self.session.add(snapshot)

        trust_stamp = (
            self.session.query(TrustStampProfileRecord)
            .filter_by(student_profile_id=record.student_profile_id)
            .one_or_none()
        )
        if trust_stamp is not None:
            trust_stamp.latest_score_id = score_record.id
            trust_stamp.visible_summary = roadmap_graph.summary

        self.session.commit()

        return ScoreResponse(
            trust_score=TrustScoreResponse.from_scorecard(scorecard),
            roadmap=RoadmapResponse.from_graph(roadmap_graph),
        )

    def get_latest_roadmap(self, student_id: int) -> RoadmapResponse:
        return RoadmapService(self.session).get_current_roadmap(student_id)

    def _to_trust_ml_session(self, record: AssessmentSessionRecord) -> AssessmentSession:
        answers_payload = [AssessmentAnswerInput.model_validate(answer) for answer in json.loads(record.answers_json)]
        evidence_payload = json.loads(record.evidence_json)
        evidence_payload = self._merge_verified_evidence(record.student_profile_id, evidence_payload)
        evidence = EvidenceProfile(
            codeforces_rating=evidence_payload.get("codeforces_rating"),
            leetcode_solved=evidence_payload.get("leetcode_solved"),
            resume_claims=tuple(evidence_payload.get("resume_claims", [])),
            verified_skills=tuple(evidence_payload.get("verified_skills", [])),
            project_tags=tuple(evidence_payload.get("project_tags", [])),
            project_count=evidence_payload.get("project_count", 0),
            github_repo_count=evidence_payload.get("github_repo_count", 0),
        )

        stage_map: dict[int, QuestionStage] = {}
        answer_events: list[AnswerEvent] = []
        for answer in answers_payload:
            stage_map.setdefault(
                answer.stage_id,
                QuestionStage(
                    stage_id=answer.stage_id,
                    name=f"Stage {answer.stage_id}",
                    difficulty_band=answer.difficulty_band,
                    time_limit_seconds=answer.max_time_seconds,
                    skill_tag=answer.skill_tag,
                ),
            )
            answer_events.append(
                AnswerEvent(
                    question_id=answer.question_id,
                    stage_id=answer.stage_id,
                    difficulty_band=answer.difficulty_band,
                    skill_tag=answer.skill_tag,
                    correct=answer.correct,
                    elapsed_seconds=answer.elapsed_seconds,
                    confidence=answer.confidence,
                    answer_changes=answer.answer_changes,
                    max_time_seconds=answer.max_time_seconds,
                )
            )

        student = record.student_profile
        return AssessmentSession(
            session_id=f"assessment-{record.id}",
            user_id=f"student-{student.id}",
            target_role=student.target_role,
            target_company=student.target_company or "Unknown",
            stages=tuple(stage_map.values()),
            answers=tuple(answer_events),
            evidence=evidence,
        )

    def _merge_verified_evidence(self, student_id: int, evidence_payload: dict) -> dict:
        merged = dict(evidence_payload)
        codeforces = (
            self.session.query(EvidenceVerificationRecord)
            .filter_by(student_profile_id=student_id, source="codeforces", verified=True)
            .order_by(EvidenceVerificationRecord.id.desc())
            .first()
        )
        if codeforces is not None and not merged.get("codeforces_rating"):
            merged["codeforces_rating"] = codeforces.rating

        github = (
            self.session.query(EvidenceVerificationRecord)
            .filter_by(student_profile_id=student_id, source="github", verified=True)
            .order_by(EvidenceVerificationRecord.id.desc())
            .first()
        )
        if github is not None and not merged.get("github_repo_count"):
            payload = json.loads(github.payload_json)
            merged["github_repo_count"] = payload.get("repo_count", 0)
            if not merged.get("project_count"):
                merged["project_count"] = min(int(payload.get("repo_count", 0) or 0), 4)

        if not merged.get("resume_claims"):
            latest_resume = (
                self.session.query(ResumeArtifact)
                .filter_by(student_profile_id=student_id)
                .order_by(ResumeArtifact.id.desc())
                .first()
            )
            if latest_resume is not None:
                merged["resume_claims"] = json.loads(latest_resume.extracted_claims_json)
        return merged

    def _resume_profile(self, record: AssessmentSessionRecord) -> ResumeProfile:
        latest_resume = (
            self.session.query(ResumeArtifact)
            .filter_by(student_profile_id=record.student_profile_id)
            .order_by(ResumeArtifact.id.desc())
            .first()
        )
        claims: list[str] = []
        source = "manual"
        if latest_resume is not None:
            claims = json.loads(latest_resume.extracted_claims_json)
            source = "resume"

        return ResumeProfile(
            inferred_target_role=record.student_profile.target_role,
            claimed_skills=tuple(claims),
            source=source,
        )
