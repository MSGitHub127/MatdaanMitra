"""
test_ero_locator.py — Unit tests for the ERO locator service

Previous version mocked 'src.services.ero_locator.mapbox.Client' which
doesn't exist — the service uses httpx, not a Mapbox SDK client.
Fixed: patches _get_client() to return a mock httpx.AsyncClient.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.services.ero_locator import ero_locator_service


def _make_geocode_response(lon: float = 72.8777, lat: float = 19.0760) -> MagicMock:
    resp = MagicMock()
    resp.status_code = 200
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {
        "features": [{"geometry": {"coordinates": [lon, lat]}}]
    }
    return resp


def _make_search_response(name: str = "Electoral Registration Officer") -> MagicMock:
    resp = MagicMock()
    resp.status_code = 200
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {
        "features": [{
            "geometry": {"coordinates": [72.8777, 19.0760]},
            "properties": {
                "name":         name,
                "full_address": "Mantralaya, Mumbai, Maharashtra 400032",
                "context": {
                    "phone": {"name": "+91-22-22025532"},
                },
            },
        }]
    }
    return resp


def _mock_client(geo_resp, search_resp) -> MagicMock:
    client = MagicMock()
    client.get = AsyncMock(side_effect=[geo_resp, search_resp])
    return client


class TestEROLocatorService:

    @pytest.fixture(autouse=True)
    def mock_pincode_fallback(self):
        """Mock India Post pincode service to return None by default during unit tests."""
        with patch("src.services.pincode.PincodeService.get_pincode_info", new_callable=AsyncMock, return_value=None):
            yield

    async def test_finds_ero_office_successfully(self):
        mock_client = _mock_client(
            _make_geocode_response(),
            _make_search_response("Electoral Registration Officer"),
        )
        with patch("src.services.ero_locator._get_client", return_value=mock_client):
            result = await ero_locator_service.find_ero_office("400001")

        assert result is not None
        assert "Electoral" in result["name"]
        assert result["distance_km"] >= 0
        assert result["latitude"] == pytest.approx(19.0760, abs=0.01)
        assert result["longitude"] == pytest.approx(72.8777, abs=0.01)
        assert "google.com/maps" in result["directions_url"]

    async def test_returns_none_when_geocode_fails(self):
        """Empty features list from geocode → service returns None."""
        fail_resp = MagicMock()
        fail_resp.status_code = 200
        fail_resp.raise_for_status = MagicMock()
        fail_resp.json.return_value = {"features": []}

        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=fail_resp)

        with patch("src.services.ero_locator._get_client", return_value=mock_client):
            result = await ero_locator_service.find_ero_office("000000")

        assert result is None

    async def test_returns_none_when_search_finds_nothing(self):
        """Geocode succeeds but no POI found → service returns None."""
        empty_search = MagicMock()
        empty_search.status_code = 200
        empty_search.raise_for_status = MagicMock()
        empty_search.json.return_value = {"features": []}

        mock_client = _mock_client(
            _make_geocode_response(),
            empty_search,
        )
        # Multiple search queries are tried — all return empty
        mock_client.get = AsyncMock(
            side_effect=[_make_geocode_response()] + [empty_search] * 5
        )

        with patch("src.services.ero_locator._get_client", return_value=mock_client):
            result = await ero_locator_service.find_ero_office("400001")

        assert result is None

    async def test_handles_network_error_gracefully(self):
        """Network errors should return None, not raise."""
        import httpx
        mock_client = MagicMock()
        mock_client.get = AsyncMock(side_effect=httpx.ConnectError("timeout"))

        with patch("src.services.ero_locator._get_client", return_value=mock_client):
            result = await ero_locator_service.find_ero_office("400001")

        assert result is None

    def test_haversine_distance_calculation(self):
        """Haversine formula sanity check — Mumbai to Pune is ~120 km."""
        dist = ero_locator_service._haversine(
            lon1=72.8777, lat1=19.0760,  # Mumbai
            lon2=73.8567, lat2=18.5204,  # Pune
        )
        assert 115 < dist < 135, f"Expected ~125 km, got {dist:.1f} km"