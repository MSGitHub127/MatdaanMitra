"""
test_intent.py — Unit tests for the intent classification node

Tests use the keyword fallback path (GCP_PROJECT_ID not set in test env),
so no Vertex AI calls are made. asyncio_mode = auto (set in pytest.ini)
handles all async tests without per-test decorators.
"""

import pytest
from langchain_core.messages import HumanMessage
from src.agents.nodes.intent import intent_node


def _make_state(message: str) -> dict:
    return {
        "messages":          [HumanMessage(content=message)],
        "session_id":        "test-session-001",
        "voter_profile":     {},
        "intent":            None,
        "retrieved_chunks":  [],
        "live_data":         None,
        "final_response":    None,
        "response_language": "en",
        "confidence_score":  0.0,
        "agent_trace":       [],
        "requires_escalation": False,
        "error":             None,
    }


class TestIntentNode:

    async def test_classifies_form_guidance(self):
        result = await intent_node(_make_state("How do I fill out Form 6?"))
        assert result["intent"] == "form_guidance"
        assert result["confidence_score"] > 0.5
        assert result["error"] is None

    async def test_classifies_voter_lookup(self):
        result = await intent_node(_make_state("Check my EPIC number ABC1234567"))
        assert result["intent"] == "voter_lookup"
        assert result["confidence_score"] > 0.5

    async def test_classifies_ero_location(self):
        result = await intent_node(_make_state("Where is the nearest ERO office?"))
        assert result["intent"] == "ero_location"

    async def test_classifies_document_check(self):
        result = await intent_node(_make_state("What documents do I need for Aadhaar proof?"))
        assert result["intent"] == "document_check"

    async def test_classifies_deadline_query(self):
        result = await intent_node(_make_state("What is the last date for registration?"))
        assert result["intent"] == "deadline_query"

    async def test_classifies_grievance_help(self):
        result = await intent_node(_make_state("My name is missing from the voter list"))
        assert result["intent"] == "grievance_help"

    async def test_appends_to_agent_trace(self):
        result = await intent_node(_make_state("How do I register?"))
        assert len(result["agent_trace"]) == 1
        assert result["agent_trace"][0]["node"] == "intent"
        assert result["agent_trace"][0]["status"] == "ok"

    async def test_handles_empty_message_gracefully(self):
        """Should return 'unknown' intent rather than crashing."""
        result = await intent_node(_make_state(""))
        assert result["intent"] in ("unknown", "form_guidance", "profile_collection")
        assert result["error"] is None