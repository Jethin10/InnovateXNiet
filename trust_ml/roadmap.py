from __future__ import annotations

from dataclasses import dataclass

from .roles import ROLE_BLUEPRINTS, get_role_blueprint
from .schemas import ResumeProfile, RoadmapGraph, RoadmapNode, RoadmapPlan, TrustScoreCard


@dataclass(frozen=True)
class RoleProfile:
    name: str
    skill_weights: dict[str, float]
    ats_keywords: tuple[str, ...]
    company_keywords: dict[str, tuple[str, ...]]


class RoleProfileStore:
    def __init__(self, profiles: dict[str, RoleProfile]) -> None:
        self._profiles = profiles

    def get(self, role_name: str) -> RoleProfile:
        try:
            return self._profiles[role_name]
        except KeyError as exc:  # pragma: no cover - defensive
            raise KeyError(f"Unknown role profile: {role_name}") from exc

    @classmethod
    def default(cls) -> "RoleProfileStore":
        return cls(
            {
                "Backend SDE": RoleProfile(
                    name="Backend SDE",
                    skill_weights={"dsa": 0.45, "fundamentals": 0.35, "projects": 0.20},
                    ats_keywords=(
                        "data structures",
                        "algorithms",
                        "backend systems",
                        "APIs",
                        "databases",
                    ),
                    company_keywords={
                        "Amazon": ("leadership principles", "scalability", "ownership"),
                        "Google": ("problem solving", "distributed systems", "quality"),
                    },
                ),
                "ML Engineer": RoleProfile(
                    name="ML Engineer",
                    skill_weights={"projects": 0.55, "dsa": 0.15, "fundamentals": 0.30},
                    ats_keywords=(
                        "machine learning",
                        "model evaluation",
                        "python",
                        "data pipelines",
                        "experimentation",
                    ),
                    company_keywords={
                        "Google": ("ml systems", "experimentation", "applied research"),
                        "Amazon": ("production ml", "metrics", "customer impact"),
                    },
                ),
                "Full Stack Developer": RoleProfile(
                    name="Full Stack Developer",
                    skill_weights={"projects": 0.4, "fundamentals": 0.3, "dsa": 0.3},
                    ats_keywords=(
                        "html",
                        "css",
                        "javascript",
                        "react",
                        "node.js",
                        "api design",
                    ),
                    company_keywords={
                        "Amazon": ("ownership", "full stack delivery", "scalability"),
                        "Google": ("web fundamentals", "product thinking", "quality"),
                    },
                ),
                "AI/ML Engineer": RoleProfile(
                    name="AI/ML Engineer",
                    skill_weights={"projects": 0.45, "fundamentals": 0.35, "dsa": 0.20},
                    ats_keywords=(
                        "python",
                        "machine learning",
                        "statistics",
                        "model evaluation",
                        "experimentation",
                    ),
                    company_keywords={
                        "Google": ("ml systems", "statistics", "applied research"),
                        "Amazon": ("production ml", "metrics", "customer impact"),
                    },
                ),
                "Frontend Developer": RoleProfile(
                    name="Frontend Developer",
                    skill_weights={"projects": 0.45, "fundamentals": 0.25, "dsa": 0.30},
                    ats_keywords=("html", "css", "javascript", "react", "accessibility", "testing", "performance"),
                    company_keywords={
                        "Google": ("web fundamentals", "quality", "product thinking"),
                        "Amazon": ("ownership", "customer experience", "frontend performance"),
                    },
                ),
                "Data Analyst": RoleProfile(
                    name="Data Analyst",
                    skill_weights={"projects": 0.50, "fundamentals": 0.35, "dsa": 0.15},
                    ats_keywords=("sql", "python", "excel", "dashboards", "statistics", "data visualization", "business metrics"),
                    company_keywords={
                        "Google": ("experimentation", "metrics", "insights"),
                        "Amazon": ("customer impact", "operational metrics", "ownership"),
                    },
                ),
                "DevOps Engineer": RoleProfile(
                    name="DevOps Engineer",
                    skill_weights={"projects": 0.55, "fundamentals": 0.30, "dsa": 0.15},
                    ats_keywords=("linux", "docker", "kubernetes", "ci/cd", "cloud", "monitoring", "terraform"),
                    company_keywords={
                        "Google": ("reliability", "automation", "distributed systems"),
                        "Amazon": ("aws", "operational excellence", "scalability"),
                    },
                ),
                "Cloud Engineer": RoleProfile(
                    name="Cloud Engineer",
                    skill_weights={"projects": 0.50, "fundamentals": 0.35, "dsa": 0.15},
                    ats_keywords=("aws", "azure", "gcp", "networking", "security", "infrastructure", "serverless"),
                    company_keywords={
                        "Google": ("gcp", "reliability", "networking"),
                        "Amazon": ("aws", "customer impact", "well architected"),
                    },
                ),
                "Cybersecurity Analyst": RoleProfile(
                    name="Cybersecurity Analyst",
                    skill_weights={"projects": 0.40, "fundamentals": 0.45, "dsa": 0.15},
                    ats_keywords=("network security", "owasp", "threat modeling", "incident response", "linux", "python", "siem"),
                    company_keywords={
                        "Google": ("security engineering", "risk", "privacy"),
                        "Amazon": ("secure systems", "incident response", "ownership"),
                    },
                ),
                "QA Automation Engineer": RoleProfile(
                    name="QA Automation Engineer",
                    skill_weights={"projects": 0.45, "fundamentals": 0.35, "dsa": 0.20},
                    ats_keywords=("testing", "selenium", "playwright", "automation", "api testing", "ci/cd", "quality"),
                    company_keywords={
                        "Google": ("quality", "test automation", "reliability"),
                        "Amazon": ("customer experience", "automation", "ownership"),
                    },
                ),
                "Mobile App Developer": RoleProfile(
                    name="Mobile App Developer",
                    skill_weights={"projects": 0.50, "fundamentals": 0.30, "dsa": 0.20},
                    ats_keywords=("android", "ios", "react native", "flutter", "mobile", "api integration", "app performance"),
                    company_keywords={
                        "Google": ("android", "quality", "product thinking"),
                        "Amazon": ("customer experience", "performance", "ownership"),
                    },
                ),
            }
        )


