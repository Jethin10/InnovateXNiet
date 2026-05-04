from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request

from app.core.config import Settings
from app.schemas import ProctoringFrameAnalysisResponse


class ProctoringVisionService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def analyze_frame(self, image_data_url: str) -> ProctoringFrameAnalysisResponse:
        model = self.settings.huggingface_proctoring_model
        if self.settings.huggingface_proctoring_disabled:
            return self._not_analyzed(model, "Hugging Face proctoring is disabled.")
        if not self.settings.huggingface_api_token:
            return self._not_analyzed(model, "Hugging Face token is not configured; local browser proctoring remains active.")

        try:
            image_bytes = self._decode_data_url(image_data_url)
        except ValueError as exc:
            return ProctoringFrameAnalysisResponse(
                analyzed=False,
                model=model,
                risk_score=0.4,
                flags=["invalid_camera_frame"],
                reason=str(exc),
            )

        request = urllib.request.Request(
            f"https://api-inference.huggingface.co/models/{model}",
            data=image_bytes,
            headers={
                "Authorization": f"Bearer {self.settings.huggingface_api_token}",
                "Content-Type": "application/octet-stream",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=8) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            return self._not_analyzed(model, f"Hugging Face analysis unavailable: {exc}")

        return self._score_objects(model, payload)

    def _decode_data_url(self, image_data_url: str) -> bytes:
        if "," not in image_data_url:
            raise ValueError("Camera frame must be a data URL.")
        header, encoded = image_data_url.split(",", 1)
        if "base64" not in header:
            raise ValueError("Camera frame must be base64 encoded.")
        return base64.b64decode(encoded, validate=True)

    def _score_objects(self, model: str, payload: object) -> ProctoringFrameAnalysisResponse:
        if isinstance(payload, dict) and payload.get("error"):
            return self._not_analyzed(model, str(payload["error"]))
        detections = payload if isinstance(payload, list) else []
        labels = [
            str(item.get("label", "")).lower()
            for item in detections
            if isinstance(item, dict) and float(item.get("score", 0) or 0) >= 0.45
        ]
        person_count = sum(1 for label in labels if "person" in label)
        flags: list[str] = []
        if person_count == 0:
            flags.append("no_person_visible")
        if person_count > 1:
            flags.append("multiple_people_visible")
        if any("phone" in label or "cell" in label for label in labels):
            flags.append("phone_visible")
        if any("book" in label for label in labels):
            flags.append("reference_material_visible")

        risk_score = min(1.0, 0.25 * len(flags))
        if "phone_visible" in flags or "multiple_people_visible" in flags:
            risk_score = max(risk_score, 0.75)
        reason = "No AI proctoring risk detected." if not flags else "AI proctoring flagged camera-frame risk."
        return ProctoringFrameAnalysisResponse(
            analyzed=True,
            model=model,
            risk_score=round(risk_score, 2),
            flags=flags,
            reason=reason,
        )

    def _not_analyzed(self, model: str, reason: str) -> ProctoringFrameAnalysisResponse:
        return ProctoringFrameAnalysisResponse(
            analyzed=False,
            model=model,
            risk_score=0.0,
            flags=[],
            reason=reason,
        )
