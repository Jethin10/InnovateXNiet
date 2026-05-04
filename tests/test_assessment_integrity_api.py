from fastapi.testclient import TestClient

from app.main import create_app


def _create_student(client: TestClient) -> tuple[int, dict[str, str]]:
    response = client.post(
        "/api/v1/students",
        json={
            "full_name": "Aarav Sharma",
            "email": "aarav@example.com",
            "target_role": "Backend SDE",
            "target_company": "Amazon",
        },
    )
    student_id = response.json()["student_id"]
    return student_id, {
        "X-Actor-Role": "student",
        "X-Actor-Student-Id": str(student_id),
    }


def test_assessment_rejects_unknown_question_ids(tmp_path):
    app = create_app({"database_url": f"sqlite:///{tmp_path / 'unknown-question.db'}"})
    client = TestClient(app)
    student_id, headers = _create_student(client)

    response = client.post(
        f"/api/v1/students/{student_id}/assessments",
        headers=headers,
        json={
            "answers": [
                {
                    "question_id": "made-up-question",
                    "stage_id": 1,
                    "difficulty_band": "easy",
                    "skill_tag": "dsa",
                    "submitted_answer": "A",
                    "correct": True,
                    "elapsed_seconds": 20,
                    "confidence": 0.9,
                    "answer_changes": 0,
                    "max_time_seconds": 60,
                }
            ],
            "evidence": {},
        },
    )

    assert response.status_code == 422
    assert "Unknown assessment question" in response.json()["detail"]


def test_assessment_uses_server_answer_key_not_client_correct_flag(tmp_path):
    app = create_app({"database_url": f"sqlite:///{tmp_path / 'server-key.db'}"})
    client = TestClient(app)
    student_id, headers = _create_student(client)

    assessment_response = client.post(
        f"/api/v1/students/{student_id}/assessments",
        headers=headers,
        json={
            "answers": [
                {
                    "question_id": "be_easy_dsa_array_lookup",
                    "stage_id": 1,
                    "difficulty_band": "easy",
                    "skill_tag": "dsa",
                    "submitted_answer": "O(n)",
                    "correct": True,
                    "elapsed_seconds": 25,
                    "confidence": 0.95,
                    "answer_changes": 0,
                    "max_time_seconds": 60,
                },
                {
                    "question_id": "be_medium_db_index",
                    "stage_id": 2,
                    "difficulty_band": "medium",
                    "skill_tag": "fundamentals",
                    "submitted_answer": "CREATE INDEX idx_users_email ON users(email)",
                    "correct": True,
                    "elapsed_seconds": 50,
                    "confidence": 0.75,
                    "answer_changes": 0,
                    "max_time_seconds": 90,
                },
            ],
            "evidence": {
                "resume_claims": ["dsa", "fundamentals"],
                "verified_skills": ["dsa"],
                "project_tags": ["backend"],
                "project_count": 1,
                "github_repo_count": 1,
            },
        },
    )

    assert assessment_response.status_code == 201
    assessment_id = assessment_response.json()["assessment_id"]

    score_response = client.post(
        f"/api/v1/assessments/{assessment_id}/score",
        headers={"X-Actor-Role": "admin"},
    )

    assert score_response.status_code == 200
    payload = score_response.json()
    assert payload["trust_score"]["raw_accuracy"] == 0.5


def test_assessment_rejects_answers_past_server_time_limit(tmp_path):
    app = create_app({"database_url": f"sqlite:///{tmp_path / 'time-limit.db'}"})
    client = TestClient(app)
    student_id, headers = _create_student(client)

    response = client.post(
        f"/api/v1/students/{student_id}/assessments",
        headers=headers,
        json={
            "answers": [
                {
                    "question_id": "be_easy_dsa_array_lookup",
                    "stage_id": 1,
                    "difficulty_band": "easy",
                    "skill_tag": "dsa",
                    "submitted_answer": "O(1)",
                    "correct": True,
                    "elapsed_seconds": 61,
                    "confidence": 0.7,
                }
            ],
            "evidence": {},
        },
    )

    assert response.status_code == 422
    assert "exceeded time limit" in response.json()["detail"]
