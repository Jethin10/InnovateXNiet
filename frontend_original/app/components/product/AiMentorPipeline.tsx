"use client";

import { useMemo, useState } from "react";
import type { ReactNode } from "react";
import { BrainCircuit, CheckCircle2, FileText, Gauge, Play, ShieldCheck, Sparkles, Upload } from "lucide-react";
import {
  AdaptiveTestEvaluationResponse,
  AdaptiveTestGenerateResponse,
  AiResumeAnalyzeResponse,
  ApiError,
  CodingProblem,
  FinalEmployabilityReportResponse,
  RecommendedJobInput,
  ScoreExplanation,
  SkillRoadmapResponse,
  apiRequest,
  jsonBody,
} from "@/app/lib/api";
import { useFeatureStore } from "@stores";

const sampleResume = `Skills: Python, React, SQL, APIs, Data Structures
Projects: Built a placement analytics dashboard using React, FastAPI and SQL for 1,000 students.
Projects: Created a coding profile tracker with GitHub evidence and ATS scoring.
Experience: Implemented REST APIs, optimized database queries, and designed dashboards.
Education: B.Tech Computer Science`;

const answerHints: Record<string, string> = {
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

const industryRoles = [
  "Backend SDE",
  "Frontend Developer",
  "Full Stack Developer",
  "AI/ML Engineer",
  "ML Engineer",
  "Data Analyst",
  "DevOps Engineer",
  "Cloud Engineer",
  "Cybersecurity Analyst",
  "QA Automation Engineer",
  "Mobile App Developer",
];

const ADAPTIVE_CODING_TEST_KEY = "placement-trust-adaptive-coding-test";

export default function AiMentorPipeline() {
  const setActiveFeatureKey = useFeatureStore((state) => state.setActiveFeatureKey);
  const [resumeText, setResumeText] = useState(() => {
    if (typeof window === "undefined") return sampleResume;
    const saved = window.sessionStorage.getItem("ai-mentor-resume-text");
    return saved || sampleResume;
  });
  const [selectedRole, setSelectedRole] = useState("Backend SDE");
  const [status, setStatus] = useState("Ready");
  const [analysis, setAnalysis] = useState<AiResumeAnalyzeResponse | null>(null);
  const [test, setTest] = useState<AdaptiveTestGenerateResponse | null>(null);
  const [evaluation, setEvaluation] = useState<AdaptiveTestEvaluationResponse | null>(null);
  const [report, setReport] = useState<FinalEmployabilityReportResponse | null>(null);
  const [roadmap, setRoadmap] = useState<SkillRoadmapResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const pipelineReady = analysis && test && evaluation && report;
  const suggestedRoles = Array.from(new Set([...(analysis?.suggested_roles ?? []), ...industryRoles]));
  const proctoringEvents = useMemo(() => [], []);

  const uploadResume = async (file: File) => {
    try {
      setError(null);
      setStatus("Parsing resume");
      const formData = new FormData();
      formData.append("file", file);
      const parsed = await apiRequest<{ text: string }>("/api/v1/pipeline/upload-resume", { method: "POST", body: formData });
      setResumeText(parsed.text);
      saveResumeText(parsed.text);
      setStatus("Resume parsed");
    } catch (caught) {
      setStatus("Resume parsing failed");
      setError(formatPipelineError(caught));
    }
  };

  const analyzeResume = async () => {
    try {
      setError(null);
      setStatus("Finding highest ATS role");
      const roleResults = await Promise.all(
        industryRoles.map((role) =>
          apiRequest<AiResumeAnalyzeResponse>("/api/v1/pipeline/analyze-resume", {
            method: "POST",
            body: jsonBody({ resume_text: resumeText, target_role: role }),
          })
        )
      );
      const best = roleResults.reduce((winner, item) => (item.ats.score > winner.ats.score ? item : winner), roleResults[0]);
      setAnalysis(best);
      setSelectedRole(best.selected_role);
      setTest(null);
      setEvaluation(null);
      setReport(null);
      saveResumeText(resumeText);
      const generatedRoadmap = await generateRoadmapFromSignals(best, null, null, best.selected_role);
      setRoadmap(generatedRoadmap);
      setStatus("Best ATS role selected");
    } catch (caught) {
      setStatus("Resume analysis failed");
      setError(formatPipelineError(caught));
    }
  };

  const changeRole = async (nextRole: string) => {
    setSelectedRole(nextRole);
    if (!analysis) return;
    try {
      setError(null);
      setStatus(`Updating analysis for ${nextRole}`);
      const nextAnalysis = await apiRequest<AiResumeAnalyzeResponse>("/api/v1/pipeline/analyze-resume", {
        method: "POST",
        body: jsonBody({ resume_text: resumeText, target_role: nextRole }),
      });
      setAnalysis(nextAnalysis);
      setTest(null);
      setEvaluation(null);
      setReport(null);
      const generatedRoadmap = await generateRoadmapFromSignals(nextAnalysis, null, null, nextRole);
      setRoadmap(generatedRoadmap);
      setStatus(`Role changed to ${nextRole}`);
    } catch (caught) {
      setStatus("Role update failed");
      setError(formatPipelineError(caught));
    }
  };

  const generateTest = async () => {
    if (!analysis) return;
    try {
      setError(null);
      setStatus("Preparing adaptive test");
      const next = await apiRequest<AdaptiveTestGenerateResponse>("/api/v1/pipeline/generate-test", {
        method: "POST",
        body: jsonBody({
          skills: analysis.skills,
          selected_role: selectedRole,
          experience_level: analysis.experience_level,
        }),
      });
      const problems = await apiRequest<CodingProblem[]>("/api/v1/coding/problems");
      const selectedProblemIds = selectAdaptiveCodingProblemIds({ analysis, focusSkills: next.focus_skills, problems, questions: next.questions, selectedRole });
      setTest(next);
      setEvaluation(null);
      setReport(null);
      setRoadmap(null);
      if (typeof window !== "undefined") {
        window.sessionStorage.setItem(
          ADAPTIVE_CODING_TEST_KEY,
          JSON.stringify({
            role: selectedRole,
            focusSkills: next.focus_skills,
            problemIds: selectedProblemIds,
            summary: next.adaptation_summary,
            resumeSkills: analysis.skills,
            missingSkills: analysis.missing_keywords,
          })
        );
      }
      setStatus("Opening coding harness");
      setActiveFeatureKey("coding");
    } catch (caught) {
      setStatus("Test generation failed");
      setError(formatPipelineError(caught));
    }
  };

  const evaluateTest = async () => {
    if (!analysis || !test) return;
    try {
      setError(null);
      setStatus("Evaluating generated test");
      const next = await apiRequest<AdaptiveTestEvaluationResponse>("/api/v1/pipeline/evaluate-test", {
        method: "POST",
        body: jsonBody({
          selected_role: selectedRole,
          skills: analysis.skills,
          answers: test.questions.map((question, index) => ({
            question_id: question.question_id,
            submitted_answer: answerHints[question.question_id] ?? "not sure",
            elapsed_seconds: Math.min(question.max_time_seconds - 5, 24 + index * 7),
            confidence: 0.75,
            answer_changes: index % 2,
          })),
          proctoring_events: proctoringEvents,
        }),
      });
      setEvaluation(next);
      setReport(null);
      setRoadmap(null);
      setStatus("Test evaluated");
    } catch (caught) {
      setStatus("Test evaluation failed");
      setError(formatPipelineError(caught));
    }
  };

  const buildReport = async () => {
    if (!analysis || !evaluation) return;
    try {
      setError(null);
      setStatus("Building final report");
      const next = await apiRequest<FinalEmployabilityReportResponse>("/api/v1/pipeline/final-report", {
        method: "POST",
        body: jsonBody({
          resume_text: resumeText,
          selected_role: selectedRole,
          skills: analysis.skills,
          ats_score: analysis.ats.score,
          test_score: evaluation.test.score,
          trust_score: evaluation.trust.score,
          skill_breakdown: evaluation.skill_breakdown,
          proctoring_events: proctoringEvents,
        }),
      });
      setReport(next);
      const generatedRoadmap = await generateRoadmapFromSignals(analysis, evaluation, next);
      setRoadmap(generatedRoadmap);
      setStatus("Final dashboard ready");
    } catch (caught) {
      setStatus("Report generation failed");
      setError(formatPipelineError(caught));
    }
  };

  const generateRoadmapFromSignals = async (
    sourceAnalysis: AiResumeAnalyzeResponse,
    sourceEvaluation: AdaptiveTestEvaluationResponse | null,
    nextReport: FinalEmployabilityReportResponse | null,
    roleOverride = selectedRole
  ) => {
    const missingSkills = Array.from(new Set([...(nextReport?.skill_gaps ?? []), ...sourceAnalysis.missing_keywords]));
    const weakAreas = sourceEvaluation?.weak_areas ?? missingSkills.slice(0, 3);
    return apiRequest<SkillRoadmapResponse>("/api/v1/pipeline/generate-roadmap", {
      method: "POST",
      body: jsonBody({
        extracted_skills: sourceAnalysis.skills,
        missing_skills: missingSkills,
        ats_score: sourceAnalysis.ats.score,
        test_score: sourceEvaluation?.test.score ?? 0,
        weak_areas: weakAreas,
        target_role: roleOverride,
        recommended_jobs: buildRecommendedJobs(roleOverride, sourceAnalysis.suggested_roles, missingSkills, sourceAnalysis.skills),
        skill_breakdown: sourceEvaluation?.skill_breakdown ?? Object.fromEntries(weakAreas.map((skill) => [skill, 0])),
        experience_level: sourceAnalysis.experience_level,
      }),
    });
  };

  const completeTask = async (taskId: string) => {
    try {
      setError(null);
      setStatus("Updating roadmap progress");
      await apiRequest("/api/v1/pipeline/update-progress", {
        method: "POST",
        body: jsonBody({ task_id: taskId, status: "completed", proof_summary: "Completed from roadmap timeline" }),
      });
      const updated = await apiRequest<SkillRoadmapResponse>("/api/v1/pipeline/roadmap");
      setRoadmap(updated);
      setStatus("Roadmap progress updated");
    } catch (caught) {
      setStatus("Roadmap update failed");
      setError(formatPipelineError(caught));
    }
  };

  const openRoadmapHarness = (skill: string, problemIds: string[]) => {
    if (typeof window !== "undefined") {
      window.sessionStorage.setItem(
        ADAPTIVE_CODING_TEST_KEY,
        JSON.stringify({
          role: selectedRole,
          focusSkills: [skill],
          problemIds,
          summary: `Roadmap practice for ${skill}. Complete these harness tasks to prove the skill and improve job match.`,
          resumeSkills: analysis?.skills ?? [],
          missingSkills: roadmap?.skill_gaps ?? [],
        })
      );
    }
    setActiveFeatureKey("coding");
  };

  return (
    <div className="relative h-[calc(100dvh-12rem)] min-h-[44rem] overflow-hidden border border-white/15 bg-[#030304] text-white shadow-[0_30px_120px_rgba(0,0,0,0.5)]">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_14%_12%,rgba(255,255,255,0.12),transparent_28%),radial-gradient(circle_at_88%_16%,rgba(77,220,175,0.13),transparent_26%),linear-gradient(135deg,rgba(255,255,255,0.04),transparent_45%)]" />
      <div className="relative grid h-full grid-rows-[auto_1fr]">
        <header className="flex items-center justify-between border-b border-white/10 bg-black/30 px-5 py-4 backdrop-blur-md">
          <div>
            <div className="text-xs uppercase tracking-[0.22em] text-white/45">Resume to Trained Analysis to Adaptive Test to Trust Report</div>
            <h3 className="mt-1 font-serif text-3xl leading-none">AI Mentor Pipeline</h3>
          </div>
          <div className="border border-white/12 bg-white/[0.04] px-3 py-2 text-xs uppercase tracking-[0.16em] text-white/55">{status}</div>
        </header>

        <div className="grid min-h-0 gap-0 overflow-hidden lg:grid-cols-[23rem_minmax(0,1fr)]">
          <aside className="min-h-0 overflow-y-auto border-r border-white/10 bg-[#0d0f15]/90 p-4">
            <Step title="1. Resume" icon={<Upload className="h-4 w-4" />}>
              <label className="mb-3 flex cursor-pointer items-center justify-center gap-2 border border-white/15 bg-white/[0.04] px-3 py-3 text-xs uppercase tracking-[0.14em] text-white/70 hover:bg-white/10">
                Upload PDF/DOCX
                <input
                  type="file"
                  accept=".pdf,.docx,.txt,.md"
                  className="hidden"
                  onChange={(event) => {
                    const file = event.target.files?.[0];
                    if (file) void uploadResume(file);
                  }}
                />
              </label>
              <textarea
                value={resumeText}
                onChange={(event) => {
                  setResumeText(event.target.value);
                  saveResumeText(event.target.value);
                }}
                className="h-48 w-full resize-none border border-white/12 bg-black/35 p-3 font-mono text-xs leading-5 text-white/76 outline-none"
              />
              <button onClick={analyzeResume} className="mt-3 w-full bg-white px-3 py-3 text-xs font-semibold uppercase tracking-[0.16em] text-black">
                Analyze With Trained AI
              </button>
            </Step>

            <Step title="2. Role + Test" icon={<BrainCircuit className="h-4 w-4" />}>
              <select
                value={selectedRole}
                onChange={(event) => void changeRole(event.target.value)}
                className="w-full border border-white/12 bg-black/60 px-3 py-3 text-sm text-white outline-none"
              >
                {suggestedRoles.map((role) => <option key={role}>{role}</option>)}
              </select>
              <button disabled={!analysis} onClick={generateTest} className="mt-3 w-full border border-white/15 bg-white/[0.05] px-3 py-3 text-xs font-semibold uppercase tracking-[0.16em] text-white/75 disabled:opacity-35">
                Start Coding Harness Test
              </button>
              <button disabled={!test} onClick={evaluateTest} className="mt-3 w-full border border-emerald-200/40 bg-emerald-300/15 px-3 py-3 text-xs font-semibold uppercase tracking-[0.16em] text-emerald-100 disabled:opacity-35">
                Evaluate Sample Answers
              </button>
              <button disabled={!evaluation} onClick={buildReport} className="mt-3 w-full bg-white px-3 py-3 text-xs font-semibold uppercase tracking-[0.16em] text-black disabled:opacity-35">
                Final Report
              </button>
            </Step>
          </aside>

          <main className="min-h-0 overflow-y-auto p-5">
            {error && <div className="mb-4 border border-red-300/30 bg-red-500/10 p-3 text-sm text-red-100">{error}</div>}
            <div className="grid gap-4 xl:grid-cols-4">
              <ScoreCard label="ATS" value={analysis?.ats.score} icon={<Gauge className="h-4 w-4" />} />
              <ScoreCard label="Test" value={evaluation?.test.score} icon={<Play className="h-4 w-4" />} />
              <ScoreCard label="Trust" value={evaluation?.trust.score} icon={<ShieldCheck className="h-4 w-4" />} />
              <ScoreCard label="Role Fit" value={report?.role_fit.score} icon={<Sparkles className="h-4 w-4" />} />
            </div>

            <div className="mt-5 grid gap-4 xl:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
              <Panel title="AI Resume Analysis">
                {analysis ? (
                  <>
                    <div className="flex flex-wrap gap-2">{analysis.skills.map((skill) => <Tag key={skill}>{skill}</Tag>)}</div>
                    <p className="mt-4 text-sm text-white/68">
                      Experience: {analysis.experience_level} / Skill match: {Math.round(analysis.skill_match_percent)}% / Model prior: {Math.round(analysis.model_readiness_score)}%
                    </p>
                    <Explanation item={analysis.ats} />
                  </>
                ) : <Empty text="Upload or paste a resume, then analyze it." />}
              </Panel>

              <Panel title="Adaptive Test">
                {test ? (
                  <>
                    <p className="mb-4 text-sm text-white/62">{test.adaptation_summary}</p>
                    <div className="grid gap-3 md:grid-cols-2">
                      {test.focus_skills.slice(0, 6).map((skill) => (
                        <div key={skill} className="border border-white/10 bg-black/22 p-3">
                          <div className="text-xs uppercase tracking-[0.14em] text-white/42">Focus Skill</div>
                          <div className="mt-2 text-sm font-semibold text-white/78">{skill.replaceAll("_", " ")}</div>
                        </div>
                      ))}
                    </div>
                  </>
                ) : <Empty text="Analyze resume first, then start the adaptive coding test in the harness." />}
              </Panel>
            </div>

            <div className="mt-4 grid gap-4 xl:grid-cols-2">
              <Panel title="Trust + Proctoring">
                {evaluation ? <Explanation item={evaluation.trust} /> : <Empty text="Evaluation merges test performance with proctoring signals." />}
              </Panel>
              <Panel title="Role Fit">
                {report ? <Explanation item={report.role_fit} /> : <Empty text="Final role fit appears after test evaluation and report generation." />}
              </Panel>
            </div>

            <Panel title="Skill Gap Roadmap" className="mt-4">
              {roadmap ? (
                <RoadmapTimeline roadmap={roadmap} onCompleteTask={completeTask} onOpenHarness={openRoadmapHarness} />
              ) : (
                <Empty text="Generate the final report to build a job-linked daily roadmap." />
              )}
            </Panel>

            {pipelineReady && (
              <div className="mt-4 border border-emerald-200/25 bg-emerald-300/10 p-4 text-sm text-emerald-100">
                <CheckCircle2 className="mr-2 inline h-4 w-4" />
                End-to-end flow complete: trained resume analysis, adaptive testing, proctoring merge, and explainable scoring.
              </div>
            )}
          </main>
        </div>
      </div>
    </div>
  );
}

