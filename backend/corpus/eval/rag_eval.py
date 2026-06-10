"""
rag_eval.py — RAG Retrieval Quality Evaluation

Measures how well the Vertex AI vector search retrieves the correct
ECI document chunks for a set of representative voter queries.

Metrics:
  Recall@3 — fraction of queries where the correct chunk is in top-3 results
  MRR      — Mean Reciprocal Rank (rewards finding the right chunk higher up)

Run from backend/ directory:
    python -m corpus.eval.rag_eval

Requires:
  - corpus/data/chunks.jsonl (run ingest.py first)
  - Vertex AI index deployed (or will run against static fallback)
  - GCP credentials configured
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
os.chdir(Path(__file__).resolve().parent.parent.parent)

from dotenv import load_dotenv
load_dotenv(".env")

logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


# ── Eval dataset ──────────────────────────────────────────────────────────────
# Each entry: (query, [expected_chunk_ids_in_priority_order])
# Chunk IDs match the output of corpus/ingest.py's _make_chunk_id() function.

EVAL_SET: list[tuple[str, list[str]]] = [
    # Form 6 — eligibility & documents
    (
        "What is the age requirement to register as a voter?",
        ["form6_eligibility_000"],
    ),
    (
        "What documents do I need to submit with Form 6?",
        ["form6_required_documents_001", "form6_eligibility_000"],
    ),
    (
        "How do I submit my voter registration application online?",
        ["form6_submission_process_002"],
    ),
    (
        "What is the last date to register for elections?",
        ["form6_deadlines_003", "eci_guidelines_qualifying_date_003"],
    ),
    # Form 6A — NRI
    (
        "I am an NRI living in the UK. Can I register to vote in India?",
        ["form6a_nri_eligibility_000"],
    ),
    (
        "What documents does an overseas Indian citizen need for voter registration?",
        ["form6a_required_documents_001", "form6a_nri_eligibility_000"],
    ),
    # Form 7 — deletion
    (
        "How do I remove a deceased person's name from the electoral roll?",
        ["form7_when_to_use_form_7_000", "form7_deletion_process_001"],
    ),
    (
        "My name appears twice in the voter list. How do I fix this?",
        ["form7_when_to_use_form_7_000", "eci_guidelines_dual_enrollment_005"],
    ),
    # Form 8 — corrections
    (
        "My name is spelled wrong on my voter card. How do I correct it?",
        ["form8_corrections_covered_000"],
    ),
    (
        "What documents do I need to correct my date of birth on the voter roll?",
        ["form8_required_documents_001"],
    ),
    # Form 8A — address change
    (
        "I moved to a new apartment in the same area. Do I need to re-register?",
        ["form8a_transposition_within_constituency_000"],
    ),
    (
        "What is the difference between Form 8 and Form 8A?",
        ["form8a_transposition_within_constituency_000", "form8_corrections_covered_000"],
    ),
    # General ECI guidelines
    (
        "The BLO came to my house. What should I keep ready?",
        ["eci_guidelines_blo_verification_000"],
    ),
    (
        "How do I download my voter ID card online?",
        ["eci_guidelines_epic_card_delivery_001"],
    ),
    (
        "My name is missing from the voter list. How do I file a complaint?",
        ["eci_guidelines_grievance_filing_002"],
    ),
    (
        "What is the qualifying date for voter registration?",
        ["eci_guidelines_qualifying_date_003"],
    ),
    (
        "What are the steps to register online on the NVSP portal?",
        ["eci_guidelines_online_registration_steps_004"],
    ),
    (
        "Is it legal to be registered as a voter in two places?",
        ["eci_guidelines_dual_enrollment_005", "form7_when_to_use_form_7_000"],
    ),
]


# ── Retrieval runner ──────────────────────────────────────────────────────────

async def _retrieve(query: str, top_k: int = 3) -> list[str]:
    """
    Embed the query and retrieve top_k chunk IDs.
    Falls back to keyword matching against the static corpus if
    Vertex AI is not configured.
    """
    from src.config.settings import settings

    # ── Vertex AI path ────────────────────────────────────────────────────────
    if settings.gcp_project_id and settings.vertex_ai_index_endpoint_id:
        try:
            from langchain_google_vertexai import VertexAIEmbeddings
            from src.services.vector_search import vector_search_service

            embeddings = VertexAIEmbeddings(
                model_name="text-embedding-004",
                project=settings.gcp_project_id,
                location=settings.gcp_location,
            )
            vector = await embeddings.aembed_query(query)
            results = await vector_search_service.search(vector, top_k=top_k)
            if results:
                return [r["chunk_id"] for r in results]
        except Exception as exc:
            logger.warning("Vertex AI retrieval failed: %s — using fallback", exc)

    # ── Static fallback: keyword overlap against chunks.jsonl ─────────────────
    chunks_path = Path("corpus/data/chunks.jsonl")
    if not chunks_path.exists():
        logger.warning("chunks.jsonl not found — run corpus/ingest.py first")
        return []

    query_words = set(query.lower().split())
    scored: list[tuple[float, str]] = []

    with open(chunks_path, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            chunk = json.loads(line)
            chunk_words = set(chunk.get("text", "").lower().split())
            overlap = len(query_words & chunk_words) / max(len(query_words), 1)
            scored.append((overlap, chunk["chunk_id"]))

    scored.sort(reverse=True)
    return [cid for _, cid in scored[:top_k]]


# ── Metrics ───────────────────────────────────────────────────────────────────

def _recall_at_k(retrieved: list[str], relevant: list[str], k: int = 3) -> float:
    return 1.0 if any(cid in retrieved[:k] for cid in relevant) else 0.0


def _reciprocal_rank(retrieved: list[str], relevant: list[str]) -> float:
    for rank, cid in enumerate(retrieved, start=1):
        if cid in relevant:
            return 1.0 / rank
    return 0.0


# ── Evaluation runner ─────────────────────────────────────────────────────────

async def run_evaluation(top_k: int = 3) -> dict:
    print(f"\n{'='*60}")
    print("  MatdaanMitra — RAG Retrieval Evaluation")
    print(f"  {len(EVAL_SET)} queries · Recall@{top_k} + MRR")
    print(f"{'='*60}\n")

    recall_scores: list[float] = []
    mrr_scores:    list[float] = []
    failures:      list[dict]  = []

    for i, (query, expected_ids) in enumerate(EVAL_SET, start=1):
        retrieved = await _retrieve(query, top_k=top_k)

        r_at_k = _recall_at_k(retrieved, expected_ids, k=top_k)
        rr     = _reciprocal_rank(retrieved, expected_ids)

        recall_scores.append(r_at_k)
        mrr_scores.append(rr)

        icon = "✅" if r_at_k == 1.0 else "❌"
        print(f"  {icon} [{i:02d}] {query[:60]}")
        if r_at_k < 1.0:
            failures.append({
                "query":     query,
                "expected":  expected_ids,
                "retrieved": retrieved,
            })
            print(f"       Expected : {expected_ids[0]}")
            print(f"       Retrieved: {retrieved[:3]}")
        print()

    recall_at_k = sum(recall_scores) / len(recall_scores)
    mrr         = sum(mrr_scores)    / len(mrr_scores)

    print(f"{'='*60}")
    print(f"  Recall@{top_k} : {recall_at_k:.3f}  ({recall_at_k*100:.1f}%)")
    print(f"  MRR       : {mrr:.3f}")
    print(f"  Failures  : {len(failures)}/{len(EVAL_SET)}")
    print(f"{'='*60}\n")

    if recall_at_k < 0.7:
        print("  ⚠️  Recall below 70% — consider:")
        print("     1. Re-running corpus/embed.py to refresh embeddings")
        print("     2. Adding more curated sections to corpus/ingest.py")
        print("     3. Expanding the static ECI fallback corpus in rag_retrieval.py\n")

    return {
        "recall_at_k": recall_at_k,
        "mrr":         mrr,
        "n_queries":   len(EVAL_SET),
        "n_failures":  len(failures),
        "failures":    failures,
    }


if __name__ == "__main__":
    asyncio.run(run_evaluation(top_k=3))