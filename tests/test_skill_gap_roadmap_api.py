from fastapi.testclient import TestClient

from app.main import create_app
from app.services.skill_gap_roadmap_service import SkillGapRoadmapService


def test_pipeline_generates_skill_gap_roadmap_and_tracks_progress(tmp_path):
    app = create_app(
        {
            "database_url": f"sqlite:///{tmp_path / 'skill-roadmap.db'}",
            "auth_secret_key": "test-secret",
        }
    )
    client = TestClient(app)

    response = client.post(
        "/api/v1/pipeline/generate-roadmap",
        json={
            "extracted_skills": ["Python", "SQL"],
            "missing_skills": ["REST API", "System Design", "Testing"],
            "ats_score": 52,
            "test_score": 48,
            "weak_areas": ["testing"],
            "target_role": "Backend SDE",
            "recommended_jobs": [
                {"title": "Backend Engineer", "match_score": 61, "required_skills": ["REST API", "Testing", "SQL"]},
                {"title": "Platform SDE", "match_score": 57, "required_skills": ["System Design", "REST API"]},
            ],
            "skill_breakdown": {"testing": 35, "sql": 80},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["target_role"] == "Backend SDE"
    assert payload["skill_gaps"][:3] == ["REST API", "Testing", "System Design"]
    assert payload["roadmap"][0]["priority"] == "High"
    assert payload["roadmap"][0]["daily_tasks"]
    assert payload["roadmap"][0]["resource_queries"]
    assert payload["roadmap"][0]["harness_questions"]
    assert payload["roadmap"][0]["job_impact"]["impacted_job_count"] >= 1
    assert "Missing" in payload["roadmap"][0]["reason"]

    latest = client.get("/api/v1/pipeline/roadmap")
    assert latest.status_code == 200
    assert latest.json()["roadmap"][0]["skill"] == payload["roadmap"][0]["skill"]

    task_id = payload["roadmap"][0]["daily_tasks"][0]["task_id"]
    progress = client.post(
        "/api/v1/pipeline/update-progress",
        json={"task_id": task_id, "status": "completed", "proof_summary": "Built CRUD endpoint"},
    )
    assert progress.status_code == 200
    assert progress.json()["completed_tasks"] == 1
    assert progress.json()["progress_percent"] > 0

    progress_get = client.get("/api/v1/pipeline/roadmap-progress")
    assert progress_get.status_code == 200
    assert progress_get.json()["completed_tasks"] == 1

    public_alias = client.get("/roadmap-progress")
    assert public_alias.status_code == 200
    assert public_alias.json()["completed_tasks"] == 1


def test_pipeline_uses_hugging_face_generated_learning_details(tmp_path, monkeypatch):
    def fake_hf(self, skill, request):
        return {
            "concepts": ["HF concept: route design", "HF concept: API validation"],
            "steps": ["HF step: implement one endpoint", "HF step: test response contracts"],
            "project": "HF project: build a job-tracking REST API",
            "daily_tasks": ["Sketch resources", "Build endpoint", "Write tests"],
        }

    monkeypatch.setattr(SkillGapRoadmapService, "_generate_with_hugging_face", fake_hf)
    app = create_app(
        {
            "database_url": f"sqlite:///{tmp_path / 'hf-roadmap.db'}",
            "auth_secret_key": "test-secret",
        }
    )
    client = TestClient(app)

    response = client.post(
        "/api/v1/pipeline/generate-roadmap",
        json={
            "extracted_skills": ["Python"],
            "missing_skills": ["REST API"],
            "ats_score": 50,
            "test_score": 40,
            "weak_areas": [],
            "target_role": "Backend SDE",
            "recommended_jobs": [
                {"title": "Backend Engineer", "match_score": 60, "required_skills": ["REST API"]}
            ],
            "skill_breakdown": {},
        },
    )

    assert response.status_code == 200
    item = response.json()["roadmap"][0]
    assert item["concepts"][0] == "HF concept: route design"
    assert item["steps"][0] == "HF step: implement one endpoint"
    assert item["project"] == "HF project: build a job-tracking REST API"
    assert item["daily_tasks"][0]["action"] == "Sketch resources"


def test_pipeline_reuses_saved_resume_analysis_for_roadmap_defaults(tmp_path):
    app = create_app(
        {
            "database_url": f"sqlite:///{tmp_path / 'saved-resume-roadmap.db'}",
            "auth_secret_key": "test-secret",
        }
    )
    client = TestClient(app)

    analysis = client.post(
        "/api/v1/pipeline/analyze-resume",
        json={
            "resume_text": "Skills: Python, SQL. Projects: Built backend APIs.",
            "target_role": "Backend SDE",
        },
    )
    assert analysis.status_code == 200

    roadmap = client.post(
        "/api/v1/pipeline/generate-roadmap",
        json={
            "target_role": "Backend SDE",
            "recommended_jobs": [
                {"title": "Backend Engineer", "match_score": 60, "required_skills": ["REST API", "Testing"]}
            ],
        },
    )

    assert roadmap.status_code == 200
    payload = roadmap.json()
    assert payload["skill_gaps"]
    assert payload["roadmap"][0]["job_impact"]["summary"]
    assert payload["roadmap"][0]["resource_queries"]


def test_pipeline_autogenerates_latest_roadmap_from_saved_resume(tmp_path):
    app = create_app(
        {
            "database_url": f"sqlite:///{tmp_path / 'auto-saved-resume-roadmap.db'}",
            "auth_secret_key": "test-secret",
        }
    )
    client = TestClient(app)

    client.post(
        "/api/v1/pipeline/analyze-resume",
        json={
            "resume_text": "Skills: React, SQL. Projects: Built dashboards.",
            "target_role": "Frontend Developer",
        },
    )
    latest = client.get("/api/v1/pipeline/roadmap")

    assert latest.status_code == 200
    payload = latest.json()
    assert payload["target_role"]
    assert payload["skill_gaps"]
    assert payload["roadmap"][0]["harness_questions"]


def test_new_resume_analysis_invalidates_previous_roadmap_snapshot(tmp_path):
    app = create_app(
        {
            "database_url": f"sqlite:///{tmp_path / 'invalidate-roadmap.db'}",
            "auth_secret_key": "test-secret",
        }
    )
    client = TestClient(app)

    client.post(
        "/api/v1/pipeline/analyze-resume",
        json={
            "resume_text": "Skills: Python, SQL. Projects: Built backend APIs.",
            "target_role": "Backend SDE",
        },
    )
    first = client.get("/api/v1/pipeline/roadmap")
    assert first.status_code == 200

    client.post(
        "/api/v1/pipeline/analyze-resume",
        json={
            "resume_text": "Skills: React, CSS. Projects: Built accessible frontend dashboards.",
            "target_role": "Frontend Developer",
        },
    )
    second = client.get("/api/v1/pipeline/roadmap")

    assert second.status_code == 200
    assert second.json()["target_role"] == "Frontend Developer"


def test_pipeline_reuses_saved_resume_analysis_for_test_generation(tmp_path):
    app = create_app(
        {
            "database_url": f"sqlite:///{tmp_path / 'saved-resume-test.db'}",
            "auth_secret_key": "test-secret",
        }
    )
    client = TestClient(app)

    client.post(
        "/api/v1/pipeline/analyze-resume",
        json={
            "resume_text": "Skills: Python, SQL. Projects: Built backend APIs.",
            "target_role": "Backend SDE",
        },
    )
    generated = client.post(
        "/api/v1/pipeline/generate-test",
        json={"selected_role": "Backend SDE"},
    )

    assert generated.status_code == 200
    assert generated.json()["questions"]