const Step = ({ title, icon, children }: { title: string; icon: ReactNode; children: ReactNode }) => (
  <section className="mb-4 border border-white/10 bg-white/[0.025] p-4">
    <h4 className="mb-3 flex items-center gap-2 text-sm font-semibold text-white">{icon}{title}</h4>
    {children}
  </section>
);

const Panel = ({ title, children, className = "" }: { title: string; children: ReactNode; className?: string }) => (
  <section className={`min-h-48 border border-white/10 bg-white/[0.025] p-5 backdrop-blur-md ${className}`}>
    <h4 className="font-serif text-2xl leading-none text-white">{title}</h4>
    <div className="mt-4">{children}</div>
  </section>
);

const ScoreCard = ({ label, value, icon }: { label: string; value?: number; icon: ReactNode }) => (
  <div className="border border-white/10 bg-white/[0.03] p-4">
    <div className="flex items-center justify-between text-xs uppercase tracking-[0.16em] text-white/42">{label}{icon}</div>
    <div className="mt-3 font-serif text-4xl leading-none text-white">{typeof value === "number" ? Math.round(value) : "--"}</div>
    <div className="mt-3 h-1.5 bg-white/10">
      <div className="h-full bg-white" style={{ width: `${Math.max(0, Math.min(value ?? 0, 100))}%` }} />
    </div>
  </div>
);

