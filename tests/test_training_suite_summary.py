from trust_ml.cli import run_training_suite


def test_training_suite_reports_candidate_aggregate_stats(tmp_path):
    artifact_dir = tmp_path / "artifacts"

    report = run_training_suite(
        artifact_dir=artifact_dir,
        samples_per_variant_values=(6,),
        seeds=(11, 23),
        include_external_data=False,
    )

    aggregate = report["suite_summary"]["candidate_aggregate"]

    assert report["suite_summary"]["total_runs"] == 2
    assert aggregate
    assert "average_roc_auc" in next(iter(aggregate.values()))
    assert "win_count" in next(iter(aggregate.values()))
