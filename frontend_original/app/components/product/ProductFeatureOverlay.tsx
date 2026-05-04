"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type { MouseEvent, ReactNode } from "react";
import { BriefcaseBusiness, CheckCircle2, ExternalLink, LogOut, MapPin, Play, Send, ShieldCheck, XCircle } from "lucide-react";
import { motion, useMotionTemplate, useMotionValue, useTransform } from "motion/react";
import {
  API_BASE_URL,
  HARNESS_APP_URL,
  JUDGE0_GITHUB_URL,
  JUDGE0_IDE_GITHUB_URL,
  AssessmentAttemptResponse,
  AtsGuidanceResponse,
  AuthTokenResponse,
  CodingProblem,
  CodingProctoringPayload,
  CodingSubmissionResponse,
  GitHubEvidenceResponse,
  IntakeResponse,
  JobMatchResponse,
  MatchedJob,
  ModelMetadataResponse,
  ProctoringFrameAnalysisResponse,
  ResumeAnalysisResponse,
  RoadmapResponse,
  ScoreResponse,
  SkillRoadmapResponse,
  StudentResponse,
  ApiError,
  apiRequest,
  codingStarterForLanguage,
  jsonBody,
} from "@/app/lib/api";
import { useFeatureStore } from "@stores";
import { PROJECTS } from "@constants";
import { ShapeLandingBackdrop } from "@/components/ui/shape-landing-hero";
import { signOutGate } from "@/app/lib/firebaseAuth";
import AiMentorPipeline from "./AiMentorPipeline";
import CodingHarnessWorkspace from "./CodingHarnessWorkspace";

interface DemoSession {
  studentId: number;
  token: string;
  stampSlug: string | null;
}

interface FeatureState {
  session?: DemoSession;
  intake?: IntakeResponse;
  resume?: ResumeAnalysisResponse;
  ats?: AtsGuidanceResponse;
  github?: GitHubEvidenceResponse;
  problems?: CodingProblem[];
  coding?: CodingSubmissionResponse;
  attempt?: AssessmentAttemptResponse;
  score?: ScoreResponse;
  roadmap?: RoadmapResponse;
  skillRoadmap?: SkillRoadmapResponse;
  jobs?: JobMatchResponse;
  stamp?: Record<string, unknown>;
  stampValid?: boolean;
  metadata?: ModelMetadataResponse;
}

const SESSION_STORAGE_KEY = "placement-trust-demo-session";
const GATE_SESSION_KEY = "placement-trust-gate-unlocked";
const ADAPTIVE_CODING_TEST_KEY = "placement-trust-adaptive-coding-test";

interface AdaptiveCodingTestIntent {
  focusSkills: string[];
  missingSkills: string[];
  problemIds: string[];
  resumeSkills: string[];
  role: string;
  summary: string;
}

const demoResume = `Backend SDE candidate with Python, SQL, APIs, FastAPI, React, data structures, and system design.
Projects: Built a placement analytics dashboard with cohort risk buckets.
Projects: Created a coding-profile tracker with GitHub and Codeforces evidence.
Evidence: API idempotency work, database indexing project, and recruiter-facing Trust Stamp.`;

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

const defaultCodingStarter = "def solve(nums, target):\n    return []\n";
const defaultCodingLanguage = "python";

const featureTitles: Record<string, string> = {
  account: "Account Passport",
  intake: "Student Intake",
  resume: "Resume ATS",
  github: "GitHub Evidence",
  coding: "Coding Harness",
  ai_pipeline: "AI Mentor Pipeline",
  assessment: "Assessment",
  score: "Trust Score",
  roadmap: "Roadmap Graph",
  stamp: "Trust Stamp",
  jobs: "Jobs That Suit You",
};

const pct = (value?: number) => (typeof value === "number" ? `${Math.round(value * 100)}%` : "--");

