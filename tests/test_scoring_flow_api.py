from fastapi.testclient import TestClient

from app.main import create_app


def _create_student_with_intake(client: TestClient) -> int:
    student_response = client.post(
        "/api/v1/students",
        json={
            "full_name": "Ishita Rao",
            "email": "ishita@example.com",
            "target_role": "Backend SDE",
            "target_company": "Amazon",
        },
    )
    student_id = student_response.json()["student_id"]
    headers = {
        "X-Actor-Role": "student",
        "X-Actor-Student-Id": str(student_id),
    }
    client.post(
        f"/api/v1/students/{student_id}/intake",
        headers=headers,
        json={
            "resume_text": (
                "Built Python APIs, used SQL, solved algorithms problems, "
                "and want a backend sde role."
            ),
            "consent_public": True,
        },
    )
    return student_id


def test_submit_assessment_score_it_and_fetch_roadmap(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'scoring.db'}"
    app = create_app({"database_url": database_url})
    client = TestClient(app)
    student_id = _create_student_with_intake(client)
    student_headers = {
        "X-Actor-Role": "student",
        "X-Actor-Student-Id": str(student_id),
    }

    assessment_response = client.post(
        f"/api/v1/students/{student_id}/assessments",
        headers=student_headers,
        json={
            "answers": [
                    {
                        "question_id": "be_easy_dsa_array_lookup",
                        "stage_id": 1,
                        "difficulty_band": "easy",
                        "skill_tag": "dsa",
                        "submitted_answer": "O(1)",
                        "elapsed_seconds": 30,
                    "confidence": 0.8,
                    "answer_changes": 0,
                    "max_time_seconds": 60,
                },
                    {
                        "question_id": "be_medium_db_index",
                        "stage_id": 2,
                        "difficulty_band": "medium",
                        "skill_tag": "fundamentals",
                        "submitted_answer": "CREATE INDEX idx_users_email ON users(email)",
                        "elapsed_seconds": 40,
                        "confidence": 0.75,
                        "answer_changes": 0,
                        "max_time_seconds": 90,
                    },
                    {
                        "question_id": "be_hard_fundamentals_transaction",
                        "stage_id": 3,
                        "difficulty_band": "hard",
                        "skill_tag": "fundamentals",
                        "submitted_answer": "eventual consistency",
                        "elapsed_seconds": 80,
                        "confidence": 0.55,
                        "answer_changes": 1,
                        "max_time_seconds": 120,
                    },
            ],
            "evidence": {
                "codeforces_rating": 1450,
                "leetcode_solved": 120,
                "resume_claims": ["python", "sql", "algorithms", "api"],
                "verified_skills": ["dsa", "fundamentals"],
                "project_tags": ["backend", "api"],
                "project_count": 2,
                "github_repo_count": 2,
            },
        },
    )

    assert assessment_response.status_code == 201
    assessment = assessment_response.json()
    assert assessment["status"] == "submitted"

    score_response = client.post(
        f"/api/v1/assessments/{assessment['assessment_id']}/score",
        headers={"X-Actor-Role": "admin"},
    )

    assert score_response.status_code == 200
    score_payload = score_response.json()
    assert 0.0 <= score_payload["trust_score"]["overall_readiness"] <= 1.0
    assert score_payload["trust_score"]["readiness_band"] in {
        "strong",
        "building",
        "emerging",
        "at_risk",
    }
    assert score_payload["roadmap"]["target_role"] == "Backend SDE"

    roadmap_response = client.get(
        f"/api/v1/students/{student_id}/roadmap",
        headers=student_headers,
    )

    assert roadmap_response.status_code == 200
    roadmap_payload = roadmap_response.json()
    assert roadmap_payload["target_role"] == "Backend SDE"
    assert len(roadmap_payload["nodes"]) > 0
