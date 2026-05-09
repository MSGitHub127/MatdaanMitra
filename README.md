# Matdaan Mitra (मतदान मित्र)

Your intelligent, conversational guide to navigating the Indian election process.

## Overview

Matdaan Mitra is an AI-powered voter assistance system designed to help Indian citizens navigate the complex voter registration process. It provides personalized guidance, real-time status verification, and step-by-step assistance for all election-related procedures.

## Features

- **Live Voter Status Verification**: Real-time lookup via ECI electoral search API
- **Constituency-Aware Deadlines**: Phase-based election schedules specific to your constituency
- **Document Gap Analysis**: Identifies required documents and suggests alternatives
- **Grievance Filing Assistant**: Generates pre-filled complaint letters for missing registrations
- **Multi-Language Support**: Available in Hindi, Marathi, Tamil, Telugu, Bengali, Kannada, and more
- **Decision Transparency**: Full agent reasoning trace with source citations

## Tech Stack

- **Frontend**: Next.js 14, TypeScript, Tailwind CSS, Firebase
- **Backend**: FastAPI, Python 3.12, LangGraph
- **AI**: Gemini 1.5 Pro via Vertex AI
- **Data**: Vertex AI Vector Search, Firestore, Redis
- **Hosting**: Firebase Hosting, Cloud Run

## Getting Started

### Prerequisites

- Node.js 18+
- Python 3.12+
- Google Cloud Project with APIs enabled
- Firebase Project

### Installation

```bash
# Backend
cd backend
pip install -r requirements.txt

# Frontend
cd frontend
npm install
```

### Configuration

Create `.env` files with your API keys:

**Backend (.env)**:
```env
GCP_PROJECT_ID=your-project-id
GCP_LOCATION=asia-south1
GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account.json
VERTEX_AI_INDEX_ID=your-vector-search-index-id
VERTEX_AI_INDEX_ENDPOINT_ID=your-endpoint-id
MAPBOX_ACCESS_TOKEN\nMAPBOX_ACCESS_TOKEN=pk.your-mapbox-access-token=your-maps-key
GOOGLE_TRANSLATE_API_KEY
MAPBOX_ACCESS_TOKEN=pk.your-mapbox-access-token\nMAPBOX_ACCESS_TOKEN=pk.your-mapbox-access-token\nMAPBOX_ACCESS_TOKEN=pk.your-mapbox-access-token=your-translate-key
FIREBASE_PROJECT_ID=your-firebase-project
FIREBASE_SERVICE_ACCOUNT_PATH=path/to/firebase-admin.json
REDIS_URL=redis://localhost:6379
FERNET_KEY=generate-with-cryptography-library
FRONTEND_URL=http://localhost:3000
GCS_BUCKET_NAME=matdaan-eci-corpus
ENVIRONMENT=development
LOG_LEVEL=INFO
```

**Frontend (.env.local)**:
```env
NEXT_PUBLIC_FIREBASE_API_KEY=your-api-key
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
NEXT_PUBLIC_FIREBASE_PROJECT_ID=your-project-id
NEXT_PUBLIC_FIREBASE_APP_ID=your-app-id
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
NEXT_PUBLIC_MAPBOX_ACCESS_TOKEN=pk.your-mapbox-access-token
```

### Running the Application

```bash
# Backend
cd backend
uvicorn src.api.main:app --reload

# Frontend
cd frontend
npm run dev
```

## Architecture

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

## Google Services Used

| Service | Use Case |
|---------|----------|
| Vertex AI (Gemini 1.5 Pro) | LLM reasoning and synthesis with 1M token context |
| Vertex AI Vector Search | ECI document similarity search with India data residency |
| Firebase Auth | Anonymous sessions + Google Sign-In for frictionless onboarding |
| Firestore | Real-time chat sync and voter profile persistence |
| Firebase Hosting | CDN edge deployment for frontend |
| Mapbox GL | Real ERO office discovery and directions |
| Cloud Translation API v3 | 9 Indian languages with custom ECI glossary |
| Cloud Logging + Monitoring | Structured agent decision logs + alerts |

## Real Data Sources

| Source | Endpoint | Use |
|--------|----------|-----|
| ECI Electoral Search | `electoralsearch.eci.gov.in/api/search` | Live voter enrollment status |
| India Post Pincode | `api.postalpincode.in/pincode/{pin}` | Address/constituency validation |
| Mapbox Geocoding | Maps Platform API | ERO office discovery |
| Google Maps Places | Maps Platform API | Nearest electoral office |
| Cloud Translation v3 | `translate.googleapis.com` | 9 Indian languages |
| ECI PDF Downloads | `eci.gov.in/files/file/...` | Form text for RAG corpus |
| Vertex AI Vector Search | GCP SDK | ECI document similarity search |
| Gemini 1.5 Pro | Vertex AI SDK | LLM reasoning and synthesis |

## Security

- All API keys stored in environment variables
- EPIC numbers encrypted with Fernet before storage
- Firebase ID token verification on every request
- Rate limiting: 30 requests/minute per user
- Political content filtering via guardrail node
- Confidence threshold: 0.75 → escalation to 1950 helpline
- All GCP resources in `asia-south1` (Mumbai) for data residency

## License

This project is built for educational purposes and uses official ECI data sources.

## Official Resources

- Election Commission of India: https://eci.gov.in
- National Voter Service Portal: https://nvsp.in
- Voter Helpline: 1950