const ProductFeatureOverlay = () => {
  const activeFeatureKey = useFeatureStore((state) => state.activeFeatureKey);
  const setActiveFeatureKey = useFeatureStore((state) => state.setActiveFeatureKey);
  const [state, setState] = useState<FeatureState>(() => {
    if (typeof window === "undefined") return {};
    const saved = window.sessionStorage.getItem(SESSION_STORAGE_KEY);
    if (!saved) return {};
    try {
      const session = JSON.parse(saved) as DemoSession;
      return session?.studentId && session?.token ? { session } : {};
    } catch {
      return {};
    }
  });
  const [status, setStatus] = useState("Ready");
  const [githubUsername, setGithubUsername] = useState("octocat");
  const githubTokenRef = useRef<HTMLInputElement>(null);
  const [includePrivateRepos, setIncludePrivateRepos] = useState(false);
  const [selectedProblemId, setSelectedProblemId] = useState("two_sum_indices");
  const [selectedCodingLanguage, setSelectedCodingLanguage] = useState(defaultCodingLanguage);
  const [code, setCode] = useState(defaultCodingStarter);
  const [adaptiveCodingIntent, setAdaptiveCodingIntent] = useState<AdaptiveCodingTestIntent | null>(null);
  const [jobLocation, setJobLocation] = useState("India");
  const [jobRemote, setJobRemote] = useState<"any" | "remote" | "onsite">("any");
  const [jobMinScore, setJobMinScore] = useState(0);
  const autoRunKeyRef = useRef<string | null>(null);

  const selectedFeature = useMemo(
    () => PROJECTS.find((feature) => feature.featureKey === activeFeatureKey),
    [activeFeatureKey]
  );

  const patchState = (next: Partial<FeatureState>) => {
    setState((current) => {
      const updated = { ...current, ...next };
      if (typeof window !== "undefined" && updated.session) {
        window.sessionStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(updated.session));
      }
      return updated;
    });
  };

  const starterForLanguage = (problem: CodingProblem, language: string) => {
    return codingStarterForLanguage(problem, language);
  };

  const ensureSession = async () => {
    if (state.session) return state.session;

    const seed = Date.now();
    const email = `feature.student.${seed}@trust.local`;
    const password = "Placement123";
    const student = await apiRequest<StudentResponse>("/api/v1/auth/register-student", {
      method: "POST",
      body: jsonBody({
        full_name: "Feature Demo Student",
        email,
        password,
        target_role: "Backend SDE",
        target_company: "Product company",
      }),
    });
    const login = await apiRequest<AuthTokenResponse>("/api/v1/auth/login", {
      method: "POST",
      body: jsonBody({ email, password }),
    });
    const session = { studentId: student.student_id, token: login.access_token, stampSlug: null };
    patchState({ session });
    return session;
  };

  const runAction = async (label: string, action: () => Promise<void>) => {
    setStatus(label);
    try {
      await action();
      setStatus("Updated from backend");
    } catch (error) {
      if (error instanceof ApiError && error.status === 429) {
        setStatus("GitHub public limit reached. Add a token, then sync.");
        return;
      }
      setStatus(error instanceof Error ? error.message : "Backend request failed");
    }
  };

  const logout = async () => {
    setStatus("Signing out");
    try {
      await signOutGate();
    } catch {
      // The local gate marker still gets cleared so the next load cannot skip sign-in.
    } finally {
      if (typeof window !== "undefined") {
        window.sessionStorage.removeItem(GATE_SESSION_KEY);
        window.sessionStorage.removeItem(SESSION_STORAGE_KEY);
        window.sessionStorage.removeItem(ADAPTIVE_CODING_TEST_KEY);
        window.sessionStorage.removeItem("ai-mentor-resume-text");
        window.location.reload();
      }
    }
  };

  const runIntake = () => runAction("Submitting intake", async () => {
    const session = await ensureSession();
    const intake = await apiRequest<IntakeResponse>(`/api/v1/students/${session.studentId}/intake`, {
      method: "POST",
      token: session.token,
      body: jsonBody({
        resume_text: demoResume,
        manual_skills: ["Python", "FastAPI", "SQL", "React", "Data Structures"],
        preferred_resource_style: "project-based",
        consent_public: true,
      }),
    });
    patchState({ intake, session: { ...session, stampSlug: intake.trust_stamp.slug } });
  });

  const runResume = () => runAction("Analyzing resume", async () => {
    const session = await ensureSession();
    const [resume, ats] = await Promise.all([
      apiRequest<ResumeAnalysisResponse>(`/api/v1/students/${session.studentId}/resume/analyze`, {
        method: "POST",
        token: session.token,
        body: jsonBody({ resume_text: demoResume, filename: "demo-resume.txt" }),
      }),
      apiRequest<AtsGuidanceResponse>(`/api/v1/students/${session.studentId}/resume/ats`, {
        method: "POST",
        token: session.token,
        body: jsonBody({
          resume_text: demoResume,
          target_role: "Backend SDE",
          target_company: "Product company",
        }),
      }),
    ]);
    patchState({ resume, ats });
  });

  const runGithub = () => runAction("Connecting GitHub", async () => {
    const session = await ensureSession();
    const accessToken = githubTokenRef.current?.value.trim() || null;
    const github = await apiRequest<GitHubEvidenceResponse>(`/api/v1/students/${session.studentId}/evidence/github`, {
      method: "POST",
      token: session.token,
      body: jsonBody({
        username: githubUsername,
        access_token: accessToken,
        include_private: includePrivateRepos,
      }),
    });
    if (githubTokenRef.current) githubTokenRef.current.value = "";
    patchState({ github });
  });

  const loadProblems = async () => {
    if (state.problems) return state.problems;
    const problems = await apiRequest<CodingProblem[]>("/api/v1/coding/problems");
    patchState({ problems });
    const selectedProblem = problems.find((problem) => problem.problem_id === selectedProblemId) ?? problems[0];
    if (selectedProblem) {
      setSelectedProblemId(selectedProblem.problem_id);
      setCode(starterForLanguage(selectedProblem, selectedCodingLanguage));
    }
    return problems;
  };

  const applyAdaptiveCodingIntent = (problems: CodingProblem[]) => {
    if (typeof window === "undefined") return;
    const rawIntent = window.sessionStorage.getItem(ADAPTIVE_CODING_TEST_KEY);
    if (!rawIntent) return;

    try {
      const intent = JSON.parse(rawIntent) as AdaptiveCodingTestIntent;
      const intentIds = new Set(intent.problemIds ?? []);
      const orderedProblems = [
        ...intent.problemIds.map((problemId) => problems.find((problem) => problem.problem_id === problemId)).filter(Boolean),
        ...problems.filter((problem) => !intentIds.has(problem.problem_id)),
      ] as CodingProblem[];
      const selectedProblem = orderedProblems[0];
      if (!selectedProblem) return;

      setAdaptiveCodingIntent(intent);
      setSelectedProblemId(selectedProblem.problem_id);
      setCode(starterForLanguage(selectedProblem, selectedCodingLanguage));
      patchState({ problems: orderedProblems, coding: undefined });
      setStatus(`Adaptive coding test for ${intent.role}`);
    } catch {
      window.sessionStorage.removeItem(ADAPTIVE_CODING_TEST_KEY);
    }
  };

  const selectCodingProblem = (problem: CodingProblem) => {
    setSelectedProblemId(problem.problem_id);
    setCode(starterForLanguage(problem, selectedCodingLanguage));
    patchState({ coding: undefined });
  };

  const selectCodingLanguage = (language: string) => {
    setSelectedCodingLanguage(language);
    const selectedProblem = state.problems?.find((problem) => problem.problem_id === selectedProblemId);
    if (selectedProblem) setCode(starterForLanguage(selectedProblem, language));
    patchState({ coding: undefined });
  };

  const runCoding = (proctoring?: CodingProctoringPayload, codeOverride?: string) => runAction("Running coding harness", async () => {
    const session = await ensureSession();
    const problems = await loadProblems();
    const problemId = problems.some((problem) => problem.problem_id === selectedProblemId)
      ? selectedProblemId
      : problems[0]?.problem_id ?? "two_sum_indices";
    const coding = await apiRequest<CodingSubmissionResponse>(`/api/v1/students/${session.studentId}/coding/submissions`, {
      method: "POST",
      token: session.token,
      body: jsonBody({ problem_id: problemId, language: selectedCodingLanguage, code: codeOverride ?? code, ...proctoring }),
    });
    patchState({ coding });
  });

  const analyzeProctoringFrame = async (imageDataUrl: string) => {
    const session = await ensureSession();
    return apiRequest<ProctoringFrameAnalysisResponse>(`/api/v1/students/${session.studentId}/proctoring/analyze-frame`, {
      method: "POST",
      token: session.token,
      body: jsonBody({ image_data_url: imageDataUrl }),
    });
  };

  const runAssessment = () => runAction("Running assessment", async () => {
    const session = await ensureSession();
    const attempt = await apiRequest<AssessmentAttemptResponse>(`/api/v1/students/${session.studentId}/assessment-attempts`, {
      method: "POST",
      token: session.token,
    });
    const assessment = await apiRequest<{ assessment_id: number }>(`/api/v1/students/${session.studentId}/assessments`, {
      method: "POST",
      token: session.token,
      body: jsonBody({
        attempt_id: attempt.attempt_id,
        answers: attempt.questions.map((question, index) => ({
          question_id: question.question_id,
          stage_id: question.stage_id,
          difficulty_band: question.difficulty_band,
          skill_tag: question.skill_tag,
          submitted_answer: answerKey[question.question_id] ?? "not sure",
          elapsed_seconds: Math.min(question.max_time_seconds - 1, 20 + index * 4),
          confidence: 0.78,
          answer_changes: index % 2,
          max_time_seconds: question.max_time_seconds,
        })),
        evidence: {
          resume_claims: state.resume?.claimed_skills ?? ["python", "sql", "react"],
          verified_skills: ["Python", "SQL", "APIs"],
          project_tags: ["FastAPI", "React", "analytics"],
          project_count: state.resume?.project_count ?? 2,
          github_repo_count: state.github?.repo_count ?? 0,
          leetcode_solved: state.coding?.passed ? 1 : 0,
        },
      }),
    });
    const score = await apiRequest<ScoreResponse>(`/api/v1/assessments/${assessment.assessment_id}/score`, {
      method: "POST",
      token: session.token,
    });
    patchState({ attempt, score, roadmap: score.roadmap });
  });

  const runRoadmap = () => runAction("Loading roadmap", async () => {
    const session = await ensureSession();
    if (!state.score) await runAssessment();
    try {
      const roadmap = await apiRequest<RoadmapResponse>(`/api/v1/students/${session.studentId}/roadmap`, {
        token: session.token,
      });
      const nextNode = roadmap.nodes.find((node) => node.status !== "completed");
      const completed = nextNode
        ? await apiRequest<RoadmapResponse>(`/api/v1/students/${session.studentId}/roadmap/nodes/${nextNode.node_id}/complete`, {
            method: "POST",
            token: session.token,
            body: jsonBody({ proof_summary: "Demo proof from integrated feature UI" }),
          })
        : roadmap;
      patchState({ roadmap: completed });
    } catch {
      patchState({ roadmap: undefined });
    }
    try {
      const skillRoadmap = await apiRequest<SkillRoadmapResponse>("/api/v1/pipeline/roadmap");
      patchState({ skillRoadmap });
    } catch {
      patchState({ skillRoadmap: undefined });
    }
  });

  const runStamp = () => runAction("Verifying Trust Stamp", async () => {
    const session = await ensureSession();
    let slug = state.session?.stampSlug ?? state.intake?.trust_stamp.slug ?? null;
    if (!slug) {
      const intake = await apiRequest<IntakeResponse>(`/api/v1/students/${session.studentId}/intake`, {
        method: "POST",
        token: session.token,
        body: jsonBody({
          resume_text: demoResume,
          manual_skills: ["Python", "FastAPI", "SQL", "React", "Data Structures"],
          preferred_resource_style: "project-based",
          consent_public: true,
        }),
      });
      slug = intake.trust_stamp.slug;
      patchState({ intake, session: { ...session, stampSlug: slug } });
    }
    if (!state.score) await runAssessment();
    const stamp = await apiRequest<Record<string, unknown>>(`/api/v1/trust-stamp/${slug}`);
    const verification = await apiRequest<{ valid: boolean }>("/api/v1/trust-stamp/verify", {
      method: "POST",
      body: jsonBody(stamp),
    });
    patchState({ stamp, stampValid: verification.valid });
  });

  const runJobs = () => runAction("Matching real-time jobs", async () => {
    const remote = jobRemote === "any" ? null : jobRemote === "remote";
    const jobs = await apiRequest<JobMatchResponse>("/match-jobs", {
      method: "POST",
      body: jsonBody({
        location: jobLocation,
        remote,
        min_match_score: jobMinScore,
        limit: 8,
        selected_role: state.resume?.inferred_target_role ?? undefined,
        skills: state.resume?.claimed_skills ?? [],
        ats_score: state.ats?.ats_score ?? 0,
        test_score: state.coding?.score ?? 0,
        trust_score: state.score ? Math.round(state.score.trust_score.overall_readiness * 100) : 0,
      }),
    });
    patchState({ jobs });
  });

  const runCurrent = () => {
    if (activeFeatureKey === "account") return runIntake();
    if (activeFeatureKey === "intake") return runIntake();
    if (activeFeatureKey === "resume") return runResume();
    if (activeFeatureKey === "github") return runGithub();
    if (activeFeatureKey === "coding") return runCoding();
    if (activeFeatureKey === "ai_pipeline") return;
    if (activeFeatureKey === "assessment" || activeFeatureKey === "score") return runAssessment();
    if (activeFeatureKey === "roadmap") return runRoadmap();
    if (activeFeatureKey === "stamp") return runStamp();
    if (activeFeatureKey === "jobs") return runJobs();
  };

  useEffect(() => {
    if (!activeFeatureKey) {
      autoRunKeyRef.current = null;
      return;
    }
    if (autoRunKeyRef.current === activeFeatureKey) return;
    autoRunKeyRef.current = activeFeatureKey;
    if (activeFeatureKey === "coding") {
      void loadProblems().then(applyAdaptiveCodingIntent);
      return;
    }
    if (activeFeatureKey === "github") {
      setStatus("Enter GitHub username, then sync backend");
      return;
    }
    void runCurrent();
  }, [activeFeatureKey]);

  if (!activeFeatureKey) return null;

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/45 p-3 backdrop-blur-[2px] selectable md:p-5">
      <section className={`relative max-h-[calc(100dvh-2rem)] overflow-hidden border border-white/15 bg-[#030303] text-white shadow-[0_32px_110px_rgba(0,0,0,0.48)] ${
        activeFeatureKey === "coding" || activeFeatureKey === "ai_pipeline" ? "w-[min(96rem,calc(100vw-1.5rem))]" : "w-[min(72rem,calc(100vw-1.5rem))]"
      }`}>
        <ShapeLandingBackdrop className="opacity-100" />
        <div className="pointer-events-none absolute inset-0 bg-black/24" />
        <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-white/40" />
        <header className="relative flex items-start justify-between border-b border-white/15 p-4">
          <div className="max-w-[calc(100%-3.5rem)]">
            <div className="w-fit border border-white/20 bg-white/[0.04] px-3 py-1 font-sans text-[0.65rem] uppercase tracking-[0.22em] text-white/70">
              {activeFeatureKey === "account" ? "Account" : selectedFeature?.date ?? "Backend"}
            </div>
            <h2 className="mt-3 font-serif text-4xl leading-[0.92] md:text-[3rem]">
              {featureTitles[activeFeatureKey] ?? "Placement Trust"}
            </h2>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={logout}
              className="inline-flex h-10 items-center gap-2 border border-red-200/30 bg-red-400/10 px-3 font-sans text-[0.65rem] font-semibold uppercase tracking-[0.14em] text-red-100 transition-colors hover:bg-red-200 hover:text-black"
              aria-label="Log out"
            >
              <LogOut className="h-3.5 w-3.5" />
              Logout
            </button>
            <button
              type="button"
              onClick={() => setActiveFeatureKey(null)}
              className="h-10 w-10 border border-white/25 bg-white/[0.04] font-sans text-xl text-white transition-colors hover:bg-white hover:text-black"
              aria-label="Close feature"
            >
              X
            </button>
          </div>
        </header>

        <div className={`relative grid max-h-[calc(100dvh-9.75rem)] gap-0 overflow-y-auto ${
          activeFeatureKey === "coding" || activeFeatureKey === "ai_pipeline" ? "md:grid-cols-1" : "md:grid-cols-[13rem_1fr]"
        }`}>
          {activeFeatureKey !== "coding" && activeFeatureKey !== "ai_pipeline" && (
          <nav className="border-b border-white/15 bg-black/12 p-3 backdrop-blur-[3px] md:border-b-0 md:border-r">
            <button
              type="button"
              onClick={() => setActiveFeatureKey("account")}
              className={`mb-2 block w-full border px-3 py-2 text-left font-sans text-[0.68rem] uppercase tracking-[0.14em] transition-colors ${
                activeFeatureKey === "account" ? "border-white bg-white text-black" : "border-white/15 bg-white/[0.04] text-white/70 hover:bg-white/10 hover:text-white"
              }`}
            >
              Account
            </button>
            {PROJECTS.map((feature) => (
              <button
                key={feature.featureKey}
                type="button"
                onClick={() => feature.featureKey && setActiveFeatureKey(feature.featureKey)}
                className={`mb-2 block w-full border px-3 py-2 text-left font-sans text-[0.68rem] uppercase tracking-[0.14em] transition-colors ${
                  activeFeatureKey === feature.featureKey ? "border-white bg-white text-black" : "border-white/15 bg-white/[0.04] text-white/70 hover:bg-white/10 hover:text-white"
                }`}
              >
                {feature.title}
              </button>
            ))}
          </nav>
          )}

          <main className="p-4 font-sans md:p-5">
            {activeFeatureKey === "ai_pipeline" ? (
              <AiMentorPipeline />
            ) : activeFeatureKey === "coding" ? (
              <CodingHarnessWorkspace
                code={code}
                loadProblems={loadProblems}
                onSelectProblem={selectCodingProblem}
                problems={state.problems ?? []}
                runCoding={runCoding}
                analyzeProctoringFrame={analyzeProctoringFrame}
                selectedLanguage={selectedCodingLanguage}
                selectedProblemId={selectedProblemId}
                setCode={setCode}
                setSelectedLanguage={selectCodingLanguage}
                status={status}
                submission={state.coding}
                adaptiveFocusSkills={adaptiveCodingIntent?.focusSkills}
                adaptiveSummary={adaptiveCodingIntent?.summary}
              />
            ) : (
              <>
            <div className="grid gap-2 sm:grid-cols-2 md:grid-cols-4">
              <Metric label="API" value={API_BASE_URL.replace("http://", "")} />
              <Metric label="Student" value={state.session ? `#${state.session.studentId}` : "New"} />
              <Metric label="Ready" value={pct(state.score?.trust_score.overall_readiness)} />
              <Metric label="Risk" value={pct(state.score?.trust_score.bluff_index)} />
            </div>

            <p className="mt-4 max-w-4xl border-y border-white/15 bg-black/18 py-3 text-sm leading-6 text-white/78 backdrop-blur-[2px]">
              {activeFeatureKey === "account"
                ? "Create or resume a demo student account, then every feature syncs against the same backend student, evidence, assessment, roadmap, and stamp state."
                : selectedFeature?.subtext}
            </p>

            <div className="mt-4 flex flex-wrap items-center gap-2">
              <button
                type="button"
                onClick={runCurrent}
                className="border border-white bg-white px-4 py-2 text-xs uppercase tracking-[0.18em] text-black shadow-[4px_4px_0_rgba(255,255,255,0.08)] transition-transform hover:-translate-y-0.5"
              >
                Sync Backend
              </button>
              {activeFeatureKey === "github" && (
                <>
                  <input
                    value={githubUsername}
                    onChange={(event) => setGithubUsername(event.target.value)}
                    className="border border-white/18 bg-white/[0.07] px-3 py-2 text-sm text-white outline-none placeholder:text-white/35 focus:bg-white/[0.12]"
                    placeholder="GitHub username"
                  />
                  <input
                    ref={githubTokenRef}
                    className="w-64 border border-white/18 bg-white/[0.07] px-3 py-2 text-sm text-white outline-none placeholder:text-white/35 focus:bg-white/[0.12]"
                    placeholder="Optional GitHub token for private repos"
                    type="password"
                    autoComplete="off"
                    spellCheck={false}
                  />
                  <label className="flex items-center gap-2 border border-white/18 bg-white/[0.05] px-3 py-2 text-[0.65rem] uppercase tracking-[0.14em] text-white/75">
                    <input
                      type="checkbox"
                      checked={includePrivateRepos}
                      onChange={(event) => setIncludePrivateRepos(event.target.checked)}
                      className="h-3 w-3 accent-white"
                    />
                    Private
                  </label>
                </>
              )}
              {activeFeatureKey === "jobs" && (
                <>
                  <input
                    value={jobLocation}
                    onChange={(event) => setJobLocation(event.target.value)}
                    className="border border-white/18 bg-white/[0.07] px-3 py-2 text-sm text-white outline-none placeholder:text-white/35 focus:bg-white/[0.12]"
                    placeholder="Location"
                  />
                  <select
                    value={jobRemote}
                    onChange={(event) => setJobRemote(event.target.value as "any" | "remote" | "onsite")}
                    className="border border-white/18 bg-black/70 px-3 py-2 text-sm text-white"
                  >
                    <option value="any">Remote + Onsite</option>
                    <option value="remote">Remote only</option>
                    <option value="onsite">Onsite only</option>
                  </select>
                  <label className="flex items-center gap-2 border border-white/18 bg-white/[0.05] px-3 py-2 text-[0.65rem] uppercase tracking-[0.14em] text-white/75">
                    Min {jobMinScore}
                    <input
                      type="range"
                      min="0"
                      max="90"
                      step="5"
                      value={jobMinScore}
                      onChange={(event) => setJobMinScore(Number(event.target.value))}
                      className="w-24 accent-white"
                    />
                  </label>
                </>
              )}
              {activeFeatureKey === "coding" && (
                <>
                  <button
                    type="button"
                    onClick={() => window.open(HARNESS_APP_URL, "_blank", "noopener,noreferrer")}
                    className="border border-emerald-300/70 bg-emerald-300 px-3 py-2 text-xs uppercase tracking-[0.14em] text-black transition-transform hover:-translate-y-0.5"
                  >
                    Open Judge0 IDE
                  </button>
                  <button
                    type="button"
                    onClick={() => void loadProblems()}
                    className="border border-white/18 bg-white/[0.05] px-3 py-2 text-xs uppercase tracking-[0.14em] text-white/75 transition-colors hover:bg-white/10 hover:text-white"
                  >
                    Load Problems
                  </button>
                  <select
                    value={selectedProblemId}
                    onChange={(event) => setSelectedProblemId(event.target.value)}
                    className="border border-white/18 bg-black/70 px-3 py-2 text-sm text-white"
                  >
                    {(state.problems ?? []).map((problem) => (
                      <option key={problem.problem_id} value={problem.problem_id}>
                        {problem.title}
                      </option>
                    ))}
                  </select>
                </>
              )}
              <span className="border border-white/15 bg-white/[0.04] px-3 py-2 text-[0.65rem] uppercase tracking-[0.16em] text-white/60">
                {status}
              </span>
            </div>

            {activeFeatureKey === "coding" && (
              <textarea
                value={code}
                onChange={(event) => setCode(event.target.value)}
                spellCheck={false}
                className="mt-4 h-44 w-full border border-white/18 bg-black/45 p-3 font-mono text-xs text-white outline-none"
              />
            )}

            <ResultPanels activeFeatureKey={activeFeatureKey} state={state} />
              </>
            )}
          </main>
        </div>
      </section>
    </div>
  );
};

