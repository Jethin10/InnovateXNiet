from __future__ import annotations

import random

from .schemas import (
    AnswerEvent,
    AssessmentSession,
    EvidenceProfile,
    QuestionStage,
    TrainingExample,
)


QUESTION_BLUEPRINTS = (
    {
        "question_id": "q1",
        "stage_id": 1,
        "difficulty_band": "easy",
        "skill_tag": "dsa",
        "max_time_seconds": 60.0,
    },
    {
        "question_id": "q2",
        "stage_id": 1,
        "difficulty_band": "easy",
        "skill_tag": "fundamentals",
        "max_time_seconds": 60.0,
    },
    {
        "question_id": "q3",
        "stage_id": 2,
        "difficulty_band": "medium",
        "skill_tag": "dsa",
        "max_time_seconds": 90.0,
    },
    {
        "question_id": "q4",
        "stage_id": 2,
        "difficulty_band": "medium",
        "skill_tag": "projects",
        "max_time_seconds": 90.0,
    },
    {
        "question_id": "q5",
        "stage_id": 3,
        "difficulty_band": "hard",
        "skill_tag": "dsa",
        "max_time_seconds": 120.0,
    },
    {
        "question_id": "q6",
        "stage_id": 3,
        "difficulty_band": "hard",
        "skill_tag": "fundamentals",
        "max_time_seconds": 120.0,
    },
)


STAGES = (
    QuestionStage(1, "Stage 1", "easy", 60.0, "foundation"),
    QuestionStage(2, "Stage 2", "medium", 90.0, "application"),
    QuestionStage(3, "Stage 3", "hard", 120.0, "depth"),
)


