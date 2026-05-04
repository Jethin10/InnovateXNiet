from __future__ import annotations

from fastapi import APIRouter, Depends, File, Request, UploadFile, status
from sqlalchemy.orm import Session

from app.core.auth import (
    ActorContext,
    get_actor_context,
    require_staff_access,
    require_student_access,
)
from app.repositories.student_repository import StudentRepository
from app.schemas import (
    AddCohortMemberRequest,
    AdaptiveTestEvaluationRequest,
    AdaptiveTestEvaluationResponse,
    AdaptiveTestGenerateRequest,
    AdaptiveTestGenerateResponse,
    AiResumeAnalyzeRequest,
    AiResumeAnalyzeResponse,
    AssessmentCreateRequest,
    AssessmentAttemptStartResponse,
    AssessmentQuestionResponse,
    AssessmentResponse,
    AuthTokenResponse,
    AtsGuidanceRequest,
    AtsGuidanceResponse,
    CodingProblemResponse,
    CodingSubmissionRequest,
    CodingSubmissionResponse,
    CohortAnalyticsResponse,
    CohortCreateRequest,
    CohortResponse,
    CreateStudentRequest,
    IntakeRequest,
    IntakeResponse,
    InstitutionCreateRequest,
    InstitutionResponse,
    LoginRequest,
    NodeCompletionRequest,
    ProctoringFrameAnalysisRequest,
    ProctoringFrameAnalysisResponse,
    RegisterStaffRequest,
    RegisterStudentRequest,
    RoadmapResponse,
    SkillRoadmapGenerateRequest,
    SkillRoadmapProgressResponse,
    SkillRoadmapProgressUpdateRequest,
    SkillRoadmapResponse,
    CodeforcesEvidenceRequest,
    CodeforcesEvidenceResponse,
    EvidenceSummaryResponse,
    FinalEmployabilityReportRequest,
    FinalEmployabilityReportResponse,
    GitHubEvidenceRequest,
    GitHubEvidenceResponse,
    JobMatchRequest,
    JobMatchResponse,
    JobsFetchResponse,
    ResumeAnalysisRequest,
    ResumeAnalysisResponse,
    ResumeUploadResponse,
    ModelMetadataResponse,
    ScoreResponse,
    StoredAssessmentPlanResponse,
    StudentResponse,
    StaffResponse,
    TrustStampVerificationResponse,
)
from app.services.ats_service import AtsGuidanceService
from app.services.coding_service import CodingHarnessService
from app.services.employability_pipeline_service import EmployabilityPipelineService
from app.services.evidence_service import EvidenceService
from app.services.auth_service import AuthService
from app.assessment.question_bank import DEFAULT_QUESTION_BANK
from app.services.intake_service import IntakeService
from app.services.institution_service import InstitutionService
from app.services.model_metadata_service import ModelMetadataService
from app.services.roadmap_service import RoadmapService
from app.services.resume_analysis_service import ResumeAnalysisService
from app.services.resume_parser_service import ResumeParserService
from app.services.scoring_service import ScoringService
from app.services.skill_gap_roadmap_service import SkillGapRoadmapService
from app.services.pipeline_resume_state_service import PipelineResumeStateService
from app.services.proctoring_service import ProctoringVisionService
from app.services.trust_stamp_service import TrustStampService
from app.services.job_matching_service import JobMatchingService


router = APIRouter()


def get_db_session(request: Request) -> Session:
    session_factory = request.app.state.session_factory
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


@router.get("/health")
def healthcheck(request: Request) -> dict[str, str]:
    settings = request.app.state.settings
    return {"status": "ok", "env": settings.app_env, "version": settings.app_version}


@router.post("/api/v1/pipeline/upload-resume", response_model=ResumeUploadResponse)
async def upload_resume(file: UploadFile = File(...)) -> ResumeUploadResponse:
    return ResumeUploadResponse(**await ResumeParserService().parse_upload(file))


@router.post("/api/v1/pipeline/analyze-resume", response_model=AiResumeAnalyzeResponse)
def analyze_resume_pipeline(
    request: AiResumeAnalyzeRequest,
    session: Session = Depends(get_db_session),
) -> AiResumeAnalyzeResponse:
    response = EmployabilityPipelineService().analyze_resume(
        resume_text=request.resume_text,
        target_role=request.target_role,
        target_company=request.target_company,
    )
    PipelineResumeStateService(session).save(request.resume_text, response)
    SkillGapRoadmapService(session).clear()
    return response


