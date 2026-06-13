"""
vector_search.py — Vertex AI Matching Engine wrapper  (performance revision)

Key improvements over original
--------------------------------
1. Dedicated ThreadPoolExecutor (max_workers=2)
   The original used asyncio's default executor (shared with every other
   run_in_executor call in the process).  Under concurrent load the sync
   Vertex AI SDK call saturated that pool, adding queuing latency.
   A dedicated 2-worker pool isolates vector search I/O.

2. Per-call timeout via asyncio.wait_for
   The SDK's find_neighbors() has no built-in timeout.  A stalled gRPC
   connection would block an executor thread indefinitely.  wrap each call
   in wait_for(timeout=SEARCH_TIMEOUT_S) so the caller always gets a result
   (or None) within a bounded window.

3. Structured error classification
   Distinguishes auth/permission errors, not-found errors, and transient
   network errors so callers and the check_apis script can give clearer
   triage messages.

4. Lazy-init race guard (threading.Lock)
   The original double-checked locking was present for the embedding model
   but absent here.  Added symmetrically.

5. Non-blocking close() for graceful shutdown
   main.py lifespan calls vector_search_service.close() — previously a no-op
   that leaked the executor thread.  Now shuts down the thread pool.
"""

from __future__ import annotations

import asyncio
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Optional

from ..config.settings import settings

logger = logging.getLogger(__name__)

# Dedicated pool: 2 workers keeps Vector Search I/O off the default executor
# while avoiding over-subscription on Cloud Run's 1-vCPU instances.
_EXECUTOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix="vx_search")

# Hard timeout per search call (seconds).  Vertex AI p99 latency is ~300ms;
# 6 s gives generous headroom while bounding worst-case stalls.
SEARCH_TIMEOUT_S = 6.0

# ── Error categories for structured logging ────────────────────────────────────

class VectorSearchError(Exception):
    """Base class for vector search errors."""

class VectorSearchAuthError(VectorSearchError):
    """IAM / credentials error (HTTP 403 / PERMISSION_DENIED)."""

class VectorSearchConfigError(VectorSearchError):
    """Endpoint or index not found (HTTP 404 / NOT_FOUND)."""

class VectorSearchTimeoutError(VectorSearchError):
    """Search call exceeded SEARCH_TIMEOUT_S."""


def _classify_error(exc: Exception) -> VectorSearchError:
    """Wrap a raw SDK exception in a structured subclass."""
    msg = str(exc)
    if "403" in msg or "PERMISSION_DENIED" in msg:
        return VectorSearchAuthError(
            "Vertex AI 403 PERMISSION_DENIED — "
            "ensure service account has roles/aiplatform.user"
        )
    if "404" in msg or "NOT_FOUND" in msg:
        return VectorSearchConfigError(
            "Vertex AI 404 NOT_FOUND — "
            "verify VERTEX_AI_INDEX_ENDPOINT_ID and VERTEX_AI_INDEX_ID"
        )
    return VectorSearchError(str(exc))


class VectorSearchService:
    """
    Async wrapper around Vertex AI Matching Engine (Vector Search).

    Thread-safety
    -------------
    The Vertex AI SDK is synchronous.  All SDK calls are dispatched to a
    private ThreadPoolExecutor so they never block the asyncio event loop.

    Lifetime
    --------
    Instantiate once at module level (singleton below).  Call close() in
    the FastAPI lifespan shutdown to drain in-flight tasks cleanly.
    """

    def __init__(self) -> None:
        self._endpoint  = None
        self._init_lock = threading.Lock()

    def _get_endpoint(self):
        """Lazily initialise the Matching Engine endpoint (thread-safe)."""
        if self._endpoint is None:
            with self._init_lock:
                if self._endpoint is None:
                    from google.cloud import aiplatform
                    aiplatform.init(
                        project=settings.gcp_project_id,
                        location=getattr(settings, "gcp_location", "us-central1"),
                    )
                    self._endpoint = aiplatform.MatchingEngineIndexEndpoint(
                        index_endpoint_name=settings.vertex_ai_index_endpoint_id
                    )
                    logger.info(
                        "VectorSearchService: endpoint initialised (%s)",
                        settings.vertex_ai_index_endpoint_id,
                    )
        return self._endpoint

    async def search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
    ) -> Optional[list[dict[str, Any]]]:
        """
        Search for nearest neighbours in the Vertex AI Vector index.

        Returns
        -------
        list[dict] — each item has:
            chunk_id  (str)   — document chunk identifier
            distance  (float) — cosine distance (lower = more similar)

        Returns None on any error — callers should fall back to the static corpus.

        The call is isolated on a dedicated ThreadPoolExecutor and wrapped in
        asyncio.wait_for() so it never blocks the event loop for more than
        SEARCH_TIMEOUT_S seconds.
        """
        if not settings.vertex_ai_index_endpoint_id or not settings.vertex_ai_index_id:
            logger.debug("Vertex AI index not configured — returning None")
            return None

        loop = asyncio.get_running_loop()

        def _sync_search() -> list[dict[str, Any]]:
            endpoint = self._get_endpoint()
            response = endpoint.find_neighbors(
                deployed_index_id=settings.vertex_ai_index_id,
                queries=[query_embedding],
                num_neighbors=top_k,
            )
            if not response or not response[0]:
                logger.info("Vector search returned no neighbors")
                return []
            return [
                {
                    "chunk_id": neighbor.id,
                    "distance": float(neighbor.distance),
                }
                for neighbor in response[0]
            ]

        try:
            future = loop.run_in_executor(_EXECUTOR, _sync_search)
            results: list[dict[str, Any]] = await asyncio.wait_for(
                future, timeout=SEARCH_TIMEOUT_S
            )
            logger.debug("Vector search: %d neighbors (top_k=%d)", len(results), top_k)
            return results

        except asyncio.TimeoutError:
            err = VectorSearchTimeoutError(
                f"Vector search timed out after {SEARCH_TIMEOUT_S}s"
            )
            logger.error("%s", err)
            return None

        except Exception as raw_exc:
            classified = _classify_error(raw_exc)
            if isinstance(classified, VectorSearchAuthError):
                logger.error("VectorSearch auth error: %s", classified)
            elif isinstance(classified, VectorSearchConfigError):
                logger.error("VectorSearch config error: %s", classified)
            else:
                logger.error("VectorSearch error: %s", raw_exc)
            return None

    def close(self) -> None:
        """
        Drain the dedicated executor on application shutdown.
        Called from FastAPI lifespan (main.py) alongside other service teardowns.
        """
        _EXECUTOR.shutdown(wait=False, cancel_futures=True)
        logger.info("VectorSearchService: executor shut down")


# Singleton — safe to import even without Vertex AI credentials
vector_search_service = VectorSearchService()