const Explanation = ({ item }: { item: ScoreExplanation }) => (
  <details className="group mt-4 border border-white/10 bg-black/20 p-4" open>
    <summary className="cursor-pointer text-sm font-semibold text-white">Why this score?</summary>
    <p className="mt-3 text-sm leading-6 text-white/68">{item.explanation}</p>
    <div className="mt-3 grid gap-3 md:grid-cols-2">
      <div>
        <div className="text-xs uppercase tracking-[0.14em] text-emerald-200">Factors</div>
        {item.factors.map((factor) => <p key={factor} className="mt-2 text-sm text-white/62">{factor}</p>)}
      </div>
      <div>
        <div className="text-xs uppercase tracking-[0.14em] text-sky-200">Next Steps</div>
        {item.improvement_tips.map((tip) => <p key={tip} className="mt-2 text-sm text-white/62">{tip}</p>)}
      </div>
    </div>
  </details>
);

const Tag = ({ children }: { children: ReactNode }) => (
  <span className="border border-white/10 bg-white/[0.05] px-2.5 py-1 text-xs text-white/70">{children}</span>
);

const Empty = ({ text }: { text: string }) => (
  <div className="flex min-h-32 items-center justify-center border border-dashed border-white/10 text-center text-sm text-white/35">
    <FileText className="mr-2 h-4 w-4" />
    {text}
  </div>
);

