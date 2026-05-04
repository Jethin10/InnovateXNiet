from __future__ import annotations

import re

from app.schemas import AtsGuidanceRequest, AtsGuidanceResponse
from trust_ml.roadmap import RoleProfileStore


def _contains_keyword(text: str, keyword: str) -> bool:
    normalized_text = text.lower()
    normalized_keyword = keyword.lower()
    pattern = r"\b" + re.escape(normalized_keyword).replace(r"\ ", r"\s+") + r"\b"
    return re.search(pattern, normalized_text) is not None


class AtsGuidanceService:
    def __init__(self) -> None:
        self.role_store = RoleProfileStore.default()

    def evaluate(self, request: AtsGuidanceRequest) -> AtsGuidanceResponse:
        profile = self.role_store.get(request.target_role)
        company_keywords = profile.company_keywords.get(request.target_company or "", ())
        keywords = tuple(dict.fromkeys((*profile.ats_keywords, *company_keywords)))

        matched = [keyword for keyword in keywords if _contains_keyword(request.resume_text, keyword)]
        missing = [keyword for keyword in keywords if keyword not in matched]
        score = int(round((len(matched) / len(keywords)) * 100)) if keywords else 0
        recommendations = [
            f"Add evidence for `{keyword}` using a project, metric, or verified platform signal."
            for keyword in missing[:5]
        ]
        if not recommendations:
            recommendations.append("Resume covers the core role keywords; focus on quantified impact.")

        return AtsGuidanceResponse(
            ats_score=score,
            matched_keywords=matched,
            missing_keywords=missing,
            recommendations=recommendations,
        )
