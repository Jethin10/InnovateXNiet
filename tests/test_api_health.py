from fastapi.testclient import TestClient

from app.main import app


def test_health_endpoint_reports_ok():
    client = TestClient(app)

    response = client.get("/health")
    payload = response.json()

    assert response.status_code == 200
    assert payload["status"] == "ok"
    assert payload["env"] == "development"
    assert payload["version"]
