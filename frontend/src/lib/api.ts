/**
 * api.ts — MatdaanMitra API client
 *
 * ALL backend calls go through this file.
 * Firebase ID tokens are injected automatically on every request.
 *
 * FIX 1 — Stale token (causes "Invalid authentication token" after ~1 hour):
 *   getIdToken(false) returns the cached token even when expired/near-expiry.
 *   Changed to getIdToken(true) to force-refresh when the token is within
 *   5 minutes of expiry. Firebase SDK handles the refresh transparently;
 *   the only cost is one extra network round-trip every ~55 minutes.
 *
 *   See: https://firebase.google.com/docs/auth/admin/verify-id-tokens#web
 *
 * FIX 2 — Race condition on first message (causes "Not authenticated"):
 *   authHeaders() called getAuth().currentUser synchronously. On first load,
 *   ensureAuth() is still in-flight (anonymous sign-in is async), so
 *   currentUser is null for the first 200–800ms. Any message sent before
 *   ensureAuth() resolves threw an ApiError(401) immediately.
 *
 *   Fix: waitForAuth() wraps onAuthStateChanged in a Promise that resolves
 *   once Firebase has a user (either from the session cache or after silent
 *   anonymous sign-in completes). authHeaders() awaits this before reading
 *   currentUser. The wait is instant if the user is already signed in.
 */

import { getAuth, onAuthStateChanged } from 'firebase/auth';
import type { EROOffice, VoterStatus, RetrievedChunk, AgentTraceEntry } from '../types/voter';
import { signOutUser, ensureAuth } from './firebase';

const BACKEND_URL =
  (process.env.NEXT_PUBLIC_BACKEND_URL ?? 'http://localhost:8000').replace(/\/$/, '');

// ─── Auth helpers ──────────────────────────────────────────────────────────────

/**
 * Resolves once Firebase Auth has a non-null current user.
 *
 * On a warm session (returning user): resolves in <5ms (synchronous from cache).
 * On first load with anonymous sign-in: resolves after ensureAuth() completes
 *   (~200–800ms depending on network). Subsequent calls resolve immediately.
 *
 * Rejects after 10 seconds to avoid hanging the UI indefinitely if Firebase
 * is completely misconfigured (no API key, wrong project, etc.).
 */
function waitForAuth(): Promise<void> {
  return new Promise((resolve, reject) => {
    const auth = getAuth();

    // If Firebase already has a user (cached session), resolve immediately
    // without setting up a listener at all.
    if (auth.currentUser) {
      resolve();
      return;
    }

    const TIMEOUT_MS = 10_000;
    let settled = false;

    const timer = setTimeout(() => {
      if (!settled) {
        settled = true;
        unsubscribe();
        reject(new ApiError(
          'Authentication timed out. Please reload the page.',
          401,
        ));
      }
    }, TIMEOUT_MS);

    const unsubscribe = onAuthStateChanged(auth, (user) => {
      if (user && !settled) {
        settled = true;
        clearTimeout(timer);
        unsubscribe();
        resolve();
      }
    });
  });
}

/**
 * Returns auth headers for a backend request.
 *
 * - Awaits waitForAuth() so we never call getIdToken on a null user.
 * - Passes forceRefresh=true so Firebase automatically renews tokens
 *   that are expired or within the SDK's refresh window (~5 min before expiry).
 *   This eliminates "Invalid authentication token" errors on long sessions.
 */
