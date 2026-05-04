# Core Backend + ML Service Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first production-shaped backend slice for the placement trust platform as a FastAPI service with persistence and ML-backed scoring.

**Architecture:** Use a Python monolith with `FastAPI` for HTTP, `SQLAlchemy` for persistence, and the existing `trust_ml` package as the internal intelligence layer. Keep app concerns in a new `app` package and treat `trust_ml` as a domain library that the backend adapts.

**Tech Stack:** Python 3.11+, FastAPI, Pydantic, SQLAlchemy, SQLite for local development, pytest, existing `trust_ml` package

---

### Task 1: Backend Skeleton

**Files:**
- Create: `app/__init__.py`
- Create: `app/main.py`
- Create: `app/core/config.py`
- Create: `app/api/__init__.py`
- Create: `app/api/routes.py`
- Test: `tests/test_api_health.py`

- [ ] Add a failing API health test for `GET /health`.
- [ ] Run `pytest tests/test_api_health.py -q` and verify it fails because the app package does not exist.
- [ ] Add the minimal FastAPI app, settings object, and `/health` route.
- [ ] Run `pytest tests/test_api_health.py -q` and verify it passes.

### Task 2: Database Bootstrap

**Files:**
- Create: `app/db/__init__.py`
- Create: `app/db/base.py`
- Create: `app/db/session.py`
- Create: `app/db/models.py`
- Test: `tests/test_db_bootstrap.py`

- [ ] Add a failing test that boots the app database metadata against a temporary SQLite file.
- [ ] Run `pytest tests/test_db_bootstrap.py -q` and verify it fails because the session and models modules do not exist.
- [ ] Add SQLAlchemy engine, declarative base, and initial ORM models for `User`, `StudentProfile`, `ResumeArtifact`, `AssessmentSessionRecord`, `TrustScoreRecord`, `RoadmapSnapshot`, and `TrustStampProfileRecord`.
- [ ] Run `pytest tests/test_db_bootstrap.py -q` and verify it passes.

### Task 3: Student Intake API

**Files:**
- Create: `app/schemas.py`
- Create: `app/repositories/student_repository.py`
- Create: `app/services/intake_service.py`
- Modify: `app/api/routes.py`
- Test: `tests/test_student_intake_api.py`

- [ ] Add a failing API test that creates a student and submits resume or manual intake data.
- [ ] Run `pytest tests/test_student_intake_api.py -q` and verify it fails for missing schemas and services.
- [ ] Implement request or response DTOs, repository helpers, and intake service using `trust_ml.intake.ResumeIntakeService` and `trust_ml.verification.VerificationPlanner`.
- [ ] Expose `POST /api/v1/students` and `POST /api/v1/students/{student_id}/intake`.
- [ ] Run `pytest tests/test_student_intake_api.py -q` and verify it passes.

### Task 4: Scoring And Roadmap API

**Files:**
- Create: `app/ml/service.py`
- Create: `app/services/scoring_service.py`
- Modify: `app/db/models.py`
- Modify: `app/api/routes.py`
- Test: `tests/test_scoring_flow_api.py`

- [ ] Add a failing test that submits an assessment payload, scores it, and fetches a roadmap snapshot.
- [ ] Run `pytest tests/test_scoring_flow_api.py -q` and verify it fails because the scoring service and ML adapter do not exist.
- [ ] Implement the ML adapter to load `artifacts/trust_model.joblib` when present and otherwise fall back to a local trained model from demo data.
- [ ] Implement persistence mapping from ORM rows into `trust_ml.schemas.AssessmentSession` and `trust_ml.schemas.EvidenceProfile`.
- [ ] Implement `POST /api/v1/students/{student_id}/assessments`, `POST /api/v1/assessments/{assessment_id}/score`, and `GET /api/v1/students/{student_id}/roadmap`.
- [ ] Run `pytest tests/test_scoring_flow_api.py -q` and verify it passes.

### Task 5: Public Trust Stamp API

**Files:**
- Create: `app/services/trust_stamp_service.py`
- Modify: `app/db/models.py`
- Modify: `app/api/routes.py`
- Test: `tests/test_trust_stamp_api.py`

- [ ] Add a failing API test that exposes a consented Trust Stamp and hides a non-consented one.
- [ ] Run `pytest tests/test_trust_stamp_api.py -q` and verify it fails because the Trust Stamp projection is missing.
- [ ] Implement Trust Stamp creation and retrieval logic using the existing trust score projection rules.
- [ ] Expose `GET /api/v1/trust-stamp/{slug}` and ensure non-consented profiles return `404`.
- [ ] Run `pytest tests/test_trust_stamp_api.py -q` and verify it passes.

### Task 6: Integration Verification

**Files:**
- Modify: `pyproject.toml`
- Test: `tests/test_api_health.py`
- Test: `tests/test_db_bootstrap.py`
- Test: `tests/test_student_intake_api.py`
- Test: `tests/test_scoring_flow_api.py`
- Test: `tests/test_trust_stamp_api.py`
- Test: `tests/test_trust_model.py`
- Test: `tests/test_product_flow.py`

- [ ] Add backend runtime dependencies for FastAPI and SQLAlchemy.
- [ ] Run the new backend API tests together.
- [ ] Run the existing ML and product-flow suites to ensure the backend work did not regress the model package.
- [ ] Start the app locally with `python -m uvicorn app.main:app --reload` and verify the service boots without import errors.
