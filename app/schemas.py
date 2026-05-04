from __future__ import annotations

from pydantic import BaseModel, Field

from trust_ml.schemas import RoadmapGraph, TrustScoreCard


class CreateStudentRequest(BaseModel):
    full_name: str
    email: str | None = None
    target_role: str
    target_company: str | None = None


class StudentResponse(BaseModel):
    student_id: int
    full_name: str
    email: str | None = None
    target_role: str
    target_company: str | None = None


class RegisterStudentRequest(BaseModel):
    full_name: str
    email: str
    password: str = Field(min_length=8)
    target_role: str
    target_company: str | None = None


class RegisterStaffRequest(BaseModel):
    full_name: str
    email: str
    password: str = Field(min_length=8)
    role: str
    registration_key: str


class LoginRequest(BaseModel):
    email: str
    password: str


class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: str
    role: str
    student_id: int | None = None


class StaffResponse(BaseModel):
    user_id: int
    full_name: str
    email: str | None = None
    role: str


class IntakeRequest(BaseModel):
    resume_text: str | None = None
    manual_skills: list[str] = Field(default_factory=list)
    preferred_resource_style: str | None = None
    consent_public: bool = False


class ResumeAnalysisRequest(BaseModel):
    resume_text: str
    filename: str | None = None


class ResumeAnalysisResponse(BaseModel):
    inferred_target_role: str
    claimed_skills: list[str]
    project_count: int
    unsupported_claims: list[str]
    risk_flags: list[str]


class AtsGuidanceRequest(BaseModel):
    resume_text: str
    target_role: str
    target_company: str | None = None


class AtsGuidanceResponse(BaseModel):
    ats_score: int
    matched_keywords: list[str]
    missing_keywords: list[str]
    recommendations: list[str]


class CodeforcesEvidenceRequest(BaseModel):
    handle: str


class GitHubEvidenceRequest(BaseModel):
    username: str = ""
    access_token: str | None = None
    include_private: bool = False


class CodeforcesEvidenceResponse(BaseModel):
    source: str
    handle: str
    verified: bool
    rating: int | None = None
    max_rating: int | None = None
    rank: str | None = None


class GitHubEvidenceResponse(BaseModel):
    source: str
    username: str
    verified: bool
    repo_count: int
    followers: int | None = None
    original_repo_count: int = 0
    private_repo_count: int = 0
    fork_repo_count: int = 0
    total_stars: int = 0
    total_forks: int = 0
    total_open_issues: int = 0
    total_commits_analyzed: int = 0
    authored_commit_count: int = 0
    recent_commit_count: int = 0
    language_breakdown: dict[str, int] = Field(default_factory=dict)
    top_languages: list[str] = Field(default_factory=list)
    contribution_summary: list[str] = Field(default_factory=list)
    repositories: list["GitHubRepositoryEvidenceResponse"] = Field(default_factory=list)
    recent_commits: list["GitHubCommitEvidenceResponse"] = Field(default_factory=list)
    project_recommendations: list["GitHubProjectRecommendationResponse"] = Field(default_factory=list)
    access_scope: str = "public"
    rate_limit_remaining: int | None = None


class GitHubRepositoryEvidenceResponse(BaseModel):
    name: str
    full_name: str
    url: str
    description: str | None = None
    primary_language: str | None = None
    private: bool = False
    fork: bool = False
    stars: int = 0
    forks: int = 0
    open_issues: int = 0
    pushed_at: str | None = None
    topics: list[str] = Field(default_factory=list)
    languages: dict[str, int] = Field(default_factory=dict)
    contributor_count: int = 0
    commit_count_analyzed: int = 0
    authored_commit_count: int = 0


class GitHubCommitEvidenceResponse(BaseModel):
    repo: str
    sha: str
    message: str
    authored_at: str | None = None
    author_login: str | None = None
    url: str | None = None


class GitHubProjectRecommendationResponse(BaseModel):
    title: str
    rationale: str
    suggested_scope: list[str]
    evidence_repo_names: list[str]


class EvidenceSummaryResponse(BaseModel):
    codeforces: dict | None = None
    github: dict | None = None
    coding_harness: dict | None = None


class CodingExampleResponse(BaseModel):
    input: dict
    expected: object


class CodingProblemResponse(BaseModel):
    problem_id: str
    title: str
    difficulty: str
    skill_tags: list[str]
    statement: str
    function_name: str
    starter_code: str
    examples: list[CodingExampleResponse]


class CodingSubmissionRequest(BaseModel):
    problem_id: str
    language: str = "python"
    code: str
    proctoring_checks: dict[str, bool] = Field(default_factory=dict)
    proctoring_events: list["ProctoringEventInput"] = Field(default_factory=list)


class CodingTestResultResponse(BaseModel):
    name: str
    passed: bool
    input: dict | None = None
    expected: object | None = None
    actual: object | None = None
    error: str | None = None


class CodingSubmissionResponse(BaseModel):
    submission_id: str
    problem_id: str
    passed: bool
    score: int
    public_results: list[CodingTestResultResponse]
    hidden_passed_count: int
    hidden_total_count: int
    integrity_flags: list[str]
    skill_tags: list[str]


class TrustStampVerificationResponse(BaseModel):
    valid: bool


class ModelMetadataResponse(BaseModel):
    model_loaded: bool
    training_summary: dict
    limitations: list[str]


class VerificationStageResponse(BaseModel):
    stage_id: int
    difficulty: str
    time_limit_minutes: int
    focus_skills: list[str]
    objective: str
    pass_rule: str


class VerificationPlanResponse(BaseModel):
    target_role: str
    claimed_skills: list[str]
    stages: list[VerificationStageResponse]


class TrustStampResponse(BaseModel):
    slug: str
    consent_public: bool


class IntakeResponse(BaseModel):
    student_id: int
    inferred_target_role: str
    claimed_skills: list[str]
    assessment_plan: VerificationPlanResponse
    trust_stamp: TrustStampResponse


class StoredAssessmentPlanResponse(BaseModel):
    student_id: int
    target_role: str
    claimed_skills: list[str]
    stages: list[VerificationStageResponse]


class AssessmentAnswerInput(BaseModel):
    question_id: str
    stage_id: int
    difficulty_band: str
    skill_tag: str
    submitted_answer: str | None = None
    correct: bool | None = None
    elapsed_seconds: float
    confidence: float
    answer_changes: int = 0
    max_time_seconds: float = 60.0


class AssessmentEvidenceInput(BaseModel):
    codeforces_rating: int | None = None
    leetcode_solved: int | None = None
    resume_claims: list[str] = Field(default_factory=list)
    verified_skills: list[str] = Field(default_factory=list)
    project_tags: list[str] = Field(default_factory=list)
    project_count: int = 0
    github_repo_count: int = 0


class AssessmentCreateRequest(BaseModel):
    attempt_id: int | None = None
    answers: list[AssessmentAnswerInput]
    evidence: AssessmentEvidenceInput


class AssessmentQuestionResponse(BaseModel):
    question_id: str
    prompt: str
    stage_id: int
    difficulty_band: str
    skill_tag: str
    max_time_seconds: float


class AssessmentAttemptStartResponse(BaseModel):
    attempt_id: int
    status: str
    expires_at: str
    questions: list[AssessmentQuestionResponse]


class AssessmentResponse(BaseModel):
    assessment_id: int
    status: str


class RoadmapNodeResponse(BaseModel):
    node_id: str
    title: str
    skill_track: str
    summary: str
    prerequisites: list[str]
    status: str
    recommended: bool
    assignment: str
    proof_requirement: str


class RoadmapResponse(BaseModel):
    target_role: str
    current_level: str
    summary: str
    nodes: list[RoadmapNodeResponse]

    @classmethod
    def from_graph(cls, graph: RoadmapGraph) -> "RoadmapResponse":
        return cls(
            target_role=graph.target_role,
            current_level=graph.current_level,
            summary=graph.summary,
            nodes=[
                RoadmapNodeResponse(
                    node_id=node.node_id,
                    title=node.title,
                    skill_track=node.skill_track,
                    summary=node.summary,
                    prerequisites=list(node.prerequisites),
                    status=node.status,
                    recommended=node.recommended,
                    assignment=node.assignment,
                    proof_requirement=node.proof_requirement,
                )
                for node in graph.nodes
            ],
        )


class NodeCompletionRequest(BaseModel):
    proof_summary: str


