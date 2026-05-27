"""
translation.py — LangGraph translation node

Runs at the end of the agent graph when the user's preferred language
is NOT English. Translates the English response into the target language
using Sarvam AI (via translator_service).

AgentState keys consumed:
  - state["final_response"]    : str  — English text set by the synthesis node
  - state["response_language"] : str  — target language short-code (e.g. "hi")

AgentState keys produced:
  - state["final_response"]    : str  — translated (or original) text

If translation fails the English text is used verbatim — translation is
best-effort and must never block the pipeline.
"""

import logging
from ..state import AgentState
from ...services.translator import translator_service

logger = logging.getLogger(__name__)


async def translation_node(state: AgentState) -> AgentState:
    """
    Translate the synthesis output into the user's preferred language.
    Returns updated state with `final_response` set.
    """
    # AgentState uses "final_response" (set by synthesis node)
    english_text: str = state.get("final_response") or ""

    # AgentState uses "response_language", not "preferred_language"
    target_lang: str = state.get("response_language") or "en"

    # Skip API call entirely for English
    if not target_lang or target_lang.lower() in ("en", "en-in", "english"):
        logger.debug("Translation node: skipping — target language is English")
        return {**state, "final_response": english_text}

    if not english_text:
        logger.warning("Translation node: final_response is empty — nothing to translate")
        return state

    logger.info(
        "Translation node: translating %d chars to %s",
        len(english_text),
        target_lang,
    )

    translated = await translator_service.translate(
        text=english_text,
        target_language=target_lang,
        source_language="en",
    )

    if translated == english_text:
        logger.warning(
            "Translation node: output unchanged — possible Sarvam API failure for lang=%s",
            target_lang,
        )

    return {**state, "final_response": translated}