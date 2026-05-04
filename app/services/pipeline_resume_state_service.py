from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.db.models import PipelineResumeState
from app.schemas import AiResumeAnalyzeResponse


class PipelineResumeStateService:
    def __init__(self, session: Session, owner_key: str = "pipeline-demo") -> None:
        self.session = session
        self.owner_key = owner_key

    def save(self, resume_text: str, analysis: AiResumeAnalyzeResponse) -> None:
        self.session.add(
            PipelineResumeState(
                owner_key=self.owner_key,
                target_role=analysis.selected_role,
                raw_text=resume_text,
                analysis_json=analysis.model_dump_json(),
            )
        )
        self.session.commit()

    def latest_analysis(self) -> AiResumeAnalyzeResponse | None:
        record = self.latest_record()
        if record is None:
            return None
        return AiResumeAnalyzeResponse.model_validate_json(record.analysis_json)

    def latest_record(self) -> PipelineResumeState | None:
        return (
            self.session.query(PipelineResumeState)
            .filter_by(owner_key=self.owner_key)
            .order_by(PipelineResumeState.id.desc())
            .first()
        )

    def latest_payload(self) -> dict:
        analysis = self.latest_analysis()
        return json.loads(analysis.model_dump_json()) if analysis else {}
