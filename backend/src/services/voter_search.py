import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
from typing import Optional, Dict, Any
import logging
from ..config.settings import settings

logger = logging.getLogger(__name__)


class VoterSearchService:
    """Service for searching voter information via ECI API."""

    ECI_SEARCH_URL = "https://electoralsearch.eci.gov.in/api/search"

    def __init__(self):
        self.client = httpx.AsyncClient(timeout=10.0)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def search_by_epic(self, epic_number: str) -> Optional[Dict[str, Any]]:
        """
        Search for voter by EPIC number.
        Returns real data from ECI API or None if not found.
        """
        try:
            response = await self.client.post(
                self.ECI_SEARCH_URL,
                json={
                    "epic_no": epic_number,
                    "state_code": "",  # Will be filled if needed
                },
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "MatdaanMitra/1.0",
                },
            )

            if response.status_code == 503:
                logger.warning("ECI API returned 503 - service unavailable")
                return None

            if response.status_code == 404:
                logger.info(f"EPIC {epic_number} not found")
                return None

            response.raise_for_status()
            data = response.json()

            # Transform ECI response to our format
            if data and "result" in data:
                return {
                    "epic_number": epic_number,
                    "name": data["result"].get("name", ""),
                    "father_name": data["result"].get("father_name", ""),
                    "age": data["result"].get("age", 0),
                    "gender": data["result"].get("gender", ""),
                    "address": data["result"].get("address", ""),
                    "polling_station": data["result"].get("polling_station", ""),
                    "assembly_constituency": data["result"].get("assembly_constituency", ""),
                    "parliamentary_constituency": data["result"].get("parliamentary_constituency", ""),
                    "status": "active",
                }

            return None

        except httpx.TimeoutException:
            logger.error("ECI API timeout")
            return None
        except httpx.HTTPError as e:
            logger.error(f"ECI API error: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in voter search: {e}")
            return None

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


# Singleton instance
voter_search_service = VoterSearchService()
