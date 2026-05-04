from fastapi.testclient import TestClient

from app.main import create_app


class _FakeHttpResponse:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self) -> bytes:
        return self.payload


def test_match_jobs_scores_and_explains_saved_resume_profile(tmp_path):
    app = create_app(
        {
            "database_url": f"sqlite:///{tmp_path / 'job-match.db'}",
            "auth_secret_key": "test-secret",
        }
    )
    client = TestClient(app)

    client.post(
        "/api/v1/pipeline/analyze-resume",
        json={
            "resume_text": "Skills: Python, React, SQL, APIs. Projects: Built dashboards and REST APIs.",
            "target_role": "Full Stack Developer",
        },
    )
    response = client.post(
        "/match-jobs",
        json={
            "ats_score": 70,
            "test_score": 60,
            "trust_score": 80,
            "location": "Remote",
            "remote": True,
            "jobs": [
                {
                    "job_id": "frontend-1",
                    "title": "Frontend Developer",
                    "company": "PixelGrid",
                    "location": "Remote",
                    "description": "React JavaScript CSS accessibility testing role",
                    "remote": True,
                    "source": "test",
                    "required_skills": ["react", "javascript", "css", "testing"],
                },
                {
                    "job_id": "devops-1",
                    "title": "DevOps Engineer",
                    "company": "InfraCo",
                    "location": "Remote",
                    "description": "Kubernetes Terraform Linux CI/CD",
                    "remote": True,
                    "source": "test",
                    "required_skills": ["kubernetes", "linux", "ci/cd"],
                },
            ],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["jobs"][0]["job_id"] == "frontend-1"
    assert payload["jobs"][0]["match_score"] > payload["jobs"][1]["match_score"]
    assert "react" in payload["jobs"][0]["matched_skills"]
    assert payload["jobs"][0]["missing_skills"]
    assert "Missing skills include" in payload["jobs"][0]["explanation"]


def test_jobs_endpoint_returns_fast_fallback_without_api_key(tmp_path):
    app = create_app(
        {
            "database_url": f"sqlite:///{tmp_path / 'jobs-fallback.db'}",
            "auth_secret_key": "test-secret",
            "rapidapi_key": None,
        }
    )
    client = TestClient(app)

    response = client.get("/jobs?query=Backend%20SDE&location=India&limit=4")

    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == "fallback"
    assert len(payload["jobs"]) <= 4
    assert payload["jobs"][0]["required_skills"]


def test_jobs_endpoint_uses_free_jobs_api_with_apply_links(tmp_path, monkeypatch):
    app = create_app(
        {
            "database_url": f"sqlite:///{tmp_path / 'jobs-open-api.db'}",
            "auth_secret_key": "test-secret",
            "rapidapi_key": None,
        }
    )
    client = TestClient(app)

    def fake_urlopen(request, timeout):
        assert "arbeitnow.com/api/job-board-api" in request.full_url
        return _FakeHttpResponse(
            b"""
            {
              "data": [
                {
                  "slug": "python-developer-remote",
                  "title": "Python Developer",
                  "company_name": "Open Jobs Co",
                  "location": "Remote",
                  "remote": true,
                  "url": "https://www.arbeitnow.com/jobs/companies/open-jobs-co/python-developer-remote",
                  "description": "Build Python APIs with SQL and React dashboards.",
                  "tags": ["Python", "SQL", "React"]
                }
              ]
            }
            """
        )

    monkeypatch.setattr("app.services.job_matching_service.urllib.request.urlopen", fake_urlopen)

    response = client.get("/jobs?query=Python%20Developer&location=Remote&limit=3")

    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == "arbeitnow"
    assert payload["jobs"][0]["apply_url"].startswith("https://www.arbeitnow.com/jobs/")
    assert payload["jobs"][0]["source"] == "arbeitnow"
    assert "python" in payload["jobs"][0]["required_skills"]


def test_recommended_jobs_uses_saved_resume_defaults(tmp_path):
    app = create_app(
        {
            "database_url": f"sqlite:///{tmp_path / 'recommended-jobs.db'}",
            "auth_secret_key": "test-secret",
        }
    )
    client = TestClient(app)
    client.post(
        "/api/v1/pipeline/analyze-resume",
        json={
            "resume_text": "Skills: SQL, Python, Excel. Projects: Built analytics dashboards.",
            "target_role": "Data Analyst",
        },
    )

    response = client.get("/recommended-jobs?limit=3")

    assert response.status_code == 200
    payload = response.json()
    assert payload["profile_role"] == "Data Analyst"
    assert len(payload["jobs"]) == 3
    assert payload["jobs"][0]["match_score"] >= payload["jobs"][-1]["match_score"]


def test_match_jobs_honors_explicit_zero_profile_scores(tmp_path):
    app = create_app(
        {
            "database_url": f"sqlite:///{tmp_path / 'job-zero-scores.db'}",
            "auth_secret_key": "test-secret",
        }
    )
    client = TestClient(app)
    client.post(
        "/api/v1/pipeline/analyze-resume",
        json={
            "resume_text": "Skills: Python, React, SQL. Projects: Built APIs.",
            "target_role": "Backend SDE",
        },
    )

    response = client.post(
        "/match-jobs",
        json={
            "skills": ["Python"],
            "ats_score": 0,
            "test_score": 0,
            "trust_score": 0,
            "selected_role": "Backend SDE",
            "jobs": [
                {
                    "job_id": "python-only",
                    "title": "Python Developer",
                    "company": "ZeroScore Labs",
                    "location": "Remote",
                    "description": "Python role",
                    "remote": True,
                    "source": "test",
                    "required_skills": ["python"],
                },
            ],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["jobs"][0]["skill_match_percent"] == 100
    assert payload["jobs"][0]["match_score"] == 40
