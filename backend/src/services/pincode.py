"""
pincode.py — India Post pincode lookup service

Bug fixed: India Post API returns a JSON *list*, not a dict.
response.json() → [{"Status": "Success", "PostOffice": [...], "Message": "..."}]

The previous code did `"PostOffice" in data` where `data` is a list, which
always evaluated False and caused the service to always return None regardless
of whether the pincode was valid.
"""

import logging
from typing import Any, Dict, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class PincodeService:
    """Validates pincodes and fetches district/state info via India Post API."""

    INDIA_POST_API_URL = "https://api.postalpincode.in/pincode"

    def __init__(self) -> None:
        # Single shared async client — closed on app shutdown via lifespan event
        self._client: Optional[httpx.AsyncClient] = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(10.0, connect=5.0),
                headers={"User-Agent": "MatdaanMitra/1.0"},
            )
        return self._client

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def get_pincode_info(self, pincode: str) -> Optional[Dict[str, Any]]:
        """
        Fetch pincode information from the India Post API.

        API contract:
          GET https://api.postalpincode.in/pincode/{pincode}
          Response: list[dict]
            [
              {
                "Status":     "Success" | "Error",
                "Message":    "Number of pincode(s) found: N",
                "PostOffice": [
                  {
                    "Name": "...", "District": "...", "State": "...",
                    "Circle": "...", "Country": "India", ...
                  }
                ]
              }
            ]

        Returns a normalised dict or None if not found / API error.
        """
        try:
            client = self._get_client()
            response = await client.get(f"{self.INDIA_POST_API_URL}/{pincode}")

            if response.status_code == 404:
                logger.info("Pincode %s not found (404)", pincode)
                return None

            response.raise_for_status()

            # Fix: API returns a list — index into the first element
            data = response.json()

            if not isinstance(data, list) or not data:
                logger.warning("India Post API unexpected response format for %s", pincode)
                return None

            item = data[0]

            if item.get("Status") != "Success":
                logger.info(
                    "India Post API returned non-success for %s: %s",
                    pincode, item.get("Message", "unknown")
                )
                return None

            post_offices: list = item.get("PostOffice") or []
            if not post_offices:
                return None

            po = post_offices[0]
            return {
                "pincode":     pincode,
                "post_office": po.get("Name", ""),
                "district":    po.get("District", ""),
                "state":       po.get("State", ""),
                "circle":      po.get("Circle", ""),
                "country":     po.get("Country", "India"),
            }

        except httpx.TimeoutException:
            logger.error("India Post API timeout for pincode %s", pincode)
            return None
        except httpx.HTTPStatusError as exc:
            logger.error("India Post API HTTP %s for %s", exc.response.status_code, pincode)
            return None
        except Exception as exc:
            logger.error("Unexpected error in pincode lookup for %s: %s", pincode, exc)
            return None

    async def validate_pincode(self, pincode: str) -> bool:
        """Return True if the pincode exists in the India Post database."""
        info = await self.get_pincode_info(pincode)
        return info is not None

    async def close(self) -> None:
        """Release the HTTP client. Call from FastAPI lifespan shutdown."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()


# Singleton — imported by routes that need pincode validation
pincode_service = PincodeService()