async function authHeaders(): Promise<HeadersInit> {
  // Wait for Firebase to have a user before trying to get a token.
  // No-op if already authenticated; ~200-800ms on first cold load.
  await waitForAuth();

  const user = getAuth().currentUser;
  if (!user) {
    // Shouldn't reach here after waitForAuth resolves, but guard anyway.
    throw new ApiError('Not authenticated. Please reload the page.', 401);
  }

  // forceRefresh=true: Firebase checks token expiry and silently refreshes
  // if needed. The returned token is always valid for at least 5 minutes.
  // Cost: ~1 extra network round-trip every ~55 minutes per session.
  const token = await user.getIdToken(/* forceRefresh= */ true);

  return {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${token}`,
  };
}

// ─── Typed error ───────────────────────────────────────────────────────────────

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number = 500,
    public readonly detail?: unknown,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

async function toApiError(res: Response): Promise<ApiError> {
  try {
    const body = await res.json();
    const msg =
      typeof body?.detail === 'string' ? body.detail : `Request failed (${res.status})`;
    return new ApiError(msg, res.status, body);
  } catch {
    return new ApiError(`Request failed (${res.status})`, res.status);
  }
}

// ─── Generic fetch ─────────────────────────────────────────────────────────────

async function apiFetch<T>(
  path: string,
  init: RequestInit & { skipAuth?: boolean } = {},
): Promise<T> {
  const { skipAuth, ...rest } = init;
  try {
    const headers = skipAuth
      ? { 'Content-Type': 'application/json' }
      : await authHeaders();
    const res = await fetch(`${BACKEND_URL}${path}`, { ...rest, headers });
    if (!res.ok) throw await toApiError(res);
    if (res.status === 204) return undefined as unknown as T;
    return res.json() as Promise<T>;
  } catch (err) {
    if (err instanceof ApiError && err.status === 401 && !skipAuth) {
      console.warn('Authentication failed (401). Retrying with fresh session...');
      try {
        await signOutUser();
        await ensureAuth();
        const headers = await authHeaders();
        const res = await fetch(`${BACKEND_URL}${path}`, { ...rest, headers });
        if (!res.ok) throw await toApiError(res);
        if (res.status === 204) return undefined as unknown as T;
        return res.json() as Promise<T>;
      } catch (retryErr) {
        throw retryErr;
      }
    }
    throw err;
  }
}

// ─── ERO locator ───────────────────────────────────────────────────────────────

export async function getEROLocation(pincode: string): Promise<EROOffice> {
  return apiFetch<EROOffice>(`/ero/${encodeURIComponent(pincode)}`);
}

// ─── Voter status ──────────────────────────────────────────────────────────────

export async function getVoterStatus(epic: string): Promise<VoterStatus> {
  return apiFetch<VoterStatus>(`/voter/${encodeURIComponent(epic)}`);
}

// ─── Chat streaming ────────────────────────────────────────────────────────────

export type SSEToken =
  | { type: 'token'; content: string }
  | { type: 'replace'; content: string }
  | { type: 'done'; confidence: number; source_chunks: RetrievedChunk[]; agent_trace: AgentTraceEntry[] }
  | { type: 'error'; error: string };

export async function* streamChat(
  sessionId: string,
  message: string,
  language: string,
): AsyncGenerator<SSEToken> {
  let headers = await authHeaders();
  let res = await fetch(`${BACKEND_URL}/chat`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ session_id: sessionId, message, language }),
  });

  if (!res.ok) {
    const err = await toApiError(res);
    if (err.status === 401) {
      console.warn('Authentication failed (401) on chat stream. Retrying with fresh session...');
      try {
        await signOutUser();
        await ensureAuth();
        headers = await authHeaders();
        res = await fetch(`${BACKEND_URL}/chat`, {
          method: 'POST',
          headers,
          body: JSON.stringify({ session_id: sessionId, message, language }),
        });
        if (!res.ok) throw await toApiError(res);
      } catch (retryErr) {
        throw retryErr;
      }
    } else {
      throw err;
    }
  }

  const reader = res.body?.getReader();
  if (!reader) throw new ApiError('No response body from chat endpoint', 500);

  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() ?? '';

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        const payload = line.slice(6).trim();
        if (payload === '[DONE]') return;
        try {
          yield JSON.parse(payload) as SSEToken;
        } catch {
          // skip malformed JSON frames
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

// ─── Sarvam TTS ────────────────────────────────────────────────────────────────

export async function synthesizeSpeech(
  text: string,
  language: string,
): Promise<string | null> {
  try {
    const data = await apiFetch<{ audio_b64: string }>('/tts', {
      method: 'POST',
      body: JSON.stringify({ text, language }),
    });
    return data.audio_b64 ?? null;
  } catch {
    return null;
  }
}

// ─── Grievance Letter ──────────────────────────────────────────────────────────

export async function generateGrievanceLetter(
  sessionId: string,
  issueType: string,
): Promise<Blob> {
  let headers = await authHeaders();
  let res = await fetch(`${BACKEND_URL}/grievance/letter`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ session_id: sessionId, issue_type: issueType }),
  });
  if (!res.ok) {
    const err = await toApiError(res);
    if (err.status === 401) {
      console.warn('Authentication failed (401) on grievance letter. Retrying with fresh session...');
      try {
        await signOutUser();
        await ensureAuth();
        headers = await authHeaders();
        res = await fetch(`${BACKEND_URL}/grievance/letter`, {
          method: 'POST',
          headers,
          body: JSON.stringify({ session_id: sessionId, issue_type: issueType }),
        });
        if (!res.ok) throw await toApiError(res);
      } catch (retryErr) {
        throw retryErr;
      }
    } else {
      throw err;
    }
  }
  return res.blob();
}