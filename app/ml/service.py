from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from trust_ml.demo_data import make_demo_training_corpus
from trust_ml.model import TrustModel


ARTIFACT_PATH = Path("artifacts/trust_model.joblib")


@lru_cache(maxsize=1)
def load_trust_model() -> TrustModel:
    if ARTIFACT_PATH.exists():
        return TrustModel.load(ARTIFACT_PATH)

    model = TrustModel(random_state=17)
    model.fit(make_demo_training_corpus(), search_best=False)
    return model
