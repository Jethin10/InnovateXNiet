import { Project } from "../types";

// TODO: Move this to API
export const PROJECTS: Project[] = [
  {
    title: 'AI Mentor Pipeline',
    date: 'CORE FLOW',
    subtext: 'Resume upload, AI skill extraction, ATS scoring, adaptive testing, proctoring signals, explainable role fit, and roadmap in one flow.',
    featureKey: 'ai_pipeline',
  },
  {
    title: 'Student Intake',
    date: 'STEP 01',
    subtext: 'Create a student, capture target role, claimed skills, consent, and generate the staged verification plan from the backend.',
    featureKey: 'intake',
  },
  {
    title: 'Resume ATS',
    date: 'STEP 02',
    subtext: 'Analyze resume claims, unsupported skills, project count, ATS keyword fit, and recommendations for the target role.',
    featureKey: 'resume',
  },
  {
    title: 'GitHub Evidence',
    date: 'STEP 03',
    subtext: 'Connect a GitHub username, inspect public repos, summarize contributions, and generate evidence-backed project upgrades.',
    featureKey: 'github',
  },
  {
    title: 'Coding Harness',
    date: 'STEP 04',
    subtext: 'Practice backend-owned problems with hidden tests, submission scoring, and coding proof recorded as evidence.',
    featureKey: 'coding',
  },
  {
    title: 'Assessment',
    date: 'STEP 05',
    subtext: 'Start a timed attempt, answer backend-owned questions, submit responses, and trigger trust scoring.',
    featureKey: 'assessment',
  },
  {
    title: 'Trust Score',
    date: 'STEP 06',
    subtext: 'View readiness, bluff-risk, evidence alignment, skill scores, explanations, and positive/risk signals.',
    featureKey: 'score',
  },
  {
    title: 'Roadmap Graph',
    date: 'STEP 07',
    subtext: 'Fetch the personalized roadmap, show locked/recommended nodes, and complete proof-gated milestones.',
    featureKey: 'roadmap',
  },
  {
    title: 'Trust Stamp',
    date: 'STEP 08',
    subtext: 'Open the consent-based public stamp, verify its signature, and show recruiter-facing evidence.',
    featureKey: 'stamp',
  },
  {
    title: 'Jobs That Suit You',
    date: 'STEP 09',
    subtext: 'Fetch live job listings, rank them by resume skills, ATS, test, and trust signals, then show match scores, gaps, and fit explanations.',
    featureKey: 'jobs',
  },
];
