from __future__ import annotations

import re

from .roles import ROLE_BLUEPRINTS, infer_role_from_text
from .schemas import ResumeProfile


class ResumeIntakeService:
    """Extracts role hints and claimed skills from resume text or manual user input."""

    def from_resume_text(self, text: str) -> ResumeProfile:
        normalized_text = text.lower()
        inferred_role = infer_role_from_text(normalized_text)
        detected_skills: list[str] = []

        keyword_map = {
            "react": ("react", "react.js"),
            "node_js": ("node", "nodejs", "node.js"),
            "express": ("express",),
            "mongodb": ("mongodb",),
            "sql": ("sql", "postgres", "mysql"),
            "javascript": ("javascript", "js"),
            "html": ("html",),
            "css": ("css",),
            "python": ("python",),
            "machine_learning": ("machine learning", "ml"),
            "statistics": ("statistics", "probability"),
            "data_structures": ("data structures", "dsa"),
            "algorithms": ("algorithms",),
            "apis": ("api", "apis", "rest"),
            "numpy": ("numpy",),
            "pandas": ("pandas",),
            "kubernetes": ("kubernetes", "k8s"),
            "redis": ("redis",),
            "fastapi": ("fastapi",),
        }

        for canonical, variants in keyword_map.items():
            if any(re.search(rf"\b{re.escape(variant)}\b", normalized_text) for variant in variants):
                detected_skills.append(canonical)

        return ResumeProfile(
            inferred_target_role=inferred_role,
            claimed_skills=tuple(dict.fromkeys(detected_skills)),
            source="resume",
        )

    def from_manual_skills(self, target_role: str, skills: list[str]) -> ResumeProfile:
        normalized_skills = [
            skill.strip().lower().replace(" ", "_").replace("-", "_")
            for skill in skills
            if skill.strip()
        ]
        return ResumeProfile(
            inferred_target_role=target_role,
            claimed_skills=tuple(dict.fromkeys(normalized_skills)),
            source="manual",
        )
