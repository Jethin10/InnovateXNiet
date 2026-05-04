from fastapi.testclient import TestClient
from urllib.error import HTTPError

from app.main import create_app


def _student(client: TestClient) -> tuple[int, dict[str, str]]:
    response = client.post(
        "/api/v1/auth/register-student",
        json={
            "full_name": "GitHub Student",
            "email": "github-student@example.com",
            "password": "StrongPass123",
            "target_role": "Full Stack SDE",
            "target_company": "Product startup",
        },
    )
    student_id = response.json()["student_id"]
    token = client.post(
        "/api/v1/auth/login",
        json={"email": "github-student@example.com", "password": "StrongPass123"},
    ).json()["access_token"]
    return student_id, {"Authorization": f"Bearer {token}"}


def test_github_evidence_generates_project_recommendations_from_repositories(tmp_path):
    app = create_app(
        {
            "database_url": f"sqlite:///{tmp_path / 'github-projects.db'}",
            "auth_secret_key": "test-secret",
        }
    )
    app.state.github_client = lambda username: {
        "login": username,
        "public_repos": 4,
        "followers": 12,
    }
    app.state.github_repos_client = lambda username: [
        {
            "name": "fastapi-placement-api",
            "language": "Python",
            "description": "REST API for placement readiness scoring",
            "stargazers_count": 3,
            "fork": False,
            "pushed_at": "2026-04-20T10:00:00Z",
        },
        {
            "name": "react-dashboard",
            "language": "TypeScript",
            "description": "Cohort analytics dashboard",
            "stargazers_count": 1,
            "fork": False,
            "pushed_at": "2026-04-22T10:00:00Z",
        },
        {
            "name": "old-fork",
            "language": "JavaScript",
            "description": "Forked starter",
            "stargazers_count": 0,
            "fork": True,
            "pushed_at": "2025-01-01T10:00:00Z",
        },
    ]
    client = TestClient(app)
    student_id, headers = _student(client)

    response = client.post(
        f"/api/v1/students/{student_id}/evidence/github",
        headers=headers,
        json={"username": "builder-dev"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["repo_count"] == 4
    assert payload["original_repo_count"] == 2
    assert payload["top_languages"] == ["Python", "TypeScript"]
    assert payload["contribution_summary"]
    assert payload["project_recommendations"][0]["title"] == "Production API reliability upgrade"
    assert "fastapi-placement-api" in payload["project_recommendations"][0]["evidence_repo_names"]

    summary = client.get(f"/api/v1/students/{student_id}/evidence", headers=headers)
    assert summary.status_code == 200
    assert summary.json()["github"]["project_recommendations"]


def test_github_evidence_uses_rich_repository_commit_and_language_signals(tmp_path):
    app = create_app(
        {
            "database_url": f"sqlite:///{tmp_path / 'github-rich-projects.db'}",
            "auth_secret_key": "test-secret",
        }
    )

    def github_profile_client(request):
        assert request.username == "builder-dev"
        assert request.access_token == "demo-token"
        assert request.include_private is True
        return {
            "user": {
                "login": "builder-dev",
                "followers": 12,
                "public_repos": 3,
            },
            "repositories": [
                {
                    "name": "placement-api",
                    "full_name": "builder-dev/placement-api",
                    "html_url": "https://github.com/builder-dev/placement-api",
                    "description": "FastAPI placement trust API",
                    "language": "Python",
                    "fork": False,
                    "private": False,
                    "stargazers_count": 9,
                    "forks_count": 2,
                    "open_issues_count": 1,
                    "pushed_at": "2026-04-25T10:00:00Z",
                    "updated_at": "2026-04-25T10:00:00Z",
                    "size": 250,
                    "topics": ["fastapi", "placement"],
                    "languages": {"Python": 10000, "TypeScript": 2500},
                    "contributors": [{"login": "builder-dev", "contributions": 14}],
                    "commits": [
                        {
                            "sha": "abc123456",
                            "html_url": "https://github.com/builder-dev/placement-api/commit/abc123456",
                            "commit": {
                                "message": "Add score audit trail",
                                "author": {"date": "2026-04-24T12:00:00Z"},
                            },
                            "author": {"login": "builder-dev"},
                        },
                        {
                            "sha": "def789012",
                            "html_url": "https://github.com/builder-dev/placement-api/commit/def789012",
                            "commit": {
                                "message": "Improve roadmap API",
                                "author": {"date": "2026-04-23T12:00:00Z"},
                            },
                            "author": {"login": "builder-dev"},
                        },
                    ],
                },
                {
                    "name": "private-ml",
                    "full_name": "builder-dev/private-ml",
                    "html_url": "https://github.com/builder-dev/private-ml",
                    "description": "Private trust model experiments",
                    "language": "Jupyter Notebook",
                    "fork": False,
                    "private": True,
                    "stargazers_count": 0,
                    "forks_count": 0,
                    "open_issues_count": 0,
                    "pushed_at": "2026-04-20T10:00:00Z",
                    "updated_at": "2026-04-20T10:00:00Z",
                    "size": 80,
                    "topics": ["ml"],
                    "languages": {"Python": 7000, "Jupyter Notebook": 3000},
                    "contributors": [{"login": "builder-dev", "contributions": 5}],
                    "commits": [
                        {
                            "sha": "feedface0",
                            "html_url": "https://github.com/builder-dev/private-ml/commit/feedface0",
                            "commit": {
                                "message": "Train first trust model",
                                "author": {"date": "2026-04-20T12:00:00Z"},
                            },
                            "author": {"login": "builder-dev"},
                        },
                    ],
                },
            ],
            "rate_limit_remaining": 4990,
        }

    app.state.github_profile_client = github_profile_client
    client = TestClient(app)
    student_id, headers = _student(client)

    response = client.post(
        f"/api/v1/students/{student_id}/evidence/github",
        headers=headers,
        json={
            "username": "builder-dev",
            "access_token": "demo-token",
            "include_private": True,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["username"] == "builder-dev"
    assert payload["repo_count"] == 2
    assert payload["private_repo_count"] == 1
    assert payload["total_commits_analyzed"] == 3
    assert payload["authored_commit_count"] == 3
    assert payload["total_stars"] == 9
    assert payload["language_breakdown"]["Python"] == 17000
    assert payload["top_languages"] == ["Python", "Jupyter Notebook", "TypeScript"]
    assert payload["repositories"][0]["name"] == "placement-api"
    assert payload["repositories"][0]["commit_count_analyzed"] == 2
    assert payload["recent_commits"][0]["message"] == "Add score audit trail"
    assert "3 commits" in payload["contribution_summary"][0]
    assert payload["access_scope"] == "authorized"
    assert payload["rate_limit_remaining"] == 4990

    summary = client.get(f"/api/v1/students/{student_id}/evidence", headers=headers)
    assert "access_token" not in summary.json()["github"]


def test_github_evidence_returns_cached_public_profile_when_rate_limited(tmp_path):
    app = create_app(
        {
            "database_url": f"sqlite:///{tmp_path / 'github-rate-limit-cache.db'}",
            "auth_secret_key": "test-secret",
        }
    )
    app.state.github_profile_client = lambda request: {
        "user": {"login": "builder-dev", "followers": 2, "public_repos": 1},
        "repositories": [
            {
                "name": "cached-api",
                "full_name": "builder-dev/cached-api",
                "html_url": "https://github.com/builder-dev/cached-api",
                "language": "Python",
                "fork": False,
                "private": False,
                "stargazers_count": 1,
                "forks_count": 0,
                "open_issues_count": 0,
                "pushed_at": "2026-04-25T10:00:00Z",
                "languages": {"Python": 100},
                "contributors": [{"login": "builder-dev", "contributions": 2}],
                "commits": [
                    {
                        "sha": "abc123456",
                        "html_url": "https://github.com/builder-dev/cached-api/commit/abc123456",
                        "commit": {"message": "Initial API", "author": {"date": "2026-04-25T12:00:00Z"}},
                        "author": {"login": "builder-dev"},
                    }
                ],
            }
        ],
        "rate_limit_remaining": 0,
    }
    client = TestClient(app)
    student_id, headers = _student(client)
    first = client.post(
        f"/api/v1/students/{student_id}/evidence/github",
        headers=headers,
        json={"username": "builder-dev"},
    )
    assert first.status_code == 200

    def rate_limited(_request):
        raise HTTPError(
            url="https://api.github.com/users/builder-dev",
            code=403,
            msg="API rate limit exceeded",
            hdrs=None,
            fp=None,
        )

    app.state.github_profile_client = rate_limited
    second = client.post(
        f"/api/v1/students/{student_id}/evidence/github",
        headers=headers,
        json={"username": "builder-dev"},
    )

    assert second.status_code == 200
    payload = second.json()
    assert payload["access_scope"] == "cached_public"
    assert payload["repositories"][0]["name"] == "cached-api"
    assert "cached" in payload["contribution_summary"][0].lower()
