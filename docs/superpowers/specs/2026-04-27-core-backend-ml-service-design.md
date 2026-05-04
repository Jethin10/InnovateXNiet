# Core Backend + ML Service Design

## Goal

Build a production-shaped backend for the placement trust platform as a single Python service that supports:

- student intake
- assessment and scoring orchestration
- roadmap generation and progression storage
- Trust Stamp projection
- institution-facing aggregate analytics
- ML inference using the existing `trust_ml` package

This slice is designed for hackathon delivery first, while keeping the boundaries clean enough to split into separate services later.

## Why A Python Monolith

For the hackathon, the strongest option is a single `FastAPI` service with embedded ML logic.

Reasons:

- the current intelligence layer already exists in Python
- one deployable unit is more reliable during demos
- shared types and service boundaries are easier to evolve quickly
- we avoid premature network boundaries between app logic and ML inference

Long term, the scoring engine can be extracted into its own inference service if load, team structure, or deployment needs justify it.

## System Scope

This first backend slice includes:

- API scaffold and runtime settings
- relational persistence layer
- user, profile, resume, evidence, assessment, trust score, roadmap, and Trust Stamp storage
- internal application services wrapping the existing ML package
- first API endpoints for health, student intake, scoring, roadmap snapshot, and Trust Stamp retrieval

This first slice does not yet include:

- a real authentication provider
- production file storage for resumes
- live third-party coding platform sync jobs
- adaptive question bank delivery
- code execution sandboxing
- real admin dashboard UI

Those are planned for later backend slices after the foundation is in place.

## Architectural Shape

The backend will use a layered monolith:

- `app.api`: HTTP routes and request or response DTOs
- `app.core`: settings, logging, dependency wiring
- `app.db`: engine, sessions, ORM models
- `app.repositories`: focused data-access helpers
- `app.services`: business logic and orchestration
- `app.ml`: adapters around `trust_ml`

The ML package remains a reusable internal domain library. The backend service becomes the product runtime around it.

## Domain Model

### User And Profile

- `User`
  - product identity record
  - role values such as `student`, `mentor`, `admin`, `recruiter`
- `StudentProfile`
  - belongs to `User`
  - stores target role, target company, skill preferences, and linked handles

### Evidence And Resume

- `ResumeArtifact`
  - uploaded filename
  - raw text
  - parse status
  - extracted claims snapshot
- `EvidenceSnapshot`
  - Codeforces handle and rating
  - LeetCode solved count when manually provided
  - GitHub project metadata when available
  - verified skills and project tags

### Assessment And Scoring

- `AssessmentPlan`
  - one generated three-stage verification plan for a profile
- `AssessmentSession`
  - one active or completed attempt
  - lifecycle states such as `draft`, `in_progress`, `submitted`, `scored`
- `AssessmentResponse`
  - a stored answer event with timing, correctness, confidence, and answer changes
- `TrustScore`
  - scored output
  - readiness and risk bands
  - bluff index
  - feature snapshot
  - model version

### Roadmap And Trust Stamp

- `RoadmapSnapshot`
  - generated roadmap graph for a profile and target role
- `RoadmapNodeProgress`
  - per-node state such as `locked`, `ready`, `completed`, `recheck_needed`
- `TrustStampProfile`
  - consent flag
  - public slug
  - visibility settings
  - latest exposed trust score reference

## Data Flow

### Intake And Scoring Flow

1. client creates a student profile
2. client submits resume text or manual skills
3. intake service extracts claims and inferred role hints
4. verification service generates a three-stage assessment plan
5. client submits assessment responses and evidence details
6. scoring service converts stored data into a `trust_ml` `AssessmentSession`
7. ML adapter produces a `TrustScore`
8. roadmap service generates and stores a roadmap snapshot
9. Trust Stamp service updates the public projection if the user opted in

### Recruiter Flow

1. recruiter opens a public Trust Stamp slug
2. backend returns only consented fields
3. response includes readiness band, verified evidence summary, and major positive or risk signals

### Institution Flow

1. institution context groups students into a cohort later
2. backend aggregates stored trust scores
3. service returns risk buckets and skill-gap heatmap data

## ML Integration Design

The backend should not reimplement ML logic. It should adapt the existing package behind a stable interface.

### ML Adapter Responsibilities

- load the current trained artifact from disk
- translate persisted ORM data into `trust_ml` schemas
- score a completed assessment session
- regenerate roadmap payloads from stored scorecards

### Production Guardrails

- every score stores the `model_version`
- every score stores the exact `feature_snapshot`
- public Trust Stamp responses must never expose raw internal features
- bluff index remains framed as a risk signal, not a fraud verdict

## Persistence Strategy

Use `SQLAlchemy` ORM with a SQLite default for local hackathon setup and a PostgreSQL-compatible schema design.

This gives:

- zero-friction local development
- easy future migration to managed Postgres
- realistic repository and service boundaries now

Alembic-style migration support should be planned, but the first code slice can rely on ORM metadata bootstrap to stay moving.

## API Surface For Slice One

- `GET /health`
- `POST /api/v1/students`
- `POST /api/v1/students/{student_id}/intake`
- `POST /api/v1/students/{student_id}/assessment-plans`
- `POST /api/v1/students/{student_id}/assessments`
- `POST /api/v1/assessments/{assessment_id}/score`
- `GET /api/v1/students/{student_id}/roadmap`
- `GET /api/v1/trust-stamp/{slug}`

These are enough to demonstrate the first full backend story without waiting on a frontend.

## Error Handling

- validation errors return structured `422` payloads through FastAPI
- missing records return `404`
- scoring without responses returns `409`
- Trust Stamp requests for non-consented profiles return `404` rather than leaking existence

## Testing Strategy

Use TDD for the backend slice:

- API tests for happy-path endpoints
- service tests for intake, scoring, and Trust Stamp behavior
- persistence tests using a temporary SQLite database
- regression tests that ensure the ML adapter still produces meaningful scorecards

## Success Criteria

This slice is successful when:

- a student profile can be created through the API
- intake can generate a verification plan
- an assessment submission can be scored through the existing ML engine
- a roadmap snapshot is persisted and retrievable
- a consented Trust Stamp can be fetched through a public endpoint
- the whole flow is covered by passing tests
