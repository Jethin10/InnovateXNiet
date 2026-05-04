from __future__ import annotations

import argparse
import json
from pathlib import Path

from .datasets import DatasetRegistry
from .demo_data import (
    make_demo_training_corpus,
    make_session_variant,
    make_synthetic_training_corpus,
)
from .external_data import load_or_download_uci_feature_examples
from .model import TrustModel
from .roadmap import RoleProfileStore, RoadmapGenerator
from .surfaces import (
    build_college_dashboard,
    build_student_result_payload,
    build_trust_stamp_payload,
)
from .training import ModelSearchTrainer


def _aggregate_candidate_metrics(suite_reports: list[dict]) -> dict[str, dict[str, float]]:
    aggregates: dict[str, dict[str, float]] = {}
    for report in suite_reports:
        for ranked in report.get("ranked_results", []):
            bucket = aggregates.setdefault(
                ranked["candidate_name"],
                {
                    "runs": 0,
                    "win_count": 0,
                    "accuracy_sum": 0.0,
                    "roc_auc_sum": 0.0,
                    "brier_score_sum": 0.0,
                    "log_loss_sum": 0.0,
                    "f1_sum": 0.0,
                },
            )
            bucket["runs"] += 1
            bucket["accuracy_sum"] += ranked["accuracy"]
            bucket["roc_auc_sum"] += ranked["roc_auc"]
            bucket["brier_score_sum"] += ranked["brier_score"]
            bucket["log_loss_sum"] += ranked["log_loss"]
            bucket["f1_sum"] += ranked["f1"]

            if ranked["candidate_name"] == report["best_candidate_name"]:
                bucket["win_count"] += 1

    summarized: dict[str, dict[str, float]] = {}
    for candidate_name, bucket in aggregates.items():
        runs = bucket["runs"] or 1
        summarized[candidate_name] = {
            "runs": int(bucket["runs"]),
            "win_count": int(bucket["win_count"]),
            "average_accuracy": round(bucket["accuracy_sum"] / runs, 6),
            "average_roc_auc": round(bucket["roc_auc_sum"] / runs, 6),
            "average_brier_score": round(bucket["brier_score_sum"] / runs, 6),
            "average_log_loss": round(bucket["log_loss_sum"] / runs, 6),
            "average_f1": round(bucket["f1_sum"] / runs, 6),
        }

    return dict(
        sorted(
            summarized.items(),
            key=lambda item: (
                -item[1]["win_count"],
                -item[1]["average_roc_auc"],
                item[1]["average_brier_score"],
                item[1]["average_log_loss"],
            ),
        )
    )


def run_demo() -> dict:
    corpus = make_demo_training_corpus()
    model = TrustModel(random_state=7).fit(corpus, search_best=False)
    evaluation = model.evaluate(corpus)

    student_session = make_session_variant("calibrated_solver")
    scorecard = model.score_session(student_session)
    roadmap = RoadmapGenerator(RoleProfileStore.default()).generate(
        scorecard,
        student_session.target_role,
        student_session.target_company,
    )

    student_payload = build_student_result_payload(student_session, scorecard, roadmap)
    trust_stamp = build_trust_stamp_payload(student_session, scorecard)
    dashboard = build_college_dashboard(
        [
            ("student-a", scorecard),
            ("student-b", model.score_session(make_session_variant("overconfident_guesser"))),
            ("student-c", model.score_session(make_session_variant("balanced_growth"))),
        ]
    )

    return {
        "evaluation": evaluation,
        "student_payload": student_payload,
        "trust_stamp": trust_stamp,
        "college_dashboard": dashboard,
        "dataset_sources": [source.__dict__ for source in DatasetRegistry.default()],
    }


