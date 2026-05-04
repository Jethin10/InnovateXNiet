from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CodingTestCase:
    name: str
    input: dict[str, Any]
    expected: Any


@dataclass(frozen=True)
class CodingProblem:
    problem_id: str
    title: str
    difficulty: str
    skill_tags: tuple[str, ...]
    statement: str
    function_name: str
    starter_code: str
    public_cases: tuple[CodingTestCase, ...]
    hidden_cases: tuple[CodingTestCase, ...]

    def public_payload(self) -> dict:
        return {
            "problem_id": self.problem_id,
            "title": self.title,
            "difficulty": self.difficulty,
            "skill_tags": list(self.skill_tags),
            "statement": self.statement,
            "function_name": self.function_name,
            "starter_code": self.starter_code,
            "examples": [
                {"input": case.input, "expected": case.expected}
                for case in self.public_cases
            ],
        }


class CodingProblemBank:
    def __init__(self, problems: tuple[CodingProblem, ...]) -> None:
        self._problems = {problem.problem_id: problem for problem in problems}

    def list_public(self) -> list[dict]:
        return [problem.public_payload() for problem in self._problems.values()]

    def require(self, problem_id: str) -> CodingProblem:
        problem = self._problems.get(problem_id)
        if problem is None:
            raise KeyError(problem_id)
        return problem


