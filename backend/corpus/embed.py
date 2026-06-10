"""
embed.py — ECI Corpus Embedding Pipeline

Reads chunks produced by ingest.py, creates embeddings via
Vertex AI text-embedding-004, saves to GCS for Vector Search indexing,
and writes embedding metadata back to Firestore.

Run from backend/ directory AFTER ingest.py:
    python -m corpus.embed

Prerequisites:
  1. corpus/data/chunks.jsonl must exist (run ingest.py first)
  2. GCP_PROJECT_ID, GCP_LOCATION, GCS_BUCKET_NAME set in backend/.env
  3. GOOGLE_APPLICATION_CREDENTIALS or ADC configured

After this script completes:
  - Firestore corpus_chunks documents will have an `embedding_created` flag
  - GCS bucket will have corpus/embeddings.jsonl (format for Vertex AI Vector Search)
  - Follow the manual steps printed at the end to create the Vertex AI index
"""

import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

# ── Bootstrap path ────────────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
)
logger = logging.getLogger(__name__)

# ── Config from env ───────────────────────────────────────────────────────────
PROJECT_ID   = os.getenv("GCP_PROJECT_ID", "")
LOCATION     = os.getenv("GCP_LOCATION", "asia-south1")
BUCKET_NAME  = os.getenv("GCS_BUCKET_NAME", "matdaan-eci-corpus")
EMBED_MODEL  = "text-embedding-004"
BATCH_SIZE   = 5   # Vertex AI embedding API: max 5 texts per request
GCS_JSONL    = "corpus/embeddings.jsonl"
CHUNKS_JSONL = Path(__file__).parent / "data" / "chunks.jsonl"


# ── Vertex AI embedding ───────────────────────────────────────────────────────

def _init_vertexai():
    import vertexai
    vertexai.init(project=PROJECT_ID, location=LOCATION)


def _embed_batch(texts: list[str]) -> list[list[float]]:
    """
    Embed a batch of texts using Vertex AI text-embedding-004.
    Returns list of float vectors (768 dimensions).
    """
    from vertexai.language_models import TextEmbeddingModel
    model = TextEmbeddingModel.from_pretrained(EMBED_MODEL)
    results = model.get_embeddings(texts)
    return [r.values for r in results]


# ── GCS upload ────────────────────────────────────────────────────────────────

def _upload_to_gcs(local_path: str, gcs_path: str) -> str:
    """Upload a local file to GCS. Returns the gs:// URI."""
    from google.cloud import storage
    client = storage.Client(project=PROJECT_ID)
    bucket = client.bucket(BUCKET_NAME)
    blob = bucket.blob(gcs_path)
    blob.upload_from_filename(local_path, content_type="application/jsonl")
    uri = f"gs://{BUCKET_NAME}/{gcs_path}"
    logger.info("Uploaded to %s", uri)
    return uri


# ── Firestore updater ─────────────────────────────────────────────────────────

def _mark_embedded_in_firestore(chunk_ids: list[str]) -> None:
    """Mark chunks as embedded in Firestore so we can skip them on re-runs."""
    import firebase_admin
    from firebase_admin import credentials, firestore as admin_fs

    sa_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH", "firebase-admin.json")
    if not firebase_admin._apps:
        cred = credentials.Certificate(sa_path)
        firebase_admin.initialize_app(cred)

    db = admin_fs.client()
    batch = db.batch()
    for i, cid in enumerate(chunk_ids):
        ref = db.collection("corpus_chunks").document(cid)
        batch.update(ref, {"embedding_created": True, "embedded_at": datetime.now(timezone.utc).isoformat()})
        if (i + 1) % 499 == 0:
            batch.commit()
            batch = db.batch()
    batch.commit()
    logger.info("Marked %d chunks as embedded in Firestore", len(chunk_ids))


# ── Main embedding pipeline ───────────────────────────────────────────────────

