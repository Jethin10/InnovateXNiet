"use client";

import Editor from "@monaco-editor/react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";
import { Camera, CheckCircle2, ChevronRight, CopyX, ExternalLink, FileCode2, Maximize2, MonitorUp, Play, RotateCcw, Send, ShieldAlert, ShieldCheck, Terminal, XCircle } from "lucide-react";
import type { CodingProblem, CodingProctoringEvent, CodingProctoringPayload, CodingSubmissionResponse, ProctoringFrameAnalysisResponse } from "@/app/lib/api";
import { HARNESS_APP_URL } from "@/app/lib/api";
import { createLocalFaceProctor } from "@/app/lib/proctoringVision";

interface CodingHarnessWorkspaceProps {
  adaptiveFocusSkills?: string[];
  adaptiveSummary?: string;
  analyzeProctoringFrame: (imageDataUrl: string) => Promise<ProctoringFrameAnalysisResponse>;
  code: string;
  loadProblems: () => Promise<CodingProblem[]>;
  onSelectProblem: (problem: CodingProblem) => void;
  problems: CodingProblem[];
  runCoding: (proctoring?: CodingProctoringPayload, codeOverride?: string) => void;
  selectedLanguage: string;
  selectedProblemId: string;
  setCode: (code: string) => void;
  setSelectedLanguage: (language: string) => void;
  status: string;
  submission?: CodingSubmissionResponse;
}

const difficultyClasses: Record<string, string> = {
  easy: "border-emerald-300/20 bg-emerald-300/10 text-emerald-200",
  medium: "border-amber-300/20 bg-amber-300/10 text-amber-200",
  hard: "border-rose-300/20 bg-rose-300/10 text-rose-200",
};

const editorOptions = {
  minimap: { enabled: false },
  fontSize: 13,
  fontLigatures: true,
  lineHeight: 22,
  padding: { top: 18, bottom: 18 },
  scrollBeyondLastLine: false,
  smoothScrolling: true,
  wordWrap: "on" as const,
  automaticLayout: true,
  tabSize: 4,
};

const secureEditorOptions = {
  ...editorOptions,
  contextmenu: false,
};

const hfModelLabel = process.env.NEXT_PUBLIC_HF_PROCTORING_MODEL ?? "MediaPipe face + Hugging Face object proctor";
const INCIDENTS_PER_RED_ALERT = 3;
const MAX_RED_ALERTS = 3;
const NON_INCIDENT_EVENTS = new Set(["proctoring_alert", "proctoring_terminated"]);

const defaultLanguageOptions = [
  { id: "python", label: "Python", monaco_language: "python" },
  { id: "java", label: "Java", monaco_language: "java" },
  { id: "c", label: "C", monaco_language: "c" },
  { id: "cpp", label: "C++", monaco_language: "cpp" },
  { id: "javascript", label: "JavaScript", monaco_language: "javascript" },
];

const demoSolutions: Record<string, string> = {
  two_sum_indices: `def solve(nums, target):
    seen = {}
    for index, value in enumerate(nums):
        needed = target - value
        if needed in seen:
            return [seen[needed], index]
        seen[value] = index
    return []
`,
  valid_parentheses: `def solve(s):
    pairs = {")": "(", "]": "[", "}": "{"}
    stack = []
    for char in s:
        if char in pairs.values():
            stack.append(char)
        elif char in pairs:
            if not stack or stack.pop() != pairs[char]:
                return False
    return not stack
`,
  merge_intervals: `def solve(intervals):
    if not intervals:
        return []
    intervals = sorted(intervals, key=lambda item: item[0])
    merged = [intervals[0]]
    for start, end in intervals[1:]:
        if start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return merged
`,
  longest_unique_substring: `def solve(s):
    seen = {}
    left = 0
    best = 0
    for right, char in enumerate(s):
        if char in seen and seen[char] >= left:
            left = seen[char] + 1
        seen[char] = right
        best = max(best, right - left + 1)
    return best
`,
  accessible_nav_labels: `def solve(nav_items):
    accessible = []
    for item in nav_items:
        text = str(item.get("text", "")).strip()
        aria = str(item.get("aria_label", "")).strip()
        if text or aria:
            accessible.append(item)
    return accessible
`,
  frontend_performance_budget: `def solve(routes, budget_ms):
    result = {"pass": 0, "fail": 0}
    for route in routes:
        if route.get("load_ms", 0) <= budget_ms:
            result["pass"] += 1
        else:
            result["fail"] += 1
    return result
`,
  normalize_resume_skills: `def solve(skills):
    normalized = set()
    for skill in skills:
        value = str(skill).strip().lower().replace("-", "_").replace(" ", "_")
        if value:
            normalized.add(value)
    return sorted(normalized)
`,
  job_match_score: `def solve(candidate_skills, required_skills):
    required = {str(skill).strip().lower() for skill in required_skills if str(skill).strip()}
    if not required:
        return 0
    candidate = {str(skill).strip().lower() for skill in candidate_skills if str(skill).strip()}
    return round((len(candidate & required) / len(required)) * 100)
`,
  api_idempotency_filter: `def solve(requests):
    seen = set()
    result = []
    for request in requests:
        key = request.get("key")
        if key in seen:
            continue
        seen.add(key)
        result.append(request)
    return result
`,
  placement_risk_buckets: `def solve(scores):
    buckets = {"low": 0, "medium": 0, "high": 0}
    for score in scores:
        if score < 50:
            buckets["high"] += 1
        elif score < 75:
            buckets["medium"] += 1
        else:
            buckets["low"] += 1
    return buckets
`,
};

