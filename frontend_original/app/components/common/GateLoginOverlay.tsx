"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { KeyRound, Mail, ShieldCheck } from "lucide-react";
import { onIdTokenChanged } from "firebase/auth";

import {
  createAccountWithEmail,
  ensureAuthPersistence,
  getFirebaseAuth,
  getFirebaseConfigStatus,
  getFriendlyAuthError,
  sendGatePasswordReset,
  signInWithEmail,
  signInWithGoogle,
} from "../../lib/firebaseAuth";

type AuthMode = "signin" | "signup";
type AuthStatus = "checking" | "idle" | "loading" | "success" | "error";
const GATE_SESSION_KEY = "placement-trust-gate-unlocked";

const getConfigMessage = () => {
  const status = getFirebaseConfigStatus();

  if (status.configured) return "";

  return `Auth config missing: ${status.missingKeys.map(String).join(", ")}.`;
};

const GateLoginOverlay = () => {
  const [mode, setMode] = useState<AuthMode>("signin");
  const [hasMounted, setHasMounted] = useState(false);
  const [isComplete, setIsComplete] = useState(false);
  const [isLeaving, setIsLeaving] = useState(false);
  const [status, setStatus] = useState<AuthStatus>("checking");
  const [message, setMessage] = useState(getConfigMessage);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const isSigningUp = mode === "signup";
  const panelActive = isSigningUp;
  const isConfigured = useMemo(() => getFirebaseConfigStatus().configured, []);

  useEffect(() => {
    setHasMounted(true);
    setIsComplete(window.sessionStorage.getItem(GATE_SESSION_KEY) === "true");
  }, []);

  useEffect(() => {
    if (window.location.hostname !== "127.0.0.1") return;

    const { protocol, port, pathname, search, hash } = window.location;
    window.location.replace(`${protocol}//localhost${port ? `:${port}` : ""}${pathname}${search}${hash}`);
  }, []);

  const unlockGate = useCallback((successMessage: string) => {
    window.sessionStorage.setItem(GATE_SESSION_KEY, "true");
    setStatus("success");
    setMessage(successMessage);
    setIsLeaving(true);
    window.setTimeout(() => setIsComplete(true), 760);
  }, []);

  useEffect(() => {
    if (!isComplete) return;
    const marker = { placementTrustGate: true };
    window.history.replaceState({ ...(window.history.state ?? {}), ...marker }, "", window.location.href);
    const keepGateSession = () => {
      window.sessionStorage.setItem(GATE_SESSION_KEY, "true");
    };
    window.addEventListener("popstate", keepGateSession);
    window.addEventListener("pageshow", keepGateSession);
    return () => {
      window.removeEventListener("popstate", keepGateSession);
      window.removeEventListener("pageshow", keepGateSession);
    };
  }, [isComplete]);

  useEffect(() => {
    if (!isConfigured) return;

    let settled = false;

    ensureAuthPersistence()
      .then((auth) => {
        if (auth.currentUser) {
          settled = true;
          unlockGate("Session restored. Opening the gate.");
        } else if (!settled) {
          setStatus("idle");
          setMessage(getConfigMessage());
        }
      })
      .catch((error) => {
        if (!settled) {
          setStatus("error");
          setMessage(getFriendlyAuthError(error));
        }
      });

    const unsubscribe = onIdTokenChanged(getFirebaseAuth(), (user) => {
      if (user) {
        settled = true;
        unlockGate("Signed in. Opening the gate.");
        return;
      }

      if (!settled) {
        setStatus("idle");
        setMessage(getConfigMessage());
      }
    });

    return () => {
      settled = true;
      unsubscribe();
    };
  }, [isConfigured, unlockGate]);

  useEffect(() => {
    if (isComplete) return;

    const preventScroll = (event: Event) => event.preventDefault();
    const originalOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    window.addEventListener("wheel", preventScroll, { passive: false, capture: true });
    window.addEventListener("touchmove", preventScroll, { passive: false, capture: true });

    return () => {
      document.body.style.overflow = originalOverflow;
      window.removeEventListener("wheel", preventScroll, { capture: true });
      window.removeEventListener("touchmove", preventScroll, { capture: true });
    };
  }, [isComplete]);

  const requireFirebase = () => {
    const configMessage = getConfigMessage();

    if (!configMessage) return true;

    setStatus("error");
    setMessage(configMessage);
    return false;
  };

  const handleEmailAuth = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!requireFirebase()) return;

    setStatus("loading");
    setMessage(isSigningUp ? "Creating your account..." : "Signing you in...");

    try {
      if (isSigningUp) {
        await createAccountWithEmail(name, email, password);
        unlockGate("Account created. Opening the gate.");
        return;
      }

      await signInWithEmail(email, password);
      unlockGate("Signed in. Opening the gate.");
    } catch (error) {
      setStatus("error");
      setMessage(getFriendlyAuthError(error));
    }
  };

  const handlePasswordReset = async () => {
    if (!requireFirebase()) return;

    if (!email.trim()) {
      setStatus("error");
      setMessage("Enter your email first, then request a reset link.");
      return;
    }

    setStatus("loading");
    setMessage("Sending reset link...");

    try {
      await sendGatePasswordReset(email);
      setStatus("success");
      setMessage("Password reset email sent. Check your inbox.");
    } catch (error) {
      setStatus("error");
      setMessage(getFriendlyAuthError(error));
    }
  };

  const handleGoogleAuth = async () => {
    if (!requireFirebase()) return;

    setStatus("loading");
    setMessage("Opening Google sign-in...");

    try {
      await signInWithGoogle();
      unlockGate("Google sign-in complete. Opening the gate.");
    } catch (error) {
      setStatus("error");
      setMessage(getFriendlyAuthError(error));
    }
  };

  const switchMode = (nextMode: AuthMode) => {
    setMode(nextMode);
    setStatus("idle");
    setMessage(getConfigMessage());
  };

  if (!hasMounted || isComplete) return null;

  return (
    <div
      className={`gate-login-overlay selectable ${isLeaving ? "gate-login-overlay--leaving" : ""}`}
      onWheel={(event) => event.preventDefault()}
      onTouchMove={(event) => event.preventDefault()}
    >
      <div className="gate-login-copy">
        <span>PLACEMENT TRUST PASSPORT</span>
        <h2>Authenticate before the gate.</h2>
      </div>

      <div className={`gate-auth-wrapper ${panelActive ? "panel-active" : ""}`}>
        <div className="gate-auth-form-box gate-register-form-box">
          <form onSubmit={handleEmailAuth}>
            <ShieldCheck className="gate-auth-mark" size={28} />
            <h1>Create Account</h1>
            <p className="gate-auth-subtitle">
              Start a verified profile that can connect GitHub evidence, resumes, and assessment results.
            </p>
            <span>Register with email</span>
            <input
              type="text"
              placeholder="Full Name"
              autoComplete="name"
              value={name}
              onChange={(event) => setName(event.target.value)}
              required={isSigningUp}
            />
            <input
              type="email"
              placeholder="Email Address"
              autoComplete="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
            />
            <input
              type="password"
              placeholder="Password"
              autoComplete="new-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              minLength={6}
              required
            />
            <button className="gate-auth-primary" type="submit" disabled={status === "loading"}>
              {status === "loading" && isSigningUp ? "Creating..." : "Create Account"}
            </button>
            <div className="gate-mobile-switch">
              <p>Already verified?</p>
              <button type="button" onClick={() => switchMode("signin")}>Sign In</button>
            </div>
          </form>
        </div>

        <div className="gate-auth-form-box gate-login-form-box">
          <form onSubmit={handleEmailAuth}>
            <KeyRound className="gate-auth-mark" size={28} />
            <h1>Sign In</h1>
            <p className="gate-auth-subtitle">
              Unlock your passport and continue into the connected backend workspace.
            </p>
            <div className="gate-social-links">
              <button
                type="button"
                aria-label="Sign in with Google"
                onClick={handleGoogleAuth}
                disabled={status === "loading"}
                title="Sign in with Google"
              >
                <Mail size={18} />
              </button>
            </div>
            <span>Use email and password</span>
            <input
              type="email"
              placeholder="Email Address"
              autoComplete="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
            />
            <input
              type="password"
              placeholder="Password"
              autoComplete="current-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />
            <button className="gate-auth-link" type="button" onClick={handlePasswordReset}>
              Forgot your password?
            </button>
            <button className="gate-auth-primary" type="submit" disabled={status === "loading"}>
              {status === "loading" && !isSigningUp ? "Signing in..." : "Sign In"}
            </button>
            <div className="gate-mobile-switch">
              <p>New to the passport?</p>
              <button type="button" onClick={() => switchMode("signup")}>Create Account</button>
            </div>
          </form>
        </div>

        <div className="gate-auth-status" data-status={status} aria-live="polite">
          {message || (status === "checking" ? "Checking Firebase session..." : "Firebase Auth ready.")}
        </div>

        <div className="gate-slide-panel-wrapper">
          <div className="gate-slide-panel">
            <div className="gate-panel-content gate-panel-content-left">
              <h1>New Here?</h1>
              <p>Create an account to bind your resume, GitHub evidence, and coding proof into one trust passport.</p>
              <button className="gate-transparent-btn" type="button" onClick={() => switchMode("signup")}>
                Create Account
              </button>
            </div>
            <div className="gate-panel-content gate-panel-content-right">
              <h1>Already Verified?</h1>
              <p>Use your existing account to reopen the gate and continue where your proof graph left off.</p>
              <button className="gate-transparent-btn" type="button" onClick={() => switchMode("signin")}>
                Sign In
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default GateLoginOverlay;
