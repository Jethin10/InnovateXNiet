export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";
export const HARNESS_APP_URL = process.env.NEXT_PUBLIC_HARNESS_APP_URL ?? "https://ide.judge0.com";
export const JUDGE0_GITHUB_URL = "https://github.com/judge0/judge0";
export const JUDGE0_IDE_GITHUB_URL = "https://github.com/judge0/ide";

export interface HealthResponse {
  status: string;
  env: string;
  version: string;
}

export interface AuthTokenResponse {
  access_token: string;
  token_type: string;
  role: string;
  student_id: number | null;
}

export interface StudentResponse {
  student_id: number;
  full_name: string;
  email: string;
  target_role: string;
  target_company: string | null;
}

export interface IntakeResponse {
  student_id: number;
  inferred_target_role: string;
  claimed_skills: string[];
  assessment_plan: {
    target_role: string;
    claimed_skills: string[];
    stages: Array<{
      stage_id: number;
      difficulty: string;
      time_limit_minutes: number;
      focus_skills: string[];
      objective: string;
      pass_rule: string;
    }>;
  };
  trust_stamp: {
    slug: string;
    consent_public: boolean;
  };
}

export interface ResumeAnalysisResponse {
  inferred_target_role: string;
  claimed_skills: string[];
  project_count: number;
  unsupported_claims: string[];
  risk_flags: string[];
}

export interface AtsGuidanceResponse {
  ats_score: number;
  matched_keywords: string[];
  missing_keywords: string[];
  recommendations: string[];
}

export interface EvidenceSummaryResponse {
  codeforces: Record<string, unknown> | null;
  github: GitHubEvidenceResponse | null;
  coding_harness: Record<string, unknown> | null;
}

export interface GitHubProjectRecommendation {
  title: string;
  rationale: string;
  suggested_scope: string[];
  evidence_repo_names: string[];
}

export interface GitHubRepositoryEvidence {
  name: string;
  full_name: string;
  url: string;
  description: string | null;
  primary_language: string | null;
  private: boolean;
  fork: boolean;
  stars: number;
  forks: number;
  open_issues: number;
  pushed_at: string | null;
  topics: string[];
  languages: Record<string, number>;
  contributor_count: number;
  commit_count_analyzed: number;
  authored_commit_count: number;
}

export interface GitHubCommitEvidence {
  repo: string;
  sha: string;
  message: string;
  authored_at: string | null;
  author_login: string | null;
  url: string | null;
}

export interface GitHubEvidenceResponse {
  source: string;
  username: string;
  verified: boolean;
  repo_count: number;
  followers: number | null;
  original_repo_count: number;
  private_repo_count: number;
  fork_repo_count: number;
  total_stars: number;
  total_forks: number;
  total_open_issues: number;
  total_commits_analyzed: number;
  authored_commit_count: number;
  recent_commit_count: number;
  language_breakdown: Record<string, number>;
  top_languages: string[];
  contribution_summary: string[];
  repositories: GitHubRepositoryEvidence[];
  recent_commits: GitHubCommitEvidence[];
  project_recommendations: GitHubProjectRecommendation[];
  access_scope: string;
  rate_limit_remaining: number | null;
}

export interface CodingProblem {
  problem_id: string;
  title: string;
  difficulty: string;
  skill_tags: string[];
  statement: string;
  function_name: string;
  starter_code: string;
  starter_code_by_language?: Record<string, string>;
  supported_languages?: Array<{
    id: string;
    label: string;
    monaco_language: string;
  }>;
  examples: Array<{
    input: Record<string, unknown>;
    expected: unknown;
  }>;
}

export interface CodingSubmissionResponse {
  submission_id: string;
  problem_id: string;
  passed: boolean;
  score: number;
  public_results: Array<{
    name: string;
    passed: boolean;
    input: Record<string, unknown> | null;
    expected: unknown;
    actual: unknown;
    error: string | null;
  }>;
  hidden_passed_count: number;
  hidden_total_count: number;
  integrity_flags: string[];
  skill_tags: string[];
}

