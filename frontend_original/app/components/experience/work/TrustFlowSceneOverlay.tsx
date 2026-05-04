"use client";

import { ArrowLeft } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { apiRequest, SkillRoadmapItem, SkillRoadmapResponse } from "@/app/lib/api";
import { Timeline } from "@/components/ui/timeline";
import type { TimelineEntry } from "@/components/ui/timeline";
import { useFeatureStore, usePortalStore } from "@stores";

const ADAPTIVE_CODING_TEST_KEY = "placement-trust-adaptive-coding-test";

const TrustFlowSceneOverlay = () => {
  const isActive = usePortalStore((state) => state.activePortalId === "work");
  const setActivePortal = usePortalStore((state) => state.setActivePortal);
  const setActiveFeatureKey = useFeatureStore((state) => state.setActiveFeatureKey);
  const [roadmap, setRoadmap] = useState<SkillRoadmapResponse | null>(null);
  const [status, setStatus] = useState("Loading generated roadmap");

  useEffect(() => {
    if (!isActive) return;
    let cancelled = false;
    setStatus("Loading generated roadmap");

    apiRequest<SkillRoadmapResponse>("/api/v1/pipeline/roadmap")
      .then((nextRoadmap) => {
        if (cancelled) return;
        setRoadmap(nextRoadmap);
        setStatus("Roadmap connected to backend");
      })
      .catch((error) => {
        if (cancelled) return;
        setRoadmap(null);
        setStatus(error instanceof Error ? error.message : "Roadmap backend unavailable");
      });

    return () => {
      cancelled = true;
    };
  }, [isActive]);

  const timelineData = useMemo(() => buildRoadmapEntries(roadmap), [roadmap]);
  const firstItem = roadmap?.roadmap[0] ?? null;

  const goBack = () => {
    const closeButton = document.querySelector<HTMLElement>(".close");
    if (closeButton) {
      closeButton.click();
      return;
    }

    setActivePortal(null);
  };

  const openHarness = (item: SkillRoadmapItem) => {
    if (typeof window !== "undefined") {
      window.sessionStorage.setItem(
        ADAPTIVE_CODING_TEST_KEY,
        JSON.stringify({
          role: roadmap?.target_role ?? "Target Role",
          focusSkills: [item.skill],
          problemIds: item.harness_questions.map((question) => question.problem_id),
          summary: `Trust Flow Map roadmap practice for ${item.skill}. Complete the linked harness tasks to improve job match.`,
          resumeSkills: [],
          missingSkills: roadmap?.skill_gaps ?? [],
        })
      );
    }
    setActiveFeatureKey("coding");
  };

  if (!isActive) return null;

  return (
    <div className="fixed inset-0 z-[9] overflow-y-auto bg-[#070612] text-white selectable">
      <div className="pointer-events-none fixed inset-0 z-0 bg-[radial-gradient(circle_at_20%_0%,rgba(88,77,255,0.16),transparent_34rem),linear-gradient(120deg,#070612_0%,#03030a_48%,#090a12_100%)]" />
      <div className="pointer-events-none fixed inset-0 z-0 opacity-45 [background-image:linear-gradient(rgba(255,255,255,0.035)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.03)_1px,transparent_1px)] [background-size:48px_48px]" />

      <button
        type="button"
        onClick={goBack}
        className="fixed left-5 top-5 z-50 inline-flex items-center gap-2 rounded-full border border-white/20 bg-black/60 px-4 py-2 text-sm font-semibold text-white shadow-[0_14px_40px_rgba(0,0,0,0.35)] backdrop-blur-md transition-colors hover:bg-white hover:text-black"
      >
        <ArrowLeft className="h-4 w-4" />
        Back
      </button>

      <section className="relative z-10 min-h-screen px-6 py-20 lg:px-12">
        <div className="mx-auto grid max-w-7xl gap-6 lg:grid-cols-[0.9fr_1.1fr]">
          <div className="h-fit border border-white/15 bg-black/70 p-5 shadow-[0_20px_80px_rgba(0,0,0,0.55)] backdrop-blur-md">
            <div className="text-[0.65rem] uppercase tracking-[0.22em] text-white/45">Generated Roadmap Data</div>
            <h1 className="mt-3 font-serif text-4xl leading-none md:text-5xl">
              {roadmap?.target_role ?? "Trust Flow Roadmap"}
            </h1>
            <p className="mt-3 text-sm leading-6 text-white/62">{status}</p>

            <div className="mt-5 grid grid-cols-3 gap-2 text-[0.65rem] uppercase tracking-[0.14em] text-white/55">
              <Metric label="Gaps" value={roadmap ? String(roadmap.skill_gaps.length) : "--"} />
              <Metric label="Stages" value={roadmap ? String(roadmap.roadmap.length) : "--"} />
              <Metric label="Progress" value={roadmap ? `${Math.round(roadmap.overall_progress_percent)}%` : "--"} />
            </div>

            {firstItem && (
              <div className="mt-5 border border-emerald-200/20 bg-emerald-300/10 p-4">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <div className="text-2xl font-semibold">{firstItem.skill}</div>
                    <p className="mt-2 text-xs uppercase tracking-[0.14em] text-emerald-100/70">
                      {firstItem.priority} / {firstItem.duration}
                    </p>
                  </div>
                  <span className="border border-emerald-200/25 bg-emerald-300/10 px-2 py-1 text-[0.65rem] uppercase tracking-[0.12em] text-emerald-100">
                    +{firstItem.job_impact.estimated_match_lift_percent}% match
                  </span>
                </div>
                <p className="mt-3 text-sm leading-6 text-white/70">{firstItem.reason}</p>
                <p className="mt-3 text-sm leading-6 text-emerald-50/82">{firstItem.job_impact.summary}</p>
                {firstItem.harness_questions.length > 0 && (
                  <button
                    type="button"
                    onClick={() => openHarness(firstItem)}
                    className="mt-4 border border-emerald-100/45 bg-emerald-100 px-3 py-2 text-[0.65rem] font-semibold uppercase tracking-[0.13em] text-black"
                  >
                    Open {firstItem.harness_questions.length} Harness Task{firstItem.harness_questions.length === 1 ? "" : "s"}
                  </button>
                )}
              </div>
            )}
          </div>

          <div className="min-h-[48rem] overflow-hidden border border-white/10 bg-black/45 backdrop-blur-sm">
            <Timeline
              data={timelineData}
              title={roadmap ? `${roadmap.target_role} Roadmap` : "Generated Roadmap"}
              description="Generated from the backend roadmap pipeline. Each stage keeps skill gaps, proof work, harness tasks, and job impact in one timeline."
              className="dark bg-transparent text-white"
            />
          </div>
        </div>
      </section>
    </div>
  );
};

