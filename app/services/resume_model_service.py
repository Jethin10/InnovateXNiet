from __future__ import annotations

from app.ml.service import load_trust_model
from trust_ml.schemas import AnswerEvent, AssessmentSession, EvidenceProfile, QuestionStage


class ResumeModelService:
    """Uses the trained trust/readiness artifact to create a resume-only readiness prior."""

    def score_resume_prior(
        self,
        *,
        resume_text: str,
        selected_role: str,
        skills: list[str],
        project_count: int,
        skill_match_percent: float,
    ) -> dict:
        model = load_trust_model()
        normalized_skills = tuple(skill.lower().replace(" ", "_") for skill in skills)
        stage = QuestionStage(
            stage_id=0,
            name="Resume prior",
            difficulty_band="medium",
            time_limit_seconds=90,
            skill_tag="projects",
        )
        proxy_accuracy = max(0.25, min((skill_match_percent / 100) * 0.75 + min(project_count, 4) * 0.06, 0.92))
        answers = tuple(
            AnswerEvent(
                question_id=f"resume_signal_{index}",
                stage_id=0,
                difficulty_band="medium",
                skill_tag=skill_tag,
                correct=proxy_accuracy >= threshold,
                elapsed_seconds=42 + index * 4,
                confidence=min(0.62 + proxy_accuracy * 0.3, 0.92),
                answer_changes=0,
                max_time_seconds=90,
            )
            for index, (skill_tag, threshold) in enumerate(
                (
                    ("projects", 0.45),
                    ("fundamentals", 0.58),
                    ("dsa", 0.68),
                ),
                start=1,
            )
        )
        session = AssessmentSession(
            session_id="resume-prior",
            user_id="resume-candidate",
            target_role=selected_role,
            target_company="General",
            stages=(stage,),
            answers=answers,
            evidence=EvidenceProfile(
                resume_claims=normalized_skills,
                verified_skills=normalized_skills[: max(1, min(len(normalized_skills), 4))],
                project_tags=normalized_skills,
                project_count=project_count,
                github_repo_count=max(0, min(project_count, 4)),
            ),
        )
        scorecard = model.score_session(session)
        return {
            "model_readiness_score": round(scorecard.overall_readiness * 100, 2),
            "model_probability": round(scorecard.model_probability * 100, 2),
            "model_version": str(model.training_summary.get("selected_model") or model.training_summary.get("estimator") or "trained_artifact"),
            "readiness_band": scorecard.readiness_band,
            "model_factors": list(scorecard.explanations),
        }
