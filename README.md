Here is the complete, integrated README file in a single block so you can copy and paste it straight into your repository.

```markdown
# 🇮🇳 MatdaanMitra (मतदान मित्र) 
**Your intelligent, conversational, and localized guide to navigating the Indian election process.**

[![Frontend](https://img.shields.io/badge/Frontend-Next.js_14-black?logo=next.js)](https://nextjs.org/)
[![Backend](https://img.shields.io/badge/Backend-FastAPI-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![AI](https://img.shields.io/badge/AI-Gemini_1.5_Pro-blue?logo=google)](https://cloud.google.com/vertex-ai)
[![Maps](https://img.shields.io/badge/Maps-MapBox-4285F4?logo=mapbox)](https://www.mapbox.com/)
[![Language](https://img.shields.io/badge/Language-Sarvam_AI-FF9900)](https://www.sarvam.ai/)

## 📖 Overview
**MatdaanMitra** is an AI-powered voter assistance platform built to democratize access to the Indian electoral system. Designed for the diverse linguistic and geographic landscape of India, it provides personalized guidance, real-time status verification, localized voice assistance, and interactive maps to help citizens navigate the voter registration and election process seamlessly.

## ✨ Key Features
* **🗣️ Hyper-Localized Voice & Text:** Powered exclusively by **Sarvam AI**, offering seamless translation and voice-agent capabilities in multiple Indian regional languages (Hindi, Marathi, Tamil, Telugu, Bengali, Kannada, etc.).
* **📍 Interactive Polling Booth Mapping:** Integrated with **MapBox** for precise geospatial rendering, helping voters discover their real Electoral Registration Officer (ERO) offices and polling stations.
* **✅ Live Voter Verification:** Real-time lookup capabilities via the ECI electoral search API.
* **📅 Constituency-Aware Deadlines:** Dynamic, phase-based election schedules tailored to a voter's specific geographic location.
* **📄 Document Gap Analysis:** Intelligently identifies missing required documents and suggests valid alternatives based on ECI guidelines.
* **⚖️ Grievance Filing Assistant:** Automatically generates pre-filled complaint letters for missing registrations.

## 🛠️ Tech Stack
* **Frontend:** Next.js 14, TypeScript, Tailwind CSS, Firebase
* **Backend:** FastAPI, Python 3.12, LangGraph
* **AI & Intelligence:** Gemini 1.5 Pro (via Vertex AI), Vertex AI Vector Search
* **Geospatial:** MapBox GL
* **Language & Voice:** Sarvam AI
* **Database & Caching:** Firestore, Redis (Memorystore)
* **Deployment:** Firebase Hosting (CDN edge), Cloud Run

---

## 🚀 Getting Started

### Prerequisites
* Node.js 18+
* Python 3.11 / 3.12
* Google Cloud Project (Vertex AI enabled)
* Firebase Project
* MapBox Account & Token
* Sarvam AI API Key

### Installation

**1. Clone the repository & setup backend**
```bash
git clone [https://github.com/your-username/matdaan-mitra.git](https://github.com/your-username/matdaan-mitra.git)
cd matdaan-mitra/backend

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows use: .\.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

```

**2. Setup frontend**

```bash
cd ../frontend
npm install

```

### Configuration

Create `.env` files in both the `backend` and `frontend` directories using the templates below.

**Backend (`backend/.env`)**:

```env
# GCP Settings
GCP_PROJECT_ID=your-project-id
GCP_LOCATION=asia-south1
GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account.json

# Vertex AI Settings
VERTEX_AI_INDEX_ID=your-vector-search-index-id
VERTEX_AI_INDEX_ENDPOINT_ID=your-endpoint-id

# Core Integrations
SARVAM_API_KEY=your-sarvam-ai-key
MAPBOX_ACCESS_TOKEN=pk.your-mapbox-access-token

# Infrastructure
FIREBASE_PROJECT_ID=your-firebase-project
FIREBASE_SERVICE_ACCOUNT_PATH=path/to/firebase-admin.json
REDIS_URL=redis://localhost:6379
GCS_BUCKET_NAME=matdaan-eci-corpus

# Security & App Config
FERNET_KEY=generate-with-cryptography-library
FRONTEND_URL=http://localhost:3000
ENVIRONMENT=development
LOG_LEVEL=INFO

```

**Frontend (`frontend/.env.local`)**:

```env
NEXT_PUBLIC_FIREBASE_API_KEY=your-api-key
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
NEXT_PUBLIC_FIREBASE_PROJECT_ID=your-project-id
NEXT_PUBLIC_FIREBASE_APP_ID=your-app-id
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
NEXT_PUBLIC_MAPBOX_ACCESS_TOKEN=pk.your-mapbox-access-token

```

### Running the Application

**Terminal 1 (Backend):**

```bash
cd backend
source .venv/bin/activate
uvicorn src.api.main:app --reload

```

**Terminal 2 (Frontend):**

```bash
cd frontend
npm run dev

```

---

## 🏗️ Architecture Flow

```text
┌─────────────────────────────────────────────────────────────────┐
│  FRONTEND (Next.js 14 + App Router)                             │
│  Map UI: MapBox GL                                              │
│  Auth: Firebase Auth (Anonymous + Google)                       │
└───────────────────┬─────────────────────────────────────────────┘
                    │ HTTPS / Server-Sent Events
┌───────────────────▼─────────────────────────────────────────────┐
│  BACKEND (FastAPI — Python)                                     │
│  Deployed on: Cloud Run                                         │
│  Rate limiting: Redis (Memorystore)                             │
└──────┬────────────┬─────────────────┬───────────────────────────┘
       │            │                 │
┌──────▼──┐  ┌──────▼──────┐  ┌──────▼──────────┐
│LangGraph│  │ Vertex AI   │  │ External APIs   │
│ Agents  │  │ Gemini 1.5  │  │ - Sarvam AI     │
│(Python) │  │ Pro via API │  │ - MapBox APIs   │
└──────┬──┘  └─────────────┘  └─────────────────┘
       │
┌──────▼──────────────────────────────────────────┐
│ KNOWLEDGE BASE (Vertex AI Vector Search)        │
│ 10,000+ ECI document chunks, embedded with      │
│ text-embedding-004 model                        │
└─────────────────────────────────────────────────┘

```

## 🔐 Security & Data Residency

* **Encryption:** EPIC numbers are encrypted using Fernet before storage.
* **Authentication:** Firebase ID token verification is required on all core requests.
* **Rate Limiting:** Capped at 30 requests/minute per user via Redis to prevent abuse.
* **AI Guardrails:** Political content filtering is enforced via a dedicated LangGraph guardrail node. Confidence thresholds below 0.75 automatically trigger an escalation to the official 1950 helpline.
* **Data Residency:** All GCP resources are localized in `asia-south1` (Mumbai) to comply with Indian data residency standards.

## 📚 Official Resources & Citations

*This project is built for educational/hackathon purposes and utilizes official ECI data guidelines.*

* **Election Commission of India:** [eci.gov.in](https://eci.gov.in)
* **National Voter Service Portal:** [nvsp.in](https://nvsp.in)
* **Voter Helpline:** 1950

```

```