class EmbeddingPipeline:

    def __init__(self):
        if not PROJECT_ID:
            raise RuntimeError(
                "GCP_PROJECT_ID is not set in backend/.env. "
                "Cannot run embedding pipeline without Vertex AI access."
            )
        _init_vertexai()
        logger.info("Vertex AI initialised — project=%s location=%s", PROJECT_ID, LOCATION)

    def run(self) -> str:
        """
        Full pipeline:
          1. Load chunks from JSONL
          2. Embed in batches
          3. Save Vertex AI-compatible JSONL to GCS
          4. Mark chunks as embedded in Firestore
          5. Print manual steps to create the Vertex AI index

        Returns the GCS URI of the embeddings JSONL.
        """
        # 1. Load chunks
        if not CHUNKS_JSONL.exists():
            raise FileNotFoundError(
                f"{CHUNKS_JSONL} not found. Run `python -m corpus.ingest` first."
            )

        chunks: list[dict[str, Any]] = []
        with open(CHUNKS_JSONL, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    chunks.append(json.loads(line))

        logger.info("Loaded %d chunks from %s", len(chunks), CHUNKS_JSONL)

        # 2. Embed in batches
        output_path = Path(__file__).parent / "data" / "embeddings.jsonl"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        embedded_ids: list[str] = []
        total = len(chunks)

        with open(output_path, "w", encoding="utf-8") as out_f:
            for batch_start in range(0, total, BATCH_SIZE):
                batch = chunks[batch_start : batch_start + BATCH_SIZE]
                texts = [c["text"] for c in batch]

                try:
                    vectors = _embed_batch(texts)
                except Exception as exc:
                    logger.error(
                        "Embedding batch %d–%d failed: %s — skipping",
                        batch_start, batch_start + len(batch) - 1, exc,
                    )
                    time.sleep(2)
                    continue

                for chunk, vector in zip(batch, vectors):
                    # Vertex AI Vector Search JSONL format:
                    # {"id": "<chunk_id>", "embedding": [0.1, 0.2, ...]}
                    record = {
                        "id":        chunk["chunk_id"],
                        "embedding": vector,
                    }
                    out_f.write(json.dumps(record) + "\n")
                    embedded_ids.append(chunk["chunk_id"])

                logger.info(
                    "Embedded %d/%d chunks…",
                    min(batch_start + BATCH_SIZE, total), total,
                )
                time.sleep(0.5)  # respect Vertex AI rate limits

        logger.info("Wrote %d embedding records to %s", len(embedded_ids), output_path)

        # 3. Upload to GCS
        gcs_uri = _upload_to_gcs(str(output_path), GCS_JSONL)

        # 4. Mark as embedded in Firestore
        try:
            _mark_embedded_in_firestore(embedded_ids)
        except Exception as exc:
            logger.warning("Firestore update failed (non-fatal): %s", exc)

        # 5. Print manual Vertex AI index creation steps
        self._print_next_steps(gcs_uri)

        return gcs_uri

    def _print_next_steps(self, gcs_uri: str) -> None:
        logger.info("\n" + "=" * 70)
        logger.info("EMBEDDING COMPLETE — Manual steps to create Vertex AI index:")
        logger.info("=" * 70)
        logger.info("")
        logger.info("Option A — GCP Console (recommended for first-time setup):")
        logger.info("  1. Go to: https://console.cloud.google.com/vertex-ai/matching-engine")
        logger.info("  2. Click 'Create Index'")
        logger.info("  3. Display name:    matdaan-eci-corpus")
        logger.info("  4. Description:     ECI voter registration document corpus")
        logger.info("  5. Input URI:       %s", gcs_uri)
        logger.info("  6. Dimensions:      768")
        logger.info("  7. Approximate NN:  Enable")
        logger.info("  8. Distance:        COSINE")
        logger.info("  9. Click Create (takes 10–20 min)")
        logger.info(" 10. After creation, click 'Deploy to Endpoint'")
        logger.info(" 11. Create a new endpoint: matdaan-eci-endpoint")
        logger.info(" 12. Note the INDEX_ID and ENDPOINT_ID")
        logger.info(" 13. Update backend/.env:")
        logger.info("       VERTEX_AI_INDEX_ID=<your-index-id>")
        logger.info("       VERTEX_AI_INDEX_ENDPOINT_ID=<your-endpoint-id>")
        logger.info("")
        logger.info("Option B — gcloud CLI:")
        logger.info(
            "  gcloud ai indexes create \\\n"
            "    --display-name=matdaan-eci-corpus \\\n"
            "    --metadata-file=- <<EOF\n"
            "  {\"contentsDeltaUri\": \"%s\", \"config\": {\"dimensions\": 768, "
            "\"approximateNeighborsCount\": 10, \"distanceMeasureType\": \"COSINE_DISTANCE\", "
            "\"algorithmConfig\": {\"treeAhConfig\": {}}}}\n  EOF",
            gcs_uri,
        )
        logger.info("=" * 70)


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    pipeline = EmbeddingPipeline()
    pipeline.run()