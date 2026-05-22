import pytest
from fastapi.testclient import TestClient
from src.api.main import app


class TestChatRoute:
    def test_chat_endpoint_requires_auth(self):
        """Test that chat endpoint requires authentication."""
        client = TestClient(app)
        response = client.post("/api/chat", json={
            "session_id": "test-123",
            "message": "Hello",
            "language": "en"
        })
        assert response.status_code == 401

    def test_health_endpoint_works(self):
        """Test that health endpoint returns status."""
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "services" in data
