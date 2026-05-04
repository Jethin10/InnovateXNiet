from fastapi.testclient import TestClient

from app.main import create_app


RESUME = """
Skills: Python, React, SQL, APIs, Data Structures
Projects: Built REST APIs and React dashboards for 1000 students.
Experience: Optimized database queries and implemented backend services.
Education: B.Tech Computer Science
"""


def test_pipeline_analyzes_resume_with_explainable_scores(tmp_path):
    app = create_app(
        {
            "database_url": f"sqlite:///{tmp_path / 'pipeline-analyze.db'}",
            "auth_secret_key": "test-secret",
        }
    )
    client = TestClient(app)

    response = client.post(
        "/api/v1/pipeline/analyze-resume",
        json={"resume_text": RESUME, "target_role": "Full Stack Developer"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert "react" in payload["skills"]
    assert payload["ats"]["score"] >= 0
    assert payload["ats"]["explanation"]
    assert payload["ats"]["factors"]
    assert payload["model_readiness_score"] >= 0
    assert payload["model_version"]
    assert payload["suggested_roles"]


def test_pipeline_generates_evaluates_and_reports_with_proctoring(tmp_path):
    app = create_app(
        {
            "database_url": f"sqlite:///{tmp_path / 'pipeline-flow.db'}",
            "auth_secret_key": "test-secret",
        }
    )
    client = TestClient(app)

    analysis = client.post(
        "/api/v1/pipeline/analyze-resume",
        json={"resume_text": RESUME, "target_role": "Backend SDE"},
    ).json()
    generated = client.post(
        "/api/v1/pipeline/generate-test",
        json={
            "skills": analysis["skills"],
            "selected_role": analysis["selected_role"],
            "experience_level": analysis["experience_level"],
        },
    )
    assert generated.status_code == 200
    questions = generated.json()["questions"]
    assert questions

    answers = [
        {
            "question_id": question["question_id"],
            "submitted_answer": "O(1)" if question["question_id"] == "be_easy_dsa_array_lookup" else "not sure",
            "elapsed_seconds": 20,
            "confidence": 0.7,
        }
        for question in questions[:3]
    ]
    evaluation = client.post(
        "/api/v1/pipeline/evaluate-test",
        json={
            "selected_role": analysis["selected_role"],
            "skills": analysis["skills"],
            "answers": answers,
            "proctoring_events": [
                {"event_type": "tab_switch", "count": 2, "severity": 0.7},
                {"event_type": "face_not_detected", "count": 1, "severity": 0.6},
            ],
        },
    )
    assert evaluation.status_code == 200
    evaluated = evaluation.json()
    assert evaluated["trust"]["score"] <= evaluated["test"]["score"]
    assert "tab switch" in " ".join(evaluated["trust"]["factors"]).lower()

    report = client.post(
        "/api/v1/pipeline/final-report",
        json={
            "resume_text": RESUME,
            "selected_role": analysis["selected_role"],
            "skills": analysis["skills"],
            "ats_score": analysis["ats"]["score"],
            "test_score": evaluated["test"]["score"],
            "trust_score": evaluated["trust"]["score"],
            "skill_breakdown": evaluated["skill_breakdown"],
            "proctoring_events": [{"event_type": "tab_switch", "count": 2, "severity": 0.7}],
        },
    )
    assert report.status_code == 200
    payload = report.json()
    assert payload["role_fit"]["explanation"]
    assert payload["roadmap"]
