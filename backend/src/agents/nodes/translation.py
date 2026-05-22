from ..state import AgentState
import logging

logger = logging.getLogger(__name__)


async def translation_node(state: AgentState) -> AgentState:
    """
    Translates the final response to the user's preferred language.
    Only runs if language is not English.
    """
    trace_entry = {
        "node": "translation",
        "timestamp": datetime.utcnow().isoformat(),
    }

    try:
        response_language = state.get("response_language", "en")
        final_response = state.get("final_response", "")

        # Only translate if not English
        if response_language == "en":
            trace_entry["status"] = "skipped"
            return state

        # Placeholder for actual translation
        # In production, this would call translator_service.translate()
        translated_response = final_response  # No translation in placeholder

        trace_entry["status"] = "success"
        trace_entry["source_language"] = "en"
        trace_entry["target_language"] = response_language

        return {
            **state,
            "final_response": translated_response,
            "agent_trace": state.get("agent_trace", []) + [trace_entry],
            "error": None,
        }

    except Exception as e:
        logger.error(f"Translation error: {e}")
        trace_entry["status"] = "error"
        trace_entry["error"] = str(e)
        # Return original response on translation error
        return state