const Metric = ({ label, value }: { label: string; value: string }) => (
  <motion.div
    className="relative overflow-hidden rounded-2xl border border-white/[0.08] bg-white/[0.025] px-4 py-3 backdrop-blur-xl"
    initial={{ opacity: 0, y: 14 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ duration: 0.45, ease: [0.16, 1, 0.3, 1] }}
    whileHover={{ y: -2, borderColor: "rgba(255,255,255,0.22)" }}
  >
    <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-white/30 to-transparent" />
    <div className="text-[0.62rem] uppercase tracking-[0.18em] text-white/45">{label}</div>
    <div className="mt-1 truncate text-sm font-semibold leading-none">{value}</div>
  </motion.div>
);

interface CodingWorkspaceProps {
  code: string;
  loadProblems: () => Promise<CodingProblem[]>;
  problems: CodingProblem[];
  runCoding: () => void;
  selectedProblemId: string;
  setCode: (code: string) => void;
  setSelectedProblemId: (problemId: string) => void;
  status: string;
  submission?: CodingSubmissionResponse;
}

const difficultyStyles: Record<string, string> = {
  easy: "bg-emerald-400/10 text-emerald-300",
  medium: "bg-amber-400/10 text-amber-300",
  hard: "bg-rose-400/10 text-rose-300",
};