@router.post("/api/v1/pipeline/generate-test", response_model=AdaptiveTestGenerateResponse)
def generate_adaptive_test(
    request: AdaptiveTestGenerateRequest,
    session: Session = Depends(get_db_session),
) -> AdaptiveTestGenerateResponse:
    latest = PipelineResumeStateService(session).latest_analysis()
    skills = request.skills or (latest.skills if latest else [])
    experience_level = request.experience_level
    if latest and (not request.skills or request.experience_level == "Beginner"):
        experience_level = latest.experience_level
    return EmployabilityPipelineService().generate_test(
        skills=skills,
        selected_role=request.selected_role,
        experience_level=experience_level,
    )


@router.post("/api/v1/pipeline/evaluate-test", response_model=AdaptiveTestEvaluationResponse)
def evaluate_adaptive_test(
    request: AdaptiveTestEvaluationRequest,
    session: Session = Depends(get_db_session),
) -> AdaptiveTestEvaluationResponse:
    latest = PipelineResumeStateService(session).latest_analysis()
    return EmployabilityPipelineService().evaluate_test(
        selected_role=request.selected_role or (latest.selected_role if latest else ""),
        skills=request.skills or (latest.skills if latest else []),
        answers=request.answers,
        proctoring_events=request.proctoring_events,
    )


@router.post("/api/v1/pipeline/final-report", response_model=FinalEmployabilityReportResponse)
def final_employability_report(
    request: FinalEmployabilityReportRequest,
    session: Session = Depends(get_db_session),
) -> FinalEmployabilityReportResponse:
    resume_state = PipelineResumeStateService(session)
    latest = resume_state.latest_analysis()
    latest_record = resume_state.latest_record()
    return EmployabilityPipelineService().final_report(
        resume_text=request.resume_text or (latest_record.raw_text if latest_record else ""),
        selected_role=request.selected_role or (latest.selected_role if latest else ""),
        skills=request.skills or (latest.skills if latest else []),
        ats_score=request.ats_score or (latest.ats.score if latest else 0.0),
        test_score=request.test_score,
        trust_score=request.trust_score,
        skill_breakdown=request.skill_breakdown,
        proctoring_events=request.proctoring_events,
    )


@router.post("/api/v1/pipeline/generate-roadmap", response_model=SkillRoadmapResponse)
def generate_skill_gap_roadmap(
    request: SkillRoadmapGenerateRequest,
    session: Session = Depends(get_db_session),
) -> SkillRoadmapResponse:
    return SkillGapRoadmapService(session).generate(request)


@router.get("/api/v1/pipeline/roadmap", response_model=SkillRoadmapResponse)
def get_skill_gap_roadmap(session: Session = Depends(get_db_session)) -> SkillRoadmapResponse:
    return SkillGapRoadmapService(session).latest()


@router.post("/api/v1/pipeline/update-progress", response_model=SkillRoadmapProgressResponse)
def update_skill_gap_roadmap_progress(
    request: SkillRoadmapProgressUpdateRequest,
    session: Session = Depends(get_db_session),
) -> SkillRoadmapProgressResponse:
    return SkillGapRoadmapService(session).update_progress(request.task_id, request.status, request.proof_summary)


@router.get("/api/v1/pipeline/roadmap-progress", response_model=SkillRoadmapProgressResponse)
def get_skill_gap_roadmap_progress(session: Session = Depends(get_db_session)) -> SkillRoadmapProgressResponse:
    return SkillGapRoadmapService(session).progress()


@router.post("/generate-roadmap", response_model=SkillRoadmapResponse)
def generate_skill_gap_roadmap_alias(
    request: SkillRoadmapGenerateRequest,
    session: Session = Depends(get_db_session),
) -> SkillRoadmapResponse:
    return SkillGapRoadmapService(session).generate(request)


@router.get("/roadmap", response_model=SkillRoadmapResponse)
def get_skill_gap_roadmap_alias(session: Session = Depends(get_db_session)) -> SkillRoadmapResponse:
    return SkillGapRoadmapService(session).latest()