VARIANTS = {
    "calibrated_solver": {
        "label": 1,
        "role": "Backend SDE",
        "company": "Amazon",
        "answers": [
            (True, 26, 0.88, 0),
            (True, 34, 0.84, 0),
            (True, 40, 0.79, 0),
            (True, 48, 0.74, 0),
            (False, 94, 0.35, 1),
            (True, 72, 0.77, 0),
        ],
        "evidence": {
            "codeforces_rating": 1580,
            "resume_claims": ("dsa", "fundamentals", "projects"),
            "verified_skills": ("dsa", "fundamentals"),
            "project_tags": ("projects", "backend"),
            "project_count": 3,
            "github_repo_count": 4,
        },
    },
    "supported_resume": {
        "label": 1,
        "role": "Backend SDE",
        "company": "Amazon",
        "answers": [
            (True, 28, 0.86, 0),
            (True, 36, 0.82, 0),
            (True, 46, 0.78, 0),
            (True, 51, 0.75, 0),
            (False, 92, 0.32, 1),
            (True, 76, 0.73, 0),
        ],
        "evidence": {
            "codeforces_rating": 1500,
            "resume_claims": ("dsa", "fundamentals", "projects"),
            "verified_skills": ("dsa", "fundamentals", "projects"),
            "project_tags": ("projects", "backend"),
            "project_count": 3,
            "github_repo_count": 3,
        },
    },
    "mismatched_resume": {
        "label": 0,
        "role": "Backend SDE",
        "company": "Amazon",
        "answers": [
            (True, 28, 0.86, 0),
            (True, 36, 0.82, 0),
            (True, 46, 0.78, 0),
            (True, 51, 0.75, 0),
            (False, 92, 0.32, 1),
            (True, 76, 0.73, 0),
        ],
        "evidence": {
            "codeforces_rating": 1080,
            "resume_claims": ("dsa", "fundamentals", "distributed_systems", "system_design"),
            "verified_skills": ("dsa", "fundamentals"),
            "project_tags": ("backend",),
            "project_count": 1,
            "github_repo_count": 1,
        },
    },
    "overconfident_guesser": {
        "label": 0,
        "role": "Backend SDE",
        "company": "Amazon",
        "answers": [
            (True, 56, 0.95, 1),
            (False, 58, 0.92, 1),
            (False, 82, 0.90, 2),
            (True, 88, 0.85, 1),
            (False, 117, 0.87, 2),
            (False, 114, 0.83, 2),
        ],
        "evidence": {
            "codeforces_rating": 920,
            "resume_claims": ("dsa", "fundamentals", "projects", "system_design"),
            "verified_skills": ("dsa",),
            "project_tags": (),
            "project_count": 0,
            "github_repo_count": 0,
        },
    },
    "fast_careful_same_accuracy": {
        "label": 1,
        "role": "Backend SDE",
        "company": "Amazon",
        "answers": [
            (True, 22, 0.82, 0),
            (True, 32, 0.79, 0),
            (True, 45, 0.76, 0),
            (False, 64, 0.41, 0),
            (True, 82, 0.72, 0),
            (False, 95, 0.36, 1),
        ],
        "evidence": {
            "codeforces_rating": 1410,
            "resume_claims": ("dsa", "projects"),
            "verified_skills": ("dsa",),
            "project_tags": ("projects", "backend"),
            "project_count": 2,
            "github_repo_count": 2,
        },
    },
    "slow_overconfident_same_accuracy": {
        "label": 0,
        "role": "Backend SDE",
        "company": "Amazon",
        "answers": [
            (True, 52, 0.98, 1),
            (True, 54, 0.91, 1),
            (True, 84, 0.88, 1),
            (False, 86, 0.80, 1),
            (True, 109, 0.85, 2),
            (False, 118, 0.79, 2),
        ],
        "evidence": {
            "codeforces_rating": 1410,
            "resume_claims": ("dsa", "projects"),
            "verified_skills": ("dsa",),
            "project_tags": ("projects", "backend"),
            "project_count": 2,
            "github_repo_count": 2,
        },
    },
    "balanced_growth": {
        "label": 1,
        "role": "Backend SDE",
        "company": "Google",
        "answers": [
            (True, 31, 0.74, 0),
            (True, 40, 0.71, 0),
            (False, 58, 0.51, 1),
            (True, 63, 0.67, 0),
            (False, 101, 0.46, 1),
            (True, 84, 0.69, 0),
        ],
        "evidence": {
            "codeforces_rating": 1320,
            "resume_claims": ("dsa", "fundamentals"),
            "verified_skills": ("dsa", "fundamentals"),
            "project_tags": ("backend",),
            "project_count": 2,
            "github_repo_count": 2,
        },
    },
    "low_signal_candidate": {
        "label": 0,
        "role": "Backend SDE",
        "company": "Amazon",
        "answers": [
            (False, 46, 0.62, 1),
            (True, 47, 0.68, 0),
            (False, 72, 0.61, 1),
            (True, 79, 0.66, 1),
            (False, 112, 0.58, 2),
            (False, 111, 0.57, 2),
        ],
        "evidence": {
            "codeforces_rating": 970,
            "resume_claims": ("dsa", "fundamentals"),
            "verified_skills": (),
            "project_tags": (),
            "project_count": 0,
            "github_repo_count": 0,
        },
    },
    "full_stack_beginner": {
        "label": 0,
        "role": "Full Stack Developer",
        "company": "Google",
        "answers": [
            (True, 42, 0.81, 1),
            (False, 55, 0.79, 1),
            (False, 79, 0.74, 2),
            (True, 84, 0.68, 1),
            (False, 112, 0.72, 2),
            (False, 116, 0.69, 2),
        ],
        "evidence": {
            "codeforces_rating": 930,
            "resume_claims": ("html", "css", "javascript", "react", "node_js"),
            "verified_skills": ("html", "css"),
            "project_tags": ("frontend",),
            "project_count": 1,
            "github_repo_count": 1,
        },
    },
    "full_stack_builder": {
        "label": 1,
        "role": "Full Stack Developer",
        "company": "Google",
        "answers": [
            (True, 24, 0.83, 0),
            (True, 30, 0.8, 0),
            (True, 45, 0.75, 0),
            (True, 52, 0.72, 0),
            (False, 96, 0.39, 1),
            (True, 78, 0.73, 0),
        ],
        "evidence": {
            "codeforces_rating": 1450,
            "resume_claims": ("html", "css", "javascript", "react", "node_js", "sql", "apis"),
            "verified_skills": ("javascript", "react", "apis"),
            "project_tags": ("projects", "backend", "frontend"),
            "project_count": 3,
            "github_repo_count": 4,
        },
    },
    "ml_beginner": {
        "label": 0,
        "role": "AI/ML Engineer",
        "company": "Amazon",
        "answers": [
            (True, 39, 0.8, 1),
            (False, 48, 0.78, 1),
            (False, 77, 0.74, 1),
            (True, 83, 0.69, 1),
            (False, 109, 0.73, 2),
            (False, 113, 0.7, 2),
        ],
        "evidence": {
            "codeforces_rating": 910,
            "resume_claims": ("python", "machine_learning", "statistics", "deep_learning"),
            "verified_skills": ("python",),
            "project_tags": ("data",),
            "project_count": 1,
            "github_repo_count": 1,
        },
    },
    "ml_builder": {
        "label": 1,
        "role": "AI/ML Engineer",
        "company": "Amazon",
        "answers": [
            (True, 27, 0.82, 0),
            (True, 34, 0.79, 0),
            (True, 49, 0.74, 0),
            (True, 57, 0.7, 0),
            (False, 98, 0.37, 1),
            (True, 82, 0.72, 0),
        ],
        "evidence": {
            "codeforces_rating": 1360,
            "resume_claims": ("python", "machine_learning", "statistics", "numpy", "pandas"),
            "verified_skills": ("python", "machine_learning", "statistics"),
            "project_tags": ("projects", "data", "deployment"),
            "project_count": 3,
            "github_repo_count": 3,
        },
    },
}


