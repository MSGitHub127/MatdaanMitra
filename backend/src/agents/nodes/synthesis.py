"""
synthesis.py — Response synthesis node

Primary:  Gemini 1.5 Pro via langchain_google_vertexai.
          Receives the retrieved chunks, live data, and voter profile,
          then generates a grounded, helpful response.

Fallback: Assembles a structured answer directly from retrieved chunk text
          when Vertex AI is unavailable.

Output state keys:
  final_response  — the synthesized English text (translated later if needed)
  confidence_score — derived from chunk scores or LLM self-reported confidence
  agent_trace     — appended entry
"""

import json
import logging
from datetime import datetime, timezone

from ..state import AgentState
from ...config.settings import settings

logger = logging.getLogger(__name__)

# ── Lazy LLM init ─────────────────────────────────────────────────────────────

_llm = None


def _get_llm():
    global _llm
    if _llm is None:
        from langchain_google_vertexai import ChatVertexAI
        _llm = ChatVertexAI(
            model_name="gemini-1.5-pro-001",
            project=settings.gcp_project_id,
            location=settings.gcp_location,
            temperature=0.25,
            max_output_tokens=1500,
        )
    return _llm


# ── System prompt ─────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """You are Matdaan Mitra, an expert voter registration assistant for Indian elections.
Your answers are grounded exclusively in official ECI (Election Commission of India) guidelines.

