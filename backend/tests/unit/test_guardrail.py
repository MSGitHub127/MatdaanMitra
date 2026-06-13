"""
test_guardrail.py — Unit tests for the political content guardrail node

guardrail_node is now async — asyncio_mode = auto in pytest.ini handles this.
"""

import pytest
from src.agents.nodes.guardrail import guardrail_node


def _make_state(response: str, confidence: float = 0.90) -> dict:
    return {
        "final_response":    response,
        "confidence_score":  confidence,
        "retrieved_chunks":  [],
        "agent_trace":       [],
        "requires_escalation": False,
        "error":             None,
    }


class TestGuardrailNode:

    async def test_blocks_political_party_mention(self):
        state = _make_state("You should vote for BJP in this election.", confidence=0.90)
        result = await guardrail_node(state)
        assert "BJP" not in result["final_response"]
        assert "voter registration" in result["final_response"].lower()
        assert result["requires_escalation"] is False

    async def test_blocks_candidate_name(self):
        state = _make_state("PM Modi announced new voter policies.", confidence=0.88)
        result = await guardrail_node(state)
        assert "Modi" not in result["final_response"]

    async def test_escalates_low_confidence(self):
        state = _make_state("The deadline is probably December.", confidence=0.60)
        result = await guardrail_node(state)
        assert result["requires_escalation"] is True
        assert "1950" in result["final_response"]

    async def test_passes_clean_registration_answer(self):
        state = _make_state(
            "You need to submit Form 6 within 30 days of relocation.",
            confidence=0.91,
        )
        result = await guardrail_node(state)
        assert "Form 6" in result["final_response"]
        assert result["requires_escalation"] is False

    async def test_passes_high_confidence_answer(self):
        state = _make_state(
            "The qualifying date for voter registration is 1st January.",
            confidence=0.85,
        )
        result = await guardrail_node(state)
        assert result["requires_escalation"] is False
        assert "1st January" in result["final_response"]

    async def test_passes_voter_found_with_polling_station(self):
        """'Polling station' must NOT be blocked — it's an electoral process term."""
        state = _make_state(
            "✅ Voter found.\n**Polling Station:** Govt. School, Ward 4\n**Status:** Active",
            confidence=0.88,
        )
        result = await guardrail_node(state)
        assert "Polling Station" in result["final_response"]
        assert result["requires_escalation"] is False

    async def test_blocks_exit_poll_content(self):
        """'Exit poll' predictions should be blocked."""
        state = _make_state(
            "According to the exit poll, Party X is leading by 40 seats.",
            confidence=0.90,
        )
        result = await guardrail_node(state)
        assert "exit poll" not in result["final_response"].lower()

    async def test_handles_empty_response(self):
        state = _make_state("", confidence=0.90)
        result = await guardrail_node(state)
        assert result["final_response"] == ""

    async def test_appends_source_citations_for_high_confidence(self):
        state = {
            "final_response":   "Submit Form 6 to your local ERO.",
            "confidence_score": 0.92,
            "retrieved_chunks": [
                {
                    "form_type":  "Form 6",
                    "section":    "Submission Process",
                    "source_url": "https://eci.gov.in/form6",
                    "confidence": 0.92,
                }
            ],
            "agent_trace":       [],
            "requires_escalation": False,
            "error":             None,
        }
        result = await guardrail_node(state)
        assert "eci.gov.in" in result["final_response"]

    async def test_guardrail_appends_to_agent_trace(self):
        state = _make_state("Form 6 is required for new registration.", confidence=0.88)
        result = await guardrail_node(state)
        assert len(result["agent_trace"]) == 1
        assert result["agent_trace"][0]["node"] == "guardrail"
        assert result["agent_trace"][0]["status"] == "ok"