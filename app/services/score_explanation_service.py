from __future__ import annotations

from app.schemas import ScoreExplanationResponse


class ScoreExplanationEngine:
    def ats(
        self,
        *,
        score: float,
        selected_role: str,
        matched_keywords: list[str],
        missing_keywords: list[str],
        structure_issues: list[str],
    ) -> ScoreExplanationResponse:
        factors = [
            f"Keyword match: {round(score)}% for {selected_role}.",
            f"Matched keywords: {', '.join(matched_keywords[:6]) or 'none detected'}.",
        ]
        if missing_keywords:
            factors.append(f"Missing keywords: {', '.join(missing_keywords[:6])}.")
        factors.extend(structure_issues[:3])
        tips = [
            f"Add concrete evidence for {keyword} in projects or experience."
            for keyword in missing_keywords[:4]
        ]
        if structure_issues:
            tips.append("Use clear sections: Summary, Skills, Projects, Experience, Education.")
        if not tips:
            tips.append("Add more quantified impact so the resume is recruiter-readable.")
        return ScoreExplanationResponse(
            score=round(score, 2),
            explanation=f"Your resume matches {round(score)}% of the strongest signals for {selected_role}.",
            factors=factors,
            improvement_tips=tips,
        )

    def test(
        self,
        *,
        score: float,
        skill_breakdown: dict[str, float],
        difficulty_breakdown: dict[str, float],
    ) -> ScoreExplanationResponse:
        strong = [skill for skill, value in skill_breakdown.items() if value >= 70]
        weak = [skill for skill, value in skill_breakdown.items() if value < 60]
        factors = [
            f"Overall answer accuracy produced a {round(score)}% test score.",
            f"Strong topics: {', '.join(strong) if strong else 'none above threshold yet'}.",
            f"Weak topics: {', '.join(weak) if weak else 'no major weak topic detected'}.",
        ]
        factors.extend(f"{level.title()} accuracy: {round(value)}%." for level, value in difficulty_breakdown.items())
        tips = [f"Practice {skill} with timed mixed questions." for skill in weak[:4]]
        if not tips:
            tips.append("Move to medium and hard scenario questions to validate depth.")
        return ScoreExplanationResponse(
            score=round(score, 2),
            explanation="Your test score is based on answer correctness, difficulty, time, and confidence consistency.",
            factors=factors,
            improvement_tips=tips,
        )

    def trust(
        self,
        *,
        score: float,
        test_score: float,
        risk_score: float,
        event_counts: dict[str, int],
    ) -> ScoreExplanationResponse:
        event_factors = [
            f"{label.replace('_', ' ')}: {count} event(s)."
            for label, count in event_counts.items()
            if count > 0
        ]
        factors = [
            f"Base test score: {round(test_score)}%.",
            f"Proctoring risk penalty: {round(risk_score)}%.",
            *(event_factors or ["No proctoring risk events were reported."]),
        ]
        tips = []
        if event_counts.get("tab_switch", 0):
            tips.append("Avoid switching tabs during verified assessments.")
        if event_counts.get("face_not_detected", 0):
            tips.append("Keep your face visible and centered during the test.")
        if event_counts.get("multiple_faces", 0):
            tips.append("Take the test alone in a quiet environment.")
        if event_counts.get("phone_detected", 0):
            tips.append("Keep phones and secondary devices away from the camera.")
        if not tips:
            tips.append("Maintain the same clean test environment in future attempts.")
        return ScoreExplanationResponse(
            score=round(score, 2),
            explanation="Your trust score merges assessment performance with proctoring risk signals.",
            factors=factors,
            improvement_tips=tips,
        )

    def role_fit(
        self,
        *,
        score: float,
        ats_score: float,
        test_score: float,
        trust_score: float,
        skill_match_percent: float,
        missing_skills: list[str],
        selected_role: str,
    ) -> ScoreExplanationResponse:
        factors = [
            f"Skill match: {round(skill_match_percent)}%.",
            f"ATS score contribution: {round(ats_score)}%.",
            f"Test score contribution: {round(test_score)}%.",
            f"Trust score contribution: {round(trust_score)}%.",
        ]
        if missing_skills:
            factors.append(f"Main gaps for {selected_role}: {', '.join(missing_skills[:5])}.")
        tips = [f"Close the {skill} gap with a project and practice set." for skill in missing_skills[:4]]
        if not tips:
            tips.append("Build a capstone project that proves the full role workflow.")
        return ScoreExplanationResponse(
            score=round(score, 2),
            explanation=f"You are a {self._band(score)} fit for {selected_role} based on resume, test, trust, and skill coverage.",
            factors=factors,
            improvement_tips=tips,
        )

    def _band(self, score: float) -> str:
        if score >= 80:
            return "strong"
        if score >= 60:
            return "moderate"
        return "developing"
