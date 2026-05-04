from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from math import exp
from typing import Any, Callable

import pandas as pd

from .features import FeatureEngineer, _clamp
from .model import TrustModel, XGBClassifier
from .schemas import AssessmentSession, FeatureVectorExample, TrainingExample

try:  # pragma: no cover - handled at runtime
    from sklearn.calibration import CalibratedClassifierCV
    from sklearn.ensemble import (
        ExtraTreesClassifier,
        GradientBoostingClassifier,
        HistGradientBoostingClassifier,
        RandomForestClassifier,
        VotingClassifier,
    )
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import (
        accuracy_score,
        brier_score_loss,
        f1_score,
        log_loss,
        roc_auc_score,
    )
    from sklearn.model_selection import RepeatedStratifiedKFold, StratifiedKFold
except ImportError:  # pragma: no cover - handled at runtime
    CalibratedClassifierCV = None
    ExtraTreesClassifier = None
    GradientBoostingClassifier = None
    HistGradientBoostingClassifier = None
    RandomForestClassifier = None
    VotingClassifier = None
    LogisticRegression = None
    accuracy_score = None
    brier_score_loss = None
    f1_score = None
    log_loss = None
    roc_auc_score = None
    RepeatedStratifiedKFold = None
    StratifiedKFold = None


@dataclass(frozen=True)
class CandidateResult:
    candidate_name: str
    accuracy: float
    roc_auc: float
    brier_score: float
    log_loss: float
    f1: float


@dataclass(frozen=True)
class SearchResult:
    model: TrustModel
    best_candidate_name: str
    best_metrics: dict[str, float]
    ranked_results: tuple[CandidateResult, ...]
    dataset_size: int
    feature_names: tuple[str, ...]
    feature_importances: tuple[tuple[str, float], ...]


