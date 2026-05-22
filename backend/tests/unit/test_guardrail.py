import pytest
from src.agents.nodes.guardrail import guardrail_node
from src.agents.state import AgentState


class TestGuardrailNode:
    def test_blocks_political_party_mention(self):
        """Test that political party mentions are blocked."""
        state = {
            "final_response": "You should vote for BJP in this election.",
            "confidence_score": 0.9,
            "retrieved_chunks": [],
            "agent_trace": [],
            "requires_escalation": False,
            "error": None,
        }
        result = guardrail_node(state)
        assert "BJP" not in result["final_response"]
        assert "voter registration" in result["final_response"].lower()

    def test_escalates_low_confidence(self):
        """Test that low confidence responses trigger escalation."""
        state = {
            "final_response": "The deadline is probably December.",
            "confidence_score": 0.60,
            "retrieved_chunks": [],
            "agent_trace": [],
            "requires_escalation": False,
            "error": None,
        }
        result = guardrail_node(state)
        assert result["requires_escalation"] == True
        assert "1950" in result["final_response"]

    def test_passes_clean_registration_answer(self):
        """Test that clean registration answers pass through."""
        state = {
            "final_response": "You need to submit Form 6 within 30 days of relocation.",
            "confidence_score": 0.91,
            "retrieved_chunks": [],
            "agent_trace": [],
            "requires_escalation": False,
            "error": None,
        }
        result = guardrail_node(state)
        assert "Form 6" in result["final_response"]
        assert result["requires_escalation"] == False