const RoadmapTimeline = ({
  roadmap,
  onCompleteTask,
  onOpenHarness,
}: {
  roadmap: SkillRoadmapResponse;
  onCompleteTask: (taskId: string) => void;
  onOpenHarness: (skill: string, problemIds: string[]) => void;
}) => (
  <div>
    <div className="mb-4 grid gap-3 md:grid-cols-3">
      <Metric label="Skill Gaps" value={roadmap.skill_gaps.length.toString()} />
      <Metric label="Progress" value={`${Math.round(roadmap.overall_progress_percent)}%`} />
      <Metric label="Streak" value={`${roadmap.streak_days} day`} />
    </div>
    <div className="space-y-4">
      {roadmap.roadmap.map((item, index) => (
        <div key={item.skill} className="grid gap-4 border border-white/10 bg-black/18 p-4 lg:grid-cols-[12rem_minmax(0,1fr)]">
          <div>
            <div className="text-xs uppercase tracking-[0.16em] text-white/35">Level {index + 1}</div>
            <h5 className="mt-2 font-serif text-2xl leading-none text-white">{item.skill}</h5>
            <div className="mt-4 h-1.5 bg-white/10">
              <div className="h-full bg-emerald-200" style={{ width: `${item.progress_percent}%` }} />
            </div>
          </div>
          <div>
            <p className="text-sm leading-6 text-white/68">{item.reason}</p>
            <p className="mt-2 border border-emerald-200/20 bg-emerald-300/10 p-2 text-sm text-emerald-100">{item.job_impact.summary}</p>
            <div className="mt-4 flex flex-wrap gap-2">
              {item.harness_questions.length > 0 && (
                <button
                  type="button"
                  onClick={() => onOpenHarness(item.skill, item.harness_questions.map((question) => question.problem_id))}
                  className="bg-emerald-100 px-3 py-2 text-[0.65rem] font-semibold uppercase tracking-[0.12em] text-black"
                >
                  Open Harness
                </button>
              )}
              {item.daily_tasks.slice(0, 3).map((task) => (
                <button
                  key={task.task_id}
                  type="button"
                  onClick={() => task.status !== "completed" && onCompleteTask(task.task_id)}
                  className="border border-white/10 bg-white/[0.03] px-3 py-2 text-xs text-white/70 hover:bg-white/10"
                >
                  Day {task.day}: {task.status === "completed" ? "Completed" : "Start"}
                </button>
              ))}
            </div>
          </div>
        </div>
      ))}
    </div>
  </div>
);

