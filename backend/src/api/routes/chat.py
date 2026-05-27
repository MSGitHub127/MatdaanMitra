"""
chat.py — Main chat endpoint

Replaces the placeholder stream_chat_response with a real pipeline:
  1. Load voter profile from Firestore (for context continuity)
  2. Build LangGraph AgentState from the request
  3. Run the full agent graph (intent → profile → RAG/live → synthesis → guardrail → translate)
  4. Stream the final_response word-by-word over SSE
  5. Send a `done` event with confidence, source_chunks, and agent_trace

The SSE format is:
  data: {"type": "token",  "content": "word "}
  data: {"type": "done",   "confidence": 0.91, "source_chunks": [...], "agent_trace": [...]}
  data: [DONE]
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import AsyncGenerator

import bleach
from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, field_validator

from ..middleware.auth import verify_firebase_token
from ..middleware.rate_limit import check_rate_limit
from ...agents.graph import agent_graph
from ...agents.state import AgentState

logger = logging.getLogger(__name__)
router = APIRouter()

_INJECTION_PATTERNS = [
    "ignore previous instructions",
    "you are now",
    "act as if",
    "disregard your",
    "system prompt",
    "jailbreak",
    "pretend you",
    "forget your instructions",
]


# ── Request model ─────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    session_id: str
    message:    str
    language:   str = "en"

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, v: str) -> str:
        import re
        if not re.match(r'^[a-zA-Z0-9_-]{10,50}$', v):
            raise ValueError("Invalid session_id format")
        return v

    @field_validator("message")
    @classmethod
    def sanitize_message(cls, v: str) -> str:
        cleaned = bleach.clean(v.strip(), tags=[], strip=True)
        if not cleaned:
            raise ValueError("Message cannot be empty")
        if len(cleaned) > 2000:
            raise ValueError("Message too long (max 2000 characters)")
        for pattern in _INJECTION_PATTERNS:
            if pattern.lower() in cleaned.lower():
                raise ValueError("Invalid input detected")
        return cleaned


# ── Firestore profile loader ──────────────────────────────────────────────────

async def _load_voter_profile(session_id: str) -> dict:
    """
    Fetch the voter profile stored in Firestore under sessions/{session_id}.
    Returns an empty dict if Firestore is unavailable or the session is new.
    """
    try:
        import asyncio
        import firebase_admin  # noqa: F401 — ensures app is initialised
        from firebase_admin import firestore

        db = firebase_admin.firestore.client()

        def _sync_fetch():
            doc = db.collection("sessions").document(session_id).get()
            if doc.exists:
                return doc.to_dict().get("voterProfile", {})
            return {}

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _sync_fetch)

    except Exception as exc:
        logger.debug("Could not load voter profile for session %s: %s", session_id, exc)
        return {}


# ── SSE streaming generator ───────────────────────────────────────────────────

async def _run_and_stream(
    session_id: str,
    message: str,
    language: str,
) -> AsyncGenerator[str, None]:
    """
    Runs the LangGraph agent and streams the response as SSE events.
    Always yields at least a `done` event — never hangs silently.
    """
    try:
        # 1. Load session context
        voter_profile = await _load_voter_profile(session_id)

        # 2. Build initial AgentState
        initial_state = AgentState(
            messages=[HumanMessage(content=message)],
            session_id=session_id,
            voter_profile=voter_profile,
            intent=None,
            retrieved_chunks=[],
            live_data=None,
            final_response=None,
            response_language=language,
            confidence_score=0.0,
            agent_trace=[],
            requires_escalation=False,
            error=None,
        )

        # 3. Run the full graph
        logger.info(
            "Running agent graph — session=%s lang=%s",
            session_id[-8:], language,
        )
        result: AgentState = await agent_graph.ainvoke(initial_state)

        final_response: str    = result.get("final_response") or ""
        confidence: float      = result.get("confidence_score", 0.5)
        source_chunks: list    = result.get("retrieved_chunks", [])
        agent_trace: list      = result.get("agent_trace", [])
        requires_escalation    = result.get("requires_escalation", False)

        # Escalation: prepend helpline reminder
        if requires_escalation:
            final_response = (
                "⚠️ My confidence in this answer is below the verified threshold. "
                "Please confirm with official sources.\n\n"
                + final_response
                + "\n\n📞 **National Voter Helpline: 1950** (toll-free)"
            )

        # 4. Stream response tokens
        words = final_response.split(" ")
        for i, word in enumerate(words):
            content = word + (" " if i < len(words) - 1 else "")
            yield f"data: {json.dumps({'type': 'token', 'content': content})}\n\n"
            await asyncio.sleep(0.022)  # ~45 words/sec — natural reading pace

        # 5. Done event — serialise only what the frontend needs
        serialisable_chunks = [
            {
                "chunk_id":   c.get("chunk_id", ""),
                "text":       c.get("text", "")[:300],  # truncate for payload size
                "confidence": c.get("confidence", 0.0),
                "source_url": c.get("source_url", ""),
                "form_type":  c.get("form_type", ""),
                "section":    c.get("section", ""),
            }
            for c in source_chunks
            if isinstance(c, dict)
        ]

        yield f"data: {json.dumps({'type': 'done', 'confidence': round(confidence, 3), 'source_chunks': serialisable_chunks, 'agent_trace': agent_trace})}\n\n"
        yield "data: [DONE]\n\n"

    except Exception as exc:
        logger.exception("Agent pipeline error for session %s: %s", session_id[-8:], exc)
        yield f"data: {json.dumps({'type': 'error', 'error': 'Something went wrong. Please try again or call 1950.'})}\n\n"
        yield "data: [DONE]\n\n"


# ── Route ─────────────────────────────────────────────────────────────────────

@router.post("/chat")
async def chat(
    raw_request: Request,
    request: ChatRequest,
    uid: str = verify_firebase_token,
):
    """
    Main chat endpoint — streams SSE tokens from the LangGraph agent.
    Rate-limited to 30 req/min per user via Redis.
    """
    # Per-user rate limiting (30 req/min)
    await check_rate_limit(raw_request, uid)

    return StreamingResponse(
        _run_and_stream(
            session_id=request.session_id,
            message=request.message,
            language=request.language,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control":    "no-cache",
            "Connection":       "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )