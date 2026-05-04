from __future__ import annotations

from collections import defaultdict
import re

from app.assessment.question_bank import DEFAULT_QUESTION_BANK
from app.schemas import (
    AdaptiveAnswerInput,
    AdaptiveTestEvaluationResponse,
    AdaptiveTestGenerateResponse,
    AdaptiveTestQuestionResponse,
    AiResumeAnalyzeResponse,
    FinalEmployabilityReportResponse,
    ProctoringEventInput,
    RoadmapPlanItemResponse,
)
from app.services.ats_service import AtsGuidanceService
from app.services.resume_model_service import ResumeModelService
from app.services.score_explanation_service import ScoreExplanationEngine
from trust_ml.intake import ResumeIntakeService
from trust_ml.roles import ROLE_BLUEPRINTS, get_role_blueprint


class EmployabilityPipelineService:
    def __init__(self) -> None:
        self.intake = ResumeIntakeService()
        self.ats = AtsGuidanceService()
        self.explainer = ScoreExplanationEngine()
        self.resume_model = ResumeModelService()

    def analyze_resume(
        self,
        *,
        resume_text: str,
        target_role: str | None,
        target_company: str | None,
    ) -> AiResumeAnalyzeResponse:
        profile = self.intake.from_resume_text(resume_text)
        selected_role = target_role or profile.inferred_target_role
        ats = self.ats.evaluate(
            request=__import__("app.schemas", fromlist=["AtsGuidanceRequest"]).AtsGuidanceRequest(
                resume_text=resume_text,
                target_role=selected_role,
                target_company=target_company,
            )
        )
        structure_issues = self._structure_issues(resume_text)
        project_count = self._project_count(resume_text)
        skill_match = self._skill_match_percent(list(profile.claimed_skills), selected_role)
        resume_prior = self.resume_model.score_resume_prior(
            resume_text=resume_text,
            selected_role=selected_role,
            skills=list(profile.claimed_skills),
            project_count=project_count,
            skill_match_percent=skill_match,
        )
        ats_explanation = self.explainer.ats(
            score=ats.ats_score,
            selected_role=selected_role,
            matched_keywords=ats.matched_keywords,
            missing_keywords=ats.missing_keywords,
            structure_issues=[
                *structure_issues,
                f"Trained model prior: {resume_prior['model_readiness_score']}% readiness ({resume_prior['readiness_band']}).",
            ],
        )
        return AiResumeAnalyzeResponse(
            skills=list(profile.claimed_skills),
            experience_level=self._experience_level(resume_text, len(profile.claimed_skills)),
            suggested_roles=self._suggest_roles(list(profile.claimed_skills), profile.inferred_target_role),
            selected_role=selected_role,
            ats=ats_explanation,
            skill_match_percent=skill_match,
            model_readiness_score=resume_prior["model_readiness_score"],
            model_version=resume_prior["model_version"],
            model_factors=resume_prior["model_factors"],
            missing_keywords=ats.missing_keywords,
            resume_suggestions=ats.recommendations,
        )

    def generate_test(self, *, skills: list[str], selected_role: str, experience_level: str) -> AdaptiveTestGenerateResponse:
        blueprint = get_role_blueprint(selected_role)
        normalized_skills = {self._normalize_skill(skill) for skill in skills}
        required = set(blueprint.claim_keywords)
        weak_skills = [skill for skill in required if self._normalize_skill(skill) not in normalized_skills]
        focus_skills = list(dict.fromkeys([*weak_skills[:4], *normalized_skills]))[:6]

        questions = []
        public_questions = DEFAULT_QUESTION_BANK.list_public()
        for question in public_questions:
            if self._question_matches_role(question["question_id"], selected_role) or question["skill_tag"] in focus_skills:
                questions.append(AdaptiveTestQuestionResponse(question_type=self._question_type(question["skill_tag"]), **question))
        if not questions:
            questions = [
                AdaptiveTestQuestionResponse(question_type=self._question_type(question["skill_tag"]), **question)
                for question in public_questions[:6]
            ]

        if experience_level.lower() == "beginner":
            questions.sort(key=lambda item: {"easy": 0, "medium": 1, "hard": 2}.get(item.difficulty_band, 1))
        else:
            questions.sort(key=lambda item: {"medium": 0, "hard": 1, "easy": 2}.get(item.difficulty_band, 1))

        return AdaptiveTestGenerateResponse(
            selected_role=selected_role,
            focus_skills=focus_skills,
            questions=questions[:8],
            adaptation_summary=(
                f"Generated {min(len(questions), 8)} questions for {selected_role}, prioritizing "
                f"{', '.join(focus_skills[:3]) or 'core fundamentals'}."
            ),
        )

    def evaluate_test(
        self,
        *,
        selected_role: str,
        skills: list[str],
        answers: list[AdaptiveAnswerInput],
        proctoring_events: list[ProctoringEventInput],
    ) -> AdaptiveTestEvaluationResponse:
        skill_totals: dict[str, list[float]] = defaultdict(list)
        difficulty_totals: dict[str, list[float]] = defaultdict(list)
        weighted_scores = []

        for answer in answers:
            question = DEFAULT_QUESTION_BANK.require(answer.question_id)
            correct = DEFAULT_QUESTION_BANK.is_correct(answer.question_id, answer.submitted_answer)
            difficulty_weight = {"easy": 0.9, "medium": 1.0, "hard": 1.12}.get(question.difficulty_band, 1.0)
            time_ratio = min(answer.elapsed_seconds / max(question.max_time_seconds, 1), 1.0)
            time_factor = 1.0 - max(time_ratio - 0.75, 0) * 0.25
            confidence_factor = 1.0 - abs((1.0 if correct else 0.0) - answer.confidence) * 0.08
            item_score = (100.0 if correct else 0.0) * difficulty_weight * time_factor * confidence_factor
            weighted_scores.append(min(item_score, 100.0))
            skill_totals[question.skill_tag].append(100.0 if correct else 0.0)
            difficulty_totals[question.difficulty_band].append(100.0 if correct else 0.0)

        test_score = sum(weighted_scores) / len(weighted_scores) if weighted_scores else 0.0
        skill_breakdown = {skill: sum(values) / len(values) for skill, values in skill_totals.items()}
        difficulty_breakdown = {level: sum(values) / len(values) for level, values in difficulty_totals.items()}
        risk_score, event_counts = self._proctoring_risk(proctoring_events)
        trust_score = max(0.0, test_score - risk_score)

        test_explanation = self.explainer.test(
            score=test_score,
            skill_breakdown=skill_breakdown,
            difficulty_breakdown=difficulty_breakdown,
        )
        trust_explanation = self.explainer.trust(
            score=trust_score,
            test_score=test_score,
            risk_score=risk_score,
            event_counts=event_counts,
        )
        weak_areas = [skill for skill, value in skill_breakdown.items() if value < 60]
        weak_areas.extend(self._missing_role_skills(skills, selected_role)[:3])
        return AdaptiveTestEvaluationResponse(
            test=test_explanation,
            trust=trust_explanation,
            proctoring_risk_score=round(risk_score, 2),
            skill_breakdown={skill: round(value, 2) for skill, value in skill_breakdown.items()},
            weak_areas=list(dict.fromkeys(weak_areas)),
        )

    def final_report(
        self,
        *,
        resume_text: str,
        selected_role: str,
        skills: list[str],
        ats_score: float,
        test_score: float,
        trust_score: float,
        skill_breakdown: dict[str, float],
        proctoring_events: list[ProctoringEventInput],
    ) -> FinalEmployabilityReportResponse:
        analysis = self.analyze_resume(resume_text=resume_text, target_role=selected_role, target_company=None)
        missing_skills = self._missing_role_skills(skills, selected_role)
        skill_match = self._skill_match_percent(skills, selected_role)
        role_fit_score = (ats_score * 0.25) + (test_score * 0.30) + (trust_score * 0.25) + (skill_match * 0.20)
        risk_score, event_counts = self._proctoring_risk(proctoring_events)
        test_explanation = self.explainer.test(
            score=test_score,
            skill_breakdown=skill_breakdown,
            difficulty_breakdown={},
        )
        trust_explanation = self.explainer.trust(
            score=trust_score,
            test_score=test_score,
            risk_score=risk_score,
            event_counts=event_counts,
        )
        return FinalEmployabilityReportResponse(
            ats=analysis.ats,
            test=test_explanation,
            trust=trust_explanation,
            role_fit=self.explainer.role_fit(
                score=role_fit_score,
                ats_score=ats_score,
                test_score=test_score,
                trust_score=trust_score,
                skill_match_percent=skill_match,
                missing_skills=missing_skills,
                selected_role=selected_role,
            ),
            extracted_skills=skills,
            skill_gaps=missing_skills,
            roadmap=self._roadmap(missing_skills, skill_breakdown, selected_role),
        )

    def _suggest_roles(self, skills: list[str], inferred_role: str) -> list[str]:
        scores = []
        normalized = {self._normalize_skill(skill) for skill in skills}
        for blueprint in ROLE_BLUEPRINTS:
            required = {self._normalize_skill(skill) for skill in blueprint.claim_keywords}
            overlap = len(required & normalized)
            scores.append((blueprint.name, overlap + (2 if blueprint.name == inferred_role else 0)))
        scores.sort(key=lambda item: item[1], reverse=True)
        return [name for name, _ in scores[:3]]

    def _skill_match_percent(self, skills: list[str], selected_role: str) -> float:
        blueprint = get_role_blueprint(selected_role)
        normalized = {self._normalize_skill(skill) for skill in skills}
        required = {self._normalize_skill(skill) for skill in blueprint.claim_keywords}
        return round((len(required & normalized) / len(required)) * 100, 2) if required else 0.0

    def _missing_role_skills(self, skills: list[str], selected_role: str) -> list[str]:
        blueprint = get_role_blueprint(selected_role)
        normalized = {self._normalize_skill(skill) for skill in skills}
        return [skill for skill in blueprint.claim_keywords if self._normalize_skill(skill) not in normalized]

    def _experience_level(self, resume_text: str, skill_count: int) -> str:
        years = [int(value) for value in re.findall(r"(\d+)\+?\s+years?", resume_text.lower())]
        max_years = max(years) if years else 0
        project_mentions = resume_text.lower().count("project")
        if max_years >= 3 or skill_count >= 8 or project_mentions >= 4:
            return "Advanced"
        if max_years >= 1 or skill_count >= 4 or project_mentions >= 2:
            return "Intermediate"
        return "Beginner"

    def _structure_issues(self, resume_text: str) -> list[str]:
        lowered = resume_text.lower()
        expected_sections = ("skills", "projects", "experience", "education")
        missing = [section for section in expected_sections if section not in lowered]
        issues = [f"Missing or unclear section: {section}." for section in missing]
        action_verbs = ("built", "created", "led", "improved", "optimized", "designed", "implemented", "deployed")
        if not any(verb in lowered for verb in action_verbs):
            issues.append("Few action verbs were detected in project or experience bullets.")
        if not re.search(r"\d+%|\d+x|\d+\s*(users|requests|ms|seconds|students)", lowered):
            issues.append("Quantified impact is weak or missing.")
        return issues

    def _project_count(self, resume_text: str) -> int:
        lowered = resume_text.lower()
        explicit_project_lines = sum(1 for line in lowered.splitlines() if line.strip().startswith("projects:"))
        project_mentions = lowered.count("project")
        return max(explicit_project_lines, min(project_mentions, 6))

    def _question_matches_role(self, question_id: str, selected_role: str) -> bool:
        normalized = selected_role.lower()
        if "full" in normalized:
            return question_id.startswith("fs_")
        if "backend" in normalized:
            return question_id.startswith("be_")
        return True

    def _question_type(self, skill_tag: str) -> str:
        if skill_tag in {"dsa", "javascript"}:
            return "coding"
        if skill_tag in {"projects", "fundamentals"}:
            return "scenario"
        return "mcq"

    def _proctoring_risk(self, events: list[ProctoringEventInput]) -> tuple[float, dict[str, int]]:
        weights = {
            "tab_switch": 7.0,
            "face_not_detected": 6.0,
            "multiple_faces": 14.0,
            "phone_detected": 18.0,
            "copy_paste": 4.0,
        }
        event_counts: dict[str, int] = defaultdict(int)
        risk = 0.0
        for event in events:
            event_type = event.event_type.strip().lower().replace(" ", "_")
            event_counts[event_type] += event.count
            risk += weights.get(event_type, 5.0) * event.count * max(event.severity, 0.2)
        return min(risk, 55.0), dict(event_counts)

    def _roadmap(self, missing_skills: list[str], skill_breakdown: dict[str, float], selected_role: str) -> list[RoadmapPlanItemResponse]:
        weak = [skill for skill, score in skill_breakdown.items() if score < 65]
        focus = list(dict.fromkeys([*missing_skills, *weak]))[:5]
        if not focus:
            focus = ["capstone", "system_design", "interview_practice"]
        return [
            RoadmapPlanItemResponse(
                title=f"Strengthen {skill.replace('_', ' ').title()}",
                skill=skill,
                project=f"Build a {selected_role} mini-project that proves {skill.replace('_', ' ')}.",
                resource=self._resource_for(skill),
                practice=f"Solve 5 targeted questions and explain trade-offs for {skill.replace('_', ' ')}.",
            )
            for skill in focus
        ]

    def _resource_for(self, skill: str) -> str:
        resources = {
            "react": "https://react.dev/learn",
            "javascript": "https://javascript.info/",
            "python": "https://docs.python.org/3/tutorial/",
            "sql": "https://sqlbolt.com/",
            "api": "https://restfulapi.net/",
            "apis": "https://restfulapi.net/",
            "data_structures": "https://neetcode.io/roadmap",
            "algorithms": "https://neetcode.io/roadmap",
            "machine_learning": "https://developers.google.com/machine-learning/crash-course",
        }
        return resources.get(self._normalize_skill(skill), "https://roadmap.sh/")

    def _normalize_skill(self, skill: str) -> str:
        return skill.strip().lower().replace(" ", "_").replace("-", "_").replace(".", "")
