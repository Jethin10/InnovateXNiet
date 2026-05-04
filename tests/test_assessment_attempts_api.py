from fastapi.testclient import TestClient

from app.db.models import AssessmentAuditEventRecord, AssessmentAttemptRecord
from app.main import create_app


def _student(client: TestClient, name: str, email: str) -> tuple[int, dict[str, str]]:
    response = client.post(
        "/api/v1/auth/register-student",
        json={
            "full_name": name,
            "email": email,
            "password": "StrongPass123",
            "target_role": "Backend SDE",
            "target_company": "Amazon",
        },
    )
    student_id = response.json()["student_id"]
    token = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "StrongPass123"},
    ).json()["access_token"]
    return student_id, {"Authorization": f"Bearer {token}"}


def test_student_can_start_assessment_attempt_with_safe_questions(tmp_path):
    app = create_app(
        {
            "database_url": f"sqlite:///{tmp_path / 'attempt-start.db'}",
            "auth_secret_key": "test-secret",
        }
    )
    client = TestClient(app)
    student_id, headers = _student(client, "Asha Iyer", "asha@example.com")

    response = client.post(
        f"/api/v1/students/{student_id}/assessment-attempts",
        headers=headers,
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["attempt_id"] > 0
    assert payload["status"] == "started"
    assert payload["expires_at"]
    assert any(question["question_id"] == "be_easy_dsa_array_lookup" for question in payload["questions"])
    assert all("answer_aliases" not in question for question in payload["questions"])


def test_assessment_submission_must_belong_to_actor_attempt(tmp_path):
    app = create_app(
        {
            "database_url": f"sqlite:///{tmp_path / 'attempt-owner.db'}",
            "auth_secret_key": "test-secret",
        }
    )
    client = TestClient(app)
    first_id, first_headers = _student(client, "First Student", "first@example.com")
    second_id, second_headers = _student(client, "Second Student", "second@example.com")
    attempt_id = client.post(
        f"/api/v1/students/{first_id}/assessment-attempts",
        headers=first_headers,
    ).json()["attempt_id"]

    response = client.post(
        f"/api/v1/students/{second_id}/assessments",
        headers=second_headers,
        json={
            "attempt_id": attempt_id,
            "answers": [
                {
                    "question_id": "be_easy_dsa_array_lookup",
                    "stage_id": 1,
                    "difficulty_band": "easy",
                    "skill_tag": "dsa",
                    "submitted_answer": "O(1)",
                    "elapsed_seconds": 20,
                    "confidence": 0.8,
                }
            ],
            "evidence": {},
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Assessment attempt does not belong to this student"


def test_scored_attempt_records_audit_events(tmp_path):
    app = create_app(
        {
            "database_url": f"sqlite:///{tmp_path / 'attempt-audit.db'}",
            "auth_secret_key": "test-secret",
        }
    )
    client = TestClient(app)
    student_id, headers = _student(client, "Audit Student", "audit@example.com")
    attempt_id = client.post(
        f"/api/v1/students/{student_id}/assessment-attempts",
        headers=headers,
    ).json()["attempt_id"]

    assessment = client.post(
        f"/api/v1/students/{student_id}/assessments",
        headers=headers,
        json={
            "attempt_id": attempt_id,
            "answers": [
                {
                    "question_id": "be_easy_dsa_array_lookup",
                    "stage_id": 1,
                    "difficulty_band": "easy",
                    "skill_tag": "dsa",
                    "submitted_answer": "O(1)",
                    "elapsed_seconds": 20,
                    "confidence": 0.8,
                }
            ],
            "evidence": {},
        },
    )
    score = client.post(
        f"/api/v1/assessments/{assessment.json()['assessment_id']}/score",
        headers={"X-Actor-Role": "admin"},
    )

    assert score.status_code == 200
    with app.state.session_factory() as session:
        attempt = session.get(AssessmentAttemptRecord, attempt_id)
        event_names = [
            event.event_type
            for event in session.query(AssessmentAuditEventRecord)
            .filter_by(attempt_id=attempt_id)
            .order_by(AssessmentAuditEventRecord.id.asc())
            .all()
        ]

    assert attempt is not None
    assert attempt.status == "scored"
    assert event_names == ["attempt_started", "assessment_submitted", "assessment_scored"]