class TrustScoreResponse(BaseModel):
    overall_readiness: float
    model_probability: float
    raw_accuracy: float
    confidence_reliability: float
    evidence_alignment: float
    calibration_gap: float
    bluff_index: float
    readiness_band: str
    risk_band: str
    skill_scores: dict[str, float]
    explanations: list[str]
    top_positive_signals: list[str]
    top_risk_signals: list[str]

    @classmethod
    def from_scorecard(cls, scorecard: TrustScoreCard) -> "TrustScoreResponse":
        return cls(
            overall_readiness=scorecard.overall_readiness,
            model_probability=scorecard.model_probability,
            raw_accuracy=scorecard.raw_accuracy,
            confidence_reliability=scorecard.confidence_reliability,
            evidence_alignment=scorecard.evidence_alignment,
            calibration_gap=scorecard.calibration_gap,
            bluff_index=scorecard.bluff_index,
            readiness_band=scorecard.readiness_band,
            risk_band=scorecard.risk_band,
            skill_scores=scorecard.skill_scores,
            explanations=list(scorecard.explanations),
            top_positive_signals=list(scorecard.top_positive_signals),
            top_risk_signals=list(scorecard.top_risk_signals),
        )


class ScoreResponse(BaseModel):
    trust_score: TrustScoreResponse
    roadmap: RoadmapResponse


class ScoreExplanationResponse(BaseModel):
    score: float
    explanation: str
    factors: list[str]
    improvement_tips: list[str]


class ResumeUploadResponse(BaseModel):
    filename: str
    text: str
    character_count: int
    parse_status: str


class ProctoringEventInput(BaseModel):
    event_type: str
    count: int = 1
    severity: float = Field(default=0.5, ge=0.0, le=1.0)


class ProctoringFrameAnalysisRequest(BaseModel):
    image_data_url: str


class ProctoringFrameAnalysisResponse(BaseModel):
    analyzed: bool
    model: str
    risk_score: float
    flags: list[str]
    reason: str


class AiResumeAnalyzeRequest(BaseModel):
    resume_text: str
    target_role: str | None = None
    target_company: str | None = None
    filename: str | None = None


class AiResumeAnalyzeResponse(BaseModel):
    skills: list[str]
    experience_level: str
    suggested_roles: list[str]
    selected_role: str
    ats: ScoreExplanationResponse
    skill_match_percent: float
    model_readiness_score: float
    model_version: str
    model_factors: list[str]
    missing_keywords: list[str]
    resume_suggestions: list[str]


class AdaptiveTestGenerateRequest(BaseModel):
    skills: list[str] = Field(default_factory=list)
    selected_role: str
    experience_level: str = "Beginner"


class AdaptiveTestQuestionResponse(BaseModel):
    question_id: str
    prompt: str
    question_type: str
    difficulty_band: str
    skill_tag: str
    max_time_seconds: float


class AdaptiveTestGenerateResponse(BaseModel):
    selected_role: str
    focus_skills: list[str]
    questions: list[AdaptiveTestQuestionResponse]
    adaptation_summary: str


class AdaptiveAnswerInput(BaseModel):
    question_id: str
    submitted_answer: str
    elapsed_seconds: float = 30.0
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)
    answer_changes: int = 0


class AdaptiveTestEvaluationRequest(BaseModel):
    selected_role: str = ""
    skills: list[str] = Field(default_factory=list)
    answers: list[AdaptiveAnswerInput]
    proctoring_events: list[ProctoringEventInput] = Field(default_factory=list)


class AdaptiveTestEvaluationResponse(BaseModel):
    test: ScoreExplanationResponse
    trust: ScoreExplanationResponse
    proctoring_risk_score: float
    skill_breakdown: dict[str, float]
    weak_areas: list[str]


class FinalEmployabilityReportRequest(BaseModel):
    resume_text: str = ""
    selected_role: str = ""
    skills: list[str] = Field(default_factory=list)
    ats_score: float = 0.0
    test_score: float = 0.0
    trust_score: float = 0.0
    skill_breakdown: dict[str, float] = Field(default_factory=dict)
    proctoring_events: list[ProctoringEventInput] = Field(default_factory=list)


class RoadmapPlanItemResponse(BaseModel):
    title: str
    skill: str
    project: str
    resource: str
    practice: str


