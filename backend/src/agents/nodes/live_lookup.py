"""
live_lookup.py — Live data lookup node

Handles two intent branches:
  voter_lookup  → calls ECI electoral search API via voter_search_service
  ero_location  → calls Mapbox geocoding + search via ero_locator_service

Fixes: Added missing `datetime` import that caused NameError at runtime.
       Connected real service implementations instead of pending stubs.
"""

import re
import logging
from datetime import datetime, timezone

from ..state import AgentState
from ...services.voter_search import voter_search_service
from ...services.ero_locator import ero_locator_service

logger = logging.getLogger(__name__)

_EPIC_RE   = re.compile(r'\b([A-Za-z]{2,3}\d{7,10})\b')
_PINCODE_RE = re.compile(r'\b(\d{6})\b')


async def live_lookup_node(state: AgentState) -> AgentState:
    trace: dict = {
        "node": "live_lookup",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    try:
        intent: str | None = state.get("intent")
        profile: dict      = state.get("voter_profile", {})
        last_message: str  = state["messages"][-1].content
        live_data: dict    = {}

        # ── Voter lookup ──────────────────────────────────────────────────────
        if intent == "voter_lookup":
            # Priority: already in profile > extracted from message
            epic = profile.get("epic_number")
            if not epic:
                m = _EPIC_RE.search(last_message.upper())
                if m:
                    epic = m.group(1)

            if epic:
                trace["epic_queried"] = epic
                result = await voter_search_service.search_by_epic(epic)
                if result:
                    live_data = {"voter_status": result, "found": True}
                    trace["found"] = True
                else:
                    live_data = {"found": False, "epic": epic}
                    trace["found"] = False
            else:
                live_data = {"found": False, "reason": "no_epic_in_message"}
                trace["reason"] = "no_epic_extracted"

        # ── ERO location ──────────────────────────────────────────────────────
        elif intent == "ero_location":
            # Priority: profile pincode > extracted from message
            pincode = profile.get("current_pincode")
            if not pincode:
                m = _PINCODE_RE.search(last_message)
                if m:
                    pincode = m.group(1)

            if pincode:
                trace["pincode_queried"] = pincode
                ero = await ero_locator_service.find_ero_office(pincode)
                if ero:
                    live_data = {"ero_office": ero, "found": True}
                    trace["found"] = True
                else:
                    live_data = {"found": False, "pincode": pincode}
                    trace["found"] = False
            else:
                live_data = {"found": False, "reason": "no_pincode_in_message"}
                trace["reason"] = "no_pincode_extracted"

        trace.update({"status": "ok", "intent": intent})

        return {
            **state,
            "live_data": live_data,
            "agent_trace": state.get("agent_trace", []) + [trace],
            "error": None,
        }

    except Exception as exc:
        logger.exception("Live lookup error: %s", exc)
        trace.update({"status": "error", "error": str(exc)})
        return {
            **state,
            "live_data": None,
            "agent_trace": state.get("agent_trace", []) + [trace],
            "error": f"Live lookup failed: {exc}",
        }