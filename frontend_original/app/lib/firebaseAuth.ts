"use client";

import { FirebaseError, initializeApp, getApps, type FirebaseApp } from "firebase/app";
import {
  browserLocalPersistence,
  createUserWithEmailAndPassword,
  getAuth,
  GoogleAuthProvider,
  sendPasswordResetEmail,
  setPersistence,
  signInWithPopup,
  signInWithEmailAndPassword,
  signOut,
  updateProfile,
  type Auth,
  type UserCredential,
} from "firebase/auth";

type FirebaseConfig = {
  apiKey?: string;
  authDomain?: string;
  projectId?: string;
  storageBucket?: string;
  messagingSenderId?: string;
  appId?: string;
  measurementId?: string;
};

const firebaseConfig: FirebaseConfig = {
  apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY,
  authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN,
  projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID,
  storageBucket: process.env.NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: process.env.NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID,
  appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID,
  measurementId: process.env.NEXT_PUBLIC_FIREBASE_MEASUREMENT_ID,
};

const requiredConfigKeys: Array<keyof FirebaseConfig> = [
  "apiKey",
  "authDomain",
  "projectId",
  "appId",
];

let firebaseApp: FirebaseApp | null = null;
let firebaseAuth: Auth | null = null;
let persistenceReady: Promise<void> | null = null;

export const isFirebaseConfigured = () =>
  requiredConfigKeys.every((key) => Boolean(firebaseConfig[key]));

export const getFirebaseConfigStatus = () => {
  const missingKeys = requiredConfigKeys.filter((key) => !firebaseConfig[key]);

  return {
    configured: missingKeys.length === 0,
    missingKeys,
  };
};

export const getFirebaseAuth = (): Auth => {
  if (!isFirebaseConfigured()) {
    throw new Error(
      "Firebase is not configured. Add the NEXT_PUBLIC_FIREBASE_* values to frontend_original/.env.local.",
    );
  }

  if (!firebaseApp) {
    firebaseApp = getApps().length ? getApps()[0] : initializeApp(firebaseConfig);
  }

  if (!firebaseAuth) {
    firebaseAuth = getAuth(firebaseApp);
  }

  return firebaseAuth;
};

export const ensureAuthPersistence = async () => {
  const auth = getFirebaseAuth();

  if (!persistenceReady) {
    persistenceReady = setPersistence(auth, browserLocalPersistence);
  }

  await persistenceReady;
  return auth;
};

export const signInWithEmail = (email: string, password: string) =>
  ensureAuthPersistence().then((auth) => signInWithEmailAndPassword(auth, email, password));

export const signInWithGoogle = async () => {
  const auth = await ensureAuthPersistence();
  const provider = new GoogleAuthProvider();
  provider.setCustomParameters({ prompt: "select_account" });
  return signInWithPopup(auth, provider);
};

export const createAccountWithEmail = async (
  name: string,
  email: string,
  password: string,
): Promise<UserCredential> => {
  const auth = await ensureAuthPersistence();
  const credential = await createUserWithEmailAndPassword(auth, email, password);

  if (name.trim()) {
    await updateProfile(credential.user, { displayName: name.trim() });
  }

  return credential;
};

export const sendGatePasswordReset = (email: string) =>
  ensureAuthPersistence().then((auth) => sendPasswordResetEmail(auth, email));

export const signOutGate = () =>
  ensureAuthPersistence().then((auth) => signOut(auth));

export const getFriendlyAuthError = (error: unknown) => {
  if (!(error instanceof FirebaseError)) {
    return error instanceof Error ? error.message : "Authentication failed. Please try again.";
  }

  const messages: Record<string, string> = {
    "auth/account-exists-with-different-credential":
      "That email already exists with a different sign-in method.",
    "auth/email-already-in-use": "That email already has an account. Try signing in.",
    "auth/invalid-credential": "The email or password is incorrect.",
    "auth/invalid-email": "Enter a valid email address.",
    "auth/missing-password": "Enter a password.",
    "auth/network-request-failed": "Network error. Check your connection and try again.",
    "auth/operation-not-allowed": "This sign-in method is not enabled in Firebase Authentication.",
    "auth/popup-closed-by-user": "The Google sign-in window was closed before sign-in finished.",
    "auth/popup-blocked": "The browser blocked Google sign-in. Allow popups for this site, then try again.",
    "auth/too-many-requests": "Too many attempts. Wait a moment and try again.",
    "auth/unauthorized-domain": "Use http://localhost:3000, or add this domain in Firebase Authorized domains.",
    "auth/user-not-found": "No account exists for that email.",
    "auth/weak-password": "Use a password with at least 6 characters.",
    "auth/wrong-password": "The email or password is incorrect.",
  };

  return messages[error.code] ?? error.message;
};