@router.post("/update-progress", response_model=SkillRoadmapProgressResponse)
def update_skill_gap_roadmap_progress_alias(
    request: SkillRoadmapProgressUpdateRequest,
    session: Session = Depends(get_db_session),
) -> SkillRoadmapProgressResponse:
    return SkillGapRoadmapService(session).update_progress(request.task_id, request.status, request.proof_summary)


@router.get("/roadmap-progress", response_model=SkillRoadmapProgressResponse)
def get_skill_gap_roadmap_progress_alias(session: Session = Depends(get_db_session)) -> SkillRoadmapProgressResponse:
    return SkillGapRoadmapService(session).progress()


@router.get("/jobs", response_model=JobsFetchResponse)
def fetch_jobs(
    request: Request,
    query: str = "",
    location: str = "",
    remote: bool | None = None,
    limit: int = 12,
    session: Session = Depends(get_db_session),
) -> JobsFetchResponse:
    return JobMatchingService(session, request.app.state.settings).fetch_jobs(query, location, remote, limit)


@router.post("/match-jobs", response_model=JobMatchResponse)
def match_jobs(
    payload: JobMatchRequest,
    request: Request,
    session: Session = Depends(get_db_session),
) -> JobMatchResponse:
    return JobMatchingService(session, request.app.state.settings).match_jobs(payload)


@router.get("/recommended-jobs", response_model=JobMatchResponse)
def recommended_jobs(
    request: Request,
    location: str = "",
    remote: bool | None = None,
    limit: int = 8,
    session: Session = Depends(get_db_session),
) -> JobMatchResponse:
    return JobMatchingService(session, request.app.state.settings).recommended_jobs(location, remote, limit)


@router.post("/api/v1/auth/register-student", status_code=status.HTTP_201_CREATED, response_model=StudentResponse)
def register_student(
    request: RegisterStudentRequest,
    fastapi_request: Request,
    session: Session = Depends(get_db_session),
) -> StudentResponse:
    return AuthService(session, fastapi_request.app.state.settings).register_student(request)


@router.post("/api/v1/auth/register-staff", status_code=status.HTTP_201_CREATED, response_model=StaffResponse)
def register_staff(
    request: RegisterStaffRequest,
    fastapi_request: Request,
    session: Session = Depends(get_db_session),
) -> StaffResponse:
    return AuthService(session, fastapi_request.app.state.settings).register_staff(request)


@router.post("/api/v1/auth/login", response_model=AuthTokenResponse)
def login(
    request: LoginRequest,
    fastapi_request: Request,
    session: Session = Depends(get_db_session),
) -> AuthTokenResponse:
    return AuthService(session, fastapi_request.app.state.settings).login(request)


@router.post("/api/v1/students", status_code=status.HTTP_201_CREATED, response_model=StudentResponse)
def create_student(
    request: CreateStudentRequest,
    session: Session = Depends(get_db_session),
) -> StudentResponse:
    profile = StudentRepository(session).create_student(
        full_name=request.full_name,
        email=request.email,
        target_role=request.target_role,
        target_company=request.target_company,
    )
    return StudentResponse(
        student_id=profile.id,
        full_name=profile.user.full_name,
        email=profile.user.email,
        target_role=profile.target_role,
        target_company=profile.target_company,
    )


@router.post("/api/v1/students/{student_id}/intake", response_model=IntakeResponse)
def submit_intake(
    student_id: int,
    request: IntakeRequest,
    session: Session = Depends(get_db_session),
    actor: ActorContext = Depends(get_actor_context),
) -> IntakeResponse:
    require_student_access(student_id, actor)
    return IntakeService(session).process(student_id, request)


@router.post("/api/v1/students/{student_id}/resume/analyze", response_model=ResumeAnalysisResponse)
def analyze_resume(
    student_id: int,
    request: ResumeAnalysisRequest,
    session: Session = Depends(get_db_session),
    actor: ActorContext = Depends(get_actor_context),
) -> ResumeAnalysisResponse:
    require_student_access(student_id, actor)
    return ResumeAnalysisService(session).analyze(student_id, request)


