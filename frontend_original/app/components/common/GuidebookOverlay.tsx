"use client";

import { ArrowRight, BookOpen, CheckCircle2, Route, ShieldCheck, X } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { PROJECTS } from "@constants";
import { useFeatureStore } from "@stores";

const GUIDEBOOK_SEEN_KEY = "placement-trust-guidebook-seen";

const principles = [
  {
    title: "What it does",
    body: "RISE turns student claims into recruiter-ready proof: resume evidence, GitHub signals, coding results, assessment scores, a roadmap, and a verifiable Trust Stamp.",
  },
  {
    title: "Why it matters",
    body: "The platform reduces guesswork for students and recruiters by showing what is verified, what is missing, and what should be improved next.",
  },
  {
    title: "How to use it",
    body: "Start from the AI Mentor Pipeline for the guided demo, or open any feature from the Backend Features portal to inspect a specific service.",
  },
];

const quickStart = [
  "Sign in or register to unlock the demo workspace.",
  "Scroll into the Trust Flow Map to see the readiness journey.",
  "Open Backend Features to run individual platform modules.",
  "Use the AI Mentor Pipeline when you want the complete end-to-end flow.",
  "Review the Trust Score, Roadmap, and Trust Stamp as the final proof layer.",
];

const GuidebookOverlay = () => {
  const setActiveFeatureKey = useFeatureStore((state) => state.setActiveFeatureKey);
  const [isOpen, setIsOpen] = useState(false);
  const [hasSeenGuide, setHasSeenGuide] = useState(true);

  useEffect(() => {
    const seen = window.localStorage.getItem(GUIDEBOOK_SEEN_KEY) === "true";
    setHasSeenGuide(seen);
  }, []);

  useEffect(() => {
    if (!isOpen) return;

    window.localStorage.setItem(GUIDEBOOK_SEEN_KEY, "true");
    setHasSeenGuide(true);

    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setIsOpen(false);
    };

    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", handleEscape);

    return () => {
      document.body.style.overflow = "";
      window.removeEventListener("keydown", handleEscape);
    };
  }, [isOpen]);

  const flowSteps = useMemo(
    () => PROJECTS.filter((project) => project.featureKey),
    []
  );

  const openFeature = (featureKey?: string) => {
    if (!featureKey) return;
    setActiveFeatureKey(featureKey);
    setIsOpen(false);
  };

  return (
    <>
      <button
        type="button"
        className="selectable fixed right-4 top-[4.4rem] z-40 inline-flex h-11 w-11 items-center justify-center border border-white/18 bg-black/55 text-white shadow-[0_14px_42px_rgba(0,0,0,0.36)] backdrop-blur-xl transition hover:border-white/42 hover:bg-white/12 focus:outline-none focus:ring-2 focus:ring-white/45 sm:right-6 sm:top-[4.8rem]"
        aria-label="Open website guidebook"
        onClick={() => setIsOpen(true)}
      >
        <BookOpen className="h-5 w-5" />
        {!hasSeenGuide && (
          <span className="absolute -right-1 -top-1 h-3 w-3 rounded-full border border-black bg-emerald-300" />
        )}
      </button>

      {isOpen && (
        <div className="selectable fixed inset-0 z-50 flex items-center justify-center bg-black/62 p-3 text-white backdrop-blur-md md:p-6">
          <section
            className="relative grid max-h-[calc(100dvh-1.5rem)] w-[min(76rem,calc(100vw-1.5rem))] overflow-hidden border border-white/16 bg-[#050506] shadow-[0_34px_120px_rgba(0,0,0,0.62)] md:max-h-[calc(100dvh-3rem)] md:grid-cols-[0.78fr_1.22fr]"
            role="dialog"
            aria-modal="true"
            aria-labelledby="guidebook-title"
          >
            <div className="relative overflow-hidden border-b border-white/12 bg-[#11110d] p-5 md:border-b-0 md:border-r md:p-7">
              <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_20%_12%,rgba(255,232,170,0.2),transparent_14rem),linear-gradient(135deg,rgba(255,255,255,0.09),transparent_34%)]" />
              <div className="relative">
                <p className="text-[0.7rem] font-bold uppercase tracking-[0.24em] text-amber-100/62">
                  Website Guidebook
                </p>
                <h2 id="guidebook-title" className="mt-3 font-serif text-4xl leading-[0.95] text-white md:text-6xl">
                  Understand the flow before you run it.
                </h2>
                <p className="mt-5 max-w-md text-sm leading-6 text-white/68">
                  This guide explains what each part of the website does, why it exists, and how users should move through the placement trust journey.
                </p>

                <div className="mt-7 space-y-3">
                  {principles.map((item) => (
                    <article key={item.title} className="border border-white/10 bg-black/22 p-4">
                      <h3 className="flex items-center gap-2 text-sm font-semibold text-white">
                        <ShieldCheck className="h-4 w-4 text-emerald-200" />
                        {item.title}
                      </h3>
                      <p className="mt-2 text-sm leading-6 text-white/62">{item.body}</p>
                    </article>
                  ))}
                </div>
              </div>
            </div>

            <div className="relative overflow-y-auto p-5 md:p-7">
              <button
                type="button"
                className="absolute right-4 top-4 grid h-10 w-10 place-items-center border border-white/14 bg-white/6 text-white/78 transition hover:border-white/35 hover:bg-white/12 focus:outline-none focus:ring-2 focus:ring-white/45"
                aria-label="Close guidebook"
                onClick={() => setIsOpen(false)}
              >
                <X className="h-5 w-5" />
              </button>

              <div className="pr-12">
                <p className="text-[0.68rem] font-bold uppercase tracking-[0.22em] text-white/42">
                  Recommended path
                </p>
                <h3 className="mt-2 font-serif text-3xl leading-none text-white md:text-4xl">
                  From student claims to trusted proof
                </h3>
              </div>

              <div className="mt-6 grid gap-3 lg:grid-cols-2">
                {quickStart.map((step, index) => (
                  <div key={step} className="flex gap-3 border border-white/10 bg-white/[0.035] p-4">
                    <span className="grid h-7 w-7 shrink-0 place-items-center border border-emerald-200/28 bg-emerald-300/10 text-xs font-bold text-emerald-100">
                      {index + 1}
                    </span>
                    <p className="text-sm leading-6 text-white/72">{step}</p>
                  </div>
                ))}
              </div>

              <div className="mt-8 flex items-center gap-2 border-b border-white/10 pb-3">
                <Route className="h-5 w-5 text-amber-100" />
                <h3 className="font-serif text-2xl leading-none text-white">Feature Flow</h3>
              </div>

              <div className="mt-4 space-y-3">
                {flowSteps.map((project, index) => (
                  <article key={project.featureKey ?? project.title} className="grid gap-4 border border-white/10 bg-black/22 p-4 md:grid-cols-[7rem_1fr_auto] md:items-center">
                    <div>
                      <div className="text-[0.65rem] font-bold uppercase tracking-[0.18em] text-white/38">{project.date}</div>
                      <div className="mt-1 text-2xl font-semibold leading-none text-white/90">{String(index + 1).padStart(2, "0")}</div>
                    </div>
                    <div>
                      <h4 className="text-base font-semibold text-white">{project.title}</h4>
                      <p className="mt-1 text-sm leading-6 text-white/62">{project.subtext}</p>
                    </div>
                    <button
                      type="button"
                      className="inline-flex items-center justify-center gap-2 border border-white/16 px-3 py-2 text-xs font-bold uppercase tracking-[0.14em] text-white/72 transition hover:border-emerald-200/45 hover:bg-emerald-300/10 hover:text-emerald-100 focus:outline-none focus:ring-2 focus:ring-white/35"
                      onClick={() => openFeature(project.featureKey)}
                    >
                      Open
                      <ArrowRight className="h-4 w-4" />
                    </button>
                  </article>
                ))}
              </div>

              <div className="mt-6 border border-emerald-200/18 bg-emerald-300/10 p-4">
                <h3 className="flex items-center gap-2 text-sm font-semibold text-emerald-100">
                  <CheckCircle2 className="h-4 w-4" />
                  Best practice for users
                </h3>
                <p className="mt-2 text-sm leading-6 text-emerald-50/78">
                  Treat the website as a proof journey: enter claims, verify them with evidence, measure readiness, then use the roadmap and Trust Stamp to explain progress clearly to mentors, placement teams, and recruiters.
                </p>
              </div>
            </div>
          </section>
        </div>
      )}
    </>
  );
};

export default GuidebookOverlay;
