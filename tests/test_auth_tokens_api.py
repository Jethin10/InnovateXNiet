from fastapi.testclient import TestClient

from app.main import create_app


def test_student_can_register_login_and_use_bearer_token(tmp_path):
    app = create_app(
        {
            "database_url": f"sqlite:///{tmp_path / 'auth-token.db'}",
            "auth_secret_key": "test-secret",
        }
    )
    client = TestClient(app)

    register_response = client.post(
        "/api/v1/auth/register-student",
        json={
            "full_name": "Devika Menon",
            "email": "devika@example.com",
            "password": "StrongPass123",
            "target_role": "Backend SDE",
            "target_company": "Amazon",
        },
    )
    assert register_response.status_code == 201
    student_id = register_response.json()["student_id"]

    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "devika@example.com", "password": "StrongPass123"},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]

    plan_response = client.get(
        f"/api/v1/students/{student_id}/assessment-plan",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert plan_response.status_code == 404


def test_login_rejects_wrong_password(tmp_path):
    app = create_app(
        {
            "database_url": f"sqlite:///{tmp_path / 'bad-password.db'}",
            "auth_secret_key": "test-secret",
        }
    )
    client = TestClient(app)
    client.post(
        "/api/v1/auth/register-student",
        json={
            "full_name": "Rohan Gupta",
            "email": "rohan@example.com",
            "password": "StrongPass123",
            "target_role": "Full Stack Developer",
        },
    )

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "rohan@example.com", "password": "wrong-password"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


def test_staff_registration_requires_admin_key(tmp_path):
    app = create_app(
        {
            "database_url": f"sqlite:///{tmp_path / 'staff-key.db'}",
            "auth_secret_key": "test-secret",
            "admin_registration_key": "let-me-in",
        }
    )
    client = TestClient(app)

    rejected = client.post(
        "/api/v1/auth/register-staff",
        json={
            "full_name": "Mentor One",
            "email": "mentor@example.com",
            "password": "StrongPass123",
            "role": "mentor",
            "registration_key": "wrong",
        },
    )
    accepted = client.post(
        "/api/v1/auth/register-staff",
        json={
            "full_name": "Mentor One",
            "email": "mentor@example.com",
            "password": "StrongPass123",
            "role": "mentor",
            "registration_key": "let-me-in",
        },
    )

    assert rejected.status_code == 403
    assert accepted.status_code == 201
