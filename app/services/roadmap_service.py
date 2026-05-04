from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.db.models import RoadmapNodeProgressRecord, RoadmapSnapshot, StudentProfile
from app.schemas import NodeCompletionRequest, RoadmapResponse


class RoadmapService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def complete_node(
        self,
        student_id: int,
        node_id: str,
        request: NodeCompletionRequest,
    ) -> RoadmapResponse:
        roadmap = self.get_current_roadmap(student_id)
        node = next((item for item in roadmap.nodes if item.node_id == node_id), None)
        if node is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Roadmap node not found")
        if node.status not in {"ready", "completed"}:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Roadmap node is locked")

        student = self.session.get(StudentProfile, student_id)
        if student is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")

        progress = (
            self.session.query(RoadmapNodeProgressRecord)
            .filter_by(student_profile_id=student_id, node_id=node_id)
            .one_or_none()
        )
        if progress is None:
            progress = RoadmapNodeProgressRecord(
                student_profile=student,
                node_id=node_id,
                node_title=node.title,
                status="completed",
                proof_summary=request.proof_summary,
            )
            self.session.add(progress)
        else:
            progress.status = "completed"
            progress.proof_summary = request.proof_summary

        self.session.commit()
        return self.get_current_roadmap(student_id)

    def get_current_roadmap(self, student_id: int) -> RoadmapResponse:
        snapshot = (
            self.session.query(RoadmapSnapshot)
            .filter_by(student_profile_id=student_id)
            .order_by(RoadmapSnapshot.id.desc())
            .first()
        )
        if snapshot is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Roadmap not found")

        roadmap = RoadmapResponse.model_validate_json(snapshot.graph_json)
        completed = {
            record.node_id
            for record in self.session.query(RoadmapNodeProgressRecord)
            .filter_by(student_profile_id=student_id, status="completed")
            .all()
        }

        updated_nodes = []
        for node in roadmap.nodes:
            data = node.model_dump()
            if node.node_id in completed:
                data["status"] = "completed"
                data["recommended"] = False
            elif all(prereq in completed for prereq in node.prerequisites):
                data["status"] = "ready"
                data["recommended"] = False
            else:
                data["status"] = "locked"
                data["recommended"] = False
            updated_nodes.append(data)

        for node in updated_nodes:
            if node["status"] == "ready":
                node["recommended"] = True
                break

        return RoadmapResponse(
            target_role=roadmap.target_role,
            current_level=roadmap.current_level,
            summary=roadmap.summary,
            nodes=updated_nodes,
        )

    def get_verified_milestones(self, student_id: int) -> list[str]:
        entries = (
            self.session.query(RoadmapNodeProgressRecord)
            .filter_by(student_profile_id=student_id, status="completed")
            .order_by(RoadmapNodeProgressRecord.id.asc())
            .all()
        )
        return [entry.node_title for entry in entries]
