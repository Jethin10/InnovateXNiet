from fastapi.testclient import TestClient

from app.main import create_app


def _build_scored_student(client: TestClient, *, consent_public: bool) -> str:
    student_response = client.post(
        "/api/v1/students",
        json={
            "full_name": "Kabir Mehta",
            "email": "kabir@example.com",
            "target_role": "Backend SDE",
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
            "resume_text": "Built Python APIs, solved algorithms, and want a backend sde role.",
            "consent_public": consent_public,
        },
    )
    slug = intake_response.json()["trust_stamp"]["slug"]

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
                        "elapsed_seconds": 38,
                        "confidence": 0.78,
                        "answer_changes": 0,
                        "max_time_seconds": 90,
                    },
                    {
                        "question_id": "be_hard_fundamentals_transaction",
                        "stage_id": 3,
                        "difficulty_band": "hard",
                        "skill_tag": "fundamentals",
                        "submitted_answer": "atomicity",
                        "elapsed_seconds": 62,
                        "confidence": 0.7,
                        "answer_changes": 0,
                        "max_time_seconds": 120,
                    },
            ],
            "evidence": {
                "codeforces_rating": 1520,
                "resume_claims": ["python", "algorithms", "api"],
                "verified_skills": ["dsa", "fundamentals"],
                "project_tags": ["backend", "api"],
                "project_count": 2,
                "github_repo_count": 2,
            },
        },
    )
    assessment_id = assessment_response.json()["assessment_id"]
    client.post(
        f"/api/v1/assessments/{assessment_id}/score",
        headers={"X-Actor-Role": "admin"},
    )
    return slug


def test_trust_stamp_endpoint_respects_consent(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'trust-stamp.db'}"
    app = create_app({"database_url": database_url})
    client = TestClient(app)

    public_slug = _build_scored_student(client, consent_public=True)
    private_slug = _build_scored_student(client, consent_public=False)

    public_response = client.get(f"/api/v1/trust-stamp/{public_slug}")
    private_response = client.get(f"/api/v1/trust-stamp/{private_slug}")

    assert public_response.status_code == 200
    public_payload = public_response.json()
    assert public_payload["public_profile_url"].endswith(public_slug)
    assert public_payload["target_role"] == "Backend SDE"
    assert 0.0 <= public_payload["overall_readiness"] <= 1.0

    assert private_response.status_code == 404
