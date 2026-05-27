"""
ero_locator.py — ERO office geolocation service

Uses Mapbox Geocoding v6 (pincode → coordinates) and Mapbox Search Box v1
(coordinates → nearest government office POI).

IMPORTANT: Previously used `requests` (synchronous) inside async functions,
which blocks the FastAPI / uvicorn event loop under concurrent load.
This version uses `httpx.AsyncClient` throughout.
"""

import httpx
import logging
from math import radians, sin, cos, sqrt, atan2
from typing import Any, Optional

from ..config.settings import settings

logger = logging.getLogger(__name__)

GEOCODE_URL = "https://api.mapbox.com/search/geocode/v6/forward"
SEARCH_URL = "https://api.mapbox.com/search/searchbox/v1/forward"

# Ordered list of POI queries — we try each in sequence and take the first hit.
# More specific terms first so we don't accidentally return a generic office.
_ERO_SEARCH_QUERIES = [
    "Electoral Registration Officer",
    "Election Commission of India office",
    "District Collector office",
    "Tehsildar office",
]

# Shared async HTTP client — reuse across requests for connection pooling.
# Created lazily on first use so unit tests don't hit the network.
_http_client: Optional[httpx.AsyncClient] = None


def _get_client() -> httpx.AsyncClient:
    """Return (or create) the shared AsyncClient."""
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(connect=5.0, read=10.0, write=5.0, pool=5.0),
            headers={"User-Agent": "MatdaanMitra/1.0 (+https://matdaanmitra.in)"},
        )
    return _http_client


class EROLocatorService:
    """Locates the nearest Electoral Registration Officer office for a pincode."""

    def __init__(self) -> None:
        self.access_token: str = settings.mapbox_access_token

    # ── Public API ────────────────────────────────────────────────────────────

    async def find_ero_office(self, pincode: str) -> Optional[dict[str, Any]]:
        """
        Resolve a 6-digit Indian pincode to the nearest ERO office.

        Returns a dict matching EROOfficeResponse, or None if not found.
        Never raises — all errors are logged and absorbed so the route layer
        can return the correct HTTP status.
        """
        try:
            coords = await self._geocode_pincode(pincode)
            if not coords:
                return None

            lon, lat = coords
            place = await self._find_nearest_office(lon, lat)
            if not place:
                logger.warning("No ERO office POI found near pincode %s", pincode)
                return None

            return self._build_response(lon, lat, place)

        except httpx.RequestError as exc:
            logger.error("Network error while looking up pincode %s: %s", pincode, exc)
            return None
        except Exception as exc:  # noqa: BLE001
            logger.exception("Unexpected error for pincode %s: %s", pincode, exc)
            return None

    # ── Private helpers ───────────────────────────────────────────────────────

    async def _geocode_pincode(self, pincode: str) -> Optional[tuple[float, float]]:
        """
        Convert a pincode string to (longitude, latitude) using Mapbox Geocoding v6.
        Returns None if the pincode cannot be geocoded.
        """
        client = _get_client()
        resp = await client.get(
            GEOCODE_URL,
            params={
                "q": f"{pincode}, India",
                "access_token": self.access_token,
                "limit": 1,
                "country": "IN",
                # Prefer postcode-type results
                "types": "postcode,place,district",
            },
        )
        resp.raise_for_status()
        data = resp.json()

        features = data.get("features", [])
        if not features:
            logger.warning("Mapbox returned no geocode results for pincode: %s", pincode)
            return None

        # Mapbox GeoJSON: coordinates are [longitude, latitude]
        coords = features[0].get("geometry", {}).get("coordinates", [])
        if len(coords) < 2:
            logger.warning("Unexpected geometry for pincode %s: %s", pincode, coords)
            return None

        return float(coords[0]), float(coords[1])

    async def _find_nearest_office(
        self, lon: float, lat: float
    ) -> Optional[dict[str, Any]]:
        """
        Search for the nearest government/ERO office POI near the given coordinates.
        Tries multiple query strings in sequence and returns the first hit.
        """
        client = _get_client()

        for query in _ERO_SEARCH_QUERIES:
            resp = await client.get(
                SEARCH_URL,
                params={
                    "q": query,
                    "access_token": self.access_token,
                    "proximity": f"{lon},{lat}",
                    "limit": 1,
                    "country": "IN",
                    "language": "en",
                    # Only return administrative / POI types
                    "types": "poi,address",
                },
            )
            if resp.status_code != 200:
                logger.warning(
                    "Search API returned %s for query '%s'", resp.status_code, query
                )
                continue

            data = resp.json()
            features = data.get("features", [])
            if features:
                logger.info("Found ERO-like office with query: '%s'", query)
                return features[0]

        return None

    def _build_response(
        self,
        origin_lon: float,
        origin_lat: float,
        place: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Extract fields from a Mapbox Search Box feature and return a dict
        matching the EROOfficeResponse Pydantic model.
        """
        geometry = place.get("geometry", {})
        coords = geometry.get("coordinates", [origin_lon, origin_lat])
        place_lon, place_lat = float(coords[0]), float(coords[1])

        properties = place.get("properties", {})
        context = properties.get("context", {})

        # Full address: prefer `full_address`, fall back to `place_formatted`
        address = properties.get("full_address") or properties.get("place_formatted", "")

        # Phone: Mapbox surfaces this inconsistently; default to helpline
        phone = (
            context.get("phone", {}).get("name")
            or properties.get("metadata", {}).get("phone")
            or "1950"  # National Voter Helpline as fallback
        )

        distance_km = self._haversine(origin_lon, origin_lat, place_lon, place_lat)

        directions_url = (
            f"https://www.google.com/maps/dir/?api=1"
            f"&destination={place_lat},{place_lon}"
            f"&travelmode=driving"
        )

        return {
            "name": properties.get("name", "Electoral Registration Officer"),
            "address": address,
            "phone": phone,
            "email": "N/A",  # Mapbox does not reliably return email
            "distance_km": round(distance_km, 2),
            "directions_url": directions_url,
            "latitude": place_lat,
            "longitude": place_lon,
        }

    @staticmethod
    def _haversine(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
        """
        Great-circle distance between two WGS-84 points in kilometres.
        (Haversine formula — accurate to ~0.5% for distances < 1000 km)
        """
        R = 6_371.0  # Earth radius in km
        φ1, φ2 = radians(lat1), radians(lat2)
        Δφ = radians(lat2 - lat1)
        Δλ = radians(lon2 - lon1)
        a = sin(Δφ / 2) ** 2 + cos(φ1) * cos(φ2) * sin(Δλ / 2) ** 2
        return R * 2 * atan2(sqrt(a), sqrt(1 - a))


# Singleton — FastAPI imports this at startup once.
ero_locator_service = EROLocatorService()