Rules:
1. Answer ONLY from the provided source chunks. Do not hallucinate.
2. Use **bold** for form names, document names, and key terms.
3. Keep answers clear, concise, and practical — the user may be a first-time voter.
4. If the source chunks don't contain enough information, say so and direct the user to eci.gov.in or helpline 1950.
5. NEVER mention political parties, candidates, or express political opinions.
6. Format lists with dashes when helpful. Keep paragraphs short."""


def _build_user_prompt(
    message: str,
    chunks: list,
    profile: dict,
    live_data: dict | None,
) -> str:
    chunks_text = "\n\n".join(
        f"[Source {i+1} — {c.get('form_type','ECI')} · {c.get('section','')}]\n{c.get('text','')}"
        for i, c in enumerate(chunks)
    ) or "No retrieved chunks — use general ECI knowledge."

    live_text = ""
    if live_data:
        if live_data.get("voter_status"):
            vs = live_data["voter_status"]
            live_text = (
                f"\nLive ECI data: Voter found — {vs.get('name','')}, "
                f"Assembly: {vs.get('assembly_constituency','')}, "
                f"Polling station: {vs.get('polling_station','')}."
            )
        elif live_data.get("ero_office"):
            ero = live_data["ero_office"]
            live_text = (
                f"\nLive ERO data: {ero.get('name','ERO Office')}, "
                f"Address: {ero.get('address','')}, "
                f"Distance: {ero.get('distance_km','')} km."
            )
        elif live_data.get("found") is False:
            live_text = "\nLive lookup: No matching record found in ECI database."

    profile_text = ""
    if profile:
        parts = []
        if profile.get("current_state"):
            parts.append(f"State: {profile['current_state']}")
        if profile.get("registration_type"):
            parts.append(f"Registration type: {profile['registration_type']}")
        if parts:
            profile_text = f"\nVoter context: {', '.join(parts)}."

    return (
        f"User question: {message}\n"
        f"{profile_text}"
        f"{live_text}\n\n"
        f"Source chunks:\n{chunks_text}\n\n"
        "Provide a helpful, grounded answer:"
    )


# ── Template fallback ─────────────────────────────────────────────────────────

def _template_response(
    chunks: list,
    live_data: dict | None,
    intent: str | None,
) -> tuple[str, float]:
    """Builds a response directly from chunks when LLM is unavailable."""

    if live_data and live_data.get("voter_status"):
        vs = live_data["voter_status"]
        if vs.get("name"):
            return (
                f"✅ **Voter found on electoral roll**\n\n"
                f"**Name:** {vs.get('name')}\n"
                f"**Assembly Constituency:** {vs.get('assembly_constituency','—')}\n"
                f"**Polling Station:** {vs.get('polling_station','—')}\n"
                f"**Status:** {vs.get('status','active').title()}\n\n"
                "For full details, visit voters.eci.gov.in or call **1950**."
            ), 0.88

    if live_data and live_data.get("ero_office"):
        ero = live_data["ero_office"]
        return (
            f"📍 **Nearest ERO Office**\n\n"
            f"**{ero.get('name','Electoral Registration Officer')}**\n"
            f"{ero.get('address','')}\n"
            f"📞 {ero.get('phone','1950')}  ·  {ero.get('distance_km','')} km away\n\n"
            f"[Get Directions]({ero.get('directions_url','https://eci.gov.in')})"
        ), 0.85

    if live_data and live_data.get("found") is False:
        reason = live_data.get("reason", "")
        if "epic" in reason:
            return (
                "I couldn't find your EPIC number in your message. "
                "Please share your **EPIC number** (e.g., MH0123456) "
                "and I'll look up your voter status."
            ), 0.70
        if "pincode" in reason:
            return (
                "Please share your **6-digit pincode** and I'll find "
                "the nearest Electoral Registration Officer office for you."
            ), 0.70
        return (
            "No matching record was found. Please verify your details "
            "at voters.eci.gov.in or call the helpline at **1950**."
        ), 0.65

    if chunks:
        # Concatenate top chunks
        text_parts = [c.get("text", "") for c in chunks[:2] if c.get("text")]
        if text_parts:
            avg_conf = sum(c.get("confidence", 0.8) for c in chunks[:2]) / len(chunks[:2])
            return "\n\n".join(text_parts), round(avg_conf, 3)

    # ── Intent-specific fallbacks when no chunks are available ────────────────
    if intent == "profile_collection":
        return (
            "To help you with voter registration, I need a few details:\n\n"
            "- **Which state** are you currently residing in?\n"
            "- **What is your 6-digit pincode?**\n"
            "- Are you registering for the **first time**, or do you need to update "
            "an existing registration (correction / change of address)?\n\n"
            "You can also share your **EPIC number** if you already have one."
        ), 0.80

    if intent in ("unknown", "off_topic"):
        return (
            "I'm Matdaan Mitra — your voter registration assistant. I can help you with:\n\n"
            "- **New voter registration** (Form 6)\n"
            "- **Updating your details** — name, address, photo (Form 8 / 8A)\n"
            "- **Finding your nearest ERO office**\n"
            "- **Checking your EPIC / voter status**\n"
            "- **Filing a grievance** if your name is missing or incorrect\n\n"
            "What would you like help with today?"
        ), 0.80

    return (
        "I don't have specific verified information for that query. "
        "Please check **eci.gov.in** or call the National Voter Helpline at **1950** "
        "for authoritative guidance."
    ), 0.40


# ── Node ──────────────────────────────────────────────────────────────────────

async def synthesis_node(state: AgentState) -> AgentState:
    trace: dict = {
        "node": "synthesis",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    try:
        last_message: str  = state["messages"][-1].content
        chunks: list       = state.get("retrieved_chunks", [])
        profile: dict      = state.get("voter_profile", {})
        live_data: dict | None = state.get("live_data")
        intent: str | None = state.get("intent")

        response_text = ""
        confidence    = 0.5

        # ── Try Gemini Pro ────────────────────────────────────────────────────
        if settings.gcp_project_id:
            try:
                from langchain_core.messages import HumanMessage, SystemMessage
                llm = _get_llm()

                result = await llm.ainvoke([
                    SystemMessage(content=_SYSTEM_PROMPT),
                    HumanMessage(content=_build_user_prompt(
                        last_message, chunks, profile, live_data
                    )),
                ])

                response_text = result.content.strip()
                # Derive confidence from chunk quality
                if chunks:
                    confidence = round(
                        sum(c.get("confidence", 0.8) for c in chunks) / len(chunks), 3
                    )
                else:
                    confidence = 0.75

                trace["method"] = "gemini_pro"
                trace["input_tokens"] = (
                    len(last_message)
                    + sum(len(c.get("text", "")) for c in chunks)
                )

            except Exception as llm_exc:
                logger.warning("Gemini synthesis failed, using template fallback: %s", llm_exc)
                response_text, confidence = _template_response(chunks, live_data, intent)
                trace["method"] = "template_fallback"
                trace["llm_error"] = str(llm_exc)
        else:
            response_text, confidence = _template_response(chunks, live_data, intent)
            trace["method"] = "template_fallback"
            logger.debug("GCP not configured — using template synthesis")

        trace.update({"status": "ok"})

        return {
            **state,
            "final_response": response_text,
            "confidence_score": confidence,
            "agent_trace": state.get("agent_trace", []) + [trace],
            "error": None,
        }

    except Exception as exc:
        logger.exception("Synthesis error: %s", exc)
        trace.update({"status": "error", "error": str(exc)})
        return {
            **state,
            "final_response": (
                "I encountered an error processing your request. "
                "Please try again, or call the voter helpline at **1950**."
            ),
            "confidence_score": 0.0,
            "agent_trace": state.get("agent_trace", []) + [trace],
            "error": f"Synthesis failed: {exc}",
        }