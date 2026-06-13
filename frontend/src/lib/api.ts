/**
 * api.ts — MatdaanMitra API client
 *
 * ALL backend calls go through this file.
 * Firebase ID tokens are injected automatically on every request.
 *
 * Fix: getVoterStatus now calls GET /voter/{epic_number}
 *      matching the actual backend route in voter.py.
 *      Previously called /voter/status?epic=... which returned 404.
 */

import { getAuth } from 'firebase/auth';
import type { EROOffice, VoterStatus, RetrievedChunk, AgentTraceEntry } from '../types/voter';

const BACKEND_URL =
  (process.env.NEXT_PUBLIC_BACKEND_URL ?? 'http://localhost:8000').replace(/\/$/, '');

// ─── Auth helpers ──────────────────────────────────────────────────────────────

async function authHeaders(): Promise<HeadersInit> {
  const user = getAuth().currentUser;
  if (!user) throw new ApiError('Not authenticated. Please reload the page.', 401);
  const token = await user.getIdToken(false);
  return { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` };
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
  const headers = skipAuth
    ? { 'Content-Type': 'application/json' }
    : await authHeaders();
  const res = await fetch(`${BACKEND_URL}${path}`, { ...rest, headers });
  if (!res.ok) throw await toApiError(res);
  if (res.status === 204) return undefined as unknown as T;
  return res.json() as Promise<T>;
}

// ─── ERO locator ───────────────────────────────────────────────────────────────

export async function getEROLocation(pincode: string): Promise<EROOffice> {
  return apiFetch<EROOffice>(`/ero/${encodeURIComponent(pincode)}`);
}

// ─── Voter status ──────────────────────────────────────────────────────────────

/**
 * Look up voter by EPIC number.
 * Backend route: GET /voter/{epic_number}  (voter.py)
 * EPIC must be exactly 10 alphanumeric characters, e.g. "MH09001234"
 */
export async function getVoterStatus(epic: string): Promise<VoterStatus> {
  return apiFetch<VoterStatus>(`/voter/${encodeURIComponent(epic)}`);
}

// ─── Chat streaming ────────────────────────────────────────────────────────────

export type SSEToken =
  | { type: 'token'; content: string }
  | { type: 'done'; confidence: number; source_chunks: RetrievedChunk[]; agent_trace: AgentTraceEntry[] }
  | { type: 'error'; error: string };

/**
 * Async generator that streams SSE tokens from POST /chat.
 * Matches the `for await (const token of streamChat(...))` pattern in useChat.ts.
 */
export async function* streamChat(
  sessionId: string,
  message: string,
  language: string,
): AsyncGenerator<SSEToken> {
  const headers = await authHeaders();
  const res = await fetch(`${BACKEND_URL}/chat`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ session_id: sessionId, message, language }),
  });

  if (!res.ok) throw await toApiError(res);

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

/**
 * Requests speech synthesis from the backend Sarvam TTS proxy (POST /tts).
 * Returns a base64-encoded WAV string or null on failure.
 */
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

/**
 * Generates a pre-filled grievance complaint letter PDF.
 * Returns the PDF as a Blob.
 */
export async function generateGrievanceLetter(
  sessionId: string,
  issueType: string,
): Promise<Blob> {
  const headers = await authHeaders();
  const res = await fetch(`${BACKEND_URL}/grievance/letter`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ session_id: sessionId, issue_type: issueType }),
  });
  if (!res.ok) throw await toApiError(res);
  return res.blob();
}