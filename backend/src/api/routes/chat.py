from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, constr, validator
import bleach
import json
import asyncio
from typing import AsyncGenerator
from datetime import datetime
import logging

from ..middleware.auth import verify_firebase_token
from ..middleware.rate_limit import check_rate_limit
from ..config.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter()


class ChatRequest(BaseModel):
    session_id: constr(pattern=r'^[a-zA-Z0-9_-]{10,50}$')
    message: constr(min_length=1, max_length=2000)
    language: str = "en"

    @validator('message')
    def sanitize_message(cls, v):
        """Sanitize user message to prevent injection attacks."""
        cleaned = bleach.clean(v, tags=[], strip=True)
        INJECTION_PATTERNS = [
            "ignore previous instructions",
            "you are now",
            "act as if",
            "disregard your",
            "system prompt",
            "jailbreak",
        ]
        for pattern in INJECTION_PATTERNS:
            if pattern.lower() in cleaned.lower():
                raise ValueError("Invalid input detected")
        return cleaned


async def stream_chat_response(
    session_id: str,
    message: str,
    language: str,
) -> AsyncGenerator[str, None]:
    """
    Stream chat response using SSE format.
    This is a placeholder - actual implementation will use LangGraph.
    """
    try:
        # Placeholder response - will be replaced with actual LangGraph implementation
        response_text = (
            "I understand you're asking about voter registration. "
            "To help you better, could you please tell me which state you're currently in?"
        )

        # Stream tokens
        for word in response_text.split():
            yield f"data: {json.dumps({'type': 'token', 'content': word + ' '})}\n\n"
            await asyncio.sleep(0.02)

        # Send done event
        yield f"data: {json.dumps({'type': 'done', 'confidence': 0.85, 'source_chunks': []})}\n\n"
        yield "data: [DONE]\n\n"

    except Exception as e:
        logger.error(f"Error in chat stream: {e}")
        yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
        yield "data: [DONE]\n\n"


@router.post("/chat")
async def chat(
    request: ChatRequest,
    uid: str = verify_firebase_token,
):
    """
    Main chat endpoint with SSE streaming.
    """
    try:
        # Check rate limit
        # await check_rate_limit(request, uid)

        # Return streaming response
        return StreamingResponse(
            stream_chat_response(
                session_id=request.session_id,
                message=request.message,
                language=request.language,
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )
