from fastapi.testclient import TestClient

from app.main import create_app


def test_question_bank_endpoint_exposes_prompts_without_answer_keys(tmp_path):
    app = create_app({"database_url": f"sqlite:///{tmp_path / 'question-bank.db'}"})
    client = TestClient(app)

    response = client.get("/api/v1/assessment-questions")

    assert response.status_code == 200
    questions = response.json()
    assert any(question["question_id"] == "be_easy_dsa_array_lookup" for question in questions)
    assert all("answer_aliases" not in question for question in questions)
    assert all("prompt" in question for question in questions)
