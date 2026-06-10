"""
test_guardrail.py — Unit tests for the political content guardrail node

guardrail_node is synchronous — no async needed.
"""

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

    def test_blocks_political_party_mention(self):
        state = _make_state("You should vote for BJP in this election.", confidence=0.90)
        result = guardrail_node(state)
        assert "BJP" not in result["final_response"]
        # Guardrail replaces with a voter-registration-only message
        assert "voter registration" in result["final_response"].lower()
        assert result["requires_escalation"] is False

    def test_blocks_candidate_name(self):
        state = _make_state("Modi announced new voter policies.", confidence=0.88)
        result = guardrail_node(state)
        assert "Modi" not in result["final_response"]

    def test_escalates_low_confidence(self):
        state = _make_state("The deadline is probably December.", confidence=0.60)
        result = guardrail_node(state)
        assert result["requires_escalation"] is True
        # Should include helpline number
        assert "1950" in result["final_response"]

    def test_passes_clean_registration_answer(self):
        state = _make_state(
            "You need to submit Form 6 within 30 days of relocation.",
            confidence=0.91,
        )
        result = guardrail_node(state)
        assert "Form 6" in result["final_response"]
        assert result["requires_escalation"] is False

    def test_passes_high_confidence_answer(self):
        state = _make_state(
            "The qualifying date for voter registration is 1st January.",
            confidence=0.85,
        )
        result = guardrail_node(state)
        assert result["requires_escalation"] is False
        assert "1st January" in result["final_response"]

    def test_handles_empty_response(self):
        state = _make_state("", confidence=0.90)
        result = guardrail_node(state)
        # Empty response passes through unchanged
        assert result["final_response"] == ""

    def test_appends_source_citations_for_high_confidence(self):
        state = {
            "final_response":   "Submit Form 6 to your local ERO.",
            "confidence_score": 0.92,
            "retrieved_chunks": [
                {
                    "section":    "Submission Process",
                    "source_url": "https://eci.gov.in/form6",
                    "confidence": 0.92,
                }
            ],
            "agent_trace":       [],
            "requires_escalation": False,
            "error":             None,
        }
        result = guardrail_node(state)
        # Citations should be appended
        assert "eci.gov.in" in result["final_response"]