@router.post("/api/v1/students/{student_id}/resume/ats", response_model=AtsGuidanceResponse)
def get_ats_guidance(
    student_id: int,
    request: AtsGuidanceRequest,
    actor: ActorContext = Depends(get_actor_context),
) -> AtsGuidanceResponse:
    require_student_access(student_id, actor)
    return AtsGuidanceService().evaluate(request)


@router.post("/api/v1/students/{student_id}/evidence/codeforces", response_model=CodeforcesEvidenceResponse)
def verify_codeforces_evidence(
    student_id: int,
    request: CodeforcesEvidenceRequest,
    fastapi_request: Request,
    session: Session = Depends(get_db_session),
    actor: ActorContext = Depends(get_actor_context),
) -> CodeforcesEvidenceResponse:
    require_student_access(student_id, actor)
    return EvidenceService(session, fastapi_request).verify_codeforces(student_id, request)


@router.post("/api/v1/students/{student_id}/evidence/github", response_model=GitHubEvidenceResponse)
def verify_github_evidence(
    student_id: int,
    request: GitHubEvidenceRequest,
    fastapi_request: Request,
    session: Session = Depends(get_db_session),
    actor: ActorContext = Depends(get_actor_context),
) -> GitHubEvidenceResponse:
    require_student_access(student_id, actor)
    return EvidenceService(session, fastapi_request).verify_github(student_id, request)


@router.get("/api/v1/students/{student_id}/evidence", response_model=EvidenceSummaryResponse)
def get_student_evidence(
    student_id: int,
    fastapi_request: Request,
    session: Session = Depends(get_db_session),
    actor: ActorContext = Depends(get_actor_context),
) -> EvidenceSummaryResponse:
    require_student_access(student_id, actor)
    return EvidenceService(session, fastapi_request).latest_summary(student_id)


@router.get("/api/v1/students/{student_id}/assessment-plan", response_model=StoredAssessmentPlanResponse)
def get_assessment_plan(
    student_id: int,
    session: Session = Depends(get_db_session),
    actor: ActorContext = Depends(get_actor_context),
) -> StoredAssessmentPlanResponse:
    require_student_access(student_id, actor)
    return IntakeService(session).get_latest_plan(student_id)


@router.get("/api/v1/assessment-questions", response_model=list[AssessmentQuestionResponse])
def list_assessment_questions() -> list[AssessmentQuestionResponse]:
    return [
        AssessmentQuestionResponse(**question)
        for question in DEFAULT_QUESTION_BANK.list_public()
    ]


@router.get("/api/v1/coding/problems", response_model=list[CodingProblemResponse])
def list_coding_problems() -> list[CodingProblemResponse]:
    return [
        CodingProblemResponse(**problem)
        for problem in CodingHarnessService(session=None).list_problems()
    ]


@router.post(
    "/api/v1/students/{student_id}/coding/submissions",
    status_code=status.HTTP_201_CREATED,
    response_model=CodingSubmissionResponse,
)
def submit_coding_solution(
    student_id: int,
    request: CodingSubmissionRequest,
    fastapi_request: Request,
    session: Session = Depends(get_db_session),
    actor: ActorContext = Depends(get_actor_context),
) -> CodingSubmissionResponse:
    require_student_access(student_id, actor)
    return CodingHarnessService(session, fastapi_request.app.state.settings).submit(student_id, request)


@router.post(
    "/api/v1/students/{student_id}/proctoring/analyze-frame",
    response_model=ProctoringFrameAnalysisResponse,
)
def analyze_proctoring_frame(
    student_id: int,
    request: ProctoringFrameAnalysisRequest,
    fastapi_request: Request,
    actor: ActorContext = Depends(get_actor_context),
) -> ProctoringFrameAnalysisResponse:
    require_student_access(student_id, actor)
    return ProctoringVisionService(fastapi_request.app.state.settings).analyze_frame(request.image_data_url)


@router.post(
    "/api/v1/students/{student_id}/assessment-attempts",
    status_code=status.HTTP_201_CREATED,
    response_model=AssessmentAttemptStartResponse,
)
def start_assessment_attempt(
    student_id: int,
    session: Session = Depends(get_db_session),
    actor: ActorContext = Depends(get_actor_context),
) -> AssessmentAttemptStartResponse:
    require_student_access(student_id, actor)
    return ScoringService(session).start_attempt(student_id)