export const LegacyCodingWorkspace = ({
  code,
  loadProblems,
  problems,
  runCoding,
  selectedProblemId,
  setCode,
  setSelectedProblemId,
  status,
  submission,
}: CodingWorkspaceProps) => {
  const selectedProblem = problems.find((problem) => problem.problem_id === selectedProblemId) ?? problems[0];
  const publicResults = submission?.public_results ?? [];
  const totalVisibleCases = publicResults.length + (submission?.hidden_total_count ?? 0);
  const passedVisibleCases = publicResults.filter((result) => result.passed).length + (submission?.hidden_passed_count ?? 0);

  return (
    <div className="grid h-[calc(100dvh-13rem)] min-h-[38rem] overflow-hidden border border-white/12 bg-[#0f1117] text-[#eff1f6] lg:grid-cols-[17rem_minmax(0,1fr)_minmax(26rem,0.92fr)]">
      <aside className="hidden border-r border-white/10 bg-[#161922] lg:block">
        <div className="border-b border-white/10 px-4 py-3">
          <div className="text-sm font-semibold">Problem List</div>
          <button
            type="button"
            onClick={() => void loadProblems()}
            className="mt-3 inline-flex items-center gap-2 rounded-md border border-white/12 bg-[#232734] px-3 py-2 text-xs text-white/75 transition-colors hover:bg-[#2b3040]"
          >
            <Play className="h-3.5 w-3.5" />
            Refresh
          </button>
        </div>
        <div className="h-[calc(100%-4.75rem)] overflow-y-auto p-2">
          {problems.map((problem, index) => (
            <button
              key={problem.problem_id}
              type="button"
              onClick={() => setSelectedProblemId(problem.problem_id)}
              className={`mb-1 grid w-full grid-cols-[1.6rem_1fr_auto] items-center gap-2 rounded-md px-3 py-2 text-left text-sm transition-colors ${
                selectedProblem?.problem_id === problem.problem_id ? "bg-[#2b3040] text-white" : "text-white/70 hover:bg-[#202431] hover:text-white"
              }`}
            >
              <span className="font-mono text-xs text-white/40">{index + 1}</span>
              <span className="truncate">{problem.title}</span>
              <span className={`rounded px-2 py-0.5 text-[0.65rem] capitalize ${difficultyStyles[problem.difficulty] ?? "bg-white/10 text-white/70"}`}>
                {problem.difficulty}
              </span>
            </button>
          ))}
        </div>
      </aside>

      <section className="overflow-y-auto border-r border-white/10 bg-[#ffffff] text-[#1f2328]">
        <div className="sticky top-0 z-10 flex items-center justify-between border-b border-slate-200 bg-white px-5 py-3">
          <div className="flex items-center gap-2 text-sm text-slate-500">
            <span>Description</span>
            <span>Solutions</span>
            <span>Submissions</span>
          </div>
          <button
            type="button"
            onClick={() => window.open(HARNESS_APP_URL, "_blank", "noopener,noreferrer")}
            className="inline-flex items-center gap-2 rounded-md border border-slate-200 px-3 py-2 text-xs font-medium text-slate-700 hover:bg-slate-50"
          >
            <ExternalLink className="h-3.5 w-3.5" />
            Judge0 IDE
          </button>
        </div>
        <div className="px-6 py-5">
          <h3 className="text-2xl font-semibold tracking-normal text-slate-950">
            {selectedProblem?.title ?? "Load a problem"}
          </h3>
          {selectedProblem && (
            <>
              <div className="mt-3 flex flex-wrap items-center gap-2">
                <span className={`rounded px-2.5 py-1 text-xs capitalize ${difficultyStyles[selectedProblem.difficulty] ?? "bg-slate-100 text-slate-600"}`}>
                  {selectedProblem.difficulty}
                </span>
                {selectedProblem.skill_tags.map((tag) => (
                  <span key={tag} className="rounded bg-slate-100 px-2.5 py-1 text-xs text-slate-600">
                    {tag}
                  </span>
                ))}
              </div>
              <p className="mt-5 text-[0.95rem] leading-7 text-slate-700">{selectedProblem.statement}</p>
              <div className="mt-6 space-y-4">
                {selectedProblem.examples.map((example, index) => (
                  <div key={`${selectedProblem.problem_id}-${index}`} className="rounded-md border border-slate-200 bg-slate-50 p-4">
                    <div className="text-sm font-semibold text-slate-900">Example {index + 1}</div>
                    <pre className="mt-3 overflow-x-auto rounded bg-white p-3 font-mono text-xs leading-6 text-slate-800">
{`Input: ${JSON.stringify(example.input)}
Output: ${JSON.stringify(example.expected)}`}
                    </pre>
                  </div>
                ))}
              </div>
              <div className="mt-6">
                <h4 className="text-sm font-semibold text-slate-950">Constraints</h4>
                <ul className="mt-3 space-y-2 text-sm text-slate-600">
                  <li>Define a function named <code className="rounded bg-slate-100 px-1.5 py-0.5 font-mono">{selectedProblem.function_name}</code>.</li>
                  <li>Hidden tests are kept server-side and are not sent to the browser.</li>
                  <li>Imports and risky runtime calls are blocked before judging.</li>
                </ul>
              </div>
            </>
          )}
        </div>
      </section>

      <section className="flex min-h-0 flex-col bg-[#0f1117]">
        <div className="flex items-center justify-between border-b border-white/10 bg-[#161922] px-4 py-3">
          <div className="flex items-center gap-2">
            <span className="rounded-md bg-[#2b3040] px-3 py-1.5 text-xs font-medium text-white">Python</span>
            <span className="text-xs text-white/45">{status}</span>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={runCoding}
              className="inline-flex items-center gap-2 rounded-md bg-[#2b3040] px-3 py-2 text-xs font-semibold text-white transition-colors hover:bg-[#363d51]"
            >
              <Play className="h-3.5 w-3.5" />
              Run
            </button>
            <button
              type="button"
              onClick={runCoding}
              className="inline-flex items-center gap-2 rounded-md bg-emerald-500 px-3 py-2 text-xs font-semibold text-black transition-colors hover:bg-emerald-400"
            >
              <Send className="h-3.5 w-3.5" />
              Submit
            </button>
          </div>
        </div>

        <textarea
          value={code}
          onChange={(event) => setCode(event.target.value)}
          spellCheck={false}
          className="min-h-0 flex-1 resize-none border-0 bg-[#0f1117] p-5 font-mono text-[0.82rem] leading-6 text-[#d7dae2] outline-none"
        />

        <div className="h-64 border-t border-white/10 bg-[#161922]">
          <div className="flex items-center justify-between border-b border-white/10 px-4 py-3">
            <div className="flex items-center gap-3 text-sm">
              <span className="font-semibold text-white">Testcase</span>
              <span className="text-white/45">Result</span>
            </div>
            {submission && (
              <span className="rounded-md bg-white/5 px-3 py-1.5 text-xs text-white/70">
                {passedVisibleCases}/{totalVisibleCases} passed
              </span>
            )}
          </div>
          <div className="h-[calc(100%-3.2rem)] overflow-y-auto p-4">
            {!submission && (
              <div className="flex h-full items-center justify-center rounded-md border border-dashed border-white/12 text-sm text-white/45">
                Run or submit to see test results.
              </div>
            )}
            {submission && (
              <div className="space-y-3">
                <div className={`flex items-center gap-2 text-sm font-semibold ${submission.passed ? "text-emerald-300" : "text-rose-300"}`}>
                  {submission.passed ? <CheckCircle2 className="h-4 w-4" /> : <XCircle className="h-4 w-4" />}
                  {submission.passed ? "Accepted" : "Wrong Answer"} · Score {submission.score}/100
                </div>
                {publicResults.map((result) => (
                  <div key={result.name} className="rounded-md border border-white/10 bg-[#0f1117] p-3">
                    <div className="flex items-center justify-between text-sm">
                      <span className="font-medium text-white">{result.name}</span>
                      <span className={result.passed ? "text-emerald-300" : "text-rose-300"}>{result.passed ? "Passed" : "Failed"}</span>
                    </div>
                    <pre className="mt-2 overflow-x-auto rounded bg-black/30 p-3 font-mono text-xs leading-5 text-white/65">
{`Input: ${JSON.stringify(result.input)}
Expected: ${JSON.stringify(result.expected)}
Actual: ${JSON.stringify(result.actual ?? result.error)}`}
                    </pre>
                  </div>
                ))}
                <div className="flex items-center gap-2 rounded-md border border-white/10 bg-[#0f1117] p-3 text-sm text-white/70">
                  <ShieldCheck className="h-4 w-4 text-emerald-300" />
                  Hidden tests passed: {submission.hidden_passed_count}/{submission.hidden_total_count}
                </div>
              </div>
            )}
          </div>
        </div>
      </section>
    </div>
  );
};

