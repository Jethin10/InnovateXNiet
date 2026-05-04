# Placement Trust Platform Context

## Problem Statement

Students preparing for placements often present resumes that are hard to verify, practice without a clear understanding of their actual level, and receive generic advice that does not connect to a target role or company. Colleges lack visibility into cohort-level skill gaps, and recruiters cannot easily distinguish evidence-backed candidates from inflated profiles.

## Product Direction

The product is a `trust-led placement passport` for `CS students seeking SDE roles`.

The core idea is not just to practice questions. It is to create an evidence-backed trust layer:

- students upload a resume or fill in claimed skills
- students take a staged, timed verification assessment
- the system analyzes ability, calibration, and inconsistencies
- the product produces a consent-based `Trust Stamp` profile
- the student receives a personalized, gated roadmap graph
- mentors and colleges see cohort-level readiness and gap analytics

## Why This Framing Was Chosen

The strongest wedge is `verified proof`, not a generic AI coach.

The exam exists to create evidence. The roadmap, ATS suggestions, and dashboards all build on top of that evidence. This keeps the story coherent and differentiated.

## Users

- `Students`: want to know current level, bluff risk, and next steps for a target role/company.
- `Recruiters`: want a quick, credible way to inspect candidate authenticity and skill depth.
- `College admins / mentors`: want readiness, gap, and intervention visibility across a cohort.

## v1 Feature Scope

### Core

- resume or skill intake
- claim verification
- staged adaptive assessment
- trust scoring
- confidence and bluff-risk analysis
- public or permissioned Trust Stamp URL
- role- and company-specific roadmap graph

### Supporting

- resume checker and ATS recommendations
- coding profile evidence via `Codeforces` first
- platform progress evidence via `LeetCode` in later iterations
- college dashboard aggregates
- demo analytics for interview-failure patterns

## Product Corrections For Production Readiness

- `Trust Stamp` must be opt-in and consent-based. A public score cannot be exposed by default.
- `Bluff index` is a risk signal, not a fraud verdict.
- Recruiter-facing claims must remain evidence-backed and auditable.
- Resume feedback should optimize for evidence alignment and clarity, not keyword stuffing.
- Institutional analytics should be role- and cohort-aware, not used as a blanket judgment on a college.
- Leaderboards should be configurable or private by default in high-anxiety settings.

## ML Scope

### What We Are Actually Building First

The first trained model is a `readiness / skill reliability` model for SDE candidates.

It uses:

- correctness by difficulty band
- time-normalized performance
- answer instability
- confidence calibration
- coding-profile evidence
- resume claim alignment
- project evidence strength

### What We Are Not Claiming Yet

- no direct supervised fraud detector
- no strong public ground-truth dataset for "bluffing"
- no separate trained roadmap or ATS model in v1

`Bluff index` in v1 is a derived trust metric built from overconfidence, instability, and evidence mismatch.

## Intelligence Architecture

### Trained ML Core

- input: assessment session plus evidence profile
- output: readiness probability plus trust-oriented readiness score

### Deterministic Trust Layer

- confidence reliability
- calibration gap
- evidence alignment
- bluff index
- skill-wise sub-scores

### AI Guidance Layer

- role roadmap graph
- ATS and resume guidance
- recruiter and student explanations

## Product Flow

1. user uploads a resume or manually fills in skills
2. the system extracts claimed skills and target-role hints
3. the system builds a 3-stage verification plan
4. the user completes easy, medium, and hard assessments
5. the model estimates readiness, trust risk, and evidence alignment
6. the system generates a role-specific roadmap graph
7. each roadmap node contains:
   - external resources
   - assignments or mini-projects
   - proof requirements
   - unlock dependencies
8. node progress should only unlock forward movement after proof is verified
9. completed verified milestones contribute to the Trust Stamp

## Production ML Requirements

- probability calibration before exposing a score to recruiters or institutions
- out-of-fold evaluation instead of in-sample reporting
- model cards and artifact versioning
- auditable feature snapshots for every prediction
- fairness review across cohort groups when real data exists
- explicit separation between `readiness`, `confidence reliability`, and `bluff risk`
- retraining only after collecting first-party assessment data with outcome labels and consent

## Dataset Decisions

### Official or trusted sources selected

- `O*NET Database`: https://www.onetcenter.org/database.html
- `BLS Skills Data`: https://www.bls.gov/emp/data/skills-data.htm
- `Codeforces API`: https://codeforces.com/apiHelp/methods?locale=en&mobile=false
- `EdNet`: https://github.com/riiid/ednet
- `FoundationalASSIST`: https://huggingface.co/datasets/ASSISTments/FoundationalASSIST
- `UCI Student Performance`: https://archive.ics.uci.edu/dataset/320/student%2Bperformance

### Usage decisions

- `EdNet` and `FoundationalASSIST` shape ability and response-behavior feature design.
- `Codeforces` is the first live external coding-evidence source.
- `O*NET` and `BLS` shape role-skill weighting and roadmap priorities.
- `UCI Student Performance` is auxiliary and not treated as truth for placement trust.
- `UCI Student Performance` is used here as transfer data for repeated training sweeps after mapping rows into the trust-feature space.
- `LeetCode` is optional and manual in v1 because official public API support was not confirmed in the planning pass.

## Demo Story

### Student View

1. student signs in
2. student selects target role and company
3. student optionally links coding profile and uploads resume
4. student completes staged assessment
5. student receives trust score, bluff index, skill breakdown, and roadmap

### Recruiter View

1. recruiter opens Trust Stamp URL
2. recruiter sees overall trust, readiness, evidence alignment, verified signals, and strengths or risks

### College View

1. mentor or admin sees aggregate trust levels
2. mentor or admin reviews weak-skill clusters and risk buckets
3. mentor or admin uses the cohort view to intervene earlier

## Current Implementation In This Workspace

This workspace is being implemented as a compact Python package focused on the ML-first trust layer:

- resume and manual-skill intake
- verification-plan generation
- schemas for assessment and trust scoring
- feature engineering for trust signals
- trainable role-aware model with candidate search and calibration
- roadmap planning and gated roadmap graph generation
- student, recruiter, and college payload builders
- synthetic cohort generation for repeatable local verification and experiment sweeps
- external transfer-data ingestion via the UCI student-performance dataset
- artifact persistence and model-card output

## Assumptions

- primary role focus is `SDE` for v1
- first version optimizes for a compelling, truthful hackathon demo
- the long-term moat is first-party assessment data collected by the product itself
- future versions can replace heuristic trust pieces with stronger supervised models once labeled outcome data exists
