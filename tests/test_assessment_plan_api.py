from fastapi.testclient import TestClient

from app.main import create_app


def test_intake_persists_assessment_plan_and_can_fetch_it(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'assessment-plan.db'}"
    app = create_app({"database_url": database_url})
    client = TestClient(app)

    create_response = client.post(
        "/api/v1/students",
        json={
            "full_name": "Riya Kapoor",
            "email": "riya@example.com",
            "target_role": "AI/ML Engineer",
            "target_company": "Google",
        },
    )
    student_id = create_response.json()["student_id"]
    headers = {
        "X-Actor-Role": "student",
        "X-Actor-Student-Id": str(student_id),
    }

    intake_response = client.post(
        f"/api/v1/students/{student_id}/intake",
        headers=headers,
        json={
            "manual_skills": ["python", "machine learning", "statistics"],
            "consent_public": False,
        },
    )

    assert intake_response.status_code == 200

    plan_response = client.get(
        f"/api/v1/students/{student_id}/assessment-plan",
        headers=headers,
    )

    assert plan_response.status_code == 200
    payload = plan_response.json()
    assert payload["student_id"] == student_id
    assert payload["target_role"] == "AI/ML Engineer"
    assert len(payload["stages"]) == 3
    assert [stage["difficulty"] for stage in payload["stages"]] == ["easy", "medium", "hard"]
