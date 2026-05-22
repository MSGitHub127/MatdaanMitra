from typing import Dict, Any
from ..state import AgentState
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


SYNTHESIS_PROMPT = """
You are a helpful voter registration assistant for Indian elections.
Use the retrieved information to answer the user's question.

User message: {message}
Retrieved information: {chunks}
Voter profile: {profile}
Live data: {live_data}

Provide a clear, helpful response. If you're not confident about the answer,
say so and direct the user to official sources.

Response:
"""


async def synthesis_node(state: AgentState) -> AgentState:
    """
    Synthesizes the final response using retrieved chunks and live data.
    Uses Gemini Pro for natural language generation.
    """
    trace_entry = {
        "node": "synthesis",
        "timestamp": datetime.utcnow().isoformat(),
    }

    try:
        last_message = state["messages"][-1].content
        chunks = state.get("retrieved_chunks", [])
        profile = state.get("voter_profile", {})
        live_data = state.get("live_data", {})

        # Placeholder for actual LLM call
        # In production, this would call Gemini Pro with the synthesis prompt

        # Build response from chunks
        if chunks:
            response_text = chunks[0]["text"]
            if len(chunks) > 1:
                response_text += "\n\n" + chunks[1]["text"]
        else:
            response_text = "I don't have specific information about that. Please check eci.gov.in for official details."

        trace_entry["status"] = "success"
        trace_entry["input_tokens"] = len(last_message) + sum(len(c["text"]) for c in chunks)

        return {
            **state,
            "final_response": response_text,
            "confidence_score": chunks[0]["confidence"] if chunks else 0.5,
            "agent_trace": state.get("agent_trace", []) + [trace_entry],
            "error": None,
        }

    except Exception as e:
        logger.error(f"Synthesis error: {e}")
        trace_entry["status"] = "error"
        trace_entry["error"] = str(e)
        return {
            **state,
            "final_response": "I encountered an error processing your request. Please try again.",
            "confidence_score": 0.0,
            "agent_trace": state.get("agent_trace", []) + [trace_entry],
            "error": f"Synthesis failed: {str(e)}",
        }