export default function CodingHarnessWorkspace({
  adaptiveFocusSkills,
  adaptiveSummary,
  analyzeProctoringFrame,
  code,
  loadProblems,
  onSelectProblem,
  problems,
  runCoding,
  selectedLanguage,
  selectedProblemId,
  setCode,
  setSelectedLanguage,
  status,
  submission,
}: CodingHarnessWorkspaceProps) {
  const harnessRef = useRef<HTMLDivElement>(null);
  const screenVideoRef = useRef<HTMLVideoElement>(null);
  const cameraVideoRef = useRef<HTMLVideoElement>(null);
  const [screenStream, setScreenStream] = useState<MediaStream | null>(null);
  const [cameraStream, setCameraStream] = useState<MediaStream | null>(null);
  const [fullscreenActive, setFullscreenActive] = useState(false);
  const [entireScreenShared, setEntireScreenShared] = useState(false);
  const [copyPasteBlocked, setCopyPasteBlocked] = useState(true);
  const [proctoringError, setProctoringError] = useState<string | null>(null);
  const [hfInsight, setHfInsight] = useState("AI proctor waits for secure camera mode.");
  const [events, setEvents] = useState<Record<string, CodingProctoringEvent>>({});
  const [testTerminated, setTestTerminated] = useState(false);
  const issuedAlertsRef = useRef(0);
  const terminationSubmittedRef = useRef(false);
  const selectedProblem = problems.find((problem) => problem.problem_id === selectedProblemId) ?? problems[0];
  const languageOptions = selectedProblem?.supported_languages?.length ? selectedProblem.supported_languages : defaultLanguageOptions;
  const activeLanguage = languageOptions.find((language) => language.id === selectedLanguage) ?? languageOptions[0];
  const activeLanguageId = activeLanguage?.id ?? "python";
  const activeMonacoLanguage = activeLanguage?.monaco_language ?? "python";
  const publicResults = submission?.public_results ?? [];
  const hiddenTotal = submission?.hidden_total_count ?? 0;
  const hiddenPassed = submission?.hidden_passed_count ?? 0;
  const visiblePassed = publicResults.filter((result) => result.passed).length + hiddenPassed;
  const visibleTotal = publicResults.length + hiddenTotal;
  const screenShareActive = Boolean(screenStream?.active);
  const cameraActive = Boolean(cameraStream?.active);
  const monitorShareActive = screenShareActive && entireScreenShared;
  const mediaReady = monitorShareActive && cameraActive && copyPasteBlocked;
  const harnessSecure = mediaReady && fullscreenActive && !testTerminated;
  const incidentCount = useMemo(
    () =>
      Object.values(events).reduce(
        (total, event) => total + (NON_INCIDENT_EVENTS.has(event.event_type) ? 0 : event.count),
        0,
      ),
    [events],
  );
  const redAlertCount = Math.min(MAX_RED_ALERTS, Math.floor(incidentCount / INCIDENTS_PER_RED_ALERT));
  const proctoringPayload = useMemo<CodingProctoringPayload>(() => ({
    proctoring_checks: {
      camera_active: cameraActive,
      copy_paste_blocked: copyPasteBlocked,
      fullscreen_active: fullscreenActive,
      screen_share_active: screenShareActive,
      screen_share_surface_monitor: monitorShareActive,
    },
    proctoring_events: Object.values(events),
  }), [cameraActive, copyPasteBlocked, events, fullscreenActive, monitorShareActive, screenShareActive]);

  const recordEvent = useCallback((eventType: string, severity = 0.65) => {
    setEvents((current) => {
      const existing = current[eventType];
      return {
        ...current,
        [eventType]: {
          event_type: eventType,
          count: (existing?.count ?? 0) + 1,
          severity,
        },
      };
    });
  }, []);

  const terminateTest = useCallback(() => {
    if (terminationSubmittedRef.current) return;
    terminationSubmittedRef.current = true;
    setTestTerminated(true);
    setProctoringError("Test closed after 3 red alerts. This attempt is submitted for zero marks.");
    const terminationEvent: CodingProctoringEvent = {
      event_type: "proctoring_terminated",
      count: 1,
      severity: 1,
    };
    runCoding(
      {
        proctoring_checks: {
          camera_active: false,
          copy_paste_blocked: copyPasteBlocked,
          fullscreen_active: false,
          screen_share_active: false,
          screen_share_surface_monitor: false,
        },
        proctoring_events: [...Object.values(events), terminationEvent],
      },
      code,
    );
    setEvents((current) => ({ ...current, proctoring_terminated: terminationEvent }));
    screenStream?.getTracks().forEach((track) => track.stop());
    cameraStream?.getTracks().forEach((track) => track.stop());
    setScreenStream(null);
    setCameraStream(null);
    setEntireScreenShared(false);
    const exitFullscreen = document.exitFullscreen?.();
    void exitFullscreen?.catch(() => undefined);
  }, [cameraStream, code, copyPasteBlocked, events, runCoding, screenStream]);

  const lockFullscreen = useCallback(async () => {
    try {
      const fullscreenTarget = harnessRef.current ?? document.documentElement;
      await fullscreenTarget.requestFullscreen?.({ navigationUI: "hide" } as FullscreenOptions);
      setFullscreenActive(Boolean(document.fullscreenElement));
      setProctoringError(null);
    } catch {
      recordEvent("fullscreen_unavailable", 0.45);
      setProctoringError("Fullscreen lock was blocked. Click Lock Fullscreen again after screen and camera are active.");
    }
  }, [recordEvent]);

  const startSecureHarness = async () => {
    setProctoringError(null);
    if (testTerminated) {
      setProctoringError("This attempt was closed after 3 red alerts.");
      return;
    }
    try {
      const displayStream = await navigator.mediaDevices.getDisplayMedia({
        audio: false,
        video: { displaySurface: "monitor" } as MediaTrackConstraints,
      });
      const displayTrack = displayStream.getVideoTracks()[0];
      const displaySurface = displayTrack?.getSettings().displaySurface;
      if (displaySurface && displaySurface !== "monitor") {
        displayStream.getTracks().forEach((track) => track.stop());
        throw new Error("Select Entire Screen, not a browser tab or application window.");
      }
      const webcamStream = await navigator.mediaDevices.getUserMedia({
        audio: false,
        video: {
          facingMode: "user",
          width: { ideal: 640 },
          height: { ideal: 360 },
        },
      });
      displayStream.getVideoTracks().forEach((track) => {
        track.addEventListener("ended", () => {
          recordEvent("screen_share_ended", 1);
          setScreenStream(null);
          setEntireScreenShared(false);
        });
      });
      webcamStream.getVideoTracks().forEach((track) => {
        track.addEventListener("ended", () => {
          recordEvent("camera_ended", 1);
          setCameraStream(null);
        });
      });
      setScreenStream(displayStream);
      setEntireScreenShared(true);
      setCameraStream(webcamStream);
      await lockFullscreen();
    } catch (error) {
      setProctoringError(error instanceof Error ? error.message : "Screen and camera permission are required before the harness starts.");
    }
  };

  const guardedRunCoding = (codeOverride?: string) => {
    if (testTerminated) {
      setProctoringError("This attempt was closed after 3 red alerts.");
      return;
    }
    if (!harnessSecure) {
      setProctoringError("Lock fullscreen, share entire screen, and keep camera active before running code.");
      return;
    }
    runCoding(proctoringPayload, codeOverride);
  };

  const demoFillAndSubmit = () => {
    if (!selectedProblem) return;
    if (activeLanguageId !== "python") {
      setProctoringError("Demo auto-submit is available for Python. Use Run or Submit for this language.");
      return;
    }
    const solution = demoSolutions[selectedProblem.problem_id];
    if (!solution) {
      setProctoringError("No demo solution is available for this problem yet.");
      return;
    }
    setCode(solution);
    guardedRunCoding(solution);
  };

  useEffect(() => {
    const handleFullscreenChange = () => {
      const active = Boolean(document.fullscreenElement);
      setFullscreenActive(active);
      if (!active) recordEvent("fullscreen_exit", 0.85);
    };
    const blockClipboard = (event: Event) => {
      event.preventDefault();
      setCopyPasteBlocked(true);
      recordEvent(event.type, 0.95);
    };
    const blockContextMenu = (event: Event) => {
      event.preventDefault();
      recordEvent("context_menu", 0.45);
    };
    const blockShortcut = (event: KeyboardEvent) => {
      const key = event.key.toLowerCase();
      if ((event.ctrlKey || event.metaKey) && ["c", "v", "x", "a", "s", "p"].includes(key)) {
        event.preventDefault();
        recordEvent(`shortcut_${key}`, key === "v" ? 0.95 : 0.55);
      }
      if (key === "escape") {
        event.preventDefault();
        recordEvent("escape_attempt", 0.95);
      }
    };
    const handleVisibility = () => {
      if (document.hidden) recordEvent("visibility_hidden", 0.85);
    };
    const handleBlur = () => recordEvent("window_blur", 0.75);

    document.addEventListener("fullscreenchange", handleFullscreenChange);
    document.addEventListener("copy", blockClipboard, true);
    document.addEventListener("cut", blockClipboard, true);
    document.addEventListener("paste", blockClipboard, true);
    document.addEventListener("drop", blockClipboard, true);
    document.addEventListener("contextmenu", blockContextMenu, true);
    document.addEventListener("keydown", blockShortcut, true);
    document.addEventListener("visibilitychange", handleVisibility);
    window.addEventListener("blur", handleBlur);
    return () => {
      document.removeEventListener("fullscreenchange", handleFullscreenChange);
      document.removeEventListener("copy", blockClipboard, true);
      document.removeEventListener("cut", blockClipboard, true);
      document.removeEventListener("paste", blockClipboard, true);
      document.removeEventListener("drop", blockClipboard, true);
      document.removeEventListener("contextmenu", blockContextMenu, true);
      document.removeEventListener("keydown", blockShortcut, true);
      document.removeEventListener("visibilitychange", handleVisibility);
      window.removeEventListener("blur", handleBlur);
    };
  }, [recordEvent]);

  useEffect(() => {
    if (!harnessSecure || testTerminated) return;
    if (redAlertCount > issuedAlertsRef.current) {
      issuedAlertsRef.current = redAlertCount;
      recordEvent("proctoring_alert", 1);
      setProctoringError(`Red alert ${redAlertCount}/${MAX_RED_ALERTS}: ${incidentCount} security incidents recorded.`);
    }
    if (redAlertCount >= MAX_RED_ALERTS) {
      terminateTest();
    }
  }, [harnessSecure, incidentCount, recordEvent, redAlertCount, terminateTest, testTerminated]);

  useEffect(() => {
    if (screenVideoRef.current && screenStream) screenVideoRef.current.srcObject = screenStream;
    if (cameraVideoRef.current && cameraStream) cameraVideoRef.current.srcObject = cameraStream;
  }, [cameraStream, screenStream]);

  useEffect(() => {
    if (!harnessSecure || !cameraStream) return;
    let cancelled = false;
    let busy = false;
    let lastHfAnalysis = 0;
    let localProctor: Awaited<ReturnType<typeof createLocalFaceProctor>> | null = null;

    const analyzeCameraFrame = async () => {
      const video = cameraVideoRef.current;
      if (!video || video.readyState < 2 || busy) return;
      busy = true;
      try {
        localProctor ??= await createLocalFaceProctor();
        const localAnalysis = localProctor.analyze(video);
        if (cancelled) return;
        setHfInsight(localAnalysis.reason);
        localAnalysis.flags.forEach((flag) => recordEvent(flag, flag === "face_off_center" ? 0.75 : 0.95));

        const now = Date.now();
        if (now - lastHfAnalysis >= 20000) {
          lastHfAnalysis = now;
          const canvas = document.createElement("canvas");
          canvas.width = 320;
          canvas.height = Math.max(1, Math.round((video.videoHeight / Math.max(video.videoWidth, 1)) * 320));
          const context = canvas.getContext("2d");
          if (!context) return;
          context.drawImage(video, 0, 0, canvas.width, canvas.height);
          const analysis = await analyzeProctoringFrame(canvas.toDataURL("image/jpeg", 0.72));
          if (cancelled) return;
          if (analysis.flags.length > 0 || !localAnalysis.flags.length) setHfInsight(analysis.reason);
          analysis.flags.forEach((flag) => recordEvent(`hf_${flag}`, Math.max(analysis.risk_score, 0.7)));
        }
      } catch (error) {
        if (!cancelled) setHfInsight(error instanceof Error ? error.message : "AI proctoring check could not run.");
      } finally {
        busy = false;
      }
    };

    void analyzeCameraFrame();
    const interval = window.setInterval(() => void analyzeCameraFrame(), 5000);
    return () => {
      cancelled = true;
      localProctor?.close();
      window.clearInterval(interval);
    };
  }, [analyzeProctoringFrame, cameraStream, harnessSecure, recordEvent]);

  useEffect(() => () => {
    screenStream?.getTracks().forEach((track) => track.stop());
    cameraStream?.getTracks().forEach((track) => track.stop());
  }, [cameraStream, screenStream]);

  return (
    <div
      ref={harnessRef}
      className={`relative overflow-hidden border border-white/15 bg-[#050507] shadow-[0_30px_110px_rgba(0,0,0,0.42)] ${
        fullscreenActive ? "h-screen min-h-screen" : "h-[calc(100dvh-12.5rem)] min-h-[42rem]"
      }`}
    >
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_18%_8%,rgba(255,255,255,0.12),transparent_25%),radial-gradient(circle_at_88%_16%,rgba(58,184,160,0.12),transparent_28%),linear-gradient(135deg,rgba(255,255,255,0.03),transparent_42%)]" />
      <div className="relative grid h-full min-h-0 grid-rows-[auto_auto_minmax(0,1fr)]">
        <header className="flex min-h-14 items-center justify-between border-b border-white/10 bg-black/30 px-4 backdrop-blur-md">
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center border border-white/20 bg-white/[0.06]">
              <FileCode2 className="h-4 w-4 text-white/80" />
            </div>
            <div>
              <div className="text-sm font-semibold text-white">Interview Harness</div>
              <div className="text-[0.65rem] uppercase tracking-[0.18em] text-white/42">Java / C / C++ / Python / JavaScript · Hidden tests</div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={mediaReady && !fullscreenActive ? lockFullscreen : startSecureHarness}
              className={`inline-flex h-9 items-center gap-2 border px-3 text-xs font-semibold transition-colors ${
                harnessSecure ? "border-emerald-200/40 bg-emerald-300/15 text-emerald-100" : "border-amber-200/45 bg-amber-300/15 text-amber-100 hover:bg-amber-300/25"
              }`}
            >
              <ShieldAlert className="h-3.5 w-3.5" />
              {harnessSecure ? "Secure Mode Active" : mediaReady ? "Lock Fullscreen" : "Start Secure Mode"}
            </button>
            {mediaReady && !fullscreenActive && (
              <button
                type="button"
                onClick={lockFullscreen}
                className="inline-flex h-9 items-center gap-2 border border-white/25 bg-white px-3 text-xs font-semibold text-black transition-colors hover:bg-emerald-200"
              >
                <Maximize2 className="h-3.5 w-3.5" />
                Lock Fullscreen
              </button>
            )}
            <button
              type="button"
              onClick={() => window.open(HARNESS_APP_URL, "_blank", "noopener,noreferrer")}
              className="inline-flex h-9 items-center gap-2 border border-white/15 bg-white/[0.04] px-3 text-xs text-white/72 transition-colors hover:bg-white/10 hover:text-white"
            >
              <ExternalLink className="h-3.5 w-3.5" />
              Judge0 IDE
            </button>
            <span className="hidden border border-white/10 bg-white/[0.035] px-3 py-2 text-[0.65rem] uppercase tracking-[0.16em] text-white/45 sm:inline-flex">
              {status}
            </span>
          </div>
        </header>

        <div className="border-b border-white/10 bg-[#090b10]/95 px-4 py-3">
          <div className="grid gap-2 md:grid-cols-[1fr_auto]">
            <div className="grid gap-2 sm:grid-cols-4">
              <SecurityCheck active={fullscreenActive} icon={<Maximize2 className="h-3.5 w-3.5" />} label="Fullscreen" />
              <SecurityCheck active={monitorShareActive} icon={<MonitorUp className="h-3.5 w-3.5" />} label="Entire screen" />
              <SecurityCheck active={cameraActive} icon={<Camera className="h-3.5 w-3.5" />} label="Camera" />
              <SecurityCheck active={copyPasteBlocked} icon={<CopyX className="h-3.5 w-3.5" />} label="No copy/paste" />
            </div>
            <div className="flex min-w-0 gap-2">
              <video ref={screenVideoRef} className="hidden h-10 w-16 border border-white/10 object-cover opacity-70 md:block" autoPlay muted playsInline />
              <video ref={cameraVideoRef} className="h-10 w-16 border border-white/10 object-cover opacity-80" autoPlay muted playsInline />
            </div>
          </div>
          <div className="mt-2 flex flex-wrap items-center gap-2 text-[0.65rem] uppercase tracking-[0.14em] text-white/42">
            <span className="border border-white/10 bg-white/[0.035] px-2 py-1">{hfModelLabel}</span>
            <span className="border border-white/10 bg-white/[0.035] px-2 py-1">
              Incidents {incidentCount}
            </span>
            <span className={`border px-2 py-1 ${redAlertCount > 0 ? "border-red-300/40 bg-red-500/20 text-red-100" : "border-white/10 bg-white/[0.035]"}`}>
              Red alerts {redAlertCount}/{MAX_RED_ALERTS}
            </span>
            <span className="border border-white/10 bg-white/[0.035] px-2 py-1 normal-case tracking-normal text-white/50">
              {hfInsight}
            </span>
            {proctoringError && <span className="border border-red-200/30 bg-red-400/12 px-2 py-1 text-red-100">{proctoringError}</span>}
          </div>
          {redAlertCount > 0 && (
            <div className="mt-3 border border-red-300/45 bg-red-500/18 px-4 py-3 text-sm font-semibold text-red-50">
              Red alert active. Every 3 incidents escalates the attempt; the third red alert closes the test and records zero marks.
            </div>
          )}
        </div>

        <div className="grid min-h-0 overflow-hidden grid-cols-1 lg:grid-cols-[18rem_minmax(24rem,0.95fr)_minmax(28rem,1.05fr)]">
          <aside className="hidden min-h-0 border-r border-white/10 bg-[#0b0d12]/88 lg:flex lg:flex-col">
            <div className="border-b border-white/10 p-4">
              <button
                type="button"
                onClick={() => void loadProblems()}
                className="inline-flex h-9 items-center gap-2 border border-white/15 bg-white/[0.04] px-3 text-xs text-white/72 transition-colors hover:bg-white/10 hover:text-white"
              >
                <RotateCcw className="h-3.5 w-3.5" />
                Refresh Bank
              </button>
            </div>
            <div className="min-h-0 flex-1 overflow-y-auto p-2">
              {problems.map((problem, index) => {
                const active = selectedProblem?.problem_id === problem.problem_id;
                return (
                  <button
                    key={problem.problem_id}
                    type="button"
                    onClick={() => onSelectProblem(problem)}
                    className={`mb-1 grid w-full grid-cols-[1.7rem_1fr_auto] items-center gap-2 px-3 py-3 text-left text-sm transition-colors ${
                      active ? "border border-white/15 bg-white text-black" : "border border-transparent text-white/66 hover:border-white/10 hover:bg-white/[0.055] hover:text-white"
                    }`}
                  >
                    <span className={`font-mono text-xs ${active ? "text-black/45" : "text-white/32"}`}>{index + 1}</span>
                    <span className="min-w-0 truncate font-medium">{problem.title}</span>
                    <ChevronRight className={`h-3.5 w-3.5 ${active ? "text-black/50" : "text-white/25"}`} />
                  </button>
                );
              })}
            </div>
          </aside>

          <section className="min-h-0 overflow-y-auto border-r border-white/10 bg-[#101116]/86 px-5 py-5 text-white backdrop-blur-md">
            {adaptiveSummary && (
              <div className="mb-5 border border-emerald-200/25 bg-emerald-300/10 p-4 text-sm leading-6 text-emerald-100">
                <div className="text-[0.65rem] uppercase tracking-[0.16em] text-emerald-100/70">Adaptive Test Mode</div>
                <p className="mt-2">{adaptiveSummary}</p>
                {adaptiveFocusSkills?.length ? (
                  <div className="mt-3 flex flex-wrap gap-2">
                    {adaptiveFocusSkills.slice(0, 6).map((skill) => (
                      <span key={skill} className="border border-emerald-200/20 bg-black/20 px-2.5 py-1 text-xs text-emerald-50/80">
                        {skill.replaceAll("_", " ")}
                      </span>
                    ))}
                  </div>
                ) : null}
              </div>
            )}
            {selectedProblem ? (
              <>
                <div className="flex flex-wrap items-center gap-2">
                  <span className="border border-white/15 bg-white/[0.04] px-2.5 py-1 text-[0.65rem] uppercase tracking-[0.16em] text-white/55">Description</span>
                  <span className="border border-white/10 bg-black/25 px-2.5 py-1 text-[0.65rem] uppercase tracking-[0.16em] text-white/35">Submissions</span>
                  <span className="border border-white/10 bg-black/25 px-2.5 py-1 text-[0.65rem] uppercase tracking-[0.16em] text-white/35">Evidence</span>
                </div>
                <h3 className="mt-5 font-serif text-[2.3rem] leading-none text-white">{selectedProblem.title}</h3>
                <div className="mt-4 flex flex-wrap gap-2">
                  <span className={`border px-2.5 py-1 text-xs capitalize ${difficultyClasses[selectedProblem.difficulty] ?? "border-white/15 bg-white/[0.04] text-white/65"}`}>
                    {selectedProblem.difficulty}
                  </span>
                  {selectedProblem.skill_tags.map((tag) => (
                    <span key={tag} className="border border-white/10 bg-white/[0.04] px-2.5 py-1 text-xs text-white/62">{tag}</span>
                  ))}
                </div>
                <p className="mt-5 text-[0.96rem] leading-7 text-white/76">{selectedProblem.statement}</p>

                <div className="mt-6 space-y-4">
                  {selectedProblem.examples.map((example, index) => (
                    <section key={`${selectedProblem.problem_id}-${index}`} className="border border-white/10 bg-black/24 p-4">
                      <h4 className="text-sm font-semibold text-white">Example {index + 1}</h4>
                      <pre className="mt-3 overflow-x-auto border border-white/10 bg-[#050507] p-3 font-mono text-xs leading-6 text-white/70">
{`Input: ${JSON.stringify(example.input)}
Output: ${JSON.stringify(example.expected)}`}
                      </pre>
                    </section>
                  ))}
                </div>

                <section className="mt-6 border border-white/10 bg-white/[0.035] p-4">
                  <h4 className="text-sm font-semibold text-white">Rules</h4>
                  <div className="mt-3 space-y-2 text-sm leading-6 text-white/62">
                    <p>Write your own implementation inside <code className="border border-white/10 bg-black/30 px-1.5 py-0.5 font-mono text-white/80">{selectedProblem.function_name}</code>.</p>
                    <p>Public examples are shown here. Hidden cases stay on the backend.</p>
                    <p>Submission snapshots become coding evidence for the student profile.</p>
                  </div>
                </section>
              </>
            ) : (
              <div className="flex h-full items-center justify-center border border-dashed border-white/12 text-sm text-white/45">
                Load problems to begin.
              </div>
            )}
          </section>

          <section className="grid min-h-0 grid-rows-[minmax(0,1fr)_17rem] bg-[#090b10]">
            <div className="grid min-h-0 grid-rows-[auto_1fr]">
              <div className="flex items-center justify-between border-b border-white/10 bg-[#11141c] px-4 py-3">
                <div className="flex items-center gap-2">
                  <select
                    value={activeLanguageId}
                    onChange={(event) => setSelectedLanguage(event.target.value)}
                    className="h-9 min-w-[8.5rem] border border-white/10 bg-[#181c26] px-3 text-xs font-semibold text-white outline-none"
                  >
                    {languageOptions.map((language) => (
                      <option key={language.id} value={language.id} className="bg-[#11141c] text-white">
                        {language.label}
                      </option>
                    ))}
                  </select>
                  <span className="text-xs text-white/38">
                    {activeLanguageId === "python" ? "local fallback enabled" : "Judge0 required"}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => guardedRunCoding()}
                    disabled={!harnessSecure || testTerminated}
                    className="inline-flex h-9 items-center gap-2 border border-white/10 bg-white/[0.07] px-3 text-xs font-semibold text-white transition-colors hover:bg-white/12 disabled:cursor-not-allowed disabled:opacity-35"
                  >
                    <Play className="h-3.5 w-3.5" />
                    Run
                  </button>
                  <button
                    type="button"
                    onClick={demoFillAndSubmit}
                    disabled={!harnessSecure || testTerminated || activeLanguageId !== "python" || !selectedProblem || !demoSolutions[selectedProblem.problem_id]}
                    className="inline-flex h-9 items-center gap-2 border border-emerald-200/35 bg-emerald-300/15 px-3 text-xs font-semibold text-emerald-100 transition-colors hover:bg-emerald-300/25 disabled:cursor-not-allowed disabled:opacity-35"
                  >
                    <FileCode2 className="h-3.5 w-3.5" />
                    Demo Full Submit
                  </button>
                  <button
                    type="button"
                    onClick={() => guardedRunCoding()}
                    disabled={!harnessSecure || testTerminated}
                    className="inline-flex h-9 items-center gap-2 bg-white px-3 text-xs font-semibold text-black transition-colors hover:bg-emerald-200 disabled:cursor-not-allowed disabled:opacity-35"
                  >
                    <Send className="h-3.5 w-3.5" />
                    Submit
                  </button>
                </div>
              </div>
              <div className="min-h-0">
                {mediaReady && !fullscreenActive && (
                  <div className="border-b border-amber-200/25 bg-amber-300/10 px-4 py-3 text-sm text-amber-100">
                    Fullscreen is required before editing. Click <button type="button" onClick={lockFullscreen} className="border border-amber-100/40 bg-amber-100 px-2 py-1 text-xs font-semibold text-black">Lock Fullscreen</button>.
                  </div>
                )}
                <Editor
                  height="100%"
                  language={activeMonacoLanguage}
                  theme="vs-dark"
                  value={code}
                  options={{ ...secureEditorOptions, readOnly: !harnessSecure || testTerminated, domReadOnly: !harnessSecure || testTerminated }}
                  onChange={(value) => {
                    if (harnessSecure && !testTerminated) setCode(value ?? "");
                  }}
                  loading={<div className="flex h-full items-center justify-center text-sm text-white/45">Loading editor...</div>}
                />
              </div>
            </div>

            <section className="min-h-0 border-t border-white/10 bg-[#11141c]">
              <div className="flex items-center justify-between border-b border-white/10 px-4 py-3">
                <div className="flex items-center gap-2 text-sm font-semibold text-white">
                  <Terminal className="h-4 w-4 text-white/65" />
                  Test Results
                </div>
                {submission && (
                  <span className="border border-white/10 bg-white/[0.055] px-3 py-1.5 text-xs text-white/68">
                    {visiblePassed}/{visibleTotal} passed
                  </span>
                )}
              </div>
              <div className="h-[calc(100%-3.25rem)] overflow-y-auto p-4">
                {!submission && (
                  <div className="flex h-full items-center justify-center border border-dashed border-white/12 text-sm text-white/42">
                    Run your code to see public and hidden test feedback.
                  </div>
                )}
                {submission && (
                  <div className="space-y-3">
                    <div className={`flex items-center gap-2 text-sm font-semibold ${submission.passed ? "text-emerald-300" : "text-rose-300"}`}>
                      {submission.passed ? <CheckCircle2 className="h-4 w-4" /> : <XCircle className="h-4 w-4" />}
                      {submission.passed ? "Accepted" : "Needs work"} · Score {submission.score}/100
                    </div>
                    {publicResults.map((result) => (
                      <div key={result.name} className="border border-white/10 bg-[#090b10] p-3">
                        <div className="flex items-center justify-between text-sm">
                          <span className="font-medium text-white">{result.name}</span>
                          <span className={result.passed ? "text-emerald-300" : "text-rose-300"}>{result.passed ? "Passed" : "Failed"}</span>
                        </div>
                        <pre className="mt-2 overflow-x-auto border border-white/8 bg-black/35 p-3 font-mono text-xs leading-5 text-white/64">
{`Input: ${JSON.stringify(result.input)}
Expected: ${JSON.stringify(result.expected)}
Actual: ${JSON.stringify(result.actual ?? result.error)}`}
                        </pre>
                      </div>
                    ))}
                    <div className="flex items-center gap-2 border border-white/10 bg-[#090b10] p-3 text-sm text-white/68">
                      <ShieldCheck className="h-4 w-4 text-emerald-300" />
                      Hidden tests passed: {hiddenPassed}/{hiddenTotal}
                    </div>
                    {submission.integrity_flags.length > 0 && (
                      <div className="border border-amber-200/25 bg-amber-300/10 p-3 text-sm text-amber-100">
                        Integrity flags: {submission.integrity_flags.join(", ")}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </section>
          </section>
        </div>
      </div>
    </div>
  );
}

const SecurityCheck = ({ active, icon, label }: { active: boolean; icon: ReactNode; label: string }) => (
  <div className={`flex items-center gap-2 border px-3 py-2 text-xs font-semibold ${
    active ? "border-emerald-200/30 bg-emerald-300/10 text-emerald-100" : "border-red-200/30 bg-red-400/10 text-red-100"
  }`}>
    {icon}
    <span>{label}</span>
  </div>
);