export interface CodingProctoringEvent {
  event_type: string;
  count: number;
  severity: number;
}

export interface CodingProctoringPayload {
  proctoring_checks: Record<string, boolean>;
  proctoring_events: CodingProctoringEvent[];
}

export interface ProctoringFrameAnalysisResponse {
  analyzed: boolean;
  model: string;
  risk_score: number;
  flags: string[];
  reason: string;
}

export interface AssessmentQuestion {
  question_id: string;
  prompt: string;
  stage_id: number;
  difficulty_band: string;
  skill_tag: string;
  max_time_seconds: number;
}

export interface AssessmentAttemptResponse {
  attempt_id: number;
  status: string;
  expires_at: string;
  questions: AssessmentQuestion[];
}

export interface AssessmentResponse {
  assessment_id: number;
  status: string;
}

export interface RoadmapNode {
  node_id: string;
  title: string;
  skill_track: string;
  summary: string;
  prerequisites: string[];
  status: string;
  recommended: boolean;
  assignment: string;
  proof_requirement: string;
}

export interface RoadmapResponse {
  target_role: string;
  current_level: string;
  summary: string;
  nodes: RoadmapNode[];
}

export interface ScoreResponse {
  trust_score: {
    overall_readiness: number;
    model_probability: number;
    raw_accuracy: number;
    confidence_reliability: number;
    evidence_alignment: number;
    calibration_gap: number;
    bluff_index: number;
    readiness_band: string;
    risk_band: string;
    skill_scores: Record<string, number>;
    explanations: string[];
    top_positive_signals: string[];
    top_risk_signals: string[];
  };
  roadmap: RoadmapResponse;
}

export interface ModelMetadataResponse {
  model_loaded: boolean;
  training_summary: Record<string, unknown>;
  limitations: string[];
}

export interface ScoreExplanation {
  score: number;
  explanation: string;
  factors: string[];
  improvement_tips: string[];
}

export interface AiResumeAnalyzeResponse {
  skills: string[];
  experience_level: string;
  suggested_roles: string[];
  selected_role: string;
  ats: ScoreExplanation;
  skill_match_percent: number;
  model_readiness_score: number;
  model_version: string;
  model_factors: string[];
  missing_keywords: string[];
  resume_suggestions: string[];
}

export interface AdaptiveTestQuestion {
  question_id: string;
  prompt: string;
  question_type: string;
  difficulty_band: string;
  skill_tag: string;
  max_time_seconds: number;
}

export interface AdaptiveTestGenerateResponse {
  selected_role: string;
  focus_skills: string[];
  questions: AdaptiveTestQuestion[];
  adaptation_summary: string;
}

export interface AdaptiveTestEvaluationResponse {
  test: ScoreExplanation;
  trust: ScoreExplanation;
  proctoring_risk_score: number;
  skill_breakdown: Record<string, number>;
  weak_areas: string[];
}

export interface FinalEmployabilityReportResponse {
  ats: ScoreExplanation;
  test: ScoreExplanation;
  trust: ScoreExplanation;
  role_fit: ScoreExplanation;
  extracted_skills: string[];
  skill_gaps: string[];
  roadmap: Array<{
    title: string;
    skill: string;
    project: string;
    resource: string;
    practice: string;
  }>;
}

export interface RecommendedJobInput {
  title: string;
  match_score: number;
  required_skills: string[];
}

export interface SkillRoadmapTask {
  task_id: string;
  day: number;
  title: string;
  action: string;
  status: string;
}

export interface SkillRoadmapJobImpact {
  impacted_job_count: number;
  estimated_match_lift_percent: number;
  jobs: string[];
  summary: string;
}

export interface SkillRoadmapHarnessQuestion {
  problem_id: string;
  title: string;
  difficulty: string;
  reason: string;
}

