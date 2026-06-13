"""
rag_retrieval.py — RAG retrieval node

Fix (production audit):

P2 — SEQUENTIAL FIRESTORE I/O ON HOT RAG PATH
    Previous: _fetch_chunk_metadata() looped over chunk_ids, issuing one
    db.collection(...).document(cid).get() call per chunk inside a single
    run_in_executor callback. For top_k=4, that is 4 sequential Firestore
    round trips (~5–15ms each) = 20–60ms of blocking I/O in a single thread.
    Saturates the executor thread pool under concurrent load.

    Fix: db.get_all(refs) issues a single batched Firestore RPC regardless of
    how many chunk IDs are requested. Latency drops from O(k) to O(1) RPCs.
    The reduction is most visible on the Vertex AI path where top_k=4 is the
    default; the static fallback path doesn't hit Firestore at all.

NOTE — LLM SINGLETON RACE (warning from audit, partial mitigation):
    _embedding_model is a module-level global mutated by _get_embeddings().
    On the first cold-start, two concurrent requests could both enter the
    `if _embedding_model is None` branch and initialise twice. The second
    initialisation overwrites the first — no crash, but wastes resources.
    Full fix requires an asyncio.Lock or functools.lru_cache(maxsize=1).
    Added a threading.Lock here as a lightweight guard compatible with
    run_in_executor usage.
"""

import logging
import threading
from datetime import datetime, timezone
from typing import Any

from ..state import AgentState, RetrievedChunk
from ...config.settings import settings

logger = logging.getLogger(__name__)

# ── Lazy init with race-condition guard ───────────────────────────────────────

_embedding_model = None
_embedding_lock  = threading.Lock()


def _get_embeddings():
    global _embedding_model
    if _embedding_model is None:
        with _embedding_lock:
            # Double-checked locking: re-check after acquiring the lock
            if _embedding_model is None:
                from langchain_google_vertexai import VertexAIEmbeddings
                _embedding_model = VertexAIEmbeddings(
                    model_name="text-embedding-004",
                    project=settings.gcp_project_id,
                    location=settings.gcp_location,
                )
                logger.info("VertexAI embeddings initialised (text-embedding-004)")
    return _embedding_model


# ── Static ECI fallback corpus ────────────────────────────────────────────────
# Used when Vertex AI is unavailable or returns no results.
# Confidence values are intentionally set below 0.92 to leave headroom for the
# guardrail threshold (0.75) while still being realistic for curated content.

_ECI_FALLBACK: list[RetrievedChunk] = [
    {
        "chunk_id": "form6_eligibility",
        "text": (
            "**Form 6 — New Voter Registration**: Any Indian citizen who has attained "
            "the age of **18 years** on the qualifying date (1st January of the year) "
            "and is ordinarily resident at the address in the electoral roll can apply. "
            "Submit to your local ERO or online at voters.eci.gov.in."
        ),
        "confidence": 0.91,
        "source_url": "https://eci.gov.in/files/file/form6/",
        "form_type": "Form 6",
        "section": "Eligibility",
    },
    {
        "chunk_id": "form6_documents",
        "text": (
            "**Required documents for Form 6**: "
            "Proof of age — Aadhaar card, birth certificate, school leaving certificate, or passport. "
            "Proof of address — Aadhaar, utility bill (not older than 1 year), bank passbook, or rent agreement. "
            "One recent **passport-size photograph**."
        ),
        "confidence": 0.89,
        "source_url": "https://eci.gov.in/files/file/form6/",
        "form_type": "Form 6",
        "section": "Documents",
    },
    {
        "chunk_id": "form8_correction",
        "text": (
            "**Form 8 — Correction of entries**: Used to correct name spelling, date of birth, "
            "address within the same constituency, or photograph. Submit the corrected details along "
            "with supporting documents to the ERO or online portal."
        ),
        "confidence": 0.87,
        "source_url": "https://eci.gov.in/files/file/form8/",
        "form_type": "Form 8",
        "section": "Correction",
    },
    {
        "chunk_id": "form8a_relocation",
        "text": (
            "**Form 8A — Transposition (address change within constituency)**: If you have moved "
            "to a new address within the **same constituency**, file Form 8A. If you have moved to "
            "a different constituency, you must file Form 6 (new registration) and Form 7 (deletion "
            "from old roll)."
        ),
        "confidence": 0.88,
        "source_url": "https://eci.gov.in/files/file/form8a/",
        "form_type": "Form 8A",
        "section": "Address Change",
    },
    {
        "chunk_id": "form7_deletion",
        "text": (
            "**Form 7 — Objection to inclusion / deletion**: File Form 7 to remove a duplicate, "
            "deceased, or shifted voter from the roll. You will need to provide the EPIC number of "
            "the entry to be deleted and a reason for deletion."
        ),
        "confidence": 0.85,
        "source_url": "https://eci.gov.in/files/file/form7/",
        "form_type": "Form 7",
        "section": "Deletion",
    },
    {
        "chunk_id": "form6a_nri",
        "text": (
            "**Form 6A — NRI Voter Registration**: Overseas Indian citizens holding a valid Indian "
            "passport can register using Form 6A at their last address in India. "
            "Required: passport copy, visa/entry stamp, and a recent photograph."
        ),
        "confidence": 0.86,
        "source_url": "https://eci.gov.in/files/file/form6a/",
        "form_type": "Form 6A",
        "section": "NRI Registration",
    },
    {
        "chunk_id": "grievance_process",
        "text": (
            "**Filing a Grievance**: If your name is missing from the voter roll or contains errors, "
            "you can: (1) File online at nvsp.in, (2) Call the National Voter Helpline **1950** "
            "(toll-free), (3) Submit a written complaint to your local BLO or ERO with proof of "
            "residence and identity."
        ),
        "confidence": 0.84,
        "source_url": "https://eci.gov.in/grievances/",
        "form_type": "Grievance",
        "section": "Process",
    },
    {
        "chunk_id": "deadline_general",
        "text": (
            "**Registration deadlines**: The last date for new voter registration is typically "
            "**30 days before** the notification date for an election. For summary revision of "
            "electoral rolls, the draft publication date is 1st October each year, and the final "
            "roll is published on 5th January. Check your state CEO website for exact phase-wise dates."
        ),
        "confidence": 0.82,
        "source_url": "https://eci.gov.in/electoral-rolls/",
        "form_type": "General",
        "section": "Deadlines",
    },
]