const ResultPanels = ({ activeFeatureKey, state }: { activeFeatureKey: string; state: FeatureState }) => {
  const showIntake = state.intake && (activeFeatureKey === "account" || activeFeatureKey === "intake");
  const showResume = activeFeatureKey === "resume" && state.resume;
  const showAts = activeFeatureKey === "resume" && state.ats;
  const showGithub = activeFeatureKey === "github" && state.github;
  const showCoding = activeFeatureKey === "coding" && state.coding;
  const showAssessmentScore = activeFeatureKey === "assessment" && state.score;
  const showAssessmentRoadmap = activeFeatureKey === "assessment" && state.roadmap;
  const showScore = activeFeatureKey === "score" && state.score;
  const showRoadmap = activeFeatureKey === "roadmap" && state.roadmap;
  const showSkillRoadmap = activeFeatureKey === "roadmap" && state.skillRoadmap;
  const showStamp = activeFeatureKey === "stamp" && state.stamp;
  const showJobs = activeFeatureKey === "jobs" && state.jobs;

  return (
    <div className="mt-5 grid gap-3 md:grid-cols-2">
    {showIntake && state.intake && (
      <Panel title="Verification Plan">
        {state.intake.assessment_plan.stages.map((stage) => (
          <Line key={stage.stage_id} label={`${stage.difficulty} / ${stage.time_limit_minutes} min`} value={stage.focus_skills.join(", ")} />
        ))}
      </Panel>
    )}

    {showResume && state.resume && (
      <Panel title="Resume Analysis">
        <Line label="Role" value={state.resume.inferred_target_role} />
        <Line label="Claims" value={state.resume.claimed_skills.join(", ")} />
        <Line label="Projects" value={String(state.resume.project_count)} />
        <Line label="Risks" value={state.resume.risk_flags.join(", ") || "None"} />
      </Panel>
    )}

    {showAts && state.ats && (
      <Panel title="ATS Guidance">
        <Line label="Score" value={`${state.ats.ats_score}/100`} />
        <Line label="Missing" value={state.ats.missing_keywords.join(", ") || "None"} />
        {state.ats.recommendations.map((item) => <p key={item} className="mt-2 text-sm">{item}</p>)}
      </Panel>
    )}

    {showGithub && state.github && (
      <Panel title="GitHub Projects">
        <Line label="Access" value={`${state.github.access_scope}${state.github.rate_limit_remaining !== null ? ` / ${state.github.rate_limit_remaining} API calls left` : ""}`} />
        <Line label="Repos" value={`${state.github.original_repo_count} original / ${state.github.repo_count} total / ${state.github.private_repo_count} private`} />
        <Line label="Commits" value={`${state.github.authored_commit_count}/${state.github.total_commits_analyzed} authored analyzed`} />
        <Line label="Stars" value={`${state.github.total_stars} stars / ${state.github.total_forks} forks`} />
        <Line label="Languages" value={state.github.top_languages.join(", ") || "Unknown"} />
        {state.github.contribution_summary.map((item) => (
          <p key={item} className="mt-2 text-sm text-white/72">{item}</p>
        ))}
      </Panel>
    )}

    {showGithub && state.github && state.github.repositories.length ? (
      <Panel title="Repository Evidence">
        {state.github.repositories.slice(0, 5).map((repo) => (
          <div key={repo.full_name} className="mt-3 border-t border-white/15 pt-3">
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <a href={repo.url} target="_blank" className="font-semibold text-white underline-offset-2 hover:underline">
                {repo.name}
              </a>
              <span className="text-[0.65rem] uppercase tracking-[0.14em] text-white/45">
                {repo.primary_language ?? "mixed"} / {repo.authored_commit_count} commits
              </span>
            </div>
            <p className="mt-1 text-sm text-white/72">{repo.description || "No description published."}</p>
            <div className="mt-2 text-xs uppercase tracking-[0.12em] text-white/45">
              {repo.stars} stars / {repo.forks} forks / {repo.contributor_count} contributors
            </div>
          </div>
        ))}
      </Panel>
    ) : null}

    {showGithub && state.github && state.github.recent_commits.length ? (
      <Panel title="Recent Commits">
        {state.github.recent_commits.slice(0, 5).map((commit) => (
          <div key={`${commit.repo}-${commit.sha}`} className="mt-3 border-t border-white/15 pt-3">
            <div className="text-[0.65rem] uppercase tracking-[0.14em] text-white/45">
              {commit.repo} / {commit.sha}
            </div>
            {commit.url ? (
              <a href={commit.url} target="_blank" className="mt-1 block text-sm font-semibold text-white underline-offset-2 hover:underline">
                {commit.message}
              </a>
            ) : (
              <div className="mt-1 text-sm font-semibold">{commit.message}</div>
            )}
            <div className="mt-1 text-xs text-white/45">{commit.authored_at ?? "No commit date"}</div>
          </div>
        ))}
      </Panel>
    ) : null}

    {showGithub && state.github && (
      <Panel title="Project Upgrades">
        {state.github.project_recommendations.map((item) => (
          <div key={item.title} className="mt-3 border-t border-white/15 pt-3">
            <div className="font-semibold">{item.title}</div>
            <p className="mt-1 text-sm text-white/72">{item.rationale}</p>
            <p className="mt-2 text-xs uppercase tracking-[0.12em] text-white/45">
              Evidence: {item.evidence_repo_names.join(", ") || "No repo selected"}
            </p>
          </div>
        ))}
      </Panel>
    )}

    {showCoding && state.coding && (
      <Panel title="Coding Harness">
        <Line label="Score" value={`${state.coding.score}/100`} />
        <Line label="Hidden Tests" value={`${state.coding.hidden_passed_count}/${state.coding.hidden_total_count}`} />
        {state.coding.public_results.map((result) => (
          <Line key={result.name} label={result.name} value={result.passed ? "pass" : result.error ?? "fail"} />
        ))}
      </Panel>
    )}

    {activeFeatureKey === "coding" && (
      <Panel title="Hardened Runner">
        <Line label="Engine" value="Judge0 CE self-host + Judge0 IDE launcher" />
        <Line label="Repos" value="Cloned into external/judge0 and external/judge0-ide" />
        <p className="mt-3 text-sm text-white/72">
          Use Judge0 for sandboxed multi-language execution, keep hidden tests on our backend, and record integrity flags with each submission.
        </p>
        <div className="mt-3 flex flex-wrap gap-2 text-xs uppercase tracking-[0.12em]">
          <a href={JUDGE0_GITHUB_URL} target="_blank" className="border border-white/15 px-3 py-2 text-white/75 hover:bg-white/10">
            Judge0 API
          </a>
          <a href={JUDGE0_IDE_GITHUB_URL} target="_blank" className="border border-white/15 px-3 py-2 text-white/75 hover:bg-white/10">
            Judge0 IDE
          </a>
        </div>
      </Panel>
    )}

    {(showAssessmentScore || showScore) && state.score && (
      <Panel title="Trust Score">
        <Line label="Readiness" value={`${pct(state.score.trust_score.overall_readiness)} / ${state.score.trust_score.readiness_band}`} />
        <Line label="Evidence" value={pct(state.score.trust_score.evidence_alignment)} />
        <Line label="Bluff Risk" value={`${pct(state.score.trust_score.bluff_index)} / ${state.score.trust_score.risk_band}`} />
        {state.score.trust_score.explanations.map((item) => <p key={item} className="mt-2 text-sm text-white/72">{item}</p>)}
      </Panel>
    )}

    {(showAssessmentRoadmap || showRoadmap) && state.roadmap && (
      <Panel title="Roadmap">
        <p className="text-sm text-white/72">{state.roadmap.summary}</p>
        {state.roadmap.nodes.slice(0, 5).map((node) => (
          <Line key={node.node_id} label={node.status} value={node.title} />
        ))}
      </Panel>
    )}

    {showSkillRoadmap && state.skillRoadmap && (
      <Panel title="Generated Skill Roadmap">
        <Line label="Gaps" value={state.skillRoadmap.skill_gaps.join(", ")} />
        <Line label="Progress" value={`${Math.round(state.skillRoadmap.overall_progress_percent)}%`} />
        {state.skillRoadmap.roadmap.slice(0, 4).map((item) => (
          <div key={item.skill} className="mt-3 border-t border-white/15 pt-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="font-semibold">{item.skill}</div>
              <span className="text-[0.65rem] uppercase tracking-[0.14em] text-white/45">{item.priority} / {item.duration}</span>
            </div>
            <p className="mt-1 text-sm text-white/72">{item.reason}</p>
            <p className="mt-2 border border-emerald-200/20 bg-emerald-300/10 p-2 text-sm text-emerald-100">{item.job_impact.summary}</p>
            <p className="mt-2 text-sm text-white/68">{item.project}</p>
          </div>
        ))}
      </Panel>
    )}

    {showStamp && state.stamp && (
      <Panel title="Trust Stamp">
        <Line label="Signature" value={state.stampValid ? "valid" : "not checked"} />
        <Line label="Readiness" value={String(state.stamp.overall_readiness ?? "--")} />
        <Line label="Summary" value={String(state.stamp.visible_summary ?? "Consent-based profile loaded")} />
      </Panel>
    )}

    {activeFeatureKey === "jobs" && (
      <Panel title="Matching Engine">
        <Line label="Formula" value="0.4 skill + 0.2 test + 0.2 ATS + 0.2 trust" />
        <Line label="Profile Role" value={state.jobs?.profile_role ?? "Saved resume role"} />
        <Line label="Source" value={state.jobs?.source ?? "JSearch when API key exists, fallback otherwise"} />
        <p className="mt-3 text-sm text-white/72">
          Listings are fetched, skill keywords are extracted from descriptions, and each card explains matched and missing skills.
        </p>
      </Panel>
    )}

    {showJobs && state.jobs && (
      <div className="md:col-span-2">
        <JobsThatSuitYouPanel jobs={state.jobs.jobs} />
      </div>
    )}
    </div>
  );
};

