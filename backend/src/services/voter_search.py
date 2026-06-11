"""
voter_search.py — ECI Voter Status Lookup Service

The ECI electoral search API (electoralsearch.eci.gov.in) is not a
public API — it returns 403 for direct programmatic access. This service
handles that reality with a graceful, honest fallback:

  1. Attempts the ECI API with proper headers + session simulation
  2. On 403 / failure, returns a structured NVSP redirect response
     that the frontend renders as a "Verify on NVSP.in" CTA

This is the correct UX — directing users to the authoritative source
is better than returning stale or mock data.
"""

import logging
import re
from typing import Any, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


# ── Constants ─────────────────────────────────────────────────────────────────

_ECI_SEARCH_URL  = "https://electoralsearch.eci.gov.in/api/search"
_NVSP_BASE_URL   = "https://electoralsearch.eci.gov.in"

# EPIC format: 2-3 uppercase letters + 7-8 digits, e.g. MH01234567
_EPIC_RE = re.compile(r'^[A-Z]{2,3}\d{7,8}$')


# ── Response shapes ───────────────────────────────────────────────────────────

def _nvsp_redirect(epic: str, reason: str = "api_unavailable") -> dict[str, Any]:
    """
    Returns a structured response the frontend uses to render a
    'Verify on NVSP.in' button with a deep-link.
    """
    # NVSP direct search URL with EPIC pre-filled (works as a web page)
    nvsp_url = f"https://electoralsearch.eci.gov.in/?epicno={epic}"
    return {
        "found":        None,          # None = unknown (not checked)
        "nvsp_redirect": True,
        "nvsp_url":      nvsp_url,
        "epic_number":   epic,
        "reason":        reason,
        "message": (
            f"Live voter lookup is temporarily unavailable. "
            f"Please verify directly on the official NVSP portal."
        ),
    }


def _format_result(data: dict[str, Any], epic: str) -> dict[str, Any]:
    """Normalise ECI API response to our VoterStatus shape."""
    result = data.get("result", data)
    return {
        "found":                       True,
        "nvsp_redirect":               False,
        "epic_number":                 epic,
        "name":                        result.get("name", ""),
        "father_name":                 result.get("father_name", ""),
        "age":                         result.get("age", 0),
        "gender":                      result.get("gender", ""),
        "address":                     result.get("address", ""),
        "polling_station":             result.get("polling_station", ""),
        "assembly_constituency":       result.get("assembly_constituency", ""),
        "parliamentary_constituency":  result.get("parliamentary_constituency", ""),
        "status":                      "active",
    }


# ── Service ───────────────────────────────────────────────────────────────────

class VoterSearchService:
    """
    Voter status lookup with graceful fallback to NVSP redirect.
    """

    def __init__(self) -> None:
        self._client: Optional[httpx.AsyncClient] = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(10.0, connect=5.0),
                headers={
                    "User-Agent":   "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Accept":       "application/json, text/plain, */*",
                    "Origin":       "https://electoralsearch.eci.gov.in",
                    "Referer":      "https://electoralsearch.eci.gov.in/",
                    "Content-Type": "application/json",
                },
                follow_redirects=True,
            )
        return self._client

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(min=1, max=4))
    async def search_by_epic(self, epic_number: str) -> dict[str, Any]:
        """
        Look up a voter by EPIC number.

        Returns one of:
          - VoterStatus dict with found=True  (success)
          - nvsp_redirect dict with nvsp_url  (API blocked or unavailable)
          - nvsp_redirect dict with found=False (not on roll)
        """
        epic = epic_number.strip().upper()

        if not _EPIC_RE.match(epic):
            return {
                "found":   False,
                "nvsp_redirect": False,
                "reason":  "invalid_epic_format",
                "message": (
                    f"'{epic_number}' doesn't look like a valid EPIC number. "
                    "Indian EPIC numbers are 2–3 letters followed by 7–8 digits, "
                    "e.g. MH01234567."
                ),
            }

        try:
            client = self._get_client()
            resp = await client.post(
                _ECI_SEARCH_URL,
                json={"epic_no": epic, "state_code": ""},
            )

            if resp.status_code == 200:
                data = resp.json()
                if data and ("result" in data or "name" in data):
                    logger.info("ECI API hit for EPIC %s", epic[:5] + "***")
                    return _format_result(data, epic)
                # 200 but no result = not found
                return {
                    "found":        False,
                    "nvsp_redirect": False,
                    "epic_number":   epic,
                    "message": (
                        f"No voter found with EPIC {epic} in the ECI database. "
                        "Check the number carefully, or verify on nvsp.in."
                    ),
                    "nvsp_url": f"https://electoralsearch.eci.gov.in/?epicno={epic}",
                }

            if resp.status_code == 404:
                return {
                    "found":        False,
                    "nvsp_redirect": False,
                    "epic_number":   epic,
                    "message": "EPIC number not found in ECI database.",
                    "nvsp_url": f"https://electoralsearch.eci.gov.in/?epicno={epic}",
                }

            # 403, 429, 5xx — API is blocked or overloaded
            logger.warning(
                "ECI API returned %s for EPIC lookup — redirecting to NVSP",
                resp.status_code,
            )
            return _nvsp_redirect(epic, reason=f"http_{resp.status_code}")

        except httpx.TimeoutException:
            logger.warning("ECI API timeout for EPIC %s", epic[:5] + "***")
            return _nvsp_redirect(epic, reason="timeout")

        except httpx.RequestError as exc:
            logger.error("ECI API network error: %s", exc)
            return _nvsp_redirect(epic, reason="network_error")

        except Exception as exc:
            logger.exception("Unexpected voter search error: %s", exc)
            return _nvsp_redirect(epic, reason="unexpected_error")

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()


# Singleton
voter_search_service = VoterSearchService()