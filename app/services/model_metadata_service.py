from __future__ import annotations

from app.ml.service import load_trust_model
from app.schemas import ModelMetadataResponse


class ModelMetadataService:
    def get_metadata(self) -> ModelMetadataResponse:
        model = load_trust_model()
        return ModelMetadataResponse(
            model_loaded=model.estimator is not None,
            training_summary=model.training_summary,
            limitations=[
                "Readiness labels are still mostly synthetic or transfer-derived until first-party outcomes accumulate.",
                "Bluff index is a calibrated risk signal, not a fraud verdict.",
                "Deployment needs ongoing drift, fairness, and outcome validation before high-stakes recruiter use.",
            ],
        )