const Metric = ({ label, value }: { label: string; value: string }) => (
  <div className="border border-white/10 bg-white/[0.035] px-3 py-2">
    <div className="text-white/35">{label}</div>
    <div className="mt-1 text-sm font-semibold text-white">{value}</div>
  </div>
);

function buildRoadmapEntries(roadmap: SkillRoadmapResponse | null): TimelineEntry[] {
  if (!roadmap || roadmap.roadmap.length === 0) {
    return [
      {
        title: "Intake",
        content: (
          <div className="rounded-lg border border-white/10 bg-white/[0.04] p-4">
            <p className="text-sm leading-6 text-white/72">
              Run the resume and roadmap flow first. The trust-flow scene will load the latest generated roadmap automatically.
            </p>
          </div>
        ),
      },
    ];
  }

  return roadmap.roadmap.slice(0, 6).map((item, index) => ({
    title: `Stage ${index + 1}`,
    content: (
      <div className="rounded-lg border border-white/10 bg-white/[0.04] p-4 shadow-[0_20px_70px_rgba(0,0,0,0.32)]">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h3 className="text-2xl font-semibold leading-tight text-white">{item.skill}</h3>
            <p className="mt-2 text-xs uppercase tracking-[0.16em] text-white/45">
              {item.priority} / {item.duration} / {Math.round(item.progress_percent)}% complete
            </p>
          </div>
          <span className="rounded-full border border-emerald-200/25 bg-emerald-300/10 px-3 py-1 text-xs uppercase tracking-[0.12em] text-emerald-100">
            +{item.job_impact.estimated_match_lift_percent}% match
          </span>
        </div>
        <p className="mt-4 text-sm leading-6 text-white/70">{item.reason}</p>
        <div className="mt-4 grid gap-3 md:grid-cols-2">
          <div className="rounded-lg border border-white/10 bg-black/24 p-3">
            <div className="text-[0.62rem] uppercase tracking-[0.18em] text-white/35">Project Proof</div>
            <p className="mt-2 text-xs leading-5 text-white/64">{item.project}</p>
          </div>
          <div className="rounded-lg border border-white/10 bg-black/24 p-3">
            <div className="text-[0.62rem] uppercase tracking-[0.18em] text-white/35">Harness Tasks</div>
            <p className="mt-2 text-xs leading-5 text-white/64">
              {item.harness_questions.map((question) => question.title).join(", ") || "Practice task generated from roadmap."}
            </p>
          </div>
        </div>
      </div>
    ),
  }));
}

export default TrustFlowSceneOverlay;
