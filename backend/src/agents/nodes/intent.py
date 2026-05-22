from typing import Literal
from ..state import AgentState
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


INTENT_PROMPT = """
You are an intent classifier for a voter registration assistant.
Classify the user's intent into one of these categories:
- profile_collection: User is providing personal information
- form_guidance: User is asking about forms or procedures
- deadline_query: User is asking about dates or deadlines
- document_check: User is asking about required documents
- voter_lookup: User is providing an EPIC number to check status
- ero_location: User is asking about ERO office locations
- grievance_help: User has a complaint or issue
- off_topic: User is asking about unrelated topics
- unknown: Cannot determine intent

User message: {message}
Voter profile: {profile}

Return JSON with intent and confidence (0-1):
{{"intent": "category", "confidence": 0.95}}
"""


async def intent_node(state: AgentState) -> AgentState:
    """
    Classifies user intent using Gemini Flash.
    Updates state.intent field.
    """
    trace_entry = {
        "node": "intent",
        "timestamp": datetime.utcnow().isoformat(),
    }

    try:
        last_message = state["messages"][-1].content
        profile_json = json.dumps(state.get("voter_profile", {}))

        # Placeholder for actual LLM call
        # In production, this would call Gemini Flash
        result = {
            "intent": "form_guidance",
            "confidence": 0.85,
        }

        trace_entry["intent"] = result.get("intent", "unknown")
        trace_entry["status"] = "success"

        return {
            **state,
            "intent": result.get("intent", "unknown"),
            "confidence_score": result.get("confidence", 0.5),
            "agent_trace": state.get("agent_trace", []) + [trace_entry],
            "error": None,
        }

    except Exception as e:
        logger.error(f"Intent classification error: {e}")
        trace_entry["status"] = "error"
        trace_entry["error"] = str(e)
        return {
            **state,
            "intent": "unknown",
            "agent_trace": state.get("agent_trace", []) + [trace_entry],
            "error": f"Intent classification failed: {str(e)}",
        }