class ModelSearchTrainer:
    """Runs candidate-model search with out-of-fold metrics and calibration."""

    def __init__(
        self,
        random_state: int = 42,
        use_calibration: bool = True,
        use_gpu_for_supported_models: bool = False,
    ) -> None:
        self.random_state = random_state
        self.use_calibration = use_calibration
        self.use_gpu_for_supported_models = use_gpu_for_supported_models
        self.feature_engineer = FeatureEngineer()

    def _require_stack(self) -> None:
        if StratifiedKFold is None or accuracy_score is None:
            raise RuntimeError(
                "scikit-learn is required for model search. "
                "Run training in an environment with the ML stack installed."
            )

    def _prepare_frame(
        self,
        corpus: list[TrainingExample]
        | list[FeatureVectorExample]
        | list[tuple[AssessmentSession, int]]
        | list[tuple[dict[str, float], int]],
    ) -> tuple[pd.DataFrame, list[int], list[str]]:
        rows: list[dict[str, float]] = []
        labels: list[int] = []

        for item in corpus:
            if isinstance(item, TrainingExample):
                features = self.feature_engineer.transform_session(item.session)
                label = int(item.readiness_label)
            elif isinstance(item, FeatureVectorExample):
                features = item.features
                label = int(item.readiness_label)
            else:
                value, label = item
                label = int(label)
                if isinstance(value, AssessmentSession):
                    features = self.feature_engineer.transform_session(value)
                else:
                    features = value

            rows.append(features)
            labels.append(label)

        if len(set(labels)) < 2:
            raise ValueError("Training corpus must contain both classes.")

        frame = pd.DataFrame(rows).fillna(0.0)
        return frame, labels, list(frame.columns)

    def _candidate_factories(self, sample_count: int) -> list[tuple[str, Callable[[], Any]]]:
        self._require_stack()

        factories: list[tuple[str, Callable[[], Any]]] = [
            (
                "logistic_regression",
                lambda: LogisticRegression(
                    random_state=self.random_state,
                    max_iter=1000,
                ),
            ),
            (
                "random_forest",
                lambda: RandomForestClassifier(
                    n_estimators=300,
                    max_depth=7,
                    min_samples_leaf=2,
                    random_state=self.random_state,
                ),
            ),
            (
                "extra_trees",
                lambda: ExtraTreesClassifier(
                    n_estimators=300,
                    max_depth=8,
                    min_samples_leaf=2,
                    random_state=self.random_state,
                ),
            ),
            (
                "gradient_boosting",
                lambda: GradientBoostingClassifier(
                    random_state=self.random_state,
                ),
            ),
            (
                "hist_gradient_boosting",
                lambda: HistGradientBoostingClassifier(
                    random_state=self.random_state,
                    max_depth=5,
                    learning_rate=0.06,
                ),
            ),
        ]

        if VotingClassifier is not None:
            factories.append(
                (
                    "soft_voting_ensemble",
                    lambda: VotingClassifier(
                        estimators=[
                            (
                                "rf",
                                RandomForestClassifier(
                                    n_estimators=220,
                                    max_depth=7,
                                    min_samples_leaf=2,
                                    random_state=self.random_state,
                                ),
                            ),
                            (
                                "et",
                                ExtraTreesClassifier(
                                    n_estimators=220,
                                    max_depth=8,
                                    min_samples_leaf=2,
                                    random_state=self.random_state,
                                ),
                            ),
                            (
                                "hgb",
                                HistGradientBoostingClassifier(
                                    random_state=self.random_state,
                                    max_depth=5,
                                    learning_rate=0.06,
                                ),
                            ),
                        ],
                        voting="soft",
                    ),
                )
            )

        if XGBClassifier is not None and sample_count >= 64:
            factories.append(
                (
                    "xgboost",
                    lambda: XGBClassifier(
                        n_estimators=180,
                        max_depth=4,
                        learning_rate=0.05,
                        subsample=0.9,
                        colsample_bytree=0.9,
                        reg_alpha=0.1,
                        reg_lambda=1.0,
                        tree_method="hist",
                        device="cuda" if self.use_gpu_for_supported_models else "cpu",
                        eval_metric="logloss",
                        random_state=self.random_state,
                    ),
                )
            )

        return factories

    def _selected_candidate_factories(
        self,
        sample_count: int,
        candidate_names: tuple[str, ...] | None = None,
    ) -> list[tuple[str, Callable[[], Any]]]:
        factories = self._candidate_factories(sample_count)
        if not candidate_names:
            return factories

        allowed = set(candidate_names)
        return [item for item in factories if item[0] in allowed]

    def _predict_probability(self, estimator: Any, frame: pd.DataFrame) -> list[float]:
        if hasattr(estimator, "predict_proba"):
            return [float(value) for value in estimator.predict_proba(frame)[:, 1]]

        if hasattr(estimator, "decision_function"):
            return [
                1.0 / (1.0 + exp(-float(value)))
                for value in estimator.decision_function(frame)
            ]

        return [float(value) for value in estimator.predict(frame)]

    def _fit_estimator(self, factory: Callable[[], Any], X: pd.DataFrame, y: list[int]) -> Any:
        estimator = factory()
        min_class_count = min(Counter(y).values())

        if self.use_calibration and CalibratedClassifierCV is not None and min_class_count >= 3:
            calibrator = CalibratedClassifierCV(
                estimator=estimator,
                method="sigmoid",
                cv=min(3, min_class_count),
            )
            calibrator.fit(X, y)
            return calibrator

        estimator.fit(X, y)
        return estimator

    def _evaluate_candidate(
        self,
        candidate_name: str,
        factory: Callable[[], Any],
        frame: pd.DataFrame,
        labels: list[int],
    ) -> CandidateResult:
        min_class_count = min(Counter(labels).values())
        n_splits = min(5, min_class_count)
        if n_splits < 2:
            raise ValueError("Need at least two samples in each class for cross-validation.")

        splitter = (
            RepeatedStratifiedKFold(
                n_splits=n_splits,
                n_repeats=2 if len(labels) >= 120 else 1,
                random_state=self.random_state,
            )
            if len(labels) >= 80
            else StratifiedKFold(
                n_splits=n_splits,
                shuffle=True,
                random_state=self.random_state,
            )
        )

        out_of_fold_probabilities = [0.0] * len(labels)
        out_of_fold_predictions = [0] * len(labels)

        for train_indices, test_indices in splitter.split(frame, labels):
            X_train = frame.iloc[train_indices]
            y_train = [labels[index] for index in train_indices]
            X_test = frame.iloc[test_indices]

            estimator = self._fit_estimator(factory, X_train, y_train)
            probabilities = self._predict_probability(estimator, X_test)

            for local_index, probability in zip(test_indices, probabilities, strict=True):
                out_of_fold_probabilities[local_index] = _clamp(float(probability))
                out_of_fold_predictions[local_index] = int(probability >= 0.5)

        return CandidateResult(
            candidate_name=candidate_name,
            accuracy=round(float(accuracy_score(labels, out_of_fold_predictions)), 6),
            roc_auc=round(float(roc_auc_score(labels, out_of_fold_probabilities)), 6),
            brier_score=round(float(brier_score_loss(labels, out_of_fold_probabilities)), 6),
            log_loss=round(float(log_loss(labels, out_of_fold_probabilities)), 6),
            f1=round(float(f1_score(labels, out_of_fold_predictions)), 6),
        )

    def _extract_feature_importances(
        self,
        estimator: Any,
        feature_names: list[str],
    ) -> tuple[tuple[str, float], ...]:
        if hasattr(estimator, "feature_importances_"):
            values = [float(value) for value in estimator.feature_importances_]
        elif hasattr(estimator, "coef_"):
            coefficients = estimator.coef_[0] if getattr(estimator.coef_, "ndim", 1) > 1 else estimator.coef_
            values = [abs(float(value)) for value in coefficients]
        elif hasattr(estimator, "estimators_") and hasattr(estimator, "named_estimators_"):
            aggregate = [0.0] * len(feature_names)
            contributor_count = 0
            for child in estimator.named_estimators_.values():
                child_importances = self._extract_feature_importances(child, feature_names)
                if child_importances:
                    mapping = dict(child_importances)
                    aggregate = [
                        current + mapping.get(feature_name, 0.0)
                        for current, feature_name in zip(aggregate, feature_names, strict=True)
                    ]
                    contributor_count += 1
            if contributor_count == 0:
                return ()
            values = [value / contributor_count for value in aggregate]
        elif hasattr(estimator, "calibrated_classifiers_"):
            aggregate = [0.0] * len(feature_names)
            contributor_count = 0
            for calibrated in estimator.calibrated_classifiers_:
                child = getattr(calibrated, "estimator", None)
                if child is None:
                    continue
                child_importances = self._extract_feature_importances(child, feature_names)
                if child_importances:
                    mapping = dict(child_importances)
                    aggregate = [
                        current + mapping.get(feature_name, 0.0)
                        for current, feature_name in zip(aggregate, feature_names, strict=True)
                    ]
                    contributor_count += 1
            if contributor_count == 0:
                return ()
            values = [value / contributor_count for value in aggregate]
        else:
            return ()

        pairs = list(zip(feature_names, values, strict=True))
        pairs.sort(key=lambda item: item[1], reverse=True)
        return tuple((name, round(score, 6)) for name, score in pairs[:10])

    def search(
        self,
        corpus: list[TrainingExample]
        | list[FeatureVectorExample]
        | list[tuple[AssessmentSession, int]]
        | list[tuple[dict[str, float], int]],
        candidate_names: tuple[str, ...] | None = None,
    ) -> SearchResult:
        frame, labels, feature_names = self._prepare_frame(corpus)
        factories = self._selected_candidate_factories(len(labels), candidate_names)
        candidate_results = [
            self._evaluate_candidate(name, factory, frame, labels)
            for name, factory in factories
        ]
        candidate_results.sort(
            key=lambda result: (
                -result.roc_auc,
                result.brier_score,
                result.log_loss,
                -result.accuracy,
            )
        )

        best_result = candidate_results[0]
        factory_map = dict(factories)
        final_estimator = self._fit_estimator(factory_map[best_result.candidate_name], frame, labels)
        feature_importances = self._extract_feature_importances(final_estimator, feature_names)

        training_summary = {
            "mode": "candidate_search",
            "examples": len(labels),
            "positive_rate": round(sum(labels) / len(labels), 6),
            "selected_model": best_result.candidate_name,
            "feature_count": len(feature_names),
            "best_metrics": asdict(best_result),
            "feature_importances": list(feature_importances),
        }
        model = TrustModel.from_trained_components(
            estimator=final_estimator,
            feature_names=feature_names,
            random_state=self.random_state,
            training_summary=training_summary,
        )
        return SearchResult(
            model=model,
            best_candidate_name=best_result.candidate_name,
            best_metrics=asdict(best_result),
            ranked_results=tuple(candidate_results),
            dataset_size=len(labels),
            feature_names=tuple(feature_names),
            feature_importances=feature_importances,
        )

    def run_experiment_suite(
        self,
        dataset_factory: Callable[
            [int, int],
            list[TrainingExample]
            | list[FeatureVectorExample]
            | list[tuple[AssessmentSession, int]]
            | list[tuple[dict[str, float], int]],
        ],
        samples_per_variant_values: tuple[int, ...],
        seeds: tuple[int, ...],
        candidate_names: tuple[str, ...] | None = None,
    ) -> list[dict[str, Any]]:
        reports: list[dict[str, Any]] = []

        for samples_per_variant in samples_per_variant_values:
            for seed in seeds:
                corpus = dataset_factory(samples_per_variant, seed)
                result = self.search(corpus, candidate_names=candidate_names)
                reports.append(
                    {
                        "samples_per_variant": samples_per_variant,
                        "seed": seed,
                        "dataset_size": result.dataset_size,
                        "best_candidate_name": result.best_candidate_name,
                        "best_metrics": result.best_metrics,
                        "top_feature_importances": list(result.feature_importances[:5]),
                        "candidate_count": len(result.ranked_results),
                        "ranked_results": [
                            asdict(candidate_result) for candidate_result in result.ranked_results
                        ],
                    }
                )
        return reports