class FinalEmployabilityReportResponse(BaseModel):
    ats: ScoreExplanationResponse
    test: ScoreExplanationResponse
    trust: ScoreExplanationResponse
    role_fit: ScoreExplanationResponse
    extracted_skills: list[str]
    skill_gaps: list[str]
    roadmap: list[RoadmapPlanItemResponse]


class RecommendedJobInput(BaseModel):
    title: str
    match_score: float = 0.0
    required_skills: list[str] = Field(default_factory=list)


class SkillRoadmapGenerateRequest(BaseModel):
    extracted_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    ats_score: float = 0.0
    test_score: float = 0.0
    weak_areas: list[str] = Field(default_factory=list)
    target_role: str
    recommended_jobs: list[RecommendedJobInput] = Field(default_factory=list)
    skill_breakdown: dict[str, float] = Field(default_factory=dict)
    experience_level: str = "Intermediate"


class SkillRoadmapTaskResponse(BaseModel):
    task_id: str
    day: int
    title: str
    action: str
    status: str = "not_started"


class SkillRoadmapJobImpactResponse(BaseModel):
    impacted_job_count: int
    estimated_match_lift_percent: int
    jobs: list[str]
    summary: str


class SkillRoadmapHarnessQuestionResponse(BaseModel):
    problem_id: str
    title: str
    difficulty: str
    reason: str


class SkillRoadmapItemResponse(BaseModel):
    skill: str
    priority: str
    duration: str
    concepts: list[str]
    practice_tasks: list[str]
    steps: list[str]
    project: str
    resources: list[str]
    resource_queries: list[str] = Field(default_factory=list)
    harness_questions: list[SkillRoadmapHarnessQuestionResponse] = Field(default_factory=list)
    daily_tasks: list[SkillRoadmapTaskResponse]
    reason: str
    job_impact: SkillRoadmapJobImpactResponse
    progress_percent: float = 0.0


class SkillRoadmapResponse(BaseModel):
    target_role: str
    skill_gaps: list[str]
    roadmap: list[SkillRoadmapItemResponse]
    overall_progress_percent: float = 0.0
    badges: list[str] = Field(default_factory=list)
    streak_days: int = 0


class SkillRoadmapProgressUpdateRequest(BaseModel):
    task_id: str
    status: str = "completed"
    proof_summary: str | None = None


class SkillRoadmapProgressResponse(BaseModel):
    completed_tasks: int
    total_tasks: int
    progress_percent: float
    badges: list[str] = Field(default_factory=list)
    streak_days: int = 0


class JobListingResponse(BaseModel):
    job_id: str
    title: str
    company: str
    location: str
    description: str
    apply_url: str | None = None
    remote: bool = False
    source: str = "fallback"
    required_skills: list[str] = Field(default_factory=list)


class JobsFetchResponse(BaseModel):
    query: str
    location: str
    source: str
    jobs: list[JobListingResponse]


class JobMatchingProfileInput(BaseModel):
    skills: list[str] = Field(default_factory=list)
    resume_text: str = ""
    ats_score: float = 0.0
    test_score: float = 0.0
    trust_score: float = 0.0
    selected_role: str | None = None


class JobMatchRequest(JobMatchingProfileInput):
    jobs: list[JobListingResponse] = Field(default_factory=list)
    location: str = ""
    remote: bool | None = None
    min_match_score: float = 0.0
    limit: int = 8


class MatchedJobResponse(JobListingResponse):
    skill_match_percent: float
    match_score: float
    explanation: str
    matched_skills: list[str]
    missing_skills: list[str]
    semantic_similarity: float = 0.0


class JobMatchResponse(BaseModel):
    source: str
    profile_role: str
    filters: dict[str, object]
    jobs: list[MatchedJobResponse]


class InstitutionCreateRequest(BaseModel):
    name: str


class InstitutionResponse(BaseModel):
    institution_id: int
    name: str


class CohortCreateRequest(BaseModel):
    institution_id: int
    name: str


class CohortResponse(BaseModel):
    cohort_id: int
    institution_id: int
    name: str


class AddCohortMemberRequest(BaseModel):
    student_id: int


class CohortAnalyticsResponse(BaseModel):
    cohort_id: int
    cohort_name: str
    total_students: int
    average_trust_score: float
    average_bluff_index: float
    risk_buckets: dict[str, int]
    skill_gap_heatmap: dict[str, float]
    flagged_students: list[str]