def _build_answer_events(answer_rows):
    events = []
    for blueprint, answer_row in zip(QUESTION_BLUEPRINTS, answer_rows, strict=True):
        correct, elapsed_seconds, confidence, answer_changes = answer_row
        events.append(
            AnswerEvent(
                question_id=blueprint["question_id"],
                stage_id=blueprint["stage_id"],
                difficulty_band=blueprint["difficulty_band"],
                skill_tag=blueprint["skill_tag"],
                correct=correct,
                elapsed_seconds=float(elapsed_seconds),
                confidence=float(confidence),
                answer_changes=int(answer_changes),
                max_time_seconds=float(blueprint["max_time_seconds"]),
            )
        )
    return tuple(events)


def make_session_variant(name: str) -> AssessmentSession:
    spec = VARIANTS[name]
    evidence = spec["evidence"]
    return AssessmentSession(
        session_id=f"session-{name}",
        user_id=f"user-{name}",
        target_role=spec["role"],
        target_company=spec["company"],
        stages=STAGES,
        answers=_build_answer_events(spec["answers"]),
        evidence=EvidenceProfile(
            codeforces_rating=evidence.get("codeforces_rating"),
            leetcode_solved=evidence.get("leetcode_solved"),
            resume_claims=tuple(evidence.get("resume_claims", ())),
            verified_skills=tuple(evidence.get("verified_skills", ())),
            project_tags=tuple(evidence.get("project_tags", ())),
            project_count=int(evidence.get("project_count", 0)),
            github_repo_count=int(evidence.get("github_repo_count", 0)),
        ),
    )


def make_demo_training_corpus() -> list[tuple[AssessmentSession, int]]:
    corpus = []
    for name, spec in VARIANTS.items():
        corpus.append((make_session_variant(name), int(spec["label"])))
    return corpus


def make_demo_training_examples() -> list[TrainingExample]:
    return [
        TrainingExample(session=session, readiness_label=label)
        for session, label in make_demo_training_corpus()
    ]


def _bounded_int(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, value))


