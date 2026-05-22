import pytest
from src.services.ero_locator import ero_locator_service
from unittest.mock import AsyncMock, patch


class TestEROLocatorService:
    @pytest.mark.asyncio
    async def test_finds_ero_office_successfully(self):
        """Test that ERO office is found successfully."""
        with patch('src.services.ero_locator.mapbox.Client') as mock_client:
            # Mock geocode response
            mock_client.geocode.return_value = [{
                "geometry": {"location": {"lat": 19.0760, "lng": 72.8777}}
            }]

            # Mock places response
            mock_client.places_nearby.return_value = {
                "features": [{
                    "center": {
                        "coordinates": [72.8777, 19.0760],
                        "type": "Point"
                    },
                    "place_name": "Electoral Registration Officer",
                    "context": {
                        "phone": "+91-1234567890",
                        "email": "ero@example.com"
                    }
                }]
            }

        result = await ero_locator_service.find_ero_office("400001")

        assert result is not None
        assert result["name"] == "Electoral Registration Officer"
        assert result["phone"] == "+91-1234567890"
        assert result["distance_km"] > 0

    @pytest.mark.asyncio
    async def test_handles_geocode_failure(self):
        """Test that geocode failure returns None."""
        with patch('src.services.ero_locator.mapbox.Client') as mock_client:
            mock_client.geocode.return_value = []

            result = await ero_locator_service.find_ero_office("invalid")

        assert result is None

    @pytest.mark.asyncio
    async def test_handles_no_places_found(self):
        """Test that no places found returns None."""
        with patch('src.services.ero_locator.mapbox.Client') as mock_client:
            mock_client.geocode.return_value = [{
                "geometry": {"location": {"lat": 19.0760, "lng": 72.8777}}
            }]
            mock_client.places_nearby.return_value = {"features": []}

            result = await ero_locator_service.find_ero_office("400001")

        assert result is None
