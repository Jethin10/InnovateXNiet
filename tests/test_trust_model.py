from pathlib import Path

from trust_ml.demo_data import (
    make_demo_training_corpus,
    make_synthetic_training_corpus,
    make_session_variant,
)
from trust_ml.features import FeatureEngineer
from trust_ml.model import TrustModel
from trust_ml.roadmap import RoleProfileStore, RoadmapGenerator
from trust_ml.schemas import FeatureVectorExample
from trust_ml.surfaces import (
    build_college_dashboard,
    build_student_result_payload,
    build_trust_stamp_payload,
)
from trust_ml.training import ModelSearchTrainer


def train_model():
    corpus = make_demo_training_corpus()
    model = TrustModel(random_state=7)
    model.fit(corpus)
    return model


def test_feature_engineering_emits_core_trust_signals():
    session = make_session_variant("calibrated_solver")
    features = FeatureEngineer().transform_session(session)

    expected_keys = {
        "accuracy_overall",
        "accuracy_easy",
        "accuracy_medium",
        "accuracy_hard",
        "avg_time_ratio",
        "confidence_mean",
        "confidence_calibration_gap",
        "answer_change_rate",
        "codeforces_rating_normalized",
        "resume_claim_alignment",
        "project_evidence_strength",
    }

    assert expected_keys.issubset(features.keys())
    assert 0.0 <= features["accuracy_overall"] <= 1.0
    assert 0.0 <= features["confidence_calibration_gap"] <= 1.0
    assert 0.0 <= features["resume_claim_alignment"] <= 1.0


def test_overconfident_guesser_scores_as_riskier_than_calibrated_solver():
    model = train_model()

    skilled = model.score_session(make_session_variant("calibrated_solver"))
    bluffer = model.score_session(make_session_variant("overconfident_guesser"))

    assert skilled.overall_readiness > bluffer.overall_readiness
    assert skilled.confidence_reliability > bluffer.confidence_reliability
    assert skilled.bluff_index < bluffer.bluff_index


def test_resume_claim_mismatch_reduces_alignment_and_increases_bluff_index():
    model = train_model()

    supported = model.score_session(make_session_variant("supported_resume"))
    mismatched = model.score_session(make_session_variant("mismatched_resume"))

    assert supported.evidence_alignment > mismatched.evidence_alignment
    assert supported.bluff_index < mismatched.bluff_index


def test_same_accuracy_but_different_behavior_creates_different_profiles():
    model = train_model()

    fast_careful = model.score_session(make_session_variant("fast_careful_same_accuracy"))
    slow_overconfident = model.score_session(make_session_variant("slow_overconfident_same_accuracy"))

    assert fast_careful.raw_accuracy == slow_overconfident.raw_accuracy
    assert fast_careful.confidence_reliability != slow_overconfident.confidence_reliability
    assert fast_careful.overall_readiness != slow_overconfident.overall_readiness
    assert fast_careful.bluff_index != slow_overconfident.bluff_index


def test_role_specific_roadmap_and_surface_payloads_are_generated():
    model = train_model()
    session = make_session_variant("calibrated_solver")
    scorecard = model.score_session(session)

    role_store = RoleProfileStore.default()
    roadmap_generator = RoadmapGenerator(role_store)

    backend_plan = roadmap_generator.generate(scorecard, "Backend SDE", "Amazon")
    ml_plan = roadmap_generator.generate(scorecard, "ML Engineer", "Google")

    assert backend_plan.title != ml_plan.title
    assert backend_plan.priority_gaps != ml_plan.priority_gaps

    student_payload = build_student_result_payload(session, scorecard, backend_plan)
    trust_stamp_payload = build_trust_stamp_payload(session, scorecard)
    dashboard_payload = build_college_dashboard(
        [
            ("student-1", scorecard),
            ("student-2", model.score_session(make_session_variant("overconfident_guesser"))),
        ]
    )

    assert student_payload["trust_score"] == scorecard.overall_readiness
    assert student_payload["readiness_band"] == scorecard.readiness_band
    assert "bluff_index" in trust_stamp_payload
    assert "top_positive_signals" in trust_stamp_payload
    assert dashboard_payload["total_students"] == 2
    assert sum(dashboard_payload["risk_buckets"].values()) == 2


def test_synthetic_corpus_generation_supports_larger_training_runs():
    corpus = make_synthetic_training_corpus(samples_per_variant=10, seed=19)

    assert len(corpus) == 120
    labels = [label for _, label in corpus]
    assert 0 in labels
    assert 1 in labels


def test_model_search_returns_ranked_results_and_best_model():
    corpus = make_synthetic_training_corpus(samples_per_variant=8, seed=31)
    trainer = ModelSearchTrainer(random_state=11)
    result = trainer.search(corpus)

    assert result.best_candidate_name
    assert len(result.ranked_results) >= 3
    assert result.best_metrics["roc_auc"] >= 0.7
    assert 0.0 <= result.best_metrics["brier_score"] <= 1.0
    assert len(result.feature_importances) > 0

    session = make_session_variant("calibrated_solver")
    scorecard = result.model.score_session(session)
    assert 0.0 <= scorecard.model_probability <= 1.0
    assert scorecard.readiness_band in {"strong", "building", "emerging", "at_risk"}
    assert scorecard.risk_band in {"low", "medium", "high"}


def test_model_search_can_focus_on_single_candidate_family():
    corpus = make_synthetic_training_corpus(samples_per_variant=6, seed=29)
    trainer = ModelSearchTrainer(random_state=9)
    result = trainer.search(corpus, candidate_names=("gradient_boosting",))

    assert result.best_candidate_name == "gradient_boosting"
    assert len(result.ranked_results) == 1


def test_model_artifact_round_trip_preserves_scores(tmp_path: Path):
    corpus = make_synthetic_training_corpus(samples_per_variant=6, seed=23)
    trainer = ModelSearchTrainer(random_state=5)
    result = trainer.search(corpus)

    artifact_path = tmp_path / "trust-model.joblib"
    result.model.save(artifact_path)
    loaded_model = TrustModel.load(artifact_path)

    session = make_session_variant("supported_resume")
    original = result.model.score_session(session)
    restored = loaded_model.score_session(session)

    assert original.overall_readiness == restored.overall_readiness
    assert original.bluff_index == restored.bluff_index


def test_model_search_accepts_mixed_session_and_feature_examples():
    session = make_session_variant("calibrated_solver")
    feature_map = FeatureEngineer().transform_session(make_session_variant("overconfident_guesser"))
    corpus = [
        (session, 1),
        FeatureVectorExample(features=feature_map, readiness_label=0),
        (make_session_variant("balanced_growth"), 1),
        FeatureVectorExample(
            features=FeatureEngineer().transform_session(make_session_variant("low_signal_candidate")),
            readiness_label=0,
        ),
    ]

    result = ModelSearchTrainer(random_state=13).search(corpus)

    assert result.dataset_size == 4
    assert result.best_candidate_name
