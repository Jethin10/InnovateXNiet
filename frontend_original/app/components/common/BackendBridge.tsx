'use client';

import { useEffect, useState } from "react";
import {
  API_BASE_URL,
  AuthTokenResponse,
  CodingProblem,
  CodingSubmissionResponse,
  GitHubEvidenceResponse,
  StudentResponse,
  apiRequest,
  codingStarterForLanguage,
  jsonBody,
} from "@/app/lib/api";
import { DemoFlowState, checkBackendHealth, runPlacementTrustDemo } from "@/app/lib/demoFlow";

type BridgeStatus = "checking" | "online" | "running" | "complete" | "error";
type WorkbenchTab = "demo" | "code" | "github";

interface DemoSession {
  studentId: number;
  token: string;
}

const percent = (value?: number) => {
  if (typeof value !== "number") return "--";
  return `${Math.round(value * 100)}%`;
};

const defaultLanguageOptions = [
  { id: "python", label: "Python", monaco_language: "python" },
  { id: "java", label: "Java", monaco_language: "java" },
  { id: "c", label: "C", monaco_language: "c" },
  { id: "cpp", label: "C++", monaco_language: "cpp" },
  { id: "javascript", label: "JavaScript", monaco_language: "javascript" },
];

const BackendBridge = () => {
  const [status, setStatus] = useState<BridgeStatus>("checking");
  const [message, setMessage] = useState("Checking backend");
  const [flow, setFlow] = useState<DemoFlowState>({});
  const [expanded, setExpanded] = useState(false);
  const [tab, setTab] = useState<WorkbenchTab>("demo");
  const [session, setSession] = useState<DemoSession | null>(null);
  const [problems, setProblems] = useState<CodingProblem[]>([]);
  const [selectedProblemId, setSelectedProblemId] = useState("two_sum_indices");
  const [selectedLanguage, setSelectedLanguage] = useState("python");
  const [code, setCode] = useState("");
  const [submission, setSubmission] = useState<CodingSubmissionResponse | null>(null);
  const [githubUsername, setGithubUsername] = useState("octocat");
  const [githubEvidence, setGithubEvidence] = useState<GitHubEvidenceResponse | null>(null);

  useEffect(() => {
    let active = true;
    checkBackendHealth()
      .then((health) => {
        if (!active) return;
        setFlow((current) => ({ ...current, health }));
        setStatus("online");
        setMessage(`API ${health.status} / ${health.version}`);
      })
      .catch((error) => {
        if (!active) return;
        setStatus("error");
        setMessage(error instanceof Error ? error.message : "Backend offline");
      });

    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!expanded || problems.length > 0) return;
    apiRequest<CodingProblem[]>("/api/v1/coding/problems")
      .then((items) => {
        setProblems(items);
        const firstProblem = items[0];
        if (firstProblem) {
          setSelectedProblemId(firstProblem.problem_id);
          setCode(codingStarterForLanguage(firstProblem, selectedLanguage));
        }
      })
      .catch((error) => setMessage(error instanceof Error ? error.message : "Problem catalog failed"));
  }, [expanded, problems.length]);

  useEffect(() => {
    const problem = problems.find((item) => item.problem_id === selectedProblemId);
    if (problem) setCode(codingStarterForLanguage(problem, selectedLanguage));
  }, [selectedLanguage, selectedProblemId, problems]);

  const ensureDemoSession = async (): Promise<DemoSession> => {
    if (session) return session;

    const seed = Date.now();
    const email = `workbench.student.${seed}@trust.local`;
    const password = "Placement123";
    const student = await apiRequest<StudentResponse>("/api/v1/auth/register-student", {
      method: "POST",
      body: jsonBody({
        full_name: "Workbench Student",
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
    const nextSession = { studentId: student.student_id, token: login.access_token };
    setSession(nextSession);
    return nextSession;
  };

  const runDemo = async () => {
    setExpanded(true);
    setStatus("running");
    setMessage("Starting backend flow");

    try {
      const result = await runPlacementTrustDemo((step, partialState) => {
        setMessage(step);
        if (partialState) {
          setFlow((current) => ({ ...current, ...partialState }));
        }
      });
      setFlow(result);
      setStatus("complete");
      setMessage("Backend integration complete");
    } catch (error) {
      setStatus("error");
      setMessage(error instanceof Error ? error.message : "Backend flow failed");
    }
  };

  const submitCode = async () => {
    setStatus("running");
    setMessage("Running coding harness");
    setSubmission(null);

    try {
      const activeSession = await ensureDemoSession();
      const result = await apiRequest<CodingSubmissionResponse>(
        `/api/v1/students/${activeSession.studentId}/coding/submissions`,
        {
          method: "POST",
          token: activeSession.token,
          body: jsonBody({
            problem_id: selectedProblemId,
            language: selectedLanguage,
            code,
          }),
        }
      );
      setSubmission(result);
      setStatus("complete");
      setMessage(result.passed ? "Coding proof verified" : "Coding proof needs work");
    } catch (error) {
      setStatus("error");
      setMessage(error instanceof Error ? error.message : "Coding submission failed");
    }
  };

  const connectGithub = async () => {
    setStatus("running");
    setMessage("Connecting GitHub evidence");
    setGithubEvidence(null);

    try {
      const activeSession = await ensureDemoSession();
      const result = await apiRequest<GitHubEvidenceResponse>(
        `/api/v1/students/${activeSession.studentId}/evidence/github`,
        {
          method: "POST",
          token: activeSession.token,
          body: jsonBody({ username: githubUsername }),
        }
      );
      setGithubEvidence(result);
      setStatus("complete");
      setMessage("GitHub projects generated");
    } catch (error) {
      setStatus("error");
      setMessage(error instanceof Error ? error.message : "GitHub connection failed");
    }
  };

  const isBusy = status === "running" || status === "checking";
  const selectedProblem = problems.find((problem) => problem.problem_id === selectedProblemId);

  return (
    <div className="fixed bottom-6 left-6 z-20 max-h-[calc(100dvh-3rem)] w-[min(34rem,calc(100vw-3rem))] overflow-y-auto rounded-md border border-white/30 bg-black/70 p-3 text-white shadow-lg backdrop-blur selectable">
      <button
        type="button"
        onClick={() => setExpanded((value) => !value)}
        className="flex w-full items-center justify-between gap-3 text-left"
      >
        <span>
          <span className="block text-[0.65rem] uppercase tracking-[0.2em] text-white/60">Backend</span>
          <span className="block text-sm font-semibold">{message}</span>
        </span>
        <span className={`h-2.5 w-2.5 rounded-full ${status === "error" ? "bg-red-400" : status === "complete" ? "bg-emerald-300" : "bg-amber-200"}`} />
      </button>

      {expanded && (
        <div className="mt-3 border-t border-white/15 pt-3">
          <div className="mb-3 grid grid-cols-3 gap-1 rounded bg-white/10 p-1 text-xs">
            {(["demo", "code", "github"] as WorkbenchTab[]).map((item) => (
              <button
                key={item}
                type="button"
                onClick={() => setTab(item)}
                className={`rounded px-2 py-2 font-semibold uppercase tracking-[0.12em] ${tab === item ? "bg-white text-black" : "text-white/70"}`}
              >
                {item}
              </button>
            ))}
          </div>

          {tab === "demo" && (
            <>
          <div className="grid grid-cols-3 gap-2 text-xs">
            <div className="rounded bg-white/10 p-2">
              <div className="text-white/55">Ready</div>
              <div className="mt-1 font-semibold">{percent(flow.score?.trust_score.overall_readiness)}</div>
            </div>
            <div className="rounded bg-white/10 p-2">
              <div className="text-white/55">Bluff</div>
              <div className="mt-1 font-semibold">{percent(flow.score?.trust_score.bluff_index)}</div>
            </div>
            <div className="rounded bg-white/10 p-2">
              <div className="text-white/55">Jobs</div>
              <div className="mt-1 font-semibold">{flow.jobs?.jobs.length ?? 0}</div>
            </div>
          </div>

          {flow.jobs?.jobs.length ? (
            <div className="mt-3 space-y-2">
              {flow.jobs.jobs.slice(0, 3).map((job) => (
                <div key={job.job_id} className="rounded bg-white/10 p-3 text-xs">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="font-semibold text-white">{job.title}</div>
                      <div className="mt-1 text-white/55">{job.company} / {job.location}</div>
                    </div>
                    <div className="rounded bg-emerald-300 px-2 py-1 font-semibold text-black">
                      {Math.round(job.match_score)}
                    </div>
                  </div>
                  <p className="mt-2 leading-5 text-white/68">{job.explanation}</p>
                </div>
              ))}
            </div>
          ) : null}

          <div className="mt-3 text-xs text-white/65">{API_BASE_URL}</div>

          <button
            type="button"
            onClick={runDemo}
            disabled={isBusy}
            className="mt-3 w-full rounded bg-white px-3 py-2 text-xs font-semibold uppercase tracking-[0.16em] text-black disabled:cursor-not-allowed disabled:opacity-50"
          >
            {status === "running" ? "Running" : "Run full flow"}
          </button>
            </>
          )}

          {tab === "code" && (
            <div className="space-y-3">
              <select
                value={selectedProblemId}
                onChange={(event) => setSelectedProblemId(event.target.value)}
                className="w-full rounded border border-white/15 bg-black/60 px-3 py-2 text-sm text-white"
              >
                {problems.map((problem) => (
                  <option key={problem.problem_id} value={problem.problem_id}>
                    {problem.title} / {problem.difficulty}
                  </option>
                ))}
              </select>

              {selectedProblem && (
                <div className="rounded bg-white/10 p-3 text-xs text-white/75">
                  <div className="font-semibold text-white">{selectedProblem.statement}</div>
                  <div className="mt-2">Function: {selectedProblem.function_name}</div>
                  <div className="mt-1">Skills: {selectedProblem.skill_tags.join(", ")}</div>
                </div>
              )}

              <select
                value={selectedLanguage}
                onChange={(event) => setSelectedLanguage(event.target.value)}
                className="w-full rounded border border-white/15 bg-black/60 px-3 py-2 text-sm text-white"
              >
                {(selectedProblem?.supported_languages?.length ? selectedProblem.supported_languages : defaultLanguageOptions).map((language) => (
                  <option key={language.id} value={language.id}>
                    {language.label}
                  </option>
                ))}
              </select>

              <textarea
                value={code}
                onChange={(event) => setCode(event.target.value)}
                spellCheck={false}
                className="h-44 w-full rounded border border-white/15 bg-black/70 p-3 font-mono text-xs text-white outline-none"
              />

              <button
                type="button"
                onClick={submitCode}
                disabled={isBusy || !selectedProblem}
                className="w-full rounded bg-white px-3 py-2 text-xs font-semibold uppercase tracking-[0.16em] text-black disabled:cursor-not-allowed disabled:opacity-50"
              >
                Submit to harness
              </button>

              {submission && (
                <div className="rounded bg-white/10 p-3 text-xs">
                  <div className="flex justify-between text-sm font-semibold">
                    <span>{submission.passed ? "Verified" : "Not verified yet"}</span>
                    <span>{submission.score}/100</span>
                  </div>
                  <div className="mt-2 text-white/70">
                    Hidden tests: {submission.hidden_passed_count}/{submission.hidden_total_count}
                  </div>
                  {submission.public_results.map((result) => (
                    <div key={result.name} className="mt-2 rounded bg-black/35 p-2">
                      <div className="font-semibold">{result.name}: {result.passed ? "pass" : "fail"}</div>
                      {result.error && <div className="mt-1 text-red-200">{result.error}</div>}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {tab === "github" && (
            <div className="space-y-3">
              <div className="flex gap-2">
                <input
                  value={githubUsername}
                  onChange={(event) => setGithubUsername(event.target.value)}
                  className="min-w-0 flex-1 rounded border border-white/15 bg-black/60 px-3 py-2 text-sm text-white outline-none"
                  placeholder="GitHub username"
                />
                <button
                  type="button"
                  onClick={connectGithub}
                  disabled={isBusy || !githubUsername.trim()}
                  className="rounded bg-white px-3 py-2 text-xs font-semibold uppercase tracking-[0.14em] text-black disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Connect
                </button>
              </div>

              {githubEvidence && (
                <div className="rounded bg-white/10 p-3 text-xs">
                  <div className="grid grid-cols-3 gap-2">
                    <div>
                      <div className="text-white/55">Repos</div>
                      <div className="font-semibold">{githubEvidence.repo_count}</div>
                    </div>
                    <div>
                      <div className="text-white/55">Original</div>
                      <div className="font-semibold">{githubEvidence.original_repo_count}</div>
                    </div>
                    <div>
                      <div className="text-white/55">Followers</div>
                      <div className="font-semibold">{githubEvidence.followers ?? 0}</div>
                    </div>
                  </div>

                  <div className="mt-3 text-white/70">{githubEvidence.top_languages.join(" / ") || "No languages detected"}</div>

                  {githubEvidence.project_recommendations.map((recommendation) => (
                    <div key={recommendation.title} className="mt-3 rounded bg-black/35 p-3">
                      <div className="text-sm font-semibold">{recommendation.title}</div>
                      <div className="mt-1 text-white/70">{recommendation.rationale}</div>
                      <ul className="mt-2 list-disc space-y-1 pl-4 text-white/75">
                        {recommendation.suggested_scope.map((scope) => (
                          <li key={scope}>{scope}</li>
                        ))}
                      </ul>
                      <div className="mt-2 text-white/50">
                        Evidence: {recommendation.evidence_repo_names.join(", ")}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default BackendBridge;
