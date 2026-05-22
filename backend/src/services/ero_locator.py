import requests
from typing import Dict, Any, Optional
import logging
from math import radians, sin, cos, sqrt, atan2
from ..config.settings import settings

logger = logging.getLogger(__name__)

GEOCODE_URL = "https://api.mapbox.com/search/geocode/v6/forward"
SEARCH_URL = "https://api.mapbox.com/search/searchbox/v1/forward"


class EROLocatorService:
    """Service for locating ERO offices using the Mapbox REST API."""

    def __init__(self):
        self.access_token = settings.mapbox_access_token

    async def find_ero_office(self, pincode: str) -> Optional[Dict[str, Any]]:
        """
        Find the nearest ERO office for a given pincode.
        Uses Mapbox Geocoding API v6 + Search API.
        """
        try:
            # Step 1: Geocode the pincode to get coordinates
            geo_resp = requests.get(
                GEOCODE_URL,
                params={
                    "q": f"{pincode}, India",
                    "access_token": self.access_token,
                    "limit": 1,
                    "country": "IN",
                },
                timeout=10,
            )
            geo_resp.raise_for_status()
            geo_data = geo_resp.json()

            features = geo_data.get("features", [])
            if not features:
                logger.warning(f"Could not geocode pincode: {pincode}")
                return None

            coords = features[0]["geometry"]["coordinates"]
            lon, lat = coords[0], coords[1]

            # Step 2: Search for ERO / election office nearby
            search_queries = [
                "Electoral Registration Officer",
                "Election Commission office",
                "Collector office",
            ]

            place = None
            for query in search_queries:
                search_resp = requests.get(
                    SEARCH_URL,
                    params={
                        "q": query,
                        "access_token": self.access_token,
                        "proximity": f"{lon},{lat}",
                        "limit": 1,
                        "country": "IN",
                        "language": "en",
                    },
                    timeout=10,
                )
                search_resp.raise_for_status()
                search_data = search_resp.json()

                if search_data.get("features"):
                    place = search_data["features"][0]
                    break

            if not place:
                logger.warning(f"No ERO office found near pincode: {pincode}")
                return None

            # Extract place details
            place_coords = place["geometry"]["coordinates"]
            place_lon, place_lat = place_coords[0], place_coords[1]
            properties = place.get("properties", {})
            context = properties.get("context", {})

            distance_km = self._calculate_distance(lon, lat, place_lon, place_lat)
            directions_url = (
                f"https://www.google.com/maps/dir/?api=1"
                f"&destination={place_lat},{place_lon}"
            )

            return {
                "name": properties.get("name", "Electoral Registration Officer"),
                "address": properties.get("full_address", properties.get("place_formatted", "")),
                "phone": context.get("phone", {}).get("name", "N/A"),
                "email": "N/A",  # Mapbox Search does not return email
                "distance_km": round(distance_km, 2),
                "directions_url": directions_url,
                "latitude": place_lat,
                "longitude": place_lon,
            }

        except requests.RequestException as e:
            logger.error(f"Mapbox API request failed for pincode {pincode}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error finding ERO office for pincode {pincode}: {e}")
            return None

    def _calculate_distance(self, lon1: float, lat1: float, lon2: float, lat2: float) -> float:
        """Calculate straight-line distance between two coordinates in km (Haversine formula)."""
        lat1, lon1 = radians(lat1), radians(lon1)
        lat2, lon2 = radians(lat2), radians(lon2)

        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        return 6371 * c  # Earth's radius in km


# Singleton instance
ero_locator_service = EROLocatorService()