@router.post(
    "/api/v1/students/{student_id}/assessments",
    status_code=status.HTTP_201_CREATED,
    response_model=AssessmentResponse,
)
def create_assessment(
    student_id: int,
    request: AssessmentCreateRequest,
    session: Session = Depends(get_db_session),
    actor: ActorContext = Depends(get_actor_context),
) -> AssessmentResponse:
    require_student_access(student_id, actor)
    return ScoringService(session).create_assessment(student_id, request)


@router.post("/api/v1/assessments/{assessment_id}/score", response_model=ScoreResponse)
def score_assessment(
    assessment_id: int,
    session: Session = Depends(get_db_session),
    actor: ActorContext = Depends(get_actor_context),
) -> ScoreResponse:
    if not (actor.is_staff or actor.role == "student"):
        require_staff_access(actor)
    return ScoringService(session).score_assessment(assessment_id)


@router.get("/api/v1/students/{student_id}/roadmap", response_model=RoadmapResponse)
def get_student_roadmap(
    student_id: int,
    session: Session = Depends(get_db_session),
    actor: ActorContext = Depends(get_actor_context),
) -> RoadmapResponse:
    require_student_access(student_id, actor)
    return ScoringService(session).get_latest_roadmap(student_id)


@router.post("/api/v1/students/{student_id}/roadmap/nodes/{node_id}/complete", response_model=RoadmapResponse)
def complete_roadmap_node(
    student_id: int,
    node_id: str,
    request: NodeCompletionRequest,
    session: Session = Depends(get_db_session),
    actor: ActorContext = Depends(get_actor_context),
) -> RoadmapResponse:
    require_student_access(student_id, actor)
    return RoadmapService(session).complete_node(student_id, node_id, request)


@router.get("/api/v1/trust-stamp/{slug}")
def get_trust_stamp(
    slug: str,
    fastapi_request: Request,
    session: Session = Depends(get_db_session),
) -> dict:
    return TrustStampService(session, fastapi_request.app.state.settings).get_public_stamp(slug)


@router.post("/api/v1/trust-stamp/verify", response_model=TrustStampVerificationResponse)
def verify_trust_stamp(
    payload: dict,
    fastapi_request: Request,
    session: Session = Depends(get_db_session),
) -> TrustStampVerificationResponse:
    return TrustStampVerificationResponse(
        **TrustStampService(session, fastapi_request.app.state.settings).verify_signature(payload)
    )


@router.get("/api/v1/model/metadata", response_model=ModelMetadataResponse)
def get_model_metadata() -> ModelMetadataResponse:
    return ModelMetadataService().get_metadata()


@router.post("/api/v1/institutions", status_code=status.HTTP_201_CREATED, response_model=InstitutionResponse)
def create_institution(
    request: InstitutionCreateRequest,
    session: Session = Depends(get_db_session),
    actor: ActorContext = Depends(get_actor_context),
) -> InstitutionResponse:
    require_staff_access(actor)
    return InstitutionService(session).create_institution(request)


@router.post("/api/v1/cohorts", status_code=status.HTTP_201_CREATED, response_model=CohortResponse)
def create_cohort(
    request: CohortCreateRequest,
    session: Session = Depends(get_db_session),
    actor: ActorContext = Depends(get_actor_context),
) -> CohortResponse:
    require_staff_access(actor)
    return InstitutionService(session).create_cohort(request.institution_id, request.name)


@router.post("/api/v1/cohorts/{cohort_id}/members", status_code=status.HTTP_201_CREATED)
def add_cohort_member(
    cohort_id: int,
    request: AddCohortMemberRequest,
    session: Session = Depends(get_db_session),
    actor: ActorContext = Depends(get_actor_context),
) -> dict[str, int]:
    require_staff_access(actor)
    return InstitutionService(session).add_member(cohort_id, request)


@router.get("/api/v1/cohorts/{cohort_id}/analytics", response_model=CohortAnalyticsResponse)
def get_cohort_analytics(
    cohort_id: int,
    session: Session = Depends(get_db_session),
    actor: ActorContext = Depends(get_actor_context),
) -> CohortAnalyticsResponse:
    require_staff_access(actor)
    return InstitutionService(session).get_analytics(cohort_id)