const Metric = ({ label, value }: { label: string; value: string }) => (
  <div className="border border-white/10 bg-white/[0.03] p-3">
    <div className="text-xs uppercase tracking-[0.14em] text-white/35">{label}</div>
    <div className="mt-2 font-serif text-2xl leading-none text-white">{value}</div>
  </div>
);

function formatPipelineError(caught: unknown) {
  if (caught instanceof ApiError) {
    const detail = typeof caught.detail === "string" ? caught.detail : JSON.stringify(caught.detail);
    return `Backend request failed (${caught.status}): ${detail}`;
  }
  if (caught instanceof Error) return caught.message;
  return "Unexpected pipeline error. Check the backend server and try again.";
}

function buildRecommendedJobs(
  selectedRole: string,
  suggestedRoles: string[],
  missingSkills: string[],
  currentSkills: string[]
): RecommendedJobInput[] {
  return Array.from(new Set([selectedRole, ...suggestedRoles])).slice(0, 4).map((role, index) => ({
    title: role,
    match_score: Math.max(45, 72 - index * 7),
    required_skills: Array.from(new Set([...missingSkills.slice(0, 4), ...currentSkills.slice(0, 3)])),
  }));
}

function selectAdaptiveCodingProblemIds({
  analysis,
  focusSkills,
  problems,
  questions,
  selectedRole,
}: {
  analysis: AiResumeAnalyzeResponse;
  focusSkills: string[];
  problems: CodingProblem[];
  questions: AdaptiveTestGenerateResponse["questions"];
  selectedRole: string;
}) {
  const signals = [
    selectedRole,
    ...analysis.skills,
    ...analysis.missing_keywords,
    ...focusSkills,
    ...questions.map((question) => question.skill_tag),
  ].map(normalizeSignal);
  const signalSet = new Set(signals.flatMap(expandCodingSignal));
  const scored = problems.map((problem, index) => {
    const tags = problem.skill_tags.map(normalizeSignal).flatMap(expandCodingSignal);
    const titleSignals = normalizeSignal(problem.title).split("_");
    const matchCount = [...new Set([...tags, ...titleSignals])].filter((tag) => signalSet.has(tag)).length;
    return { problem, score: matchCount * 2, index };
  });

  scored.sort((left, right) => right.score - left.score || left.index - right.index);
  const selected = scored.filter((item) => item.score > 0).slice(0, 4).map((item) => item.problem.problem_id);
  if (selected.length >= 2) return selected;

  return [
    ...selected,
    ...["normalize_resume_skills", "job_match_score", "api_idempotency_filter", "placement_risk_buckets", "two_sum_indices"]
      .filter((problemId) => problems.some((problem) => problem.problem_id === problemId) && !selected.includes(problemId)),
  ].slice(0, 4);
}

