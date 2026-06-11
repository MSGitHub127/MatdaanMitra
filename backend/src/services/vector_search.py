"""
vector_search.py — Vertex AI Matching Engine wrapper

Fix: Previous implementation called aiplatform.MatchingEngineIndexEndpoint
     in __init__, which crashed at module import when Vertex AI credentials
     were absent. Now uses lazy initialization — the endpoint is only
     instantiated on the first actual search() call.
"""

import logging
from typing import Any, Optional

from ..config.settings import settings

logger = logging.getLogger(__name__)


class VectorSearchService:
    """Async wrapper around Vertex AI Matching Engine (Vector Search)."""

    def __init__(self) -> None:
        # Defer all Vertex AI SDK calls until first use
        self._endpoint = None

    def _get_endpoint(self):
        """Lazily initialise the Matching Engine endpoint."""
        if self._endpoint is None:
            from google.cloud import aiplatform
            aiplatform.init(
                project=settings.gcp_project_id,
                location=settings.gcp_location,
            )
            self._endpoint = aiplatform.MatchingEngineIndexEndpoint(
                index_endpoint_name=settings.vertex_ai_index_endpoint_id
            )
        return self._endpoint

    async def search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
    ) -> Optional[list[dict[str, Any]]]:
        """
        Search for nearest neighbours in the Vertex AI Vector index.

        Returns a list of dicts with keys:
          chunk_id  — the document chunk identifier (str)
          distance  — cosine distance (float, lower = more similar)

        The caller is responsible for fetching full metadata (text, source_url,
        form_type, section) from Firestore using chunk_id.

        Returns None on any error — callers should fall back to static corpus.
        """
        if not settings.vertex_ai_index_endpoint_id or not settings.vertex_ai_index_id:
            logger.debug("Vertex AI index not configured — returning None")
            return None

        try:
            import asyncio
            endpoint = self._get_endpoint()

            def _sync_search():
                return endpoint.find_neighbors(
                    deployed_index_id=settings.vertex_ai_index_id,
                    queries=[query_embedding],
                    num_neighbors=top_k,
                )

            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(None, _sync_search)

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

        except Exception as exc:
            logger.error("Vector search error: %s", exc)
            return None


# Singleton — safe to import even without Vertex AI credentials
vector_search_service = VectorSearchService()