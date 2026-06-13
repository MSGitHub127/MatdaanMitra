/**
 * voter.ts — All TypeScript interfaces for MatdaanMitra
 *
 * FIX (P0 — production audit):
 *   VoterStatus was declared as a single flat interface with required fields
 *   (name, father_name, age, etc.) that are ABSENT in 2 of 3 backend response
 *   shapes. Components accessing voterStatus.name on an nvsp_redirect payload
 *   would throw TypeError: Cannot read properties of undefined.
 *
 *   The backend returns three distinct shapes from GET /voter/{epic}:
 *     1. VoterStatusFound      — found=true, nvsp_redirect=false → all fields present
 *     2. VoterStatusRedirect   — nvsp_redirect=true → only nvsp_url present
 *     3. VoterStatusNotFound   — found=false, nvsp_redirect=false → only message/reason
 *
 *   VoterStatus is now a TypeScript discriminated union. All consumer components
 *   MUST narrow before accessing non-base fields:
 *
 *     if (voter.nvsp_redirect) {
 *       // TypeScript knows: VoterStatusRedirect → voter.nvsp_url is safe
 *     } else if (voter.found === true) {
 *       // TypeScript knows: VoterStatusFound → voter.name, voter.age etc. safe
 *     } else {
 *       // TypeScript knows: VoterStatusNotFound → voter.message, voter.reason safe
 *     }
 *
 * FIX (P3 — production audit):
 *   AgentTraceEntry: fields loosened to reflect per-node shape variance.
 *   Previously confidence_scores?: number[] was assumed universal; only
 *   rag_retrieval sets it. Guardrail sets confidence: number (singular).
 *   Synthesis sets method and input_tokens. Using a base + extra fields
 *   pattern prevents silent undefined access in UI rendering.
 */

// ─────────────────────────────────────────────────────────────────────────────
// VoterStatus — Discriminated Union
// ─────────────────────────────────────────────────────────────────────────────

/** Fields present in every response shape from GET /voter/{epic} */
interface VoterStatusBase {
  epic_number: string;
  found: boolean | null;
  nvsp_redirect: boolean;
  message?: string;
  reason?: string;
}

/** Voter found in the ECI roll — all demographic fields are present */
export interface VoterStatusFound extends VoterStatusBase {
  found: true;
  nvsp_redirect: false;
  name: string;
  father_name: string;
  age: number;
  gender: string;
  address: string;
  polling_station: string;
  assembly_constituency: string;
  parliamentary_constituency: string;
  status: string;
}

/** ECI returned an NVSP redirect (API quota / state-level routing) */
export interface VoterStatusRedirect extends VoterStatusBase {
  nvsp_redirect: true;
  nvsp_url: string;
}

/** Voter not found in the roll */
export interface VoterStatusNotFound extends VoterStatusBase {
  found: false;
  nvsp_redirect: false;
  nvsp_url?: string;
}

/**
 * The union type. Always narrow before accessing non-base fields:
 *
 *   if (status.nvsp_redirect) { ... status.nvsp_url ... }
 *   else if (status.found === true) { ... status.name ... }
 *   else { ... status.message ... }
 */
export type VoterStatus = VoterStatusFound | VoterStatusRedirect | VoterStatusNotFound;


// ─────────────────────────────────────────────────────────────────────────────
// Voter Profile
// ─────────────────────────────────────────────────────────────────────────────

export type RegistrationType = 'new' | 'relocation' | 'correction' | 'nri';

export interface VoterProfile {
  // Identity
  name?: string;
  epic_number?: string;
  preferred_language?: string;

  // Location
  current_state?: string;
  current_pincode?: string;
  previous_state?: string;
  previous_constituency?: string;

  // Registration
  registration_type?: RegistrationType;
  checklist?: Record<string, boolean>;

  // Dates (ISO strings set by backend / Firestore)
  registered_at?: string;
  last_updated?: string;
}


// ─────────────────────────────────────────────────────────────────────────────
// RAG / Chat types
// ─────────────────────────────────────────────────────────────────────────────

export interface RetrievedChunk {
  chunk_id: string;
  text: string;
  confidence: number;
  source_url: string;
  form_type: string;
  section: string;
}

/**
 * AgentTraceEntry — per-node shapes differ; use Record<string, unknown> extras
 * instead of declaring node-specific fields as required/optional on the union.
 *
 * Safe access pattern:
 *   const scores = entry.confidence_scores as number[] | undefined;
 *   const conf   = entry.confidence as number | undefined;
 */
export interface AgentTraceEntry {
  node: string;
  timestamp: string;
  status?: string;
  error?: string;
  // rag_retrieval fields
  retrieved_chunks?: string[];
  confidence_scores?: number[];
  method?: string;
  // synthesis fields
  input_tokens?: number;
  // guardrail fields
  confidence?: number;
  pattern?: string;
  // intent fields
  decision?: string;
  latency_ms?: number;
  // Allow arbitrary node-specific fields without casting everywhere
  [key: string]: unknown;
}

export interface Message {
  id: string;
  role: 'user' | 'bot';
  text: string;
  timestamp: Date;
  isStreaming?: boolean;
  confidence?: number;
  sourceChunks?: RetrievedChunk[];
  agentTrace?: AgentTraceEntry[];
}


// ─────────────────────────────────────────────────────────────────────────────
// ERO / Location types
// ─────────────────────────────────────────────────────────────────────────────

export interface EROOffice {
  name: string;
  address: string;
  phone: string;
  email: string;
  /**
   * FIX (P3): verified as number (float km) from ero_locator.py.
   * If Mapbox ever changes its format, add a typeof guard in the component:
   *   const km = typeof office.distance_km === 'number' ? office.distance_km : parseFloat(String(office.distance_km));
   */
  distance_km: number;
  directions_url: string;
  latitude: number;
  longitude: number;
}


// ─────────────────────────────────────────────────────────────────────────────
// Registration / Document types
// ─────────────────────────────────────────────────────────────────────────────

export interface RegistrationDeadline {
  form_type: string;
  deadline: string;
  description: string;
  phase: number;
}

export interface DocumentRequirement {
  id: string;
  name: string;
  description: string;
  required_for: RegistrationType[];
  alternatives: string[];
}