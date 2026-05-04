from fastapi.testclient import TestClient

from app.main import create_app


def _seed_scored_student(client: TestClient, name: str) -> int:
    student_response = client.post(
        "/api/v1/students",
        json={
            "full_name": name,
            "email": f"{name.lower().replace(' ', '.')}@example.com",
            "target_role": "Backend SDE",
            "target_company": "Amazon",
        },
    )
    student_id = student_response.json()["student_id"]
    headers = {"X-Actor-Role": "student", "X-Actor-Student-Id": str(student_id)}
    client.post(
        f"/api/v1/students/{student_id}/intake",
        headers=headers,
        json={
            "resume_text": "Built Python APIs, solved algorithms, and want a backend sde role.",
            "consent_public": False,
        },
    )
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
                        "elapsed_seconds": 42,
                        "confidence": 0.74,
                        "answer_changes": 0,
                        "max_time_seconds": 90,
                    },
                    {
                        "question_id": "be_hard_fundamentals_transaction",
                        "stage_id": 3,
                        "difficulty_band": "hard",
                        "skill_tag": "fundamentals",
                        "submitted_answer": "eventual consistency",
                        "elapsed_seconds": 78,
                        "confidence": 0.48,
                        "answer_changes": 1,
                        "max_time_seconds": 120,
                    },
            ],
            "evidence": {
                "resume_claims": ["python", "algorithms", "api"],
                "verified_skills": ["dsa", "fundamentals"],
                "project_tags": ["backend"],
                "project_count": 1,
                "github_repo_count": 1,
            },
        },
    )
    assessment_id = assessment_response.json()["assessment_id"]
    client.post(
        f"/api/v1/assessments/{assessment_id}/score",
        headers={"X-Actor-Role": "admin"},
    )
    return student_id


def test_admin_can_fetch_cohort_analytics(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'analytics.db'}"
    app = create_app({"database_url": database_url})
    client = TestClient(app)

    first_student_id = _seed_scored_student(client, "Arjun Patel")
    second_student_id = _seed_scored_student(client, "Sara Khan")

    institution_response = client.post(
        "/api/v1/institutions",
        headers={"X-Actor-Role": "admin"},
        json={"name": "NIET"},
    )
    institution_id = institution_response.json()["institution_id"]

    cohort_response = client.post(
        "/api/v1/cohorts",
        headers={"X-Actor-Role": "admin"},
        json={"institution_id": institution_id, "name": "2026 Final Year"},
    )
    cohort_id = cohort_response.json()["cohort_id"]

    for student_id in (first_student_id, second_student_id):
        member_response = client.post(
            f"/api/v1/cohorts/{cohort_id}/members",
            headers={"X-Actor-Role": "admin"},
            json={"student_id": student_id},
        )
        assert member_response.status_code == 201

    analytics_response = client.get(
        f"/api/v1/cohorts/{cohort_id}/analytics",
        headers={"X-Actor-Role": "admin"},
    )

    assert analytics_response.status_code == 200
    payload = analytics_response.json()
    assert payload["cohort_name"] == "2026 Final Year"
    assert payload["total_students"] == 2
    assert sum(payload["risk_buckets"].values()) == 2
