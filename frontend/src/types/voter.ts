export type RegistrationType = "new" | "relocation" | "correction" | "nri";

export interface VoterProfile {
  name?: string;
  current_state?: string;
  current_pincode?: string;
  previous_state?: string;
  previous_constituency?: string;
  registration_type?: RegistrationType;
  epic_number?: string;
  preferred_language?: string;
  checklist?: Record<string, boolean>;
}

export interface RetrievedChunk {
  chunk_id: string;
  text: string;
  confidence: number;
  source_url: string;
  form_type: string;
  section: string;
}

export interface Message {
  id: string;
  role: "user" | "bot";
  text: string;
  timestamp: Date;
  isStreaming?: boolean;
  confidence?: number;
  sourceChunks?: RetrievedChunk[];
  agentTrace?: AgentTraceEntry[];
}

export interface AgentTraceEntry {
  node: string;
  timestamp: string;
  input_tokens?: number;
  retrieved_chunks?: string[];
  confidence_scores?: number[];
  decision?: string;
  latency_ms?: number;
  status?: string;
  error?: string;
}

export interface VoterStatus {
  epic_number: string;
  name: string;
  father_name: string;
  age: number;
  gender: string;
  address: string;
  polling_station: string;
  assembly_constituency: string;
  parliamentary_constituency: string;
  status: "active" | "inactive" | "pending";
}

export interface EROOffice {
  name: string;
  address: string;
  phone: string;
  email: string;
  distance_km: number;
  directions_url: string;
  latitude: number;
  longitude: number;
}

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
