import mapbox
from typing import Dict, Any, Optional
import logging
from ..config.settings import settings

logger = logging.getLogger(__name__)


class EROLocatorService:
    """Service for locating ERO offices using Mapbox GL."""

    def __init__(self):
        self.client = mapbox.Client(access_token=settings.mapbox_access_token)

    async def find_ero_office(self, pincode: str) -> Optional[Dict[str, Any]]:
        """
        Find the nearest ERO office for a given pincode.
        Returns real data from Mapbox GL API.
        """
        try:
            # First, geocode the pincode to get coordinates
            geocode_result = self.client.geocode(f"{pincode}, India")
            if not geocode_result:
                logger.warning(f"Could not geocode pincode: {pincode}")
                return None

            location = geocode_result[0]["geometry"]["coordinates"]
            lon, lat = location  # Mapbox GL returns [lon, lat]

            # Search for ERO offices nearby
            places_result = self.client.places_nearby(
                location=[lon, lat],
                radius=10000,  # 10km radius
                query="Electoral Registration Officer ERO",
            )

            if not places_result.get("features"):
                # Try alternative search terms
                places_result = self.client.places_nearby(
                    location=[lon, lat],
                    radius=10000,
                    query="CEO office election commission",
                )

            if not places_result.get("features"):
                logger.warning(f"No ERO office found near pincode: {pincode}")
                return None

            # Get the first result
            place = places_result["features"][0]
            place_center = place["center"]

            # Calculate distance (simplified - using straight-line distance)
            # In production, you could use Mapbox Directions API for actual driving distance
            distance_km = self._calculate_distance(
                lon, lat,
                place_center["coordinates"][0],
                place_center["coordinates"][1]
            )

            # Generate directions URL
            directions_url = f"https://www.google.com/maps/dir/?api=1&destination={place_center['coordinates'][1]},{place_center['coordinates'][0]}"

            return {
                "name": place.get("place_name", "Electoral Registration Officer"),
                "address": place.get("place_name", ""),  # Mapbox uses place_name for formatted address
                "phone": place.get("context", {}).get("phone", "N/A"),
                "email": place.get("context", {}).get("email", "N/A"),
                "distance_km": round(distance_km, 2),
                "directions_url": directions_url,
                "latitude": place_center["coordinates"][1],
                "longitude": place_center["coordinates"][0],
            }

    def _calculate_distance(self, lon1, lat1, lon2, lat2):
        """Calculate straight-line distance between two coordinates in km."""
        from math import radians, sin, cos, sqrt, atan2

        # Convert to radians
        lat1, lon1 = radians(lat1), radians(lon1)
        lat2, lon2 = radians(lat2), radians(lon2)

        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
        c = 2 * atan2(sqrt(a) / (1 - a))

        r = 6371  # Earth's radius in km
        return r * c


# Singleton instance
ero_locator_service = EROLocatorService()
EOF