from __future__ import annotations

from .roles import get_role_blueprint
from .schemas import ResumeProfile, VerificationPlan, VerificationStagePlan


class VerificationPlanner:
    """Builds the three-stage verification plan used to test claimed skills."""

    def build(self, profile: ResumeProfile) -> VerificationPlan:
        blueprint = get_role_blueprint(profile.inferred_target_role)
        claimed_skills = profile.claimed_skills or blueprint.claim_keywords[:3]
        focus = tuple(dict.fromkeys((*claimed_skills[:4], *blueprint.claim_keywords[:3])))

        stages = (
            VerificationStagePlan(
                stage_id=1,
                difficulty="easy",
                time_limit_minutes=18,
                focus_skills=focus[:3],
                objective="Check whether the user genuinely understands the basics they claim.",
                pass_rule="Clear core fundamentals with steady timing and low inconsistency.",
            ),
            VerificationStagePlan(
                stage_id=2,
                difficulty="medium",
                time_limit_minutes=28,
                focus_skills=focus[:4],
                objective="Verify applied understanding on role-relevant tasks and patterns.",
                pass_rule="Solve intermediate tasks with acceptable confidence calibration.",
            ),
            VerificationStagePlan(
                stage_id=3,
                difficulty="hard",
                time_limit_minutes=40,
                focus_skills=focus[:5],
                objective="Stress test depth using harder role-specific scenarios and proof tasks.",
                pass_rule="Demonstrate depth, reasoning quality, and low claim-evidence mismatch.",
            ),
        )

        return VerificationPlan(
            target_role=blueprint.name,
            claimed_skills=tuple(claimed_skills),
            stages=stages,
        )
