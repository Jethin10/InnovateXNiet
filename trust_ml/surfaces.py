from __future__ import annotations

from collections import Counter

from .schemas import AssessmentSession, RoadmapPlan, TrustScoreCard


def build_student_result_payload(
    session: AssessmentSession,
    scorecard: TrustScoreCard,
    roadmap: RoadmapPlan,
) -> dict:
    return {
        "user_id": session.user_id,
        "target_role": session.target_role,
        "target_company": session.target_company,
        "trust_score": scorecard.overall_readiness,
        "readiness_band": scorecard.readiness_band,
        "risk_band": scorecard.risk_band,
        "raw_accuracy": scorecard.raw_accuracy,
        "confidence_reliability": scorecard.confidence_reliability,
        "evidence_alignment": scorecard.evidence_alignment,
        "priority_gaps": roadmap.priority_gaps,
        "next_actions": roadmap.action_items,
        "ats_keywords": roadmap.ats_keywords,
        "explanations": scorecard.explanations,
        "top_positive_signals": scorecard.top_positive_signals,
        "top_risk_signals": scorecard.top_risk_signals,
    }


def build_trust_stamp_payload(
    session: AssessmentSession,
    scorecard: TrustScoreCard,
) -> dict:
    return {
        "public_profile_url": f"https://truststamp.local/profile/{session.user_id}",
        "session_id": session.session_id,
        "target_role": session.target_role,
        "target_company": session.target_company,
        "overall_readiness": scorecard.overall_readiness,
        "readiness_band": scorecard.readiness_band,
        "risk_band": scorecard.risk_band,
        "bluff_index": scorecard.bluff_index,
        "confidence_reliability": scorecard.confidence_reliability,
        "skill_scores": scorecard.skill_scores,
        "top_positive_signals": scorecard.top_positive_signals,
        "top_risk_signals": scorecard.top_risk_signals,
        "verified_evidence": {
            "codeforces_rating": session.evidence.codeforces_rating,
            "project_count": session.evidence.project_count,
            "verified_skills": session.evidence.verified_skills,
        },
        "resume_alignment": scorecard.evidence_alignment,
    }


def build_college_dashboard(
    entries: list[tuple[str, TrustScoreCard]],
) -> dict:
    total_students = len(entries)
    average_trust_score = 0.0
    average_bluff_index = 0.0
    risk_buckets = Counter({"low_risk": 0, "medium_risk": 0, "high_risk": 0})
    skill_gap_heatmap = Counter({"dsa": 0.0, "fundamentals": 0.0, "projects": 0.0})
    flagged_students: list[str] = []

    for student_id, scorecard in entries:
        average_trust_score += scorecard.overall_readiness
        average_bluff_index += scorecard.bluff_index

        if scorecard.bluff_index >= 0.55 or scorecard.overall_readiness < 0.40:
            risk_buckets["high_risk"] += 1
            flagged_students.append(student_id)
        elif scorecard.bluff_index >= 0.35 or scorecard.overall_readiness < 0.65:
            risk_buckets["medium_risk"] += 1
        else:
            risk_buckets["low_risk"] += 1

        for skill, value in scorecard.skill_scores.items():
            skill_gap_heatmap[skill] += round(1.0 - value, 3)

    if total_students:
        average_trust_score = round(average_trust_score / total_students, 3)
        average_bluff_index = round(average_bluff_index / total_students, 3)
        for skill in list(skill_gap_heatmap.keys()):
            skill_gap_heatmap[skill] = round(skill_gap_heatmap[skill] / total_students, 3)

    return {
        "total_students": total_students,
        "average_trust_score": average_trust_score,
        "average_bluff_index": average_bluff_index,
        "risk_buckets": dict(risk_buckets),
        "skill_gap_heatmap": dict(skill_gap_heatmap),
        "flagged_students": flagged_students,
    }