const JobsThatSuitYouPanel = ({ jobs }: { jobs: MatchedJob[] }) => (
  <motion.section
    className="relative overflow-hidden rounded-[2rem] border border-white/[0.08] bg-white/[0.025] p-5 shadow-[0_24px_80px_rgba(0,0,0,0.32)] backdrop-blur-xl"
    initial={{ opacity: 0, y: 28 }}
    whileInView={{ opacity: 1, y: 0 }}
    viewport={{ once: true, margin: "-80px" }}
    transition={{ duration: 0.55, ease: [0.16, 1, 0.3, 1] }}
  >
    <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-emerald-200/40 to-transparent" />
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div>
        <div className="text-[0.65rem] uppercase tracking-[0.2em] text-emerald-100/60">Ranked Recommendations</div>
        <h3 className="mt-2 font-serif text-3xl leading-none text-white">Jobs That Suit You</h3>
      </div>
      <span className="border border-emerald-200/30 bg-emerald-300/10 px-3 py-2 text-xs uppercase tracking-[0.14em] text-emerald-100">
        {jobs.length} matches
      </span>
    </div>

    <div className="mt-5 grid gap-3 lg:grid-cols-2">
      {jobs.map((job) => (
        <article key={job.job_id} className="border border-white/10 bg-black/24 p-4 transition-colors hover:border-white/24 hover:bg-white/[0.045]">
          <div className="flex items-start justify-between gap-4">
            <div>
              <div className="flex items-center gap-2 text-[0.65rem] uppercase tracking-[0.16em] text-white/42">
                <BriefcaseBusiness className="h-3.5 w-3.5" />
                {job.company}
              </div>
              <h4 className="mt-2 text-lg font-semibold leading-tight text-white">{job.title}</h4>
              <div className="mt-2 flex items-center gap-2 text-xs text-white/48">
                <MapPin className="h-3.5 w-3.5" />
                {job.location} / {job.remote ? "Remote" : "Onsite"}
              </div>
            </div>
            <div className="min-w-16 border border-emerald-200/25 bg-emerald-300/10 px-3 py-2 text-center">
              <div className="text-2xl font-semibold leading-none text-emerald-100">{Math.round(job.match_score)}</div>
              <div className="mt-1 text-[0.55rem] uppercase tracking-[0.13em] text-emerald-100/55">Match</div>
            </div>
          </div>
          <div className="mt-4 h-1 bg-white/10">
            <div className="h-full bg-emerald-200" style={{ width: `${Math.min(100, Math.max(0, job.match_score))}%` }} />
          </div>
          <p className="mt-3 text-sm leading-6 text-white/68">{job.explanation}</p>
          <div className="mt-3 flex flex-wrap gap-2">
            {job.matched_skills.slice(0, 6).map((skill) => (
              <span key={skill} className="border border-emerald-200/25 bg-emerald-300/10 px-2 py-1 text-[0.68rem] text-emerald-100">{skill}</span>
            ))}
            {job.missing_skills.slice(0, 4).map((skill) => (
              <span key={skill} className="border border-amber-200/20 bg-amber-300/10 px-2 py-1 text-[0.68rem] text-amber-100">{skill}</span>
            ))}
          </div>
          <div className="mt-3 flex flex-wrap items-center justify-between gap-2 text-xs text-white/45">
            <span>Skill match {Math.round(job.skill_match_percent)}%</span>
            {job.apply_url ? (
              <a
                href={job.apply_url}
                target="_blank"
                rel="noopener noreferrer"
                className="border border-emerald-200/35 bg-emerald-300/10 px-3 py-2 uppercase tracking-[0.12em] text-emerald-100 hover:bg-emerald-200 hover:text-black"
              >
                Apply Now
              </a>
            ) : (
              <span className="border border-white/10 px-3 py-2 uppercase tracking-[0.12em]">No apply link</span>
            )}
          </div>
        </article>
      ))}
    </div>
  </motion.section>
);

