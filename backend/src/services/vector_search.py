from google.cloud import aiplatform
from typing import List, Dict, Any, Optional
import logging
from ..config.settings import settings

logger = logging.getLogger(__name__)


class VectorSearchService:
    """Service for searching ECI document embeddings using Vertex AI Vector Search."""

    def __init__(self):
        aiplatform.init(
            project=settings.gcp_project_id,
            location=settings.gcp_location,
        )
        self.index_endpoint = aiplatform.MatchingEngineIndexEndpoint(
            index_endpoint_name=settings.vertex_ai_index_endpoint_id
        )

    async def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Search for similar documents in the vector index.
        Returns list of chunks with metadata.
        """
        try:
            response = self.index_endpoint.find_neighbors(
                deployed_index_id=settings.vertex_ai_index_id,
                queries=[query_embedding],
                num_neighbors=top_k,
            )

            if not response or not response[0]:
                logger.warning("No results found in vector search")
                return []

            results = []
            for neighbor in response[0]:
                # MatchNeighbor only exposes .id and .distance.
                # Fetch full metadata (text, source_url, etc.) from your
                # external store (GCS / Firestore / BigQuery) using chunk_id.
                results.append({
                    "chunk_id": neighbor.id,
                    "distance": neighbor.distance,
                    # Metadata fields below must be populated by a separate
                    # lookup against your document store using chunk_id.
                    "text": "",
                    "confidence": neighbor.distance,
                    "source_url": "",
                    "form_type": "",
                    "section": "",
                })

            return results

        except Exception as e:
            logger.error(f"Vector search error: {e}")
            return None


# Singleton instance
vector_search_service = VectorSearchService()
