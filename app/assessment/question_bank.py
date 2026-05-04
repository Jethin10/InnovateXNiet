from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class AssessmentQuestion:
    question_id: str
    prompt: str
    stage_id: int
    difficulty_band: str
    skill_tag: str
    max_time_seconds: float
    answer_aliases: tuple[str, ...]


def _normalize_answer(value: str) -> str:
    lowered = value.strip().lower()
    lowered = re.sub(r"\s+", " ", lowered)
    return lowered.replace(" ", "")


class QuestionBank:
    """Backend-owned v1 question bank and answer-key evaluator."""

    def __init__(self, questions: tuple[AssessmentQuestion, ...]) -> None:
        self._questions = {question.question_id: question for question in questions}

    def get(self, question_id: str) -> AssessmentQuestion | None:
        return self._questions.get(question_id)

    def list_public(self) -> list[dict]:
        return [
            {
                "question_id": question.question_id,
                "prompt": question.prompt,
                "stage_id": question.stage_id,
                "difficulty_band": question.difficulty_band,
                "skill_tag": question.skill_tag,
                "max_time_seconds": question.max_time_seconds,
            }
            for question in self._questions.values()
        ]

    def list_question_ids(self) -> list[str]:
        return list(self._questions.keys())

    def list_public_by_ids(self, question_ids: list[str]) -> list[dict]:
        allowed = set(question_ids)
        return [
            question
            for question in self.list_public()
            if question["question_id"] in allowed
        ]

    def require(self, question_id: str) -> AssessmentQuestion:
        question = self.get(question_id)
        if question is None:
            raise KeyError(question_id)
        return question

    def is_correct(self, question_id: str, submitted_answer: str) -> bool:
        question = self.require(question_id)
        normalized = _normalize_answer(submitted_answer)
        return any(normalized == _normalize_answer(alias) for alias in question.answer_aliases)


DEFAULT_QUESTION_BANK = QuestionBank(
    questions=(
        AssessmentQuestion(
            question_id="be_easy_dsa_array_lookup",
            prompt="What is the time complexity of accessing an array element by index?",
            stage_id=1,
            difficulty_band="easy",
            skill_tag="dsa",
            max_time_seconds=60.0,
            answer_aliases=("O(1)", "constant time"),
        ),
        AssessmentQuestion(
            question_id="be_easy_fundamentals_http_status",
            prompt="Which HTTP status code represents a missing resource?",
            stage_id=1,
            difficulty_band="easy",
            skill_tag="fundamentals",
            max_time_seconds=60.0,
            answer_aliases=("404", "not found", "404 not found"),
        ),
        AssessmentQuestion(
            question_id="be_medium_db_index",
            prompt="Write a SQL statement or phrase that adds an index for user email lookups.",
            stage_id=2,
            difficulty_band="medium",
            skill_tag="fundamentals",
            max_time_seconds=90.0,
            answer_aliases=(
                "CREATE INDEX idx_users_email ON users(email)",
                "index on users.email",
                "add an index on email",
            ),
        ),
        AssessmentQuestion(
            question_id="be_medium_api_idempotency",
            prompt="What mechanism helps safely retry POST requests without duplicate side effects?",
            stage_id=2,
            difficulty_band="medium",
            skill_tag="projects",
            max_time_seconds=90.0,
            answer_aliases=("idempotency key", "idempotent request key"),
        ),
        AssessmentQuestion(
            question_id="be_hard_dsa_binary_search",
            prompt="What is the time complexity of binary search on a sorted array?",
            stage_id=3,
            difficulty_band="hard",
            skill_tag="dsa",
            max_time_seconds=120.0,
            answer_aliases=("O(log n)", "logarithmic time"),
        ),
        AssessmentQuestion(
            question_id="be_hard_fundamentals_transaction",
            prompt="Which ACID property guarantees all-or-nothing transaction behavior?",
            stage_id=3,
            difficulty_band="hard",
            skill_tag="fundamentals",
            max_time_seconds=120.0,
            answer_aliases=("atomicity", "atomic transaction"),
        ),
        AssessmentQuestion(
            question_id="fs_easy_html_semantic",
            prompt="Which HTML element is best for the main navigation links?",
            stage_id=1,
            difficulty_band="easy",
            skill_tag="html",
            max_time_seconds=60.0,
            answer_aliases=("nav", "<nav>", "navigation"),
        ),
        AssessmentQuestion(
            question_id="fs_medium_css_flex",
            prompt="Which CSS layout model is commonly used to align items in one dimension?",
            stage_id=2,
            difficulty_band="medium",
            skill_tag="css",
            max_time_seconds=90.0,
            answer_aliases=("flexbox", "display flex", "display:flex"),
        ),
        AssessmentQuestion(
            question_id="fs_hard_js_closure",
            prompt="What JavaScript concept allows an inner function to remember outer variables?",
            stage_id=3,
            difficulty_band="hard",
            skill_tag="javascript",
            max_time_seconds=120.0,
            answer_aliases=("closure", "closures"),
        ),
    )
)
