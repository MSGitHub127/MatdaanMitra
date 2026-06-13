"""
translator.py — Language services via Sarvam AI

Replaces the previous Google Cloud Translation implementation.
Handles:
  - Text translation (Sarvam /translate endpoint)
  - Text-to-speech synthesis (Sarvam /text-to-speech endpoint)

Sarvam AI language codes use the BCP-47 + IN region format:
  en-IN, hi-IN, mr-IN, ta-IN, te-IN, bn-IN, kn-IN, gu-IN, ml-IN, pa-IN, od-IN

Docs: https://docs.sarvam.ai
"""

import base64
import logging
from typing import Optional

import httpx

from ..config.settings import settings

logger = logging.getLogger(__name__)

SARVAM_BASE = "https://api.sarvam.ai"
TRANSLATE_URL = f"{SARVAM_BASE}/translate"
TTS_URL       = f"{SARVAM_BASE}/text-to-speech"

# Short-code → Sarvam BCP-47 code
LANG_MAP: dict[str, str] = {
    "en": "en-IN",
    "hi": "hi-IN",
    "mr": "mr-IN",
    "ta": "ta-IN",
    "te": "te-IN",
    "bn": "bn-IN",
    "kn": "kn-IN",
    "gu": "gu-IN",
    "ml": "ml-IN",
    "pa": "pa-IN",
    "od": "od-IN",
}

# A natural-sounding female speaker per language
TTS_SPEAKERS: dict[str, str] = {
    "hi-IN": "anushka",
    "mr-IN": "anushka",
    "ta-IN": "pavithra",
    "te-IN": "pavithra",
    "bn-IN": "anushka",
    "kn-IN": "anushka",
    "gu-IN": "anushka",
    "ml-IN": "anushka",
    "pa-IN": "anushka",
    "od-IN": "anushka",
    "en-IN": "anushka",
}

# Shared async client — pooled, reused across requests
_client: Optional[httpx.AsyncClient] = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            timeout=httpx.Timeout(connect=5.0, read=15.0, write=5.0, pool=5.0),
            headers={
                "api-subscription-key": settings.sarvam_api_key,
                "Content-Type": "application/json",
                "User-Agent": "MatdaanMitra/1.0",
            },
        )
    return _client


def _sarvam_code(lang_code: str) -> str:
    """Convert short language code to Sarvam BCP-47 code. Defaults to en-IN."""
    return LANG_MAP.get(lang_code.lower(), "en-IN")


class TranslatorService:
    """
    Sarvam AI — Translation and Text-to-Speech service.

    Both methods are async and share a single httpx.AsyncClient for
    connection pooling. They never raise — errors are logged and
    graceful fallbacks are returned so the LangGraph pipeline keeps running.
    """

    async def translate(
        self,
        text: str,
        target_language: str,
        source_language: str = "en",
    ) -> str:
        """
        Translate `text` from `source_language` → `target_language`.

        Returns the original `text` unchanged if:
          - target == source (no round-trip needed)
          - Sarvam API is unreachable
          - text is blank

        Args:
            text: The text to translate.
            target_language: Short code, e.g. "hi", "gu", "ta".
            source_language: Short code of the input language (default "en").

        Returns:
            Translated string, or the original text on failure.
        """
        if not text or not text.strip():
            return text

        src = _sarvam_code(source_language)
        tgt = _sarvam_code(target_language)

        if src == tgt:
            return text  # nothing to do

        try:
            client = _get_client()
            resp = await client.post(
                TRANSLATE_URL,
                json={
                    "input": text,
                    "source_language_code": src,
                    "target_language_code": tgt,
                    "speaker_gender": "Female",
                    "mode": "formal",
                    "model": "mayura:v1",
                    "enable_preprocessing": True,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            translated = data.get("translated_text", "").strip()

            if not translated:
                logger.warning(
                    "Sarvam translate returned empty result for lang=%s", target_language
                )
                return text

            logger.debug(
                "Translated %d chars from %s → %s", len(text), src, tgt
            )
            return translated

        except httpx.HTTPStatusError as exc:
            logger.error(
                "Sarvam translate HTTP %s for lang=%s: %s",
                exc.response.status_code, target_language, exc.response.text[:200],
            )
            return text
        except httpx.RequestError as exc:
            logger.error("Sarvam translate network error for lang=%s: %s", target_language, exc)
            return text
        except Exception as exc:  # noqa: BLE001
            logger.exception("Unexpected translate error for lang=%s: %s", target_language, exc)
            return text

    async def synthesize_speech(
        self,
        text: str,
        language: str = "en",
    ) -> Optional[str]:
        """
        Convert `text` to speech using Sarvam TTS.

        Returns a base64-encoded WAV string, or None on failure.
        The frontend decodes and plays this directly — no file storage required.

        Args:
            text: The text to speak. Sarvam supports up to ~500 chars per call.
            language: Short language code, e.g. "hi", "ta", "en".
        """
        if not text or not text.strip():
            return None

        lang_code = _sarvam_code(language)
        speaker   = TTS_SPEAKERS.get(lang_code, "anushka")

        # Sarvam TTS works best with chunks ≤ 500 chars
        chunk = text[:500]

        try:
            client = _get_client()
            resp = await client.post(
                TTS_URL,
                json={
                    "inputs": [chunk],
                    "target_language_code": lang_code,
                    "speaker": speaker,
                    "pitch": 0,
                    "pace": 1.05,
                    "loudness": 1.5,
                    "speech_sample_rate": 22050,
                    "enable_preprocessing": True,
                    "model": "bulbul:v2",
                },
            )
            resp.raise_for_status()
            data = resp.json()

            audios: list[str] = data.get("audios", [])
            if not audios:
                logger.warning("Sarvam TTS returned no audio for lang=%s", language)
                return None

            logger.debug("TTS synthesized %d chars in %s", len(chunk), lang_code)
            return audios[0]  # Already base64-encoded WAV

        except httpx.HTTPStatusError as exc:
            logger.error(
                "Sarvam TTS HTTP %s for lang=%s: %s",
                exc.response.status_code, language, exc.response.text[:200],
            )
            return None
        except httpx.RequestError as exc:
            logger.error("Sarvam TTS network error for lang=%s: %s", language, exc)
            return None
        except Exception as exc:  # noqa: BLE001
            logger.exception("Unexpected TTS error for lang=%s: %s", language, exc)
            return None


# Singleton — imported by translation node and TTS route
translator_service = TranslatorService()