function normalizeSignal(value: string) {
  return value.trim().toLowerCase().replace(/[\s-]+/g, "_").replace(/[^a-z0-9_]/g, "");
}

function expandCodingSignal(value: string) {
  const aliases: Record<string, string[]> = {
    api: ["api", "apis", "backend", "idempotency"],
    apis: ["api", "apis", "backend", "idempotency"],
    rest_api: ["api", "apis", "backend", "idempotency"],
    sql: ["sql", "analytics", "dashboards"],
    react: ["frontend", "dashboards", "analytics"],
    data_structures: ["arrays", "hash_map", "sets", "stack", "dsa"],
    algorithms: ["arrays", "sorting", "sliding_window", "dsa"],
    ats: ["ats", "job_matching", "sets"],
    job_matching: ["ats", "job_matching", "sets"],
    projects: ["resume", "analytics", "dashboards"],
    backend_sde: ["backend", "apis", "idempotency"],
    frontend_developer: ["frontend", "strings", "dashboards"],
    full_stack_developer: ["frontend", "backend", "apis", "dashboards"],
    data_analyst: ["analytics", "sql", "dashboards"],
  };
  return [value, ...(aliases[value] ?? [])];
}

function saveResumeText(text: string) {
  if (typeof window === "undefined") return;
  window.sessionStorage.setItem("ai-mentor-resume-text", text);
}
