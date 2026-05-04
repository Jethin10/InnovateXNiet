from fastapi.testclient import TestClient

from app.main import create_app


def test_student_scoped_endpoint_requires_matching_actor_headers(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'authz.db'}"
    app = create_app({"database_url": database_url})
    client = TestClient(app)

    student_response = client.post(
        "/api/v1/students",
        json={
            "full_name": "Neha Singh",
            "email": "neha@example.com",
            "target_role": "Backend SDE",
            "target_company": "Amazon",
        },
    )
    student_id = student_response.json()["student_id"]

    unauthenticated = client.get(f"/api/v1/students/{student_id}/assessment-plan")
    wrong_student = client.get(
        f"/api/v1/students/{student_id}/assessment-plan",
        headers={"X-Actor-Role": "student", "X-Actor-Student-Id": "999"},
    )
    admin_access = client.get(
        f"/api/v1/students/{student_id}/assessment-plan",
        headers={"X-Actor-Role": "admin"},
    )

    assert unauthenticated.status_code == 401
    assert wrong_student.status_code == 403
    assert admin_access.status_code in {200, 404}