export interface SkillRoadmapItem {
  skill: string;
  priority: string;
  duration: string;
  concepts: string[];
  practice_tasks: string[];
  steps: string[];
  project: string;
  resources: string[];
  resource_queries: string[];
  harness_questions: SkillRoadmapHarnessQuestion[];
  daily_tasks: SkillRoadmapTask[];
  reason: string;
  job_impact: SkillRoadmapJobImpact;
  progress_percent: number;
}

export interface SkillRoadmapResponse {
  target_role: string;
  skill_gaps: string[];
  roadmap: SkillRoadmapItem[];
  overall_progress_percent: number;
  badges: string[];
  streak_days: number;
}

export interface SkillRoadmapProgressResponse {
  completed_tasks: number;
  total_tasks: number;
  progress_percent: number;
  badges: string[];
  streak_days: number;
}

export interface JobListing {
  job_id: string;
  title: string;
  company: string;
  location: string;
  description: string;
  apply_url: string | null;
  remote: boolean;
  source: string;
  required_skills: string[];
}

export interface JobsFetchResponse {
  query: string;
  location: string;
  source: string;
  jobs: JobListing[];
}

export interface JobMatchRequest {
  skills: string[];
  resume_text: string;
  ats_score: number;
  test_score: number;
  trust_score: number;
  selected_role?: string | null;
  jobs?: JobListing[];
  location?: string;
  remote?: boolean | null;
  min_match_score?: number;
  limit?: number;
}

export interface MatchedJob extends JobListing {
  skill_match_percent: number;
  match_score: number;
  explanation: string;
  matched_skills: string[];
  missing_skills: string[];
  semantic_similarity: number;
}

export interface JobMatchResponse {
  source: string;
  profile_role: string;
  filters: Record<string, unknown>;
  jobs: MatchedJob[];
}

export class ApiError extends Error {
  status: number;
  detail: unknown;

  constructor(status: number, detail: unknown) {
    super(typeof detail === "string" ? detail : `API request failed with status ${status}`);
    this.status = status;
    this.detail = detail;
  }
}

interface RequestOptions extends RequestInit {
  token?: string | null;
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers = new Headers(options.headers);
  const isFormData = typeof FormData !== "undefined" && options.body instanceof FormData;
  if (!headers.has("Content-Type") && options.body && !isFormData) headers.set("Content-Type", "application/json");
  if (options.token) headers.set("Authorization", `Bearer ${options.token}`);

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let detail: unknown = response.statusText;
    try {
      const payload = await response.json();
      detail = payload.detail ?? payload;
    } catch {
      detail = response.statusText;
    }
    throw new ApiError(response.status, detail);
  }

  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export function jsonBody(payload: unknown) {
  return JSON.stringify(payload);
}

export function codingStarterForLanguage(problem: CodingProblem, language: string): string {
  const apiStarter = problem.starter_code_by_language?.[language];
  if (apiStarter) return apiStarter;

  const example = problem.examples[0];
  const args = Object.keys(example?.input ?? {});
  const sampleInput = JSON.stringify(example?.input ?? {});
  const sampleExpected = JSON.stringify(example?.expected ?? null);

  if (language === "javascript") {
    return `function ${problem.function_name}(${args.join(", ")}) {\n  return null;\n}\n`;
  }

  if (language === "java") {
    return `class Solution {\n    // ${problem.title}\n    // Input JSON: ${sampleInput}\n    // Expected JSON: ${sampleExpected}\n    static String ${problem.function_name}(String inputJson) {\n        return \"null\";\n    }\n}\n`;
  }

  if (language === "c") {
    return `// ${problem.title}\n// Input JSON: ${sampleInput}\n// Expected JSON: ${sampleExpected}\nconst char* ${problem.function_name}(const char* input_json) {\n    return \"null\";\n}\n`;
  }

  if (language === "cpp") {
    return `#include <string>\nusing namespace std;\n\n// ${problem.title}\n// Input JSON: ${sampleInput}\n// Expected JSON: ${sampleExpected}\nstring ${problem.function_name}(const string& inputJson) {\n    return \"null\";\n}\n`;
  }

  return problem.starter_code;
}
