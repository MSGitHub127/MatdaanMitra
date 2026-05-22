import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class PincodeService:
    """Service for validating pincodes and fetching constituency information via India Post API."""

    INDIA_POST_API_URL = "https://api.postalpincode.in/pincode"

    def __init__(self):
        self.client = httpx.AsyncClient(timeout=10.0)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def get_pincode_info(self, pincode: str) -> Optional[Dict[str, Any]]:
        """
        Fetch pincode information from India Post API.
        Returns real data or None if not found.
        """
        try:
            response = await self.client.get(f"{self.INDIA_POST_API_URL}/{pincode}")

            if response.status_code == 404:
                logger.info(f"Pincode {pincode} not found")
                return None

            response.raise_for_status()
            data = response.json()

            if data and "PostOffice" in data and isinstance(data["PostOffice"], list) and len(data["PostOffice"]) > 0:
                post_office = data["PostOffice"][0]
                return {
                    "pincode": pincode,
                    "post_office": post_office.get("Name", ""),
                    "district": post_office.get("District", ""),
                    "state": post_office.get("State", ""),
                    "circle": post_office.get("Circle", ""),
                    "country": post_office.get("Country", "India"),
                }

            return None

        except httpx.TimeoutException:
            logger.error("India Post API timeout")
            return None
        except httpx.HTTPError as e:
            logger.error(f"India Post API error: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in pincode lookup: {e}")
            return None

    async def validate_pincode(self, pincode: str) -> bool:
        """
        Validate if a pincode exists in the India Post database.
        Returns True if valid, False otherwise.
        """
        info = await self.get_pincode_info(pincode)
        return info is not None

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


# Singleton instance
pincode_service = PincodeService()
