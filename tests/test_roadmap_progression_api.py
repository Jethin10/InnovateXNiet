from fastapi.testclient import TestClient

from app.main import create_app


def test_completing_a_roadmap_node_updates_progress_and_trust_stamp(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'roadmap-progress.db'}"
    app = create_app({"database_url": database_url})
    client = TestClient(app)

    student_response = client.post(
        "/api/v1/students",
        json={
            "full_name": "Mira Das",
            "email": "mira@example.com",
            "target_role": "Full Stack Developer",
            "target_company": "Amazon",
        },
    )
    student_id = student_response.json()["student_id"]
    headers = {
        "X-Actor-Role": "student",
        "X-Actor-Student-Id": str(student_id),
    }

    intake_response = client.post(
        f"/api/v1/students/{student_id}/intake",
        headers=headers,
        json={
            "manual_skills": [],
            "consent_public": True,
        },
    )
    slug = intake_response.json()["trust_stamp"]["slug"]

    assessment_response = client.post(
        f"/api/v1/students/{student_id}/assessments",
        headers=headers,
        json={
            "answers": [
                    {
                        "question_id": "fs_easy_html_semantic",
                        "stage_id": 1,
                        "difficulty_band": "easy",
                        "skill_tag": "html",
                        "submitted_answer": "nav",
                        "elapsed_seconds": 28,
                    "confidence": 0.82,
                    "answer_changes": 0,
                    "max_time_seconds": 60,
                },
                    {
                        "question_id": "fs_medium_css_flex",
                        "stage_id": 2,
                        "difficulty_band": "medium",
                        "skill_tag": "css",
                        "submitted_answer": "grid",
                        "elapsed_seconds": 60,
                        "confidence": 0.45,
                        "answer_changes": 1,
                        "max_time_seconds": 90,
                    },
                    {
                        "question_id": "fs_hard_js_closure",
                        "stage_id": 3,
                        "difficulty_band": "hard",
                        "skill_tag": "javascript",
                        "submitted_answer": "prototype",
                        "elapsed_seconds": 82,
                        "confidence": 0.35,
                        "answer_changes": 1,
                        "max_time_seconds": 120,
                    },
            ],
            "evidence": {
                "resume_claims": ["html"],
                "verified_skills": ["html"],
                "project_tags": [],
                "project_count": 0,
                "github_repo_count": 0,
            },
        },
    )
    assessment_id = assessment_response.json()["assessment_id"]
    client.post(
        f"/api/v1/assessments/{assessment_id}/score",
        headers={"X-Actor-Role": "admin"},
    )

    before_response = client.get(
        f"/api/v1/students/{student_id}/roadmap",
        headers=headers,
    )
    before_payload = before_response.json()
    html_node = next(node for node in before_payload["nodes"] if node["node_id"] == "fs_html")
    css_node = next(node for node in before_payload["nodes"] if node["node_id"] == "fs_css")

    assert html_node["status"] in {"ready", "completed"}
    assert css_node["status"] == "locked"

    complete_response = client.post(
        f"/api/v1/students/{student_id}/roadmap/nodes/fs_html/complete",
        headers=headers,
        json={"proof_summary": "Submitted semantic HTML landing page and passed quiz."},
    )

    assert complete_response.status_code == 200

    after_response = client.get(
        f"/api/v1/students/{student_id}/roadmap",
        headers=headers,
    )
    after_payload = after_response.json()
    html_node_after = next(node for node in after_payload["nodes"] if node["node_id"] == "fs_html")
    css_node_after = next(node for node in after_payload["nodes"] if node["node_id"] == "fs_css")

    assert html_node_after["status"] == "completed"
    assert css_node_after["status"] == "ready"

    trust_stamp_response = client.get(f"/api/v1/trust-stamp/{slug}")

    assert trust_stamp_response.status_code == 200
    trust_payload = trust_stamp_response.json()
    assert "HTML Basics" in trust_payload["verified_milestones"]
