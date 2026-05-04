from trust_ml.intake import ResumeIntakeService
from trust_ml.roadmap import PersonalizedRoadmapBuilder
from trust_ml.schemas import EvidenceProfile
from trust_ml.verification import VerificationPlanner
from trust_ml.model import TrustModel
from trust_ml.demo_data import make_synthetic_training_corpus, make_session_variant


def _train_model() -> TrustModel:
    return TrustModel(random_state=17).fit(
        make_synthetic_training_corpus(samples_per_variant=8, seed=13)
    )


def test_resume_intake_extracts_role_and_claimed_skills():
    text = """
    Built React and Node.js apps, used MongoDB and Express,
    solved DSA problems, and deployed projects with GitHub.
    Looking for a full stack developer role.
    """

    profile = ResumeIntakeService().from_resume_text(text)

    assert profile.inferred_target_role == "Full Stack Developer"
    assert "react" in profile.claimed_skills
    assert "node_js" in profile.claimed_skills
    assert "mongodb" in profile.claimed_skills


def test_verification_planner_builds_three_stages_with_increasing_depth():
    intake = ResumeIntakeService()
    profile = intake.from_manual_skills(
        target_role="AI/ML Engineer",
        skills=["python", "machine learning", "statistics"],
    )

    plan = VerificationPlanner().build(profile)

    assert len(plan.stages) == 3
    assert plan.stages[0].difficulty == "easy"
    assert plan.stages[1].difficulty == "medium"
    assert plan.stages[2].difficulty == "hard"
    assert plan.stages[0].time_limit_minutes < plan.stages[1].time_limit_minutes < plan.stages[2].time_limit_minutes


def test_full_stack_beginner_roadmap_starts_with_foundation_nodes():
    intake = ResumeIntakeService()
    profile = intake.from_manual_skills(
        target_role="Full Stack Developer",
        skills=[],
    )
    model = _train_model()
    scorecard = model.score_session(make_session_variant("low_signal_candidate"))

    graph = PersonalizedRoadmapBuilder().build(profile, scorecard)

    first_node = graph.nodes[0]
    assert first_node.title == "HTML Basics"
    assert first_node.status == "ready"
    assert any(node.title == "JavaScript Foundations" and node.status == "locked" for node in graph.nodes)


def test_stronger_user_gets_advanced_nodes_unlocked():
    intake = ResumeIntakeService()
    profile = intake.from_manual_skills(
        target_role="Backend SDE",
        skills=["python", "sql", "apis", "data structures"],
    )
    model = _train_model()
    scorecard = model.score_session(make_session_variant("calibrated_solver"))

    graph = PersonalizedRoadmapBuilder().build(profile, scorecard)

    assert any(node.title == "REST API Design" and node.status in {"ready", "completed"} for node in graph.nodes)
    assert any(node.status == "completed" for node in graph.nodes)
