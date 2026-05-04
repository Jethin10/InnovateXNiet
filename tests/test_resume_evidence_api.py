from fastapi.testclient import TestClient

from app.db.models import TrustScoreRecord
from app.main import create_app


def _student_and_headers(client: TestClient) -> tuple[int, dict[str, str]]:
    response = client.post(
        "/api/v1/auth/register-student",
        json={
            "full_name": "Naina Roy",
            "email": "naina@example.com",
            "password": "StrongPass123",
            "target_role": "Backend SDE",
            "target_company": "Amazon",
        },
    )
    student_id = response.json()["student_id"]
    token = client.post(
        "/api/v1/auth/login",
        json={"email": "naina@example.com", "password": "StrongPass123"},
    ).json()["access_token"]
    return student_id, {"Authorization": f"Bearer {token}"}


def test_resume_analysis_returns_claims_projects_and_risk_flags(tmp_path):
    app = create_app(
        {
            "database_url": f"sqlite:///{tmp_path / 'resume-analysis.db'}",
            "auth_secret_key": "test-secret",
        }
    )
    client = TestClient(app)
    student_id, headers = _student_and_headers(client)

    response = client.post(
        f"/api/v1/students/{student_id}/resume/analyze",
        headers=headers,
        json={
            "resume_text": """
            Backend SDE candidate. Skills: Python, SQL, APIs, Kubernetes.
            Projects: Built a FastAPI inventory API with PostgreSQL.
            Projects: Created a URL shortener with Redis caching.
            """,
            "filename": "resume.txt",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["inferred_target_role"] == "Backend SDE"
    assert "python" in payload["claimed_skills"]
    assert payload["project_count"] == 2
    assert "kubernetes" in payload["unsupported_claims"]
    assert payload["risk_flags"]


def test_codeforces_evidence_is_persisted_and_returned_to_assessment(tmp_path):
    app = create_app(
        {
            "database_url": f"sqlite:///{tmp_path / 'codeforces-evidence.db'}",
            "auth_secret_key": "test-secret",
        }
    )
    app.state.codeforces_client = lambda handle: {
        "status": "OK",
        "result": [
            {
                "handle": handle,
                "rating": 1560,
                "maxRating": 1620,
                "rank": "specialist",
            }
        ],
    }
    client = TestClient(app)
    student_id, headers = _student_and_headers(client)

    response = client.post(
        f"/api/v1/students/{student_id}/evidence/codeforces",
        headers=headers,
        json={"handle": "tourist-lite"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["verified"] is True
    assert payload["rating"] == 1560
    assert payload["source"] == "codeforces"

    latest_response = client.get(
        f"/api/v1/students/{student_id}/evidence",
        headers=headers,
    )
    assert latest_response.status_code == 200
    assert latest_response.json()["codeforces"]["handle"] == "tourist-lite"


def test_verified_codeforces_evidence_is_used_during_scoring(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'verified-evidence-scoring.db'}"
    app = create_app(
        {
            "database_url": database_url,
            "auth_secret_key": "test-secret",
        }
    )
    app.state.codeforces_client = lambda handle: {
        "status": "OK",
        "result": [{"handle": handle, "rating": 1700, "maxRating": 1710}],
    }
    client = TestClient(app)
    student_id, headers = _student_and_headers(client)
    client.post(
        f"/api/v1/students/{student_id}/evidence/codeforces",
        headers=headers,
        json={"handle": "verified-handle"},
    )

    assessment = client.post(
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

    session_factory = app.state.session_factory
    with session_factory() as session:
        record = session.query(TrustScoreRecord).order_by(TrustScoreRecord.id.desc()).first()
        assert record is not None
        assert '"codeforces_rating_normalized": 0.5' in record.feature_snapshot_json