DEFAULT_CODING_PROBLEM_BANK = CodingProblemBank(
    problems=(
        CodingProblem(
            problem_id="two_sum_indices",
            title="Two Sum Indices",
            difficulty="easy",
            skill_tags=("arrays", "hash-map"),
            statement=(
                "Return the indices of two numbers in nums that add up to target. "
                "Exactly one valid pair exists, and the same element cannot be used twice."
            ),
            function_name="solve",
            starter_code="def solve(nums, target):\n    return []\n",
            public_cases=(
                CodingTestCase("basic pair", {"nums": [2, 7, 11, 15], "target": 9}, [0, 1]),
            ),
            hidden_cases=(
                CodingTestCase("uses later complement", {"nums": [3, 2, 4], "target": 6}, [1, 2]),
                CodingTestCase("handles duplicate values", {"nums": [3, 3], "target": 6}, [0, 1]),
            ),
        ),
        CodingProblem(
            problem_id="valid_parentheses",
            title="Valid Parentheses",
            difficulty="easy",
            skill_tags=("stack", "strings"),
            statement="Return true when every bracket in s is closed by the correct type in the correct order.",
            function_name="solve",
            starter_code="def solve(s):\n    return False\n",
            public_cases=(
                CodingTestCase("balanced mixed brackets", {"s": "()[]{}"}, True),
            ),
            hidden_cases=(
                CodingTestCase("wrong order", {"s": "([)]"}, False),
                CodingTestCase("nested valid", {"s": "{[()]}"}, True),
            ),
        ),
        CodingProblem(
            problem_id="merge_intervals",
            title="Merge Intervals",
            difficulty="medium",
            skill_tags=("arrays", "sorting"),
            statement="Merge all overlapping intervals and return them sorted by start time.",
            function_name="solve",
            starter_code="def solve(intervals):\n    return intervals\n",
            public_cases=(
                CodingTestCase("overlapping middle", {"intervals": [[1, 3], [2, 6], [8, 10]]}, [[1, 6], [8, 10]]),
            ),
            hidden_cases=(
                CodingTestCase("touching intervals", {"intervals": [[1, 4], [4, 5]]}, [[1, 5]]),
                CodingTestCase("already separate", {"intervals": [[1, 2], [3, 4]]}, [[1, 2], [3, 4]]),
            ),
        ),
        CodingProblem(
            problem_id="longest_unique_substring",
            title="Longest Unique Substring",
            difficulty="medium",
            skill_tags=("sliding-window", "strings"),
            statement="Return the length of the longest substring of s without repeated characters.",
            function_name="solve",
            starter_code="def solve(s):\n    return 0\n",
            public_cases=(
                CodingTestCase("repeating window", {"s": "abcabcbb"}, 3),
            ),
            hidden_cases=(
                CodingTestCase("all same", {"s": "bbbbb"}, 1),
                CodingTestCase("empty string", {"s": ""}, 0),
            ),
        ),
        CodingProblem(
            problem_id="accessible_nav_labels",
            title="Accessible Nav Labels",
            difficulty="easy",
            skill_tags=("accessibility", "frontend", "html"),
            statement=(
                "A frontend audit found unlabeled navigation links. Given nav_items with text and aria_label, "
                "return only the items that are accessible: visible text or aria_label must be present after trimming."
            ),
            function_name="solve",
            starter_code="def solve(nav_items):\n    return []\n",
            public_cases=(
                CodingTestCase(
                    "filters empty labels",
                    {
                        "nav_items": [
                            {"text": "Home", "aria_label": ""},
                            {"text": " ", "aria_label": "Open profile"},
                            {"text": "", "aria_label": ""},
                        ]
                    },
                    [
                        {"text": "Home", "aria_label": ""},
                        {"text": " ", "aria_label": "Open profile"},
                    ],
                ),
            ),
            hidden_cases=(
                CodingTestCase(
                    "keeps explicit labels",
                    {"nav_items": [{"text": "", "aria_label": "Settings"}, {"text": "Docs", "aria_label": ""}]},
                    [{"text": "", "aria_label": "Settings"}, {"text": "Docs", "aria_label": ""}],
                ),
                CodingTestCase("empty nav", {"nav_items": []}, []),
            ),
        ),
        CodingProblem(
            problem_id="frontend_performance_budget",
            title="Frontend Performance Budget",
            difficulty="medium",
            skill_tags=("performance", "frontend", "analytics"),
            statement=(
                "A frontend dashboard tracks route load times in milliseconds. Return a dictionary with pass and fail "
                "counts where a route passes when load_ms is less than or equal to budget_ms."
            ),
            function_name="solve",
            starter_code="def solve(routes, budget_ms):\n    return {\"pass\": 0, \"fail\": 0}\n",
            public_cases=(
                CodingTestCase(
                    "mixed routes",
                    {"routes": [{"load_ms": 1200}, {"load_ms": 2400}, {"load_ms": 900}], "budget_ms": 1500},
                    {"pass": 2, "fail": 1},
                ),
            ),
            hidden_cases=(
                CodingTestCase(
                    "boundary passes",
                    {"routes": [{"load_ms": 1500}, {"load_ms": 1501}], "budget_ms": 1500},
                    {"pass": 1, "fail": 1},
                ),
                CodingTestCase("empty routes", {"routes": [], "budget_ms": 1000}, {"pass": 0, "fail": 0}),
            ),
        ),
        CodingProblem(
            problem_id="normalize_resume_skills",
            title="Normalize Resume Skills",
            difficulty="easy",
            skill_tags=("resume", "strings", "data-cleaning"),
            statement=(
                "Build the resume-analysis helper used before matching. Return a sorted list of unique skills, "
                "lowercased, trimmed, and with spaces or hyphens converted to underscores."
            ),
            function_name="solve",
            starter_code="def solve(skills):\n    return []\n",
            public_cases=(
                CodingTestCase(
                    "mixed casing and separators",
                    {"skills": [" React ", "REST API", "rest-api", "SQL"]},
                    ["react", "rest_api", "sql"],
                ),
            ),
            hidden_cases=(
                CodingTestCase(
                    "deduplicates normalized values",
                    {"skills": ["Data Structures", "data-structures", " Python", "python "]},
                    ["data_structures", "python"],
                ),
                CodingTestCase("handles empty input", {"skills": []}, []),
            ),
        ),
        CodingProblem(
            problem_id="job_match_score",
            title="Job Match Score",
            difficulty="medium",
            skill_tags=("ats", "job-matching", "sets"),
            statement=(
                "Compute the candidate's job match score. Return the percentage of required skills that are present "
                "in candidate_skills, rounded to the nearest integer. Matching is case-insensitive."
            ),
            function_name="solve",
            starter_code="def solve(candidate_skills, required_skills):\n    return 0\n",
            public_cases=(
                CodingTestCase(
                    "partial backend match",
                    {"candidate_skills": ["Python", "SQL", "React"], "required_skills": ["python", "sql", "apis", "system design"]},
                    50,
                ),
            ),
            hidden_cases=(
                CodingTestCase(
                    "full match with case differences",
                    {"candidate_skills": ["REST API", "Testing"], "required_skills": ["rest api", "testing"]},
                    100,
                ),
                CodingTestCase(
                    "no required skills",
                    {"candidate_skills": ["python"], "required_skills": []},
                    0,
                ),
            ),
        ),
        CodingProblem(
            problem_id="api_idempotency_filter",
            title="API Idempotency Filter",
            difficulty="medium",
            skill_tags=("apis", "backend", "idempotency"),
            statement=(
                "A backend receives payment or assessment requests with idempotency keys. Return only the first "
                "request for each key, preserving the original order."
            ),
            function_name="solve",
            starter_code="def solve(requests):\n    return []\n",
            public_cases=(
                CodingTestCase(
                    "drops duplicate retry",
                    {"requests": [{"key": "a", "value": 10}, {"key": "a", "value": 10}, {"key": "b", "value": 20}]},
                    [{"key": "a", "value": 10}, {"key": "b", "value": 20}],
                ),
            ),
            hidden_cases=(
                CodingTestCase(
                    "keeps first different payload",
                    {"requests": [{"key": "x", "value": 1}, {"key": "y", "value": 2}, {"key": "x", "value": 9}]},
                    [{"key": "x", "value": 1}, {"key": "y", "value": 2}],
                ),
                CodingTestCase("empty request log", {"requests": []}, []),
            ),
        ),
        CodingProblem(
            problem_id="placement_risk_buckets",
            title="Placement Risk Buckets",
            difficulty="medium",
            skill_tags=("analytics", "sql", "dashboards"),
            statement=(
                "Power the placement analytics dashboard. Given student readiness scores from 0 to 100, return a "
                "dictionary with low, medium, and high risk counts. Scores below 50 are high risk, 50-74 are medium, "
                "and 75 or above are low."
            ),
            function_name="solve",
            starter_code="def solve(scores):\n    return {\"low\": 0, \"medium\": 0, \"high\": 0}\n",
            public_cases=(
                CodingTestCase("mixed cohort", {"scores": [92, 74, 49, 50, 20]}, {"low": 1, "medium": 2, "high": 2}),
            ),
            hidden_cases=(
                CodingTestCase("all ready", {"scores": [75, 88, 100]}, {"low": 3, "medium": 0, "high": 0}),
                CodingTestCase("empty cohort", {"scores": []}, {"low": 0, "medium": 0, "high": 0}),
            ),
        ),
    )
)