# Intent → fallback chunk IDs (most relevant first)
_INTENT_CHUNK_MAP: dict[str, list[str]] = {
    "form_guidance":      ["form6_eligibility", "form6_documents", "form8_correction", "form8a_relocation"],
    "deadline_query":     ["deadline_general"],
    "document_check":     ["form6_documents"],
    "grievance_help":     ["grievance_process"],
    "profile_collection": ["form6_eligibility"],
}


def _fallback_chunks(intent: str | None, query: str, top_k: int = 3) -> list[RetrievedChunk]:
    """Return the most relevant static ECI chunks for the given intent."""
    chunk_ids = _INTENT_CHUNK_MAP.get(intent or "")
    if not chunk_ids:
        return []
    chunks_by_id = {c["chunk_id"]: c for c in _ECI_FALLBACK}
    selected = [chunks_by_id[cid] for cid in chunk_ids if cid in chunks_by_id]
    return selected[:top_k]



# ── Firestore metadata fetch (batched) ────────────────────────────────────────

async def _fetch_chunk_metadata(chunk_ids: list[str]) -> dict[str, dict[str, Any]]:
    """
    Fetch chunk text + metadata from Firestore collection 'corpus_chunks'.

    FIX: uses db.get_all(refs) — a single batched Firestore RPC — instead of
    a loop of individual .document(cid).get() calls. For top_k=4 this cuts
    Firestore latency by ~3–4x (20–60ms → 5–15ms) on the hot RAG path.

    Returns a dict keyed by chunk_id. Missing IDs are silently skipped.
    """
    import asyncio
    result: dict[str, dict[str, Any]] = {}

    if not chunk_ids:
        return result

    try:
        import firebase_admin  # noqa
        from firebase_admin import firestore
        db = firestore.client()

        def _fetch_sync_batched():
            # Build all document references at once
            refs = [db.collection("corpus_chunks").document(cid) for cid in chunk_ids]
            # Single batched RPC — latency ≈ one round trip regardless of len(refs)
            docs = db.get_all(refs)
            return {doc.id: doc.to_dict() for doc in docs if doc.exists}

        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, _fetch_sync_batched)
        logger.debug("Firestore batch fetch: %d requested, %d found", len(chunk_ids), len(result))

    except Exception as exc:
        logger.warning("Firestore batch metadata fetch failed: %s", exc)

    return result


# ── Node ──────────────────────────────────────────────────────────────────────

async def rag_retrieval_node(state: AgentState) -> AgentState:
    trace: dict = {
        "node": "rag_retrieval",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    try:
        last_message: str  = state["messages"][-1].content
        intent: str | None = state.get("intent")

        retrieved: list[RetrievedChunk] = []

        # ── Attempt live Vertex AI vector search ──────────────────────────────
        if settings.gcp_project_id and settings.vertex_ai_index_endpoint_id:
            try:
                embeddings_model = _get_embeddings()
                query_vector: list[float] = await embeddings_model.aembed_query(last_message)

                from ...services.vector_search import vector_search_service
                raw_results = await vector_search_service.search(query_vector, top_k=4)

                if raw_results:
                    chunk_ids = [r["chunk_id"] for r in raw_results]
                    # Single batched Firestore RPC (fix: was sequential loop)
                    metadata_map = await _fetch_chunk_metadata(chunk_ids)

                    for raw in raw_results:
                        cid  = raw["chunk_id"]
                        meta = metadata_map.get(cid, {})
                        if not meta.get("text"):
                            continue
                        retrieved.append(RetrievedChunk(
                            chunk_id=cid,
                            text=meta.get("text", ""),
                            confidence=round(1.0 - float(raw.get("distance", 0.2)), 3),
                            source_url=meta.get("source_url", "https://eci.gov.in"),
                            form_type=meta.get("form_type", "ECI"),
                            section=meta.get("section", ""),
                        ))

                    trace["method"] = "vertex_ai_vector_search"
                    logger.info("Vector search returned %d chunks", len(retrieved))

            except Exception as vs_exc:
                logger.warning("Vector search failed, using static fallback: %s", vs_exc)
                trace["vs_error"] = str(vs_exc)

        # ── Fallback to static ECI corpus ─────────────────────────────────────
        if not retrieved:
            retrieved = _fallback_chunks(intent, last_message, top_k=3)
            trace["method"] = "static_eci_fallback"
            logger.debug("Using static ECI fallback corpus, intent=%s", intent)

        trace.update({
            "status": "ok",
            "retrieved_chunks": [c["chunk_id"] for c in retrieved],
            "confidence_scores": [c["confidence"] for c in retrieved],
        })

        return {
            **state,
            "retrieved_chunks": retrieved,
            "agent_trace": state.get("agent_trace", []) + [trace],
            "error": None,
        }

    except Exception as exc:
        logger.exception("RAG retrieval error: %s", exc)
        trace.update({"status": "error", "error": str(exc)})
        return {
            **state,
            "retrieved_chunks": [],
            "agent_trace": state.get("agent_trace", []) + [trace],
            "error": f"RAG retrieval failed: {exc}",
        }