def run_training_suite(
    artifact_dir: str | Path = "artifacts",
    samples_per_variant_values: tuple[int, ...] = (24, 48, 96),
    seeds: tuple[int, ...] = (11, 23, 47),
    include_external_data: bool = True,
    data_dir: str | Path = "data/uci",
    focus_model: str | None = None,
    use_gpu: bool = False,
) -> dict:
    trainer = ModelSearchTrainer(
        random_state=17,
        use_gpu_for_supported_models=use_gpu,
    )
    external_examples = (
        load_or_download_uci_feature_examples(data_dir=data_dir)
        if include_external_data
        else []
    )

    def combined_dataset_factory(samples_per_variant: int, seed: int):
        synthetic_examples = make_synthetic_training_corpus(
            samples_per_variant=samples_per_variant,
            seed=seed,
        )
        return [*synthetic_examples, *external_examples]

    suite_reports = trainer.run_experiment_suite(
        dataset_factory=combined_dataset_factory,
        samples_per_variant_values=samples_per_variant_values,
        seeds=seeds,
        candidate_names=(focus_model,) if focus_model else None,
    )

    champion_corpus = combined_dataset_factory(
        samples_per_variant=max(samples_per_variant_values),
        seed=seeds[-1],
    )
    champion_result = trainer.search(
        champion_corpus,
        candidate_names=(focus_model,) if focus_model else None,
    )
    win_counts: dict[str, int] = {}
    for report in suite_reports:
        model_name = report["best_candidate_name"]
        win_counts[model_name] = win_counts.get(model_name, 0) + 1

    output_dir = Path(artifact_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    model_path = output_dir / "trust_model.joblib"
    report_path = output_dir / "training_report.json"
    model_card_path = output_dir / "MODEL_CARD.md"

    champion_result.model.save(model_path)
    report = {
        "champion_model": champion_result.best_candidate_name,
        "champion_metrics": champion_result.best_metrics,
        "dataset_size": champion_result.dataset_size,
        "feature_names": list(champion_result.feature_names),
        "feature_importances": list(champion_result.feature_importances),
        "external_examples": len(external_examples),
        "suite_summary": {
            "total_runs": len(suite_reports),
            "candidate_win_counts": win_counts,
            "candidate_aggregate": _aggregate_candidate_metrics(suite_reports),
            "focused_model": focus_model,
            "use_gpu": use_gpu,
        },
        "suite_reports": suite_reports,
    }
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    model_card_path.write_text(
        "\n".join(
            [
                "# Trust Model Card",
                "",
                "## Summary",
                f"- Selected model: `{champion_result.best_candidate_name}`",
                f"- Training rows: `{champion_result.dataset_size}`",
                f"- External transfer rows: `{len(external_examples)}`",
                "",
                "## Metrics",
                f"- ROC AUC: `{champion_result.best_metrics['roc_auc']}`",
                f"- Accuracy: `{champion_result.best_metrics['accuracy']}`",
                f"- Brier score: `{champion_result.best_metrics['brier_score']}`",
                f"- Log loss: `{champion_result.best_metrics['log_loss']}`",
                "",
                "## Top Feature Drivers",
                *[
                    f"- `{name}`: `{score}`"
                    for name, score in champion_result.feature_importances[:8]
                ],
                "",
                "## Limits",
                "- This artifact is trained on synthetic cohorts derived from demo archetypes.",
                "- The bluff index is a risk signal and not a fraud label.",
                "- Real-world deployment needs first-party labeled outcomes, fairness checks, and consent controls.",
            ]
        ),
        encoding="utf-8",
    )

    return {
        "champion_model": champion_result.best_candidate_name,
        "champion_metrics": champion_result.best_metrics,
        "dataset_size": champion_result.dataset_size,
        "feature_importances": list(champion_result.feature_importances),
        "external_examples": len(external_examples),
        "suite_summary": {
            "total_runs": len(suite_reports),
            "candidate_win_counts": win_counts,
            "candidate_aggregate": _aggregate_candidate_metrics(suite_reports),
            "focused_model": focus_model,
            "use_gpu": use_gpu,
        },
        "artifacts": {
            "model_path": str(model_path),
            "report_path": str(report_path),
            "model_card_path": str(model_card_path),
        },
        "suite_reports": suite_reports,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Trust model utilities")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("demo", help="Run the demo scoring flow")

    train_parser = subparsers.add_parser("train", help="Run model search and save artifacts")
    train_parser.add_argument("--artifact-dir", default="artifacts")
    train_parser.add_argument("--samples-per-variant", default="24,48,96")
    train_parser.add_argument("--seeds", default="11,23,47")
    train_parser.add_argument("--data-dir", default="data/uci")
    train_parser.add_argument("--no-external-data", action="store_true")
    train_parser.add_argument("--focus-model", default=None)
    train_parser.add_argument("--use-gpu", action="store_true")

    args = parser.parse_args()

    if args.command == "train":
        sample_values = tuple(
            int(value.strip())
            for value in args.samples_per_variant.split(",")
            if value.strip()
        )
        seeds = tuple(
            int(value.strip())
            for value in args.seeds.split(",")
            if value.strip()
        )
        print(
            json.dumps(
                run_training_suite(
                    artifact_dir=args.artifact_dir,
                    samples_per_variant_values=sample_values,
                    seeds=seeds,
                    include_external_data=not args.no_external_data,
                    data_dir=args.data_dir,
                    focus_model=args.focus_model,
                    use_gpu=args.use_gpu,
                ),
                indent=2,
            )
        )
        return

    print(json.dumps(run_demo(), indent=2))
