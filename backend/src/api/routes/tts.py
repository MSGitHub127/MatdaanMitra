"""
tts.py — Text-to-Speech proxy route

Accepts a text + language from the frontend, calls Sarvam AI TTS,
and returns base64-encoded WAV audio. The frontend plays this directly
via the HTML5 Audio API — no file storage required.

Rate-limited to 20 req/min per user (enforced by the Redis middleware).
"""

import logging
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from ..middleware.auth import verify_firebase_token
from ...services.translator import translator_service

logger = logging.getLogger(__name__)

router = APIRouter()

SUPPORTED_LANGS = {
    "en", "hi", "mr", "ta", "te", "bn", "kn", "gu", "ml", "pa", "od",
}


class TTSRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=600)
    language: str = Field(default="en", min_length=2, max_length=8)


class TTSResponse(BaseModel):
    audio_b64: str
    language:  str
    chars:     int


@router.post("/tts", response_model=TTSResponse)
async def synthesize_speech(
    request: TTSRequest,
    uid: str = verify_firebase_token,
):
    """
    Convert text to speech using Sarvam AI (bulbul:v1 model).

    Returns a base64-encoded WAV string which the frontend decodes
    and plays directly via:
        const bytes = Uint8Array.from(atob(audio_b64), c => c.charCodeAt(0));
        const blob  = new Blob([bytes], { type: 'audio/wav' });
        new Audio(URL.createObjectURL(blob)).play();
    """
    lang = request.language.lower().split("-")[0]  # normalise "hi-IN" → "hi"

    if lang not in SUPPORTED_LANGS:
        logger.warning("TTS: unsupported language '%s' — falling back to 'en'", lang)
        lang = "en"

    audio_b64 = await translator_service.synthesize_speech(
        text=request.text,
        language=lang,
    )

    if not audio_b64:
        logger.error("TTS: Sarvam returned no audio for lang=%s", lang)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Speech synthesis is temporarily unavailable. "
                "Please try again in a moment."
            ),
        )

    return TTSResponse(
        audio_b64=audio_b64,
        language=lang,
        chars=len(request.text),
    )