from fastapi.testclient import TestClient

from app.main import create_app


def test_create_student_and_generate_intake_plan(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'student-intake.db'}"
    app = create_app({"database_url": database_url})
    client = TestClient(app)

    create_response = client.post(
        "/api/v1/students",
        json={
            "full_name": "Aarav Sharma",
            "email": "aarav@example.com",
            "target_role": "Full Stack Developer",
            "target_company": "Amazon",
        },
    )

    assert create_response.status_code == 201
    student = create_response.json()
    assert student["full_name"] == "Aarav Sharma"
    assert student["target_role"] == "Full Stack Developer"
    headers = {
        "X-Actor-Role": "student",
        "X-Actor-Student-Id": str(student["student_id"]),
    }

    intake_response = client.post(
        f"/api/v1/students/{student['student_id']}/intake",
        headers=headers,
        json={
            "resume_text": (
                "Built React and Node.js apps with MongoDB, solved DSA questions, "
                "and want a full stack developer role."
            ),
            "preferred_resource_style": "docs-first",
            "consent_public": True,
        },
    )

    assert intake_response.status_code == 200
    payload = intake_response.json()
    assert payload["student_id"] == student["student_id"]
    assert payload["inferred_target_role"] == "Full Stack Developer"
    assert "react" in payload["claimed_skills"]
    assert len(payload["assessment_plan"]["stages"]) == 3
    assert payload["assessment_plan"]["stages"][0]["difficulty"] == "easy"
    assert payload["trust_stamp"]["consent_public"] is True
