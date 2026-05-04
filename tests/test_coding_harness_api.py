from fastapi.testclient import TestClient

from app.main import create_app


PROCTORING_CHECKS = {
    "fullscreen_active": True,
    "screen_share_active": True,
    "screen_share_surface_monitor": True,
    "camera_active": True,
    "copy_paste_blocked": True,
}


def _student(client: TestClient) -> tuple[int, dict[str, str]]:
    response = client.post(
        "/api/v1/auth/register-student",
        json={
            "full_name": "Harness Student",
            "email": "harness@example.com",
            "password": "StrongPass123",
            "target_role": "Backend SDE",
            "target_company": "Amazon",
        },
    )
    student_id = response.json()["student_id"]
    token = client.post(
        "/api/v1/auth/login",
        json={"email": "harness@example.com", "password": "StrongPass123"},
    ).json()["access_token"]
    return student_id, {"Authorization": f"Bearer {token}"}


def test_coding_problem_catalog_hides_answer_keys_and_hidden_cases(tmp_path):
    app = create_app(
        {
            "database_url": f"sqlite:///{tmp_path / 'coding-catalog.db'}",
            "auth_secret_key": "test-secret",
        }
    )
    client = TestClient(app)

    response = client.get("/api/v1/coding/problems")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) >= 3
    assert any(problem["problem_id"] == "two_sum_indices" for problem in payload)
    assert all("hidden_cases" not in problem for problem in payload)
    assert all("solution" not in problem for problem in payload)


def test_student_can_submit_python_solution_against_public_and_hidden_tests(tmp_path):
    app = create_app(
        {
            "database_url": f"sqlite:///{tmp_path / 'coding-submit.db'}",
            "auth_secret_key": "test-secret",
        }
    )
    client = TestClient(app)
    student_id, headers = _student(client)

    response = client.post(
        f"/api/v1/students/{student_id}/coding/submissions",
        headers=headers,
        json={
            "problem_id": "two_sum_indices",
            "language": "python",
            "code": """
def solve(nums, target):
    seen = {}
    for index, value in enumerate(nums):
        need = target - value
        if need in seen:
            return [seen[need], index]
        seen[value] = index
    return []
""",
            "proctoring_checks": PROCTORING_CHECKS,
            "proctoring_events": [],
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["passed"] is True
    assert payload["score"] == 100
    assert payload["hidden_passed_count"] == payload["hidden_total_count"]
    assert payload["public_results"][0]["passed"] is True
    assert "expected" in payload["public_results"][0]
    assert payload["integrity_flags"] == []

    summary = client.get(f"/api/v1/students/{student_id}/evidence", headers=headers)
    assert summary.status_code == 200
    assert summary.json()["coding_harness"]["solved_count"] == 1


def test_coding_submission_requires_secure_proctoring_state(tmp_path):
    app = create_app(
        {
            "database_url": f"sqlite:///{tmp_path / 'coding-proctoring.db'}",
            "auth_secret_key": "test-secret",
        }
    )
    client = TestClient(app)
    student_id, headers = _student(client)

    response = client.post(
        f"/api/v1/students/{student_id}/coding/submissions",
        headers=headers,
        json={
            "problem_id": "two_sum_indices",
            "language": "python",
            "code": "def solve(nums, target):\n    return [0, 1]\n",
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "fullscreen_not_active"


def test_coding_submission_rejects_screen_camera_without_fullscreen(tmp_path):
    app = create_app(
        {
            "database_url": f"sqlite:///{tmp_path / 'coding-no-fullscreen.db'}",
            "auth_secret_key": "test-secret",
        }
    )
    client = TestClient(app)
    student_id, headers = _student(client)

    checks = {**PROCTORING_CHECKS, "fullscreen_active": False}
    response = client.post(
        f"/api/v1/students/{student_id}/coding/submissions",
        headers=headers,
        json={
            "problem_id": "two_sum_indices",
            "language": "python",
            "code": "def solve(nums, target):\n    return [0, 1]\n",
            "proctoring_checks": checks,
            "proctoring_events": [],
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "fullscreen_not_active"


def test_coding_submission_rejects_copy_paste_attempts(tmp_path):
    app = create_app(
        {
            "database_url": f"sqlite:///{tmp_path / 'coding-copy-paste.db'}",
            "auth_secret_key": "test-secret",
        }
    )
    client = TestClient(app)
    student_id, headers = _student(client)

    response = client.post(
        f"/api/v1/students/{student_id}/coding/submissions",
        headers=headers,
        json={
            "problem_id": "two_sum_indices",
            "language": "python",
            "code": "def solve(nums, target):\n    return [0, 1]\n",
            "proctoring_checks": PROCTORING_CHECKS,
            "proctoring_events": [{"event_type": "paste", "count": 1, "severity": 0.95}],
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "copy_paste_attempt"


def test_proctoring_frame_analysis_falls_back_without_hugging_face_token(tmp_path):
    app = create_app(
        {
            "database_url": f"sqlite:///{tmp_path / 'coding-hf-proctor.db'}",
            "auth_secret_key": "test-secret",
            "huggingface_api_token": None,
        }
    )
    client = TestClient(app)
    student_id, headers = _student(client)

    response = client.post(
        f"/api/v1/students/{student_id}/proctoring/analyze-frame",
        headers=headers,
        json={"image_data_url": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2w=="},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["analyzed"] is False
    assert payload["model"]
    assert "local browser proctoring" in payload["reason"]


def test_coding_submission_rejects_import_based_cheating_attempt(tmp_path):
    app = create_app(
        {
            "database_url": f"sqlite:///{tmp_path / 'coding-cheat.db'}",
            "auth_secret_key": "test-secret",
        }
    )
    client = TestClient(app)
    student_id, headers = _student(client)

    response = client.post(
        f"/api/v1/students/{student_id}/coding/submissions",
        headers=headers,
        json={
            "problem_id": "two_sum_indices",
            "language": "python",
            "code": "import os\n\ndef solve(nums, target):\n    return os.listdir('.')",
        },
    )

    assert response.status_code == 422
    assert "Imports are disabled" in response.json()["detail"]


def test_coding_submission_uses_judge0_when_configured(tmp_path, monkeypatch):
    app = create_app(
        {
            "database_url": f"sqlite:///{tmp_path / 'coding-judge0.db'}",
            "auth_secret_key": "test-secret",
            "judge0_base_url": "http://judge0.local",
        }
    )
    client = TestClient(app)
    student_id, headers = _student(client)
    calls = []

    class FakeJudge0Response:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def read(self):
            return b'{"stdout":"{\\"passed\\": true, \\"actual\\": [0, 1]}\\n","status":{"description":"Accepted"}}'

    def fake_urlopen(request, timeout):
        calls.append((request.full_url, timeout))
        return FakeJudge0Response()

    monkeypatch.setattr("app.services.coding_service.urllib.request.urlopen", fake_urlopen)

    response = client.post(
        f"/api/v1/students/{student_id}/coding/submissions",
        headers=headers,
        json={
            "problem_id": "two_sum_indices",
            "language": "python",
            "code": "def solve(nums, target):\n    return [0, 1]\n",
            "proctoring_checks": PROCTORING_CHECKS,
            "proctoring_events": [],
        },
    )

    assert response.status_code == 201
    assert calls
    assert calls[0][0] == "http://judge0.local/submissions?wait=true"
    assert response.json()["passed"] is True
