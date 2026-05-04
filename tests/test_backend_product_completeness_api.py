from fastapi.testclient import TestClient

from app.main import create_app


def _student(client: TestClient) -> tuple[int, dict[str, str]]:
    response = client.post(
        "/api/v1/auth/register-student",
        json={
            "full_name": "Backend Complete",
            "email": "complete@example.com",
            "password": "StrongPass123",
            "target_role": "Backend SDE",
            "target_company": "Amazon",
        },
    )
    student_id = response.json()["student_id"]
    token = client.post(
        "/api/v1/auth/login",
        json={"email": "complete@example.com", "password": "StrongPass123"},
    ).json()["access_token"]
    return student_id, {"Authorization": f"Bearer {token}"}


def _score_student(client: TestClient, student_id: int, headers: dict[str, str]) -> str:
    intake = client.post(
        f"/api/v1/students/{student_id}/intake",
        headers=headers,
        json={
            "resume_text": "Backend SDE with Python, SQL, APIs and algorithms projects.",
            "consent_public": True,
        },
    )
    slug = intake.json()["trust_stamp"]["slug"]
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
    client.post(
        f"/api/v1/assessments/{assessment.json()['assessment_id']}/score",
        headers={"X-Actor-Role": "admin"},
    )
    return slug


def test_ats_guidance_scores_resume_against_role_keywords(tmp_path):
    app = create_app(
        {
            "database_url": f"sqlite:///{tmp_path / 'ats.db'}",
            "auth_secret_key": "test-secret",
        }
    )
    client = TestClient(app)
    student_id, headers = _student(client)

    response = client.post(
        f"/api/v1/students/{student_id}/resume/ats",
        headers=headers,
        json={
            "resume_text": "Built Python APIs with SQL and backend services.",
            "target_role": "Backend SDE",
            "target_company": "Amazon",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert 0 <= payload["ats_score"] <= 100
    assert "algorithms" in payload["missing_keywords"]
    assert payload["recommendations"]


def test_github_evidence_is_verified_and_returned(tmp_path):
    app = create_app(
        {
            "database_url": f"sqlite:///{tmp_path / 'github.db'}",
            "auth_secret_key": "test-secret",
        }
    )
    app.state.github_client = lambda username: {
        "login": username,
        "public_repos": 7,
        "followers": 3,
    }
    client = TestClient(app)
    student_id, headers = _student(client)

    response = client.post(
        f"/api/v1/students/{student_id}/evidence/github",
        headers=headers,
        json={"username": "builder-dev"},
    )

    assert response.status_code == 200
    assert response.json()["repo_count"] == 7
    summary = client.get(f"/api/v1/students/{student_id}/evidence", headers=headers)
    assert summary.json()["github"]["username"] == "builder-dev"


def test_public_trust_stamp_includes_verifiable_signature(tmp_path):
    app = create_app(
        {
            "database_url": f"sqlite:///{tmp_path / 'signed-stamp.db'}",
            "auth_secret_key": "test-secret",
        }
    )
    client = TestClient(app)
    student_id, headers = _student(client)
    slug = _score_student(client, student_id, headers)

    stamp = client.get(f"/api/v1/trust-stamp/{slug}")
    assert stamp.status_code == 200
    payload = stamp.json()
    assert payload["signature"]

    verify = client.post("/api/v1/trust-stamp/verify", json=payload)
    assert verify.status_code == 200
    assert verify.json()["valid"] is True

    payload["overall_readiness"] = 0.0
    tampered = client.post("/api/v1/trust-stamp/verify", json=payload)
    assert tampered.status_code == 200
    assert tampered.json()["valid"] is False


def test_model_metadata_endpoint_exposes_governance_summary(tmp_path):
    app = create_app({"database_url": f"sqlite:///{tmp_path / 'model-meta.db'}"})
    client = TestClient(app)

    response = client.get("/api/v1/model/metadata")

    assert response.status_code == 200
    payload = response.json()
    assert payload["model_loaded"] is True
    assert payload["limitations"]
    assert "selected_model" in payload["training_summary"]


def test_frontend_demo_flow_replaces_cohort_analytics_with_job_matching():
    demo_flow = (
        __import__("pathlib").Path("frontend_original/app/lib/demoFlow.ts").read_text(encoding="utf-8")
    )
    projects = (
        __import__("pathlib").Path("frontend_original/app/constants/projects.ts").read_text(encoding="utf-8")
    )

    assert "Jobs That Suit You" in projects
    assert "featureKey: 'jobs'" in projects
    assert "AI Mentor Pipeline" in projects
    assert "featureKey: 'ai_pipeline'" in projects
    assert "JobMatchResponse" in demo_flow
    assert "/match-jobs" in demo_flow
    assert "CohortAnalyticsResponse" not in demo_flow
    assert "/api/v1/cohorts" not in demo_flow
