"""
intent.py — Intent classification node

Primary:  Gemini 1.5 Flash via langchain_google_vertexai (fast, cheap).
Fallback: Keyword pattern matching — runs when GCP credentials are absent
          or the Vertex AI API returns an error.

Output state keys:
  intent          — one of the 9 defined intent categories
  confidence_score — 0.0–1.0
  agent_trace     — appended entry
"""

import json
import logging
import re
from datetime import datetime, timezone

from ..state import AgentState
from ...config.settings import settings

logger = logging.getLogger(__name__)

# ── Lazy LLM initialisation ───────────────────────────────────────────────────

_llm = None


def _get_llm():
    global _llm
    if _llm is None:
        from langchain_google_vertexai import ChatVertexAI
        _llm = ChatVertexAI(
            model_name="gemini-1.5-flash-001",
            project=settings.gcp_project_id,
            location=settings.gcp_location,
            temperature=0,
            max_output_tokens=120,
        )
    return _llm


# ── Prompt ────────────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """You are an intent classifier for an Indian voter registration assistant.
Classify the user message into exactly one of these intents:

  profile_collection  — user is sharing personal info (name, state, pincode, EPIC)
  form_guidance       — asking about registration forms (Form 6, 7, 8, 8A, 6A)
  deadline_query      — asking about dates, deadlines, phases
  document_check      — asking about required documents or proof
  voter_lookup        — wants to check voter roll status via EPIC number
  ero_location        — wants to find an ERO/BLO office, nearby election office
  grievance_help      — has a complaint, missing name, wrong entry
  off_topic           — unrelated to voter registration
  unknown             — cannot determine intent

Reply with JSON only — no markdown, no explanation:
{"intent": "<category>", "confidence": <0.0-1.0>}"""


# ── Keyword fallback ──────────────────────────────────────────────────────────

_KEYWORD_RULES: list[tuple[str, list[str]]] = [
    ("voter_lookup",      ["epic", "voter id", "voter card", "check status", "enrolled", "roll number"]),
    ("ero_location",      ["ero", "ero office", "blo", "booth officer", "polling office", "where is", "nearest office", "find office"]),
    # deadline_query must come before form_guidance: "last date for registration"
    # contains "registration" which would otherwise match form_guidance first.
    ("deadline_query",    ["deadline", "last date", "cutoff", "by when", "how many days", "phase", "schedule"]),
    ("form_guidance",     ["form 6", "form 7", "form 8", "form 6a", "form 8a", "register", "registration", "enroll", "how to apply"]),
    ("document_check",    ["document", "aadhaar", "proof", "certificate", "photo", "id proof", "address proof", "what do i need"]),
    ("grievance_help",    ["missing", "not found", "wrong", "error", "complaint", "grievance", "problem", "issue", "deleted"]),
    ("profile_collection",["my name", "i am from", "i live in", "my pincode", "my state", "my address"]),
]


def _keyword_classify(message: str) -> tuple[str, float]:
    msg_lower = message.lower()
    for intent, keywords in _KEYWORD_RULES:
        if any(kw in msg_lower for kw in keywords):
            return intent, 0.72  # below the 0.75 guardrail threshold — safe fallback confidence
    return "unknown", 0.40


# ── Node ──────────────────────────────────────────────────────────────────────

async def intent_node(state: AgentState) -> AgentState:
    trace: dict = {
        "node": "intent",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    try:
        last_message: str = state["messages"][-1].content
        profile_summary = {
            k: v for k, v in state.get("voter_profile", {}).items()
            if k in ("current_state", "registration_type", "epic_number")
        }

        # ── Try Gemini Flash ──────────────────────────────────────────────────
        if settings.gcp_project_id:
            try:
                from langchain_core.messages import HumanMessage, SystemMessage
                llm = _get_llm()
                response = await llm.ainvoke([
                    SystemMessage(content=_SYSTEM_PROMPT),
                    HumanMessage(content=(
                        f"User message: {last_message}\n"
                        f"Known profile: {json.dumps(profile_summary)}"
                    )),
                ])
                raw = response.content.strip()
                # Strip any accidental markdown fences
                raw = re.sub(r"```(?:json)?|```", "", raw).strip()
                parsed = json.loads(raw)
                intent: str = parsed.get("intent", "unknown")
                confidence: float = float(parsed.get("confidence", 0.5))
                trace["method"] = "gemini_flash"
                logger.debug("Gemini intent: %s (%.2f)", intent, confidence)

            except Exception as llm_exc:
                logger.warning("Gemini intent failed, using keyword fallback: %s", llm_exc)
                intent, confidence = _keyword_classify(last_message)
                trace["method"] = "keyword_fallback"
                trace["llm_error"] = str(llm_exc)
        else:
            intent, confidence = _keyword_classify(last_message)
            trace["method"] = "keyword_fallback"
            logger.debug("GCP not configured — keyword intent: %s", intent)

        trace.update({"intent": intent, "confidence": confidence, "status": "ok"})
        return {
            **state,
            "intent": intent,
            "confidence_score": confidence,
            "agent_trace": state.get("agent_trace", []) + [trace],
            "error": None,
        }

    except Exception as exc:
        logger.exception("Intent node error: %s", exc)
        trace.update({"status": "error", "error": str(exc)})
        return {
            **state,
            "intent": "unknown",
            "agent_trace": state.get("agent_trace", []) + [trace],
            "error": f"Intent classification failed: {exc}",
        }