class RoadmapGenerator:
    def __init__(self, role_store: RoleProfileStore) -> None:
        self.role_store = role_store

    def generate(
        self,
        scorecard: TrustScoreCard,
        target_role: str,
        target_company: str,
    ) -> RoadmapPlan:
        profile = self.role_store.get(target_role)
        deficits = []

        for skill, weight in profile.skill_weights.items():
            current_score = scorecard.skill_scores.get(skill, scorecard.overall_readiness)
            deficits.append((skill, (1.0 - current_score) * weight))

        deficits.sort(key=lambda item: item[1], reverse=True)
        priority_gaps = tuple(skill for skill, _ in deficits[:3])
        company_keywords = profile.company_keywords.get(target_company, ())
        ats_keywords = tuple(dict.fromkeys(profile.ats_keywords + company_keywords))

        action_templates = {
            "dsa": "Practice staged DSA sets with strict timers and post-question confidence tagging.",
            "fundamentals": "Review CS fundamentals with concise notes on OS, DBMS, networking, and trade-offs.",
            "projects": "Ship one stronger proof project with measurable outcomes and architecture explanation.",
        }
        action_items = tuple(action_templates[skill] for skill in priority_gaps)

        summary = (
            f"Focus on {', '.join(priority_gaps[:2])} to improve fit for {target_role} roles "
            f"at {target_company}, while keeping the trust profile evidence-backed."
        )

        return RoadmapPlan(
            title=f"{target_role} roadmap for {target_company}",
            target_role=target_role,
            target_company=target_company,
            summary=summary,
            priority_gaps=priority_gaps,
            action_items=action_items,
            ats_keywords=ats_keywords,
        )


class PersonalizedRoadmapBuilder:
    """Builds a gated roadmap graph for the user's current level and target role."""

    def build(self, profile: ResumeProfile, scorecard: TrustScoreCard) -> RoadmapGraph:
        blueprint = get_role_blueprint(profile.inferred_target_role)
        claimed_skills = set(profile.claimed_skills)
        completed_nodes: set[str] = set()
        nodes: list[RoadmapNode] = []

        for template in blueprint.roadmap_nodes:
            has_claim_signal = any(skill in claimed_skills for skill in template.completion_skills)
            enough_readiness = scorecard.overall_readiness >= template.threshold
            enough_projects = scorecard.skill_scores.get("projects", 0.0) >= max(template.threshold - 0.1, 0.3)
            enough_fundamentals = scorecard.skill_scores.get("fundamentals", 0.0) >= max(template.threshold - 0.1, 0.3)

            completed = False
            if template.skill_track == "frontend":
                completed = has_claim_signal and enough_readiness
            elif template.skill_track in {"backend", "data", "ml"}:
                completed = has_claim_signal and enough_projects and enough_readiness
            elif template.skill_track in {"fundamentals", "math", "dsa"}:
                completed = has_claim_signal and enough_fundamentals

            prerequisites_met = all(prereq in completed_nodes for prereq in template.prerequisites)

            if completed:
                status = "completed"
                completed_nodes.add(template.node_id)
            elif prerequisites_met:
                status = "ready"
            else:
                status = "locked"

            recommended = status == "ready" and (
                not nodes or all(existing.status != "ready" or not existing.recommended for existing in nodes)
            )

            node = RoadmapNode(
                node_id=template.node_id,
                title=template.title,
                skill_track=template.skill_track,
                summary=template.summary,
                prerequisites=template.prerequisites,
                resources=template.resources,
                assignment=template.assignment,
                proof_requirement=template.proof_requirement,
                status=status,
                recommended=recommended,
            )
            nodes.append(node)

        summary = (
            f"Roadmap for {blueprint.name} starting from a {scorecard.readiness_band} readiness profile "
            f"with {scorecard.risk_band} verification risk."
        )
        return RoadmapGraph(
            target_role=blueprint.name,
            current_level=scorecard.readiness_band,
            nodes=tuple(nodes),
            summary=summary,
        )
