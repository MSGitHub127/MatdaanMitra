"""
profile_builder.py — Voter profile extraction node

Extracts structured profile fields from the conversation message using
regex patterns — no LLM call needed for this node (fast, deterministic).

Fixes: Added missing `datetime` import that caused NameError at runtime.
"""

import re
import logging
from datetime import datetime, timezone

from ..state import AgentState

logger = logging.getLogger(__name__)

_INDIAN_STATES = [
    "andhra pradesh", "arunachal pradesh", "assam", "bihar", "chhattisgarh",
    "goa", "gujarat", "haryana", "himachal pradesh", "jharkhand", "karnataka",
    "kerala", "madhya pradesh", "maharashtra", "manipur", "meghalaya", "mizoram",
    "nagaland", "odisha", "punjab", "rajasthan", "sikkim", "tamil nadu", "telangana",
    "tripura", "uttar pradesh", "uttarakhand", "west bengal", "delhi",
    "jammu and kashmir", "jammu kashmir", "ladakh",
]

# EPIC numbers: 3 letters + 7 digits, e.g. MH0123456
_EPIC_RE = re.compile(r'\b([A-Za-z]{2,3}\d{7,10})\b')
_PINCODE_RE = re.compile(r'\b(\d{6})\b')


async def profile_builder_node(state: AgentState) -> AgentState:
    trace: dict = {
        "node": "profile_builder",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    try:
        last_message: str = state["messages"][-1].content.lower()
        profile: dict = dict(state.get("voter_profile", {}))

        # ── State detection ───────────────────────────────────────────────────
        for state_name in _INDIAN_STATES:
            if state_name in last_message:
                profile["current_state"] = state_name.title()
                break

        # ── Pincode ───────────────────────────────────────────────────────────
        pin_match = _PINCODE_RE.search(last_message)
        if pin_match:
            profile["current_pincode"] = pin_match.group(1)

        # ── EPIC number ───────────────────────────────────────────────────────
        epic_match = _EPIC_RE.search(last_message.upper())
        if epic_match:
            profile["epic_number"] = epic_match.group(1)

        # ── Registration type ─────────────────────────────────────────────────
        if any(kw in last_message for kw in ("first time", "new voter", "never registered", "fresh")):
            profile["registration_type"] = "new"
        elif any(kw in last_message for kw in ("moved", "relocated", "shifted", "new address")):
            profile["registration_type"] = "relocation"
        elif any(kw in last_message for kw in ("nri", "overseas", "abroad", "foreign")):
            profile["registration_type"] = "nri"
        elif any(kw in last_message for kw in ("correction", "change name", "wrong detail", "update")):
            profile["registration_type"] = "correction"

        extracted = [k for k in ("current_state", "current_pincode", "epic_number", "registration_type")
                     if k in profile]
        trace.update({"status": "ok", "extracted_fields": extracted})

        return {
            **state,
            "voter_profile": profile,
            "agent_trace": state.get("agent_trace", []) + [trace],
            "error": None,
        }

    except Exception as exc:
        logger.exception("Profile builder error: %s", exc)
        trace.update({"status": "error", "error": str(exc)})
        return {
            **state,
            "agent_trace": state.get("agent_trace", []) + [trace],
            "error": f"Profile builder failed: {exc}",
        }