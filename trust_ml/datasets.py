from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DatasetSource:
    name: str
    url: str
    category: str
    usage: str
    official: bool
    notes: str


class DatasetRegistry:
    """Registry of sources chosen for the trust model prototype."""

    @staticmethod
    def default() -> tuple[DatasetSource, ...]:
        return (
            DatasetSource(
                name="O*NET Database",
                url="https://www.onetcenter.org/database.html",
                category="occupation-taxonomy",
                usage="Role-skill mapping and roadmap priorities.",
                official=True,
                notes="Primary source for technology skills, tasks, and work activities.",
            ),
            DatasetSource(
                name="BLS Skills Data",
                url="https://www.bls.gov/emp/data/skills-data.htm",
                category="occupation-skills",
                usage="Role weighting and explainable skill importance.",
                official=True,
                notes="Derived from O*NET and useful for weighting placement roadmaps.",
            ),
            DatasetSource(
                name="Codeforces API",
                url="https://codeforces.com/apiHelp/methods?locale=en&mobile=false",
                category="coding-profile",
                usage="Live external evidence for contest history and rating.",
                official=True,
                notes="Chosen as the first hard integration because it has a public API.",
            ),
            DatasetSource(
                name="EdNet",
                url="https://github.com/riiid/ednet",
                category="student-interactions",
                usage="Behavior feature design for answer timing and uncertainty.",
                official=True,
                notes="Useful for shaping interaction-level trust features.",
            ),
            DatasetSource(
                name="FoundationalASSIST",
                url="https://huggingface.co/datasets/ASSISTments/FoundationalASSIST",
                category="student-interactions",
                usage="Behavior feature design for hint, response, and mastery signals.",
                official=True,
                notes="Published by ASSISTments and useful for educational modeling ideas.",
            ),
            DatasetSource(
                name="UCI Student Performance",
                url="https://archive.ics.uci.edu/dataset/320/student%2Bperformance",
                category="auxiliary-readiness",
                usage="Auxiliary benchmark for readiness-style experimentation only.",
                official=True,
                notes="Not treated as ground truth for placement trust.",
            ),
            DatasetSource(
                name="LeetCode",
                url="https://leetcode.com/",
                category="coding-profile",
                usage="Optional manual evidence in v1.",
                official=False,
                notes="No official public API was locked during planning, so it is not a hard dependency.",
            ),
        )
