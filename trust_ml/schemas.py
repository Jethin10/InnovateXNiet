from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class QuestionStage:
    stage_id: int
    name: str
    difficulty_band: str
    time_limit_seconds: float
    skill_tag: str


@dataclass(frozen=True)
class AnswerEvent:
    question_id: str
    stage_id: int
    difficulty_band: str
    skill_tag: str
    correct: bool
    elapsed_seconds: float
    confidence: float
    answer_changes: int = 0
    max_time_seconds: float = 60.0


@dataclass(frozen=True)
class EvidenceProfile:
    codeforces_rating: int | None = None
    leetcode_solved: int | None = None
    resume_claims: tuple[str, ...] = ()
    verified_skills: tuple[str, ...] = ()
    project_tags: tuple[str, ...] = ()
    project_count: int = 0
    github_repo_count: int = 0


@dataclass(frozen=True)
class AssessmentSession:
    session_id: str
    user_id: str
    target_role: str
    target_company: str
    stages: tuple[QuestionStage, ...]
    answers: tuple[AnswerEvent, ...]
    evidence: EvidenceProfile


@dataclass(frozen=True)
class TrainingExample:
    session: AssessmentSession
    readiness_label: int


@dataclass(frozen=True)
class FeatureVectorExample:
    features: dict[str, float]
    readiness_label: int


@dataclass(frozen=True)
class ResumeProfile:
    inferred_target_role: str
    claimed_skills: tuple[str, ...]
    source: str


@dataclass(frozen=True)
class VerificationStagePlan:
    stage_id: int
    difficulty: str
    time_limit_minutes: int
    focus_skills: tuple[str, ...]
    objective: str
    pass_rule: str


@dataclass(frozen=True)
class VerificationPlan:
    target_role: str
    claimed_skills: tuple[str, ...]
    stages: tuple[VerificationStagePlan, ...]


@dataclass(frozen=True)
class RoadmapResource:
    title: str
    url: str
    kind: str


@dataclass(frozen=True)
class RoadmapNode:
    node_id: str
    title: str
    skill_track: str
    summary: str
    prerequisites: tuple[str, ...]
    resources: tuple[RoadmapResource, ...]
    assignment: str
    proof_requirement: str
    status: str
    recommended: bool


@dataclass(frozen=True)
class RoadmapGraph:
    target_role: str
    current_level: str
    nodes: tuple[RoadmapNode, ...]
    summary: str


@dataclass(frozen=True)
class TrustScoreCard:
    overall_readiness: float
    model_probability: float
    raw_accuracy: float
    skill_scores: dict[str, float]
    confidence_reliability: float
    evidence_alignment: float
    calibration_gap: float
    bluff_index: float
    readiness_band: str = "emerging"
    risk_band: str = "medium"
    feature_snapshot: dict[str, float] = field(default_factory=dict)
    explanations: tuple[str, ...] = ()
    top_positive_signals: tuple[str, ...] = ()
    top_risk_signals: tuple[str, ...] = ()


@dataclass(frozen=True)
class RoadmapPlan:
    title: str
    target_role: str
    target_company: str
    summary: str
    priority_gaps: tuple[str, ...]
    action_items: tuple[str, ...]
    ats_keywords: tuple[str, ...]
