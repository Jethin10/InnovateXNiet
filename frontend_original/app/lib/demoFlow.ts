import {
  AssessmentAttemptResponse,
  AssessmentQuestion,
  AtsGuidanceResponse,
  EvidenceSummaryResponse,
  HealthResponse,
  IntakeResponse,
  JobMatchResponse,
  ModelMetadataResponse,
  ResumeAnalysisResponse,
  RoadmapResponse,
  ScoreResponse,
  StudentResponse,
  apiRequest,
  jsonBody,
} from "./api";

export interface DemoFlowState {
  health?: HealthResponse;
  metadata?: ModelMetadataResponse;
  student?: StudentResponse;
  intake?: IntakeResponse;
  resume?: ResumeAnalysisResponse;
  ats?: AtsGuidanceResponse;
  evidence?: EvidenceSummaryResponse;
  attempt?: AssessmentAttemptResponse;
  score?: ScoreResponse;
  roadmap?: RoadmapResponse;
  jobs?: JobMatchResponse;
}

const demoResume = `Aarav Sharma is a final-year computer science student targeting backend SDE roles.
Skills: Python, JavaScript, SQL, APIs, data structures, React, FastAPI.
Projects: built a placement analytics dashboard, a resume parser, and a coding-profile tracker.
Evidence: GitHub portfolio, database indexing project, API idempotency work.`;

const answerKey: Record<string, string> = {
  be_easy_dsa_array_lookup: "O(1)",
  be_easy_fundamentals_http_status: "404",
  be_medium_db_index: "CREATE INDEX idx_users_email ON users(email)",
  be_medium_api_idempotency: "idempotency key",
  be_hard_dsa_binary_search: "O(log n)",
  be_hard_fundamentals_transaction: "atomicity",
  fs_easy_html_semantic: "nav",
  fs_medium_css_flex: "flexbox",
  fs_hard_js_closure: "closure",
};

const makeAssessmentAnswer = (question: AssessmentQuestion, index: number) => ({
  question_id: question.question_id,
  stage_id: question.stage_id,
  difficulty_band: question.difficulty_band,
  skill_tag: question.skill_tag,
  submitted_answer: answerKey[question.question_id] ?? "not sure",
  elapsed_seconds: Math.min(question.max_time_seconds - 1, 22 + index * 4),
  confidence: index % 3 === 0 ? 0.82 : 0.72,
  answer_changes: index % 2,
  max_time_seconds: question.max_time_seconds,
});

export const checkBackendHealth = () => apiRequest<HealthResponse>("/health");

export async function runPlacementTrustDemo(
  onStep: (message: string, state?: Partial<DemoFlowState>) => void
): Promise<DemoFlowState> {
  const seed = Date.now();
  const password = "Placement123";
  const nextState: DemoFlowState = {};

  onStep("Checking backend health");
  nextState.health = await apiRequest<HealthResponse>("/health");
  nextState.metadata = await apiRequest<ModelMetadataResponse>("/api/v1/model/metadata");
  onStep("Backend online", nextState);

  const studentEmail = `demo.student.${seed}@trust.local`;
  onStep("Creating student");
  nextState.student = await apiRequest<StudentResponse>("/api/v1/auth/register-student", {
    method: "POST",
    body: jsonBody({
      full_name: "Aarav Sharma",
      email: studentEmail,
      password,
      target_role: "Backend SDE",
      target_company: "Fintech product company",
    }),
  });
  const login = await apiRequest<{ access_token: string }>("/api/v1/auth/login", {
    method: "POST",
    body: jsonBody({ email: studentEmail, password }),
  });
  onStep("Student authenticated", nextState);

  const studentId = nextState.student.student_id;
  onStep("Submitting intake");
  nextState.intake = await apiRequest<IntakeResponse>(`/api/v1/students/${studentId}/intake`, {
    method: "POST",
    token: login.access_token,
    body: jsonBody({
      resume_text: demoResume,
      manual_skills: ["Python", "FastAPI", "SQL", "Data Structures", "React"],
      preferred_resource_style: "project-based",
      consent_public: true,
    }),
  });
  nextState.resume = await apiRequest<ResumeAnalysisResponse>(`/api/v1/students/${studentId}/resume/analyze`, {
    method: "POST",
    token: login.access_token,
    body: jsonBody({ resume_text: demoResume, filename: "demo-resume.txt" }),
  });
  nextState.ats = await apiRequest<AtsGuidanceResponse>(`/api/v1/students/${studentId}/resume/ats`, {
    method: "POST",
    token: login.access_token,
    body: jsonBody({
      resume_text: demoResume,
      target_role: "Backend SDE",
      target_company: "Fintech product company",
    }),
  });
  onStep("Resume analyzed", nextState);

  onStep("Verifying evidence");
  try {
    await apiRequest(`/api/v1/students/${studentId}/evidence/github`, {
      method: "POST",
      token: login.access_token,
      body: jsonBody({ username: "octocat" }),
    });
  } catch {
    // External evidence APIs can be unavailable; the backend flow continues with resume evidence.
  }
  nextState.evidence = await apiRequest<EvidenceSummaryResponse>(`/api/v1/students/${studentId}/evidence`, {
    token: login.access_token,
  });
  onStep("Evidence collected", nextState);

  onStep("Running assessment");
  nextState.attempt = await apiRequest<AssessmentAttemptResponse>(`/api/v1/students/${studentId}/assessment-attempts`, {
    method: "POST",
    token: login.access_token,
  });
  const assessment = await apiRequest<{ assessment_id: number }>(`/api/v1/students/${studentId}/assessments`, {
    method: "POST",
    token: login.access_token,
    body: jsonBody({
      attempt_id: nextState.attempt.attempt_id,
      answers: nextState.attempt.questions.map(makeAssessmentAnswer),
      evidence: {
        codeforces_rating: null,
        leetcode_solved: 120,
        resume_claims: nextState.resume.claimed_skills,
        verified_skills: ["Python", "SQL", "APIs"],
        project_tags: ["FastAPI", "React", "analytics"],
        project_count: nextState.resume.project_count || 3,
        github_repo_count: Number(nextState.evidence.github?.repo_count ?? 0),
      },
    }),
  });
  nextState.score = await apiRequest<ScoreResponse>(`/api/v1/assessments/${assessment.assessment_id}/score`, {
    method: "POST",
    token: login.access_token,
  });
  nextState.roadmap = await apiRequest<RoadmapResponse>(`/api/v1/students/${studentId}/roadmap`, {
    token: login.access_token,
  });
  onStep("Student flow scored", nextState);

  onStep("Matching jobs that suit you");
  nextState.jobs = await apiRequest<JobMatchResponse>("/match-jobs", {
    method: "POST",
    body: jsonBody({
      location: "India",
      remote: null,
      min_match_score: 0,
      limit: 6,
      selected_role: nextState.resume.inferred_target_role,
      skills: nextState.resume.claimed_skills,
      ats_score: nextState.ats.ats_score,
      test_score: Math.round((nextState.score.trust_score.raw_accuracy ?? 0) * 100),
      trust_score: Math.round(nextState.score.trust_score.overall_readiness * 100),
    }),
  });
  onStep("Backend integration complete", nextState);

  return nextState;
}
