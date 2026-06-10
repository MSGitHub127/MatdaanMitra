"""
conftest.py — Shared pytest fixtures for MatdaanMitra tests

Provides:
  - firebase_token_override: bypasses Firebase auth on every route
  - no_redis: disables Redis rate limiting so tests don't need a real Redis
  - mock_agent: returns a fixed agent response so chat tests don't call Vertex AI
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient


# ── Firebase auth bypass ───────────────────────────────────────────────────────

TEST_UID = "test-uid-matdaan-123"


@pytest.fixture(autouse=True)
def firebase_token_override():
    """
    Override verify_firebase_token dependency for ALL tests automatically.
    Routes behave as if a valid Firebase token was provided.
    """
    from src.api.middleware.auth import verify_firebase_token
    from src.api.main import app

    app.dependency_overrides[verify_firebase_token] = lambda: TEST_UID
    yield
    app.dependency_overrides.clear()


# ── Redis bypass ───────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def no_redis():
    """
    Patch RateLimitMiddleware and check_rate_limit to no-ops.
    Tests should never need a running Redis instance.
    """
    async def _noop_rate_limit(*args, **kwargs):
        return None

    with patch("src.api.middleware.rate_limit.check_rate_limit", side_effect=_noop_rate_limit):
        yield


# ── FastAPI test client ────────────────────────────────────────────────────────

@pytest.fixture
def client():
    from src.api.main import app
    return TestClient(app, raise_server_exceptions=False)


# ── Mock agent graph ──────────────────────────────────────────────────────────

@pytest.fixture
def mock_agent_graph():
    """
    Patches agent_graph.ainvoke to return a fixed successful state.
    Prevents any Vertex AI / Gemini calls during integration tests.
    """
    fixed_state = {
        "final_response":   "You need to submit Form 6 to register as a new voter.",
        "confidence_score": 0.91,
        "retrieved_chunks": [],
        "agent_trace":      [{"node": "intent_classifier", "status": "ok"}],
        "voter_profile":    {},
        "requires_escalation": False,
        "error": None,
    }

    with patch("src.api.routes.chat.agent_graph") as mock_graph:
        mock_graph.ainvoke = AsyncMock(return_value=fixed_state)
        yield mock_graph


# ── Firestore bypass ──────────────────────────────────────────────────────────

@pytest.fixture
def no_firestore():
    """
    Patches all Firestore calls in chat.py to return empty session data.
    Tests never need a real Firebase project.
    """
    with patch("src.api.routes.chat._load_session", return_value=({}, [])), \
         patch("src.api.routes.chat._save_session", new_callable=AsyncMock):
        yield