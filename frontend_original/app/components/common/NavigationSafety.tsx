"use client";

import { useLayoutEffect } from "react";

const HISTORY_KEY = "placementTrustNavigation";
const SAFE_ENTRY = "safe";
const GUARD_ENTRY = "guard";

const withNavigationState = (entry: typeof SAFE_ENTRY | typeof GUARD_ENTRY) => ({
  ...(window.history.state ?? {}),
  [HISTORY_KEY]: entry,
});

const NavigationSafety = () => {
  useLayoutEffect(() => {
    if (!["localhost", "127.0.0.1"].includes(window.location.hostname)) return;

    let disposed = false;
    let hasArmed = false;

    const armBackGuard = () => {
      if (disposed) return;
      if (hasArmed && window.history.state?.[HISTORY_KEY] === GUARD_ENTRY) return;
      window.history.replaceState(withNavigationState(SAFE_ENTRY), "", window.location.href);
      window.history.pushState(withNavigationState(GUARD_ENTRY), "", window.location.href);
      hasArmed = true;
    };

    armBackGuard();

    const handlePopState = () => {
      armBackGuard();
    };

    const handlePageShow = () => {
      armBackGuard();
    };

    window.addEventListener("popstate", handlePopState);
    window.addEventListener("pageshow", handlePageShow);
    return () => {
      disposed = true;
      window.removeEventListener("popstate", handlePopState);
      window.removeEventListener("pageshow", handlePageShow);
    };
  }, []);

  return null;
};

export default NavigationSafety;
