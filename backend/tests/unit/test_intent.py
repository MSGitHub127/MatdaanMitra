import pytest
from src.agents.nodes.intent import intent_node
from src.agents.state import AgentState
from langchain_core.messages import HumanMessage


class TestIntentNode:
    @pytest.mark.asyncio
    async def test_classifies_form_guidance_intent(self):
        """Test that form guidance questions are classified correctly."""
        state = {
            "messages": [HumanMessage(content="How do I fill out Form 6?")],
            "session_id": "test-123",
            "voter_profile": {},
            "intent": None,
            "retrieved_chunks": [],
            "live_data": None,
            "final_response": None,
            "response_language": "en",
            "confidence_score": 0.0,
            "agent_trace": [],
            "requires_escalation": False,
            "error": None,
        }
        result = await intent_node(state)
        assert result["intent"] == "form_guidance"
        assert result["confidence_score"] > 0.5

    @pytest.mark.asyncio
    async def test_classifies_voter_lookup_intent(self):
        """Test that EPIC number lookups are classified correctly."""
        state = {
            "messages": [HumanMessage(content="Check my EPIC number ABC1234567")],
            "session_id": "test-123",
            "voter_profile": {},
            "intent": None,
            "retrieved_chunks": [],
            "live_data": None,
            "final_response": None,
            "response_language": "en",
            "confidence_score": 0.0,
            "agent_trace": [],
            "requires_escalation": False,
            "error": None,
        }
        result = await intent_node(state)
        assert result["intent"] == "voter_lookup"
        assert result["confidence_score"] > 0.5
