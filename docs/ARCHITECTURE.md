# Architecture Documentation

## System Overview

Matdaan Mitra is a full-stack AI application consisting of:

1. **Frontend**: Next.js 14 with App Router, deployed on Firebase Hosting
2. **Backend**: FastAPI (Python 3.12), deployed on Cloud Run
3. **AI Layer**: LangGraph multi-agent system with Gemini 1.5 Pro
4. **Data Layer**: Firestore, Vertex AI Vector Search, Redis

## Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│  FRONTEND (Next.js 14 + App Router)                             │
│  Deployed on: Firebase Hosting (CDN edge)                       │
│  Auth: Firebase Auth (anonymous sessions + Google Sign-In)      │
│  Real-time: Firestore onSnapshot for chat streaming             │
└───────────────────┬─────────────────────────────────────────────┘
                    │ HTTPS / Server-Sent Events
┌───────────────────▼─────────────────────────────────────────────┐
│  BACKEND (FastAPI — Python 3.12)                                │
│  Deployed on: Cloud Run (min-instances=1, max=50)               │
│  Auth middleware: Firebase ID token verification                │
│  Rate limiting: Redis (Memorystore) — 30 req/min per user       │
└──────┬────────────┬─────────────────┬───────────────────────────┘
       │            │                 │
┌──────▼──┐  ┌──────▼──────┐  ┌──────▼──────────┐
│LangGraph│  │ Vertex AI   │  │ Firestore       │
│ Agents  │  │ Gemini 1.5  │  │ (chat history + │
│(Python) │  │ Pro via API │  │  voter profiles)│
└──────┬──┘  └─────────────┘  └─────────────────┘
       │
┌──────▼──────────────────────────────────────────┐
│ KNOWLEDGE BASE (Vertex AI Vector Search)        │
│ 10,000+ ECI document chunks, embedded with      │
│ text-embedding-004 model                        │
└─────────────────────────────────────────────────┘
```

## LangGraph Agent Graph

```
                    ┌─────────────────┐
     user message → │  INTENT NODE    │
                    │  (Gemini Flash) │
                    └────────┬────────┘
                             │ routes to one of:
         ┌───────────────────┼──────────────────────┐
         ▼                   ▼                       ▼
┌─────────────┐   ┌──────────────────┐   ┌───────────────────┐
│ PROFILE     │   │ RAG RETRIEVAL    │   │ LIVE LOOKUP       │
│ BUILDER     │   │ NODE             │   │ NODE              │
│             │   │ (ECI vector DB)  │   │ (NVSP API call)   │
│ Collects:   │   │                  │   │                   │
│ • state     │   │ Retrieves top-5  │   │ Returns real      │
│ • status    │   │ chunks, scores   │   │ enrollment status │
│ • type      │   │ them, reranks    │   │ from ECI database │
└──────┬──────┘   └────────┬─────────┘   └─────────┬─────────┘
       │                   │                         │
       └──────────┬────────┘                         │
                  ▼                                   │
        ┌─────────────────┐                           │
        │ SYNTHESIS NODE  │←──────────────────────────┘
        │                 │
        │ Combines RAG    │
        │ chunks + live   │
        │ data + profile  │
        └────────┬────────┘
                 │
        ┌────────▼────────┐
        │ GUARDRAIL NODE  │
        │                 │
        │ Strips political│
        │ bias · Adds     │
        │ citations ·     │
        │ Checks conf.    │
        └────────┬────────┘
                 │
        ┌────────▼────────┐
        │ TRANSLATION     │
        │ NODE            │
        │ (if non-English)│
        └─────────────────┘
```

## Agent State Schema

```python
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    session_id: str
    voter_profile: VoterProfile
    intent: Literal[
        "profile_collection", "form_guidance", "deadline_query",
        "document_check", "voter_lookup", "ero_location",
        "grievance_help", "off_topic", "unknown"
    ] | None
    retrieved_chunks: list[RetrievedChunk]
    live_data: dict | None
    final_response: str | None
    response_language: str
    confidence_score: float
    agent_trace: list[dict]
    requires_escalation: bool
    error: str | None
```

## API Endpoints

### POST /api/chat
Main SSE streaming conversation endpoint.

**Request:**
```json
{
  "session_id": "session-123",
  "message": "How do I register to vote?",
  "language": "en"
}
```

**Response (SSE stream):**
```
data: {"type": "token", "content": "To "}

data: {"type": "token", "content": "register "}

data: {"type": "done", "confidence": 0.92, "source_chunks": [...]}

data: [DONE]
```

### GET /api/voter/{epic_number}
Real-time ECI voter status lookup.

### GET /api/ero/{pincode}
Nearest ERO office via Google Maps.

### PATCH /api/profile/{session_id}/checklist
Update document checklist state.

### GET /health
Real dependency health check.

## Data Flow

1. User sends message via frontend
2. Firebase Auth verifies token
3. Rate limiter checks request count
4. LangGraph processes message through nodes:
   - Intent classification
   - Profile building
   - RAG retrieval
   - Live data lookup
   - Synthesis
   - Guardrail check
   - Translation (if needed)
5. Response streamed via SSE
6. Chat history saved to Firestore

## Deployment Architecture

### Frontend (Firebase Hosting)
- CDN edge caching
- Automatic SSL
- Global distribution
- Zero cold starts

### Backend (Cloud Run)
- `--min-instances=2` (no cold starts)
- `--max-instances=100`
- `--concurrency=80`
- `--memory=2Gi`
- `--cpu=2`
- Region: `asia-south1` (Mumbai)

### Database (Firestore)
- Real-time sync
- Automatic scaling
- Offline support
- Security rules

### Cache (Redis Memorystore)
- Sliding window rate limiting
- Session state caching
- API response caching (1 hour TTL)
