from __future__ import annotations

from math import exp
from pathlib import Path
import pickle
from statistics import mean
from typing import Any

import pandas as pd

from .features import FeatureEngineer, _clamp
from .schemas import AssessmentSession, FeatureVectorExample, TrainingExample, TrustScoreCard

try:
    from xgboost import XGBClassifier
except ImportError:  # pragma: no cover - optional dependency
    XGBClassifier = None

try:  # pragma: no cover - handled at runtime
    from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
    from sklearn.metrics import accuracy_score, roc_auc_score
except ImportError:  # pragma: no cover - handled at runtime
    HistGradientBoostingClassifier = None
    RandomForestClassifier = None
    accuracy_score = None
    roc_auc_score = None

try:  # pragma: no cover - optional dependency
    import joblib
except ImportError:  # pragma: no cover - optional dependency
    joblib = None


class TrustModel:
    """Trainable trust/readiness model with explainable trust metrics."""

    def __init__(self, random_state: int = 42) -> None:
        self.random_state = random_state
        self.feature_engineer = FeatureEngineer()
        self.feature_names: list[str] = []
        self.estimator: Any = None
        self.training_summary: dict[str, Any] = {}

    def _build_estimator(self, sample_count: int):
        if RandomForestClassifier is None or HistGradientBoostingClassifier is None:
            raise RuntimeError(
                "scikit-learn is required to train TrustModel. "
                "Use an environment with the ML stack installed."
            )

        if sample_count < 32:
            return RandomForestClassifier(
                n_estimators=200,
                max_depth=4,
                random_state=self.random_state,
            )

        if XGBClassifier is not None:
            return XGBClassifier(
                n_estimators=64,
                max_depth=3,
                learning_rate=0.1,
                subsample=0.9,
                colsample_bytree=0.9,
                eval_metric="logloss",
                random_state=self.random_state,
            )

        return HistGradientBoostingClassifier(random_state=self.random_state)

    def fit(
        self,
        corpus: list[TrainingExample]
        | list[FeatureVectorExample]
        | list[tuple[AssessmentSession, int]]
        | list[tuple[dict[str, float], int]],
        search_best: bool | None = None,
    ) -> "TrustModel":
        if search_best is None:
            search_best = len(corpus) >= 32

        if search_best:
            from .training import ModelSearchTrainer

            search_result = ModelSearchTrainer(random_state=self.random_state).search(corpus)
            self.estimator = search_result.model.estimator
            self.feature_names = search_result.model.feature_names
            self.training_summary = search_result.model.training_summary
            return self

        rows: list[dict[str, float]] = []
        labels: list[int] = []

        for item in corpus:
            if isinstance(item, TrainingExample):
                features = self.feature_engineer.transform_session(item.session)
                readiness_label = item.readiness_label
            elif isinstance(item, FeatureVectorExample):
                features = item.features
                readiness_label = item.readiness_label
            else:
                value, readiness_label = item
                if isinstance(value, AssessmentSession):
                    features = self.feature_engineer.transform_session(value)
                else:
                    features = value

            rows.append(features)
            labels.append(int(readiness_label))

        if len(set(labels)) < 2:
            raise ValueError("Training corpus must contain both positive and negative labels.")

        frame = pd.DataFrame(rows).fillna(0.0)
        self.feature_names = list(frame.columns)
        self.estimator = self._build_estimator(len(labels))
        self.estimator.fit(frame[self.feature_names], labels)
        self.training_summary = {
            "examples": float(len(labels)),
            "positive_rate": float(sum(labels) / len(labels)),
            "estimator": self.estimator.__class__.__name__,
            "mode": "direct_fit",
        }
        return self

    def _predict_probability(self, features: dict[str, float]) -> float:
        if self.estimator is None or not self.feature_names:
            raise RuntimeError("TrustModel must be fitted before scoring sessions.")

        frame = pd.DataFrame([features]).reindex(columns=self.feature_names, fill_value=0.0)
        if hasattr(self.estimator, "predict_proba"):
            probability = float(self.estimator.predict_proba(frame)[0][1])
        else:  # pragma: no cover - fallback for classifiers without predict_proba
            decision = float(self.estimator.decision_function(frame)[0])
            probability = 1.0 / (1.0 + exp(-decision))
        return _clamp(probability)

    def _derive_skill_scores(self, features: dict[str, float]) -> dict[str, float]:
        return {
            "dsa": round(_clamp(features.get("skill_score_dsa", 0.0)), 3),
            "fundamentals": round(_clamp(features.get("skill_score_fundamentals", 0.0)), 3),
            "projects": round(_clamp(features.get("skill_score_projects", 0.0)), 3),
        }

    def _readiness_band(self, overall_readiness: float) -> str:
        if overall_readiness >= 0.8:
            return "strong"
        if overall_readiness >= 0.6:
            return "building"
        if overall_readiness >= 0.4:
            return "emerging"
        return "at_risk"

    def _risk_band(self, bluff_index: float) -> str:
        if bluff_index >= 0.6:
            return "high"
        if bluff_index >= 0.35:
            return "medium"
        return "low"

    def _top_signal_labels(
        self,
        features: dict[str, float],
        confidence_reliability: float,
        evidence_alignment: float,
    ) -> tuple[tuple[str, ...], tuple[str, ...]]:
        positive_candidates = {
            "strong weighted assessment accuracy": (
                features["weighted_accuracy"]
                if features["weighted_accuracy"] >= 0.6
                else 0.0
            ),
            "good confidence calibration": (
                confidence_reliability
                if confidence_reliability >= 0.6 and features["overconfidence_rate"] <= 0.15
                else 0.0
            ),
            "resume and evidence align well": (
                evidence_alignment
                if evidence_alignment >= 0.6 and features["resume_claim_inflation"] <= 0.2
                else 0.0
            ),
            "good project proof": (
                features["project_evidence_strength"]
                if features["project_evidence_strength"] >= 0.45
                else 0.0
            ),
            "stable performance across stages": (
                1.0 - features["stage_progression_drop"]
                if features["stage_progression_drop"] <= 0.2
                and features["weighted_accuracy"] >= 0.5
                else 0.0
            ),
            "healthy coding profile signal": (
                features["codeforces_rating_normalized"]
                if features["codeforces_rating_normalized"] >= 0.25
                else 0.0
            ),
        }
        risk_candidates = {
            "high overconfidence on incorrect answers": features["overconfidence_rate"],
            "resume claims exceed evidence": features["resume_claim_inflation"],
            "answers changed frequently": features["answer_change_rate"],
            "performance dropped on harder stages": features["stage_progression_drop"],
            "confidence is volatile": features["confidence_volatility"],
            "external evidence is weak": 1.0 - evidence_alignment,
        }

        top_positive = tuple(
            label
            for label, value in sorted(
                positive_candidates.items(),
                key=lambda item: item[1],
                reverse=True,
            )[:3]
            if value > 0.0
        )
        top_risks = tuple(
            label
            for label, value in sorted(
                risk_candidates.items(),
                key=lambda item: item[1],
                reverse=True,
            )[:3]
            if value >= 0.2
        )
        return top_positive, top_risks

    def score_session(self, session: AssessmentSession) -> TrustScoreCard:
        features = self.feature_engineer.transform_session(session)
        model_probability = self._predict_probability(features)

        raw_accuracy = _clamp(features["accuracy_overall"])
        calibration_gap = _clamp(features["confidence_calibration_gap"])
        confidence_reliability = _clamp(
            (1.0 - calibration_gap) * 0.75 + features["confidence_correct_delta"] * 0.25
        )
        evidence_alignment = _clamp(
            features["resume_claim_alignment"] * 0.5
            + features["external_evidence_score"] * 0.25
            + features["project_evidence_strength"] * 0.25
        )
        bluff_index = _clamp(
            features["overconfidence_rate"] * 0.40
            + features["answer_change_rate"] * 0.20
            + (1.0 - evidence_alignment) * 0.25
            + features["resume_claim_inflation"] * 0.10
            + max(0.0, 0.55 - raw_accuracy) * 0.15
        )

        heuristic_readiness = _clamp(
            features["weighted_accuracy"] * 0.40
            + (1.0 - features["avg_time_ratio"]) * 0.15
            + confidence_reliability * 0.20
            + evidence_alignment * 0.20
            + (1.0 - features["stage_progression_drop"]) * 0.05
        )
        overall_readiness = _clamp(model_probability * 0.70 + heuristic_readiness * 0.30)

        explanations: list[str] = []
        if raw_accuracy >= 0.75:
            explanations.append("Strong assessment accuracy across the staged questions.")
        if confidence_reliability < 0.50:
            explanations.append("Confidence behavior is poorly calibrated against correctness.")
        if evidence_alignment < 0.50:
            explanations.append("Resume and external evidence are not well aligned.")
        if bluff_index >= 0.55:
            explanations.append("Trust risk is elevated due to overconfidence or unstable responses.")
        if not explanations:
            explanations.append("Profile looks reasonably consistent across assessment and evidence.")

        readiness_band = self._readiness_band(overall_readiness)
        risk_band = self._risk_band(bluff_index)
        top_positive_signals, top_risk_signals = self._top_signal_labels(
            features,
            confidence_reliability,
            evidence_alignment,
        )

        return TrustScoreCard(
            overall_readiness=round(overall_readiness, 3),
            model_probability=round(model_probability, 3),
            raw_accuracy=round(raw_accuracy, 3),
            skill_scores=self._derive_skill_scores(features),
            confidence_reliability=round(confidence_reliability, 3),
            evidence_alignment=round(evidence_alignment, 3),
            calibration_gap=round(calibration_gap, 3),
            bluff_index=round(bluff_index, 3),
            readiness_band=readiness_band,
            risk_band=risk_band,
            feature_snapshot={key: round(value, 3) for key, value in features.items()},
            explanations=tuple(explanations),
            top_positive_signals=top_positive_signals,
            top_risk_signals=top_risk_signals,
        )

    def evaluate(
        self,
        corpus: list[TrainingExample] | list[tuple[AssessmentSession, int]],
    ) -> dict[str, float]:
        if accuracy_score is None or roc_auc_score is None:
            raise RuntimeError(
                "scikit-learn is required to evaluate TrustModel. "
                "Use an environment with the ML stack installed."
            )

        rows: list[dict[str, float]] = []
        labels: list[int] = []

        for item in corpus:
            if isinstance(item, TrainingExample):
                session = item.session
                readiness_label = item.readiness_label
            else:
                session, readiness_label = item

            rows.append(self.feature_engineer.transform_session(session))
            labels.append(int(readiness_label))

        probabilities = [self._predict_probability(row) for row in rows]
        predictions = [1 if value >= 0.5 else 0 for value in probabilities]

        metrics = {
            "accuracy": float(accuracy_score(labels, predictions)),
            "mean_probability": float(mean(probabilities)),
        }
        if len(set(labels)) > 1:
            metrics["roc_auc"] = float(roc_auc_score(labels, probabilities))
        return metrics

    def save(self, path: str | Path) -> None:
        payload = {
            "random_state": self.random_state,
            "feature_names": self.feature_names,
            "training_summary": self.training_summary,
            "estimator": self.estimator,
        }
        target = Path(path)
        if joblib is not None:
            joblib.dump(payload, target)
            return
        with target.open("wb") as handle:
            pickle.dump(payload, handle)

    @classmethod
    def load(cls, path: str | Path) -> "TrustModel":
        source = Path(path)
        if joblib is not None:
            payload = joblib.load(source)
        else:
            with source.open("rb") as handle:
                payload = pickle.load(handle)

        model = cls(random_state=int(payload["random_state"]))
        model.feature_names = list(payload["feature_names"])
        model.training_summary = dict(payload["training_summary"])
        model.estimator = payload["estimator"]
        return model

    @classmethod
    def from_trained_components(
        cls,
        estimator: Any,
        feature_names: list[str],
        random_state: int,
        training_summary: dict[str, Any],
    ) -> "TrustModel":
        model = cls(random_state=random_state)
        model.estimator = estimator
        model.feature_names = list(feature_names)
        model.training_summary = dict(training_summary)
        return model