def _bounded_float(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _mutate_answer_row(
    base_row: tuple[bool, int, float, int],
    max_time_seconds: float,
    label: int,
    rng: random.Random,
) -> tuple[bool, int, float, int]:
    correct, elapsed_seconds, confidence, answer_changes = base_row

    if rng.random() < 0.06:
        correct = not correct

    time_jitter = rng.randint(-12, 12)
    elapsed_seconds = _bounded_int(
        int(elapsed_seconds + time_jitter + (4 if label == 0 else -2)),
        8,
        int(max_time_seconds),
    )

    confidence_shift = rng.uniform(-0.08, 0.08)
    if label == 0 and not correct:
        confidence_shift += rng.uniform(0.02, 0.08)
    if label == 1 and correct:
        confidence_shift += rng.uniform(-0.02, 0.05)

    confidence = _bounded_float(confidence + confidence_shift, 0.05, 0.99)
    answer_changes = _bounded_int(
        answer_changes + rng.choice((-1, 0, 0, 1)),
        0,
        3,
    )

    return correct, elapsed_seconds, round(confidence, 2), answer_changes


def _mutate_evidence(evidence: dict, label: int, rng: random.Random) -> dict:
    mutated = dict(evidence)

    rating = int(mutated.get("codeforces_rating", 1100) or 1100)
    rating_shift = rng.randint(-90, 90) + (40 if label == 1 else -25)
    mutated["codeforces_rating"] = _bounded_int(rating + rating_shift, 800, 2200)

    project_count = int(mutated.get("project_count", 0))
    mutated["project_count"] = _bounded_int(
        project_count + rng.choice((-1, 0, 0, 1)),
        0,
        5,
    )

    github_repo_count = int(mutated.get("github_repo_count", 0))
    mutated["github_repo_count"] = _bounded_int(
        github_repo_count + rng.choice((-1, 0, 1)),
        0,
        8,
    )

    claims = list(mutated.get("resume_claims", ()))
    if label == 0 and rng.random() < 0.25 and "system_design" not in claims:
        claims.append("system_design")
    if label == 1 and rng.random() < 0.20 and "backend" not in claims:
        claims.append("backend")
    mutated["resume_claims"] = tuple(dict.fromkeys(claims))

    tags = list(mutated.get("project_tags", ()))
    if label == 1 and rng.random() < 0.30 and "api_design" not in tags:
        tags.append("api_design")
    mutated["project_tags"] = tuple(dict.fromkeys(tags))

    return mutated


def make_synthetic_training_corpus(
    samples_per_variant: int = 32,
    seed: int = 42,
) -> list[tuple[AssessmentSession, int]]:
    rng = random.Random(seed)
    synthetic_corpus: list[tuple[AssessmentSession, int]] = []

    for variant_name, spec in VARIANTS.items():
        base_answers = spec["answers"]
        label = int(spec["label"])

        for sample_index in range(samples_per_variant):
            answers = []
            for blueprint, base_row in zip(QUESTION_BLUEPRINTS, base_answers, strict=True):
                answers.append(
                    _mutate_answer_row(
                        base_row,
                        float(blueprint["max_time_seconds"]),
                        label,
                        rng,
                    )
                )

            evidence = _mutate_evidence(spec["evidence"], label, rng)
            session = AssessmentSession(
                session_id=f"session-{variant_name}-{seed}-{sample_index}",
                user_id=f"user-{variant_name}-{seed}-{sample_index}",
                target_role=spec["role"],
                target_company=spec["company"],
                stages=STAGES,
                answers=_build_answer_events(tuple(answers)),
                evidence=EvidenceProfile(
                    codeforces_rating=evidence.get("codeforces_rating"),
                    leetcode_solved=evidence.get("leetcode_solved"),
                    resume_claims=tuple(evidence.get("resume_claims", ())),
                    verified_skills=tuple(evidence.get("verified_skills", ())),
                    project_tags=tuple(evidence.get("project_tags", ())),
                    project_count=int(evidence.get("project_count", 0)),
                    github_repo_count=int(evidence.get("github_repo_count", 0)),
                ),
            )
            synthetic_corpus.append((session, label))

    return synthetic_corpus
