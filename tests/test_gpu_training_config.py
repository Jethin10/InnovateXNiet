from trust_ml.training import ModelSearchTrainer


def test_xgboost_candidate_uses_cuda_when_gpu_enabled():
    trainer = ModelSearchTrainer(random_state=7, use_gpu_for_supported_models=True)

    factories = dict(trainer._candidate_factories(sample_count=128))

    if "xgboost" not in factories:
        return

    estimator = factories["xgboost"]()
    params = estimator.get_params()

    assert params["device"] == "cuda"
