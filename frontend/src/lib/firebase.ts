/**
 * firebase.ts — Firebase client with anonymous + Google Sign-In
 *
 * Exports:
 *   auth          — Firebase Auth instance
 *   db            — Firestore instance
 *   ensureAuth    — Anonymous sign-in (silent, used on first load)
 *   signInWithGoogle — Google OAuth popup (links to existing anonymous session)
 *   signOutUser   — Signs out and clears local state
 *   isAnonymous   — Returns true if current user is anonymous
 *   onAuthChange  — Subscribe to auth state changes
 */

import { initializeApp, getApps, type FirebaseApp } from 'firebase/app';
import {
  getAuth,
  signInAnonymously,
  GoogleAuthProvider,
  signInWithPopup,
  linkWithPopup,
  signOut,
  onAuthStateChanged,
  type Auth,
  type User,
} from 'firebase/auth';
import { getFirestore, type Firestore } from 'firebase/firestore';

const firebaseConfig = {
  apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY,
  authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN,
  projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID,
  appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID,
};

const app: FirebaseApp =
  getApps().length ? getApps()[0] : initializeApp(firebaseConfig);

export const auth: Auth = getAuth(app);
export const db: Firestore = getFirestore(app);

// ── Anonymous sign-in ─────────────────────────────────────────────────────────

/**
 * Ensures a Firebase user exists. Signs in anonymously if no user is present.
 * Used silently on app load — user never sees a UI prompt.
 */
export async function ensureAuth(): Promise<string> {
  let user = auth.currentUser;
  if (!user) {
    const credential = await signInAnonymously(auth);
    user = credential.user;
  }
  return user.uid;
}

// ── Google Sign-In ────────────────────────────────────────────────────────────

/**
 * Opens the Google Sign-In popup.
 *
 * If the current user is anonymous, links the anonymous account to the
 * Google credential — preserving their conversation history and voter profile.
 *
 * If no user exists, performs a fresh Google sign-in.
 *
 * Returns the UID on success, throws on cancellation or error.
 */
export async function signInWithGoogle(): Promise<string> {
  const provider = new GoogleAuthProvider();
  provider.setCustomParameters({ prompt: 'select_account' });

  const currentUser = auth.currentUser;

  if (currentUser?.isAnonymous) {
    // Link anonymous session → Google account (preserves history)
    try {
      const result = await linkWithPopup(currentUser, provider);
      return result.user.uid;
    } catch (err: unknown) {
      // If the Google account already has a Firebase account, just sign in
      const code = (err as { code?: string })?.code;
      if (code === 'auth/credential-already-in-use' || code === 'auth/email-already-in-use') {
        const result = await signInWithPopup(auth, provider);
        return result.user.uid;
      }
      throw err;
    }
  }

  const result = await signInWithPopup(auth, provider);
  return result.user.uid;
}

// ── Sign out ──────────────────────────────────────────────────────────────────

export async function signOutUser(): Promise<void> {
  await signOut(auth);
}

// ── Auth state helpers ────────────────────────────────────────────────────────

export function isAnonymous(): boolean {
  return auth.currentUser?.isAnonymous ?? true;
}

export function getCurrentUser(): User | null {
  return auth.currentUser;
}

/**
 * Subscribe to auth state changes.
 * Returns the unsubscribe function — call it in useEffect cleanup.
 */
export function onAuthChange(callback: (user: User | null) => void): () => void {
  return onAuthStateChanged(auth, callback);
}