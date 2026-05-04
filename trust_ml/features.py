from __future__ import annotations

from collections import defaultdict
from statistics import mean

from .roles import get_role_blueprint
from .schemas import AssessmentSession


def _clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, value))


def _normalize_skill_name(value: str) -> str:
    normalized = value.strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "data_structures": "dsa",
        "algorithms": "dsa",
        "dbms": "fundamentals",
        "operating_systems": "fundamentals",
        "computer_networks": "fundamentals",
        "api_design": "projects",
        "backend_systems": "backend",
    }
    return aliases.get(normalized, normalized)


class FeatureEngineer:
    """Turns an assessment session into explainable trust features."""

    difficulty_bands = ("easy", "medium", "hard")
    skill_groups = ("dsa", "fundamentals", "projects")
    difficulty_weights = {"easy": 1.0, "medium": 1.5, "hard": 2.0}

    def transform_session(self, session: AssessmentSession) -> dict[str, float]:
        answers = session.answers
        evidence = session.evidence

        if not answers:
            raise ValueError("Assessment session must contain at least one answer event.")

        correctness = [1.0 if answer.correct else 0.0 for answer in answers]
        confidences = [_clamp(answer.confidence) for answer in answers]
        time_ratios = [
            _clamp(answer.elapsed_seconds / answer.max_time_seconds)
            for answer in answers
        ]
        answer_change_values = [_clamp(answer.answer_changes / 3.0) for answer in answers]

        difficulty_accuracy: dict[str, list[float]] = defaultdict(list)
        skill_accuracy: dict[str, list[float]] = defaultdict(list)
        stage_accuracy: dict[int, list[float]] = defaultdict(list)
        correct_skills: set[str] = {
            _normalize_skill_name(value) for value in evidence.verified_skills
        } | {_normalize_skill_name(value) for value in evidence.project_tags}

        weighted_correct = 0.0
        total_weight = 0.0
        for answer in answers:
            score = 1.0 if answer.correct else 0.0
            normalized_skill = _normalize_skill_name(answer.skill_tag)
            difficulty_accuracy[answer.difficulty_band].append(score)
            skill_accuracy[normalized_skill].append(score)
            stage_accuracy[answer.stage_id].append(score)

            weight = self.difficulty_weights.get(answer.difficulty_band, 1.0)
            weighted_correct += score * weight
            total_weight += weight

            if answer.correct:
                correct_skills.add(normalized_skill)

        resume_claims = tuple(_normalize_skill_name(skill) for skill in evidence.resume_claims)
        claim_hits = sum(1 for claim in resume_claims if claim in correct_skills)
        resume_claim_alignment = (
            claim_hits / len(resume_claims) if resume_claims else 1.0
        )
        resume_claim_inflation = 1.0 - _clamp(resume_claim_alignment)

        codeforces_rating_normalized = 0.0
        if evidence.codeforces_rating is not None:
            codeforces_rating_normalized = _clamp(
                (evidence.codeforces_rating - 800) / 1800.0
            )

        leetcode_solved_normalized = 0.0
        if evidence.leetcode_solved is not None:
            leetcode_solved_normalized = _clamp(evidence.leetcode_solved / 500.0)

        project_evidence_strength = _clamp(
            (evidence.project_count / 4.0) * 0.6
            + (len(set(evidence.project_tags)) / 4.0) * 0.4
        )

        external_evidence_score = _clamp(
            codeforces_rating_normalized * 0.55
            + leetcode_solved_normalized * 0.15
            + project_evidence_strength * 0.30
        )
        role_blueprint = get_role_blueprint(session.target_role)
        role_weights = role_blueprint.model_skill_weights
        stage_1_accuracy = mean(stage_accuracy.get(1, [0.0]))
        stage_3_accuracy = mean(stage_accuracy.get(3, [0.0]))

        features: dict[str, float] = {
            "accuracy_overall": mean(correctness),
            "weighted_accuracy": weighted_correct / total_weight if total_weight else 0.0,
            "avg_time_ratio": mean(time_ratios),
            "confidence_mean": mean(confidences),
            "confidence_calibration_gap": mean(
                abs(confidence - score)
                for confidence, score in zip(confidences, correctness, strict=True)
            ),
            "overconfidence_rate": mean(
                max(confidence - score, 0.0)
                for confidence, score in zip(confidences, correctness, strict=True)
            ),
            "underconfidence_rate": mean(
                max(score - confidence, 0.0)
                for confidence, score in zip(confidences, correctness, strict=True)
            ),
            "answer_change_rate": mean(answer_change_values),
            "resume_claim_alignment": _clamp(resume_claim_alignment),
            "resume_claim_inflation": resume_claim_inflation,
            "project_evidence_strength": project_evidence_strength,
            "codeforces_rating_normalized": codeforces_rating_normalized,
            "leetcode_solved_normalized": leetcode_solved_normalized,
            "external_evidence_score": external_evidence_score,
            "stage_progression_drop": _clamp(stage_1_accuracy - stage_3_accuracy),
        }

        confidence_on_correct = [
            confidence
            for confidence, score in zip(confidences, correctness, strict=True)
            if score == 1.0
        ]
        confidence_on_incorrect = [
            confidence
            for confidence, score in zip(confidences, correctness, strict=True)
            if score == 0.0
        ]

        if confidence_on_correct and confidence_on_incorrect:
            delta = mean(confidence_on_correct) - mean(confidence_on_incorrect)
        elif confidence_on_correct:
            delta = mean(confidence_on_correct)
        else:
            delta = -mean(confidence_on_incorrect)

        features["confidence_correct_delta"] = _clamp((delta + 1.0) / 2.0)
        features["confidence_volatility"] = _clamp(
            max(confidences) - min(confidences) if confidences else 0.0
        )

        for band in self.difficulty_bands:
            values = difficulty_accuracy.get(band, [])
            features[f"accuracy_{band}"] = mean(values) if values else 0.0

        for skill in self.skill_groups:
            values = skill_accuracy.get(skill, [])
            observed_accuracy = mean(values) if values else 0.0
            if skill == "projects":
                observed_accuracy = _clamp(
                    observed_accuracy * 0.5 + project_evidence_strength * 0.5
                )
            features[f"skill_score_{skill}"] = observed_accuracy

        features["target_role_dsa_weight"] = role_weights.get("dsa", 0.0)
        features["target_role_fundamentals_weight"] = role_weights.get("fundamentals", 0.0)
        features["target_role_projects_weight"] = role_weights.get("projects", 0.0)
        features["target_role_fit_proxy"] = _clamp(
            features["skill_score_dsa"] * role_weights.get("dsa", 0.0)
            + features["skill_score_fundamentals"] * role_weights.get("fundamentals", 0.0)
            + features["skill_score_projects"] * role_weights.get("projects", 0.0)
        )
        features["role_is_full_stack"] = 1.0 if role_blueprint.name == "Full Stack Developer" else 0.0
        features["role_is_backend"] = 1.0 if role_blueprint.name == "Backend SDE" else 0.0
        features["role_is_ai_ml"] = 1.0 if role_blueprint.name == "AI/ML Engineer" else 0.0

        return {name: round(value, 6) for name, value in features.items()}
