"""
chat.py — Main chat endpoint

Complete implementation with:
  - Session persistence (Firestore load/save)
  - Multi-turn conversation history
  - EPIC number encryption before Firestore write
  - SSE streaming
"""

import asyncio
import json
import logging
import re
from datetime import datetime, timezone
from typing import AsyncGenerator

import bleach
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, HumanMessage
from pydantic import BaseModel, field_validator

from ..middleware.auth import verify_firebase_token
from ..middleware.rate_limit import check_rate_limit
from ...agents.graph import agent_graph
from ...agents.state import AgentState
from ...services.encryption import encryption_service

logger = logging.getLogger(__name__)
router  = APIRouter()

_MAX_HISTORY_TURNS = 4

_INJECTION_PATTERNS = [
    "ignore previous instructions", "you are now", "act as if",
    "disregard your", "system prompt", "jailbreak",
    "pretend you", "forget your instructions",
]


# ── Request model ─────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    session_id: str
    message:    str
    language:   str = "en"

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, v: str) -> str:
        if not re.match(r'^[a-zA-Z0-9_\-]{8,60}$', v):
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


# ── EPIC encryption helpers ───────────────────────────────────────────────────

def _encrypt_profile_epic(profile: dict) -> dict:
    """Encrypt EPIC number before Firestore write. Skips if already encrypted."""
    epic = profile.get("epic_number", "")
    if not epic or len(epic) > 20:  # Fernet tokens are ~180 chars; raw EPICs <= 12
        return profile
    try:
        return {**profile, "epic_number": encryption_service.encrypt(epic)}
    except Exception as exc:
        logger.warning("EPIC encryption failed, omitting from profile: %s", exc)
        return {k: v for k, v in profile.items() if k != "epic_number"}


def _decrypt_profile_epic(profile: dict) -> dict:
    """Decrypt EPIC number after Firestore read. Falls back gracefully."""
    epic = profile.get("epic_number", "")
    if not epic or len(epic) <= 20:  # Short = raw (unencrypted legacy session)
        return profile
    try:
        decrypted = encryption_service.decrypt(epic)
        if decrypted:
            return {**profile, "epic_number": decrypted}
    except Exception:
        pass
    return profile


# ── Firestore session helpers ─────────────────────────────────────────────────

async def _load_session(session_id: str) -> tuple[dict, list[dict]]:
    """
    Load voter profile + conversation history from Firestore.
    Returns (voter_profile, conversation_history).
    History is capped at _MAX_HISTORY_TURNS * 2 messages.
    """
    try:
        import firebase_admin  # noqa
        from firebase_admin import firestore

        db = firestore.client()

        def _sync_load():
            doc = db.collection("sessions").document(session_id).get()
            if not doc.exists:
                return {}, []
            data    = doc.to_dict()
            profile = data.get("voterProfile", {})
            history = data.get("conversationHistory", [])
            return profile, history[-(  _MAX_HISTORY_TURNS * 2):]

        loop = asyncio.get_event_loop()
        profile, history = await loop.run_in_executor(None, _sync_load)
        return _decrypt_profile_epic(profile), history

    except Exception as exc:
        logger.debug("Session load failed for %s: %s", session_id[-8:], exc)
        return {}, []


async def _save_session(
    session_id: str,
    voter_profile: dict,
    human_message: str,
    bot_message: str,
    language: str,
) -> None:
    """Persist updated profile + new message pair to Firestore."""
    try:
        import firebase_admin  # noqa
        from firebase_admin import firestore

        db  = firestore.client()
        now = datetime.now(timezone.utc).isoformat()

        new_messages = [
            {"role": "user",      "content": human_message, "timestamp": now, "language": language},
            {"role": "assistant", "content": bot_message,   "timestamp": now, "language": language},
        ]

        encrypted_profile = _encrypt_profile_epic(voter_profile)

        def _sync_save():
            ref = db.collection("sessions").document(session_id)
            ref.set(
                {
                    "voterProfile":        encrypted_profile,
                    "lastUpdated":         now,
                    "lastLanguage":        language,
                    "conversationHistory": firestore.ArrayUnion(new_messages),
                },
                merge=True,
            )

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _sync_save)
        logger.debug("Session saved for %s", session_id[-8:])

    except Exception as exc:
        logger.warning("Session save failed for %s: %s", session_id[-8:], exc)


# ── SSE streaming generator ───────────────────────────────────────────────────

async def _run_and_stream(
    session_id: str,
    message: str,
    language: str,
) -> AsyncGenerator[str, None]:
    full_response = ""
    try:
        voter_profile, history = await _load_session(session_id)

        # Build LangChain message list including conversation history
        history_messages = []
        for turn in history:
            role    = turn.get("role", "user")
            content = turn.get("content", "")
            if content:
                history_messages.append(
                    HumanMessage(content=content) if role == "user"
                    else AIMessage(content=content)
                )

        initial_state = AgentState(
            messages=[*history_messages, HumanMessage(content=message)],
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

        logger.info(
            "Agent graph — session=%s turns=%d lang=%s",
            session_id[-8:], len(history) // 2, language,
        )
        result: AgentState = await agent_graph.ainvoke(initial_state)

        final_response: str = result.get("final_response") or ""
        confidence: float   = result.get("confidence_score", 0.5)
        source_chunks: list = result.get("retrieved_chunks", [])
        agent_trace: list   = result.get("agent_trace", [])
        updated_profile     = result.get("voter_profile", voter_profile)

        if result.get("requires_escalation"):
            final_response = (
                "⚠️ My confidence is below the verified threshold. "
                "Please confirm with official sources.\n\n"
                + final_response
                + "\n\n📞 **National Voter Helpline: 1950** (toll-free)"
            )

        full_response = final_response

        words = final_response.split(" ")
        for i, word in enumerate(words):
            yield f"data: {json.dumps({'type': 'token', 'content': word + (' ' if i < len(words) - 1 else '')})}\n\n"
            await asyncio.sleep(0.022)

        serialisable_chunks = [
            {
                "chunk_id":   c.get("chunk_id", ""),
                "text":       c.get("text", "")[:300],
                "confidence": c.get("confidence", 0.0),
                "source_url": c.get("source_url", ""),
                "form_type":  c.get("form_type", ""),
                "section":    c.get("section", ""),
            }
            for c in source_chunks if isinstance(c, dict)
        ]

        yield f"data: {json.dumps({'type': 'done', 'confidence': round(confidence, 3), 'source_chunks': serialisable_chunks, 'agent_trace': agent_trace})}\n\n"
        yield "data: [DONE]\n\n"

        await _save_session(session_id, updated_profile, message, full_response, language)

    except Exception as exc:
        logger.exception("Agent pipeline error for session %s: %s", session_id[-8:], exc)
        yield f"data: {json.dumps({'type': 'error', 'error': 'Something went wrong. Please try again or call 1950.'})}\n\n"
        yield "data: [DONE]\n\n"


# ── Route ─────────────────────────────────────────────────────────────────────

@router.post("/chat")
async def chat(
    raw_request: Request,
    request: ChatRequest,
    uid: str = Depends(verify_firebase_token),
):
    await check_rate_limit(raw_request, uid)
    return StreamingResponse(
        _run_and_stream(request.session_id, request.message, request.language),
        media_type="text/event-stream",
        headers={
            "Cache-Control":     "no-cache",
            "Connection":        "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )