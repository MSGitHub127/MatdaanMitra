from typing import Dict, Any
from ..state import AgentState
import re
import logging

logger = logging.getLogger(__name__)


async def profile_builder_node(state: AgentState) -> AgentState:
    """
    Extracts and updates voter profile information from conversation.
    Identifies state, pincode, registration type, etc.
    """
    trace_entry = {
        "node": "profile_builder",
        "timestamp": datetime.utcnow().isoformat(),
    }

    try:
        last_message = state["messages"][-1].content.lower()
        current_profile = state.get("voter_profile", {})

        # Extract state name (common Indian states)
        STATES = [
            "andhra pradesh", "arunachal pradesh", "assam", "bihar", "chhattisgarh",
            "goa", "gujarat", "haryana", "himachal pradesh", "jharkhand", "karnataka",
            "kerala", "madhya pradesh", "maharashtra", "manipur", "meghalaya", "mizoram",
            "nagaland", "odisha", "punjab", "rajasthan", "sikkim", "tamil nadu", "telangana",
            "tripura", "uttar pradesh", "uttarakhand", "west bengal", "delhi", "jammu kashmir",
        ]

        # Check for state mention
        for state_name in STATES:
            if state_name in last_message:
                current_profile["current_state"] = state_name.title()
                break

        # Extract pincode (6 digits)
        pincode_match = re.search(r'\b(\d{6})\b', last_message)
        if pincode_match:
            current_profile["current_pincode"] = pincode_match.group(1)

        # Determine registration type
        if "first time" in last_message or "new voter" in last_message:
            current_profile["registration_type"] = "new"
        elif "moved" in last_message or "relocated" in last_message or "shifted" in last_message:
            current_profile["registration_type"] = "relocation"
        elif "nri" in last_message or "overseas" in last_message:
            current_profile["registration_type"] = "nri"
        elif "correction" in last_message or "change" in last_message:
            current_profile["registration_type"] = "correction"

        trace_entry["status"] = "success"
        trace_entry["extracted_fields"] = list(current_profile.keys())

        return {
            **state,
            "voter_profile": current_profile,
            "agent_trace": state.get("agent_trace", []) + [trace_entry],
            "error": None,
        }

    except Exception as e:
        logger.error(f"Profile builder error: {e}")
        trace_entry["status"] = "error"
        trace_entry["error"] = str(e)
        return {
            **state,
            "agent_trace": state.get("agent_trace", []) + [trace_entry],
            "error": f"Profile builder failed: {str(e)}",
        }
