'use client';

import { FileText, LogOut, UserRound } from "lucide-react";
import { AnimatedDock } from "@/components/ui/animated-dock";
import { signOutGate } from "@/app/lib/firebaseAuth";
import { useFeatureStore, usePortalStore } from "@stores";

const GATE_SESSION_KEY = "placement-trust-gate-unlocked";
const FEATURE_SESSION_KEY = "placement-trust-demo-session";
const ADAPTIVE_CODING_TEST_KEY = "placement-trust-adaptive-coding-test";

const AccountDock = () => {
  const setActiveFeatureKey = useFeatureStore((state) => state.setActiveFeatureKey);
  const isPortalActive = usePortalStore((state) => !!state.activePortalId);
  const logout = async () => {
    try {
      await signOutGate();
    } catch {
      // Reload after clearing session state so Firebase errors cannot leave the gate open.
    } finally {
      window.sessionStorage.removeItem(GATE_SESSION_KEY);
      window.sessionStorage.removeItem(FEATURE_SESSION_KEY);
      window.sessionStorage.removeItem(ADAPTIVE_CODING_TEST_KEY);
      window.sessionStorage.removeItem("ai-mentor-resume-text");
      window.location.reload();
    }
  };

  return (
    <div
      className={`fixed bottom-5 left-1/2 z-30 -translate-x-1/2 transition-opacity duration-500 ${
        isPortalActive ? "opacity-100" : "opacity-95"
      }`}
    >
      <AnimatedDock
        className="border-0 bg-transparent shadow-none backdrop-blur-0"
        items={[
          {
            link: "https://github.com/Jethin10/",
            target: "_blank",
            label: "GitHub",
            Icon: <GitHubIcon />,
          },
          {
            link: "https://www.linkedin.com/in/jethin-kosaraju/",
            target: "_blank",
            label: "LinkedIn",
            Icon: <LinkedInIcon />,
          },
          {
            link: "#account",
            label: "Account",
            Icon: <UserRound size={23} />,
            onClick: () => setActiveFeatureKey("account"),
          },
          {
            link: "https://leetcode.com/u/ishu7w/",
            target: "_blank",
            label: "LeetCode",
            Icon: <LeetCodeIcon />,
          },
          {
            link: "/Jethin_Resume.pdf",
            target: "_blank",
            label: "Resume",
            Icon: <ResumeIcon />,
          },
          {
            link: "#logout",
            label: "Logout",
            Icon: <LogOut size={22} />,
            onClick: logout,
          },
        ]}
      />
    </div>
  );
};

const GitHubIcon = () => (
  <svg aria-hidden="true" viewBox="0 0 24 24" className="h-[22px] w-[22px]" fill="currentColor">
    <path d="M12 .5a12 12 0 0 0-3.79 23.39c.6.11.82-.26.82-.58v-2.05c-3.34.73-4.04-1.42-4.04-1.42-.55-1.38-1.34-1.75-1.34-1.75-1.09-.75.08-.74.08-.74 1.2.09 1.84 1.24 1.84 1.24 1.07 1.83 2.8 1.3 3.49.99.11-.78.42-1.3.76-1.6-2.66-.3-5.47-1.33-5.47-5.93 0-1.31.47-2.38 1.24-3.22-.12-.3-.54-1.52.12-3.18 0 0 1.01-.32 3.3 1.23a11.5 11.5 0 0 1 6 0c2.29-1.55 3.3-1.23 3.3-1.23.66 1.66.24 2.88.12 3.18.77.84 1.24 1.91 1.24 3.22 0 4.61-2.81 5.62-5.49 5.92.43.37.81 1.1.81 2.22v3.29c0 .32.22.69.83.57A12 12 0 0 0 12 .5Z" />
  </svg>
);

const LinkedInIcon = () => (
  <svg aria-hidden="true" viewBox="0 0 24 24" className="h-[22px] w-[22px]" fill="currentColor">
    <path d="M20.45 20.45h-3.56v-5.57c0-1.33-.02-3.04-1.85-3.04-1.85 0-2.14 1.45-2.14 2.94v5.67H9.34V9h3.42v1.56h.05c.48-.91 1.64-1.86 3.37-1.86 3.61 0 4.27 2.37 4.27 5.46v6.29ZM5.32 7.43a2.06 2.06 0 1 1 0-4.12 2.06 2.06 0 0 1 0 4.12Zm1.78 13.02H3.54V9H7.1v11.45ZM22.23 0H1.76C.79 0 0 .77 0 1.72v20.56C0 23.23.79 24 1.76 24h20.47c.97 0 1.77-.77 1.77-1.72V1.72C24 .77 23.2 0 22.23 0Z" />
  </svg>
);

const LeetCodeIcon = () => (
  <svg aria-hidden="true" viewBox="0 0 24 24" className="h-[23px] w-[23px]" fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.2">
    <path d="m14.4 4.2-7.1 7.1a3.4 3.4 0 0 0 0 4.8l2.1 2.1a3.4 3.4 0 0 0 4.8 0l2-2" />
    <path d="m9.2 6.7 3-3a3.3 3.3 0 0 1 4.7 0" />
    <path d="M9.7 12h10" />
    <path d="m14 19.7-1.8 1.8" />
  </svg>
);

const ResumeIcon = () => (
  <span className="relative flex h-[23px] w-[20px] items-center justify-center">
    <FileText size={23} strokeWidth={2.1} />
    <span className="absolute bottom-[3px] h-[2px] w-[9px] bg-current" />
  </span>
);

export default AccountDock;