const Panel = ({ title, children }: { title: string; children: ReactNode }) => {
  const x = useMotionValue(0);
  const y = useMotionValue(0);
  const mouseX = useMotionValue(0);
  const mouseY = useMotionValue(0);
  const rotateX = useTransform(y, [-0.5, 0.5], ["4deg", "-4deg"]);
  const rotateY = useTransform(x, [-0.5, 0.5], ["-4deg", "4deg"]);

  const handleMouseMove = (event: MouseEvent<HTMLDivElement>) => {
    const rect = event.currentTarget.getBoundingClientRect();
    const mouseXPos = event.clientX - rect.left;
    const mouseYPos = event.clientY - rect.top;

    x.set(mouseXPos / rect.width - 0.5);
    y.set(mouseYPos / rect.height - 0.5);
    mouseX.set(mouseXPos);
    mouseY.set(mouseYPos);
  };

  const handleMouseLeave = () => {
    x.set(0);
    y.set(0);
  };

  return (
    <motion.section
      style={{ rotateX, rotateY, transformStyle: "preserve-3d" }}
      className="group relative min-h-[13rem] overflow-hidden rounded-[2rem] border border-white/[0.08] bg-white/[0.025] p-5 shadow-[0_24px_80px_rgba(0,0,0,0.32)] backdrop-blur-xl perspective-[1000px]"
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      initial={{ opacity: 0, y: 36, scale: 0.97 }}
      whileInView={{ opacity: 1, y: 0, scale: 1 }}
      viewport={{ once: true, margin: "-80px" }}
      transition={{ duration: 0.65, ease: [0.16, 1, 0.3, 1] }}
      whileHover={{ borderColor: "rgba(255,255,255,0.22)" }}
    >
      <motion.div
        className="pointer-events-none absolute -inset-px rounded-[2rem] opacity-0 transition duration-500 group-hover:opacity-100"
        style={{
          background: useMotionTemplate`
            radial-gradient(
              560px circle at ${mouseX}px ${mouseY}px,
              rgba(255,255,255,0.10),
              transparent 78%
            )
          `,
        }}
      />
      <div className="pointer-events-none absolute inset-x-6 top-0 h-px bg-gradient-to-r from-transparent via-white/40 to-transparent" />
      <div className="pointer-events-none absolute right-0 top-0 h-28 w-28 translate-x-1/2 -translate-y-1/2 rounded-full bg-white/[0.08] blur-[56px]" />
      <div className="relative z-10 flex h-full flex-col" style={{ transform: "translateZ(28px)" }}>
        <h3 className="font-serif text-2xl leading-none text-white drop-shadow-[0_0_22px_rgba(255,255,255,0.2)]">
          {title}
        </h3>
        <div className="mt-4 text-white/82">{children}</div>
      </div>
    </motion.section>
  );
};

const Line = ({ label, value }: { label: string; value: string }) => (
  <div className="mt-2 grid grid-cols-[6.5rem_1fr] gap-3 border-t border-white/12 pt-2 text-sm">
    <span className="uppercase tracking-[0.12em] text-white/45">{label}</span>
    <span>{value}</span>
  </div>
);

export default ProductFeatureOverlay;
