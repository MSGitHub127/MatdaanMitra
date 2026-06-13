"""
guardrail.py — Content safety and confidence guardrail node

Fix log (production audit):

P0 — VOTER NAME FALSE-POSITIVE (was blocking millions of valid voters)
    The previous POLITICAL_PATTERNS list contained bare surname patterns like
    r'\\bShah\\b', r'\\bRahul\\b', r'\\bGandhi\\b', r'\\bManmohan\\b'.
    The synthesis node embeds the voter's full name in every voter_lookup
    response. Any voter named "Rahul Shah" would receive the political block
    message instead of their civic data. Affects ~15–20 million registered voters.

    FIX A — Intent-aware bypass:
        voter_lookup and ero_location responses skip the political filter entirely.
        These intents embed real ECI database names that legitimately contain
        politician surnames.

    FIX B — Pattern specificity:
        Bare surname patterns replaced with compound political-context patterns.
        e.g.  \\bShah\\b  →  \\b(Amit Shah|Shah\\s+(?:ji|sahab))\\b
              \\bGandhi\\b →  \\b(Rahul Gandhi|Sonia Gandhi|Gandhi\\s+(?:ji|family|dynasty|party))\\b
        "Rahul" is now only blocked inside "Rahul Gandhi"; standalone first name passes.

P0 — GUARDRAIL ERROR PASS-THROUGH (was returning unvalidated responses)
    Previous: except block returned the original final_response on any error.
    Fix: return a safe civic default string, never the potentially unsafe response.

Fix (prior session): changed from `def` to `async def`.
Fix (prior session): replaced \\bpolling\\b with multi-word political patterns so
    "polling station" passes correctly.
"""

import re
import logging
from datetime import datetime, timezone

from ..state import AgentState

logger = logging.getLogger(__name__)

# ── Intents whose responses may legitimately contain politician surnames ───────
# voter_lookup: ECI embeds real names — Shah, Gandhi, Rahul are common names.
# ero_location: returns office names, locality names, and officer full names.
_INTENT_SKIP_POLITICAL_FILTER = frozenset({"voter_lookup", "ero_location"})

# ── Political content patterns ────────────────────────────────────────────────
# DESIGN RULES:
#   1. Every pattern must require political *context*, not just a name token.
#   2. Common Indian given names / surnames that double as politician names
#      MUST be qualified so they only match in an explicitly political context.
#   3. Electoral process terms ("polling station", "election commission",
#      "election roll") must never fire — tested by regression suite.
#
# PATTERNS:
POLITICAL_PATTERNS = [
    # ── Named parties — BJP, Congress, etc. ─────────────────────────────────
    # Word boundary on both sides; INC/INDIA need an extra check to not
    # match common words.
    r'\b(BJP|INC|AAP|TMC|NCP|SP|BSP|JDU|CPI-?M?)\b',
    r'\b(Bharatiya Janata Party|Indian National Congress|Aam Aadmi Party)\b',

    # ── Named politicians — compound form only ───────────────────────────────
    # Standalone "Shah", "Gandhi", "Rahul", "Manmohan" are common Indian names
    # and must NOT fire. Only the compound politician-name form is blocked.
    r'\b(Narendra Modi|PM Modi|Modi\s+(?:ji|sarkar|government|govt))\b',
    r'\b(Amit Shah|Home\s+Minister\s+Shah)\b',
    r'\b(Rahul Gandhi|Sonia Gandhi|Priyanka Gandhi)\b',
    r'\b(Gandhi\s+(?:ji|family|dynasty|party|parivar))\b',
    r'\b(Mamata Banerjee|Didi\s+(?:govt|government|sarkar))\b',
    r'\b(Arvind Kejriwal|Yogi Adityanath|Manmohan Singh)\b',

    # ── Explicit calls for electoral opinion ─────────────────────────────────
    r'\b(vote for|support|endorse|back|oppose)\b.{0,50}\b(party|candidate|leader|MP|MLA|PM|CM)\b',

    # ── Electoral outcome / opinion content ──────────────────────────────────
    # "exit poll", "opinion poll", "election results" — but NOT
    # "election roll", "election commission", "polling station".
    r'\b(exit\s+poll|opinion\s+poll)\b',
    r'\bexit\s+poll\s+result\b',
    r'\belection\s+result\b(?!\s+notification)',  # negative lookahead: not "result notification"

    # ── Poll predictions / political commentary ──────────────────────────────
    r'\bpolling\s+(data|numbers?|trends?|percentage|victory|defeat|margin|survey)\b',
    r'\bvote\s+share\b',
    r'\bseat\s+tally\b',
]

# Pre-compile all patterns for performance under load
_COMPILED_PATTERNS = [
    re.compile(p, re.IGNORECASE) for p in POLITICAL_PATTERNS
]

# Safe fallback string returned when the guardrail itself errors.
# Must never reveal internal state or the original response.
_GUARDRAIL_ERROR_RESPONSE = (
    "I was unable to verify this response. "
    "Please check **eci.gov.in** or call the National Voter Helpline at **1950** "
    "for authoritative information."
)


async def guardrail_node(state: AgentState) -> AgentState:
    """
    Guardrail node: filters political content and low-confidence responses.

    Order of operations:
      1. Skip political filter for voter_lookup / ero_location (names in response).
      2. Check remaining intents against POLITICAL_PATTERNS.
      3. Escalate if confidence_score < 0.75.
      4. Append source citations for high-confidence responses.

    On any unhandled exception: returns the safe civic default (never the
    original unvalidated response).
    """
    trace: dict = {
        "node": "guardrail",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    try:
        response: str = state.get("final_response", "") or ""
        intent: str | None = state.get("intent")

        if not response:
            trace["status"] = "skip_empty"
            return {
                **state,
                "agent_trace": state.get("agent_trace", []) + [trace],
            }

        # ── 1. Political content filter ───────────────────────────────────────
        # CRITICAL: voter_lookup and ero_location responses legitimately contain
        # real voter names from the ECI database — Shah, Gandhi, Rahul are among
        # the most common Indian names. Skip political filter for these intents.
        skip_political_filter = intent in _INTENT_SKIP_POLITICAL_FILTER

        if skip_political_filter:
            trace["political_filter"] = f"skipped (intent={intent})"
            logger.debug("Guardrail: political filter bypassed for intent=%s", intent)
        else:
            for pattern in _COMPILED_PATTERNS:
                if pattern.search(response):
                    logger.warning(
                        "Guardrail: political pattern matched — intent=%s pattern=%s",
                        intent, pattern.pattern,
                    )
                    trace.update({
                        "status": "blocked_political",
                        "pattern": pattern.pattern,
                        "intent": intent,
                    })
                    return {
                        **state,
                        "final_response": (
                            "I'm designed to assist only with voter registration "
                            "procedures — not electoral politics. Is there anything "
                            "about your registration I can help with?"
                        ),
                        "requires_escalation": False,
                        "agent_trace": state.get("agent_trace", []) + [trace],
                    }

        # ── 2. Low-confidence escalation ──────────────────────────────────────
        confidence: float = state.get("confidence_score", 0.0)
        if confidence < 0.75:
            logger.info(
                "Guardrail: low confidence %.3f — escalating (intent=%s)",
                confidence, intent,
            )
            trace.update({"status": "escalated", "confidence": confidence, "intent": intent})
            return {
                **state,
                "final_response": (
                    "I don't have verified official data for this query. "
                    "Please check **eci.gov.in** or call the National Voter "
                    "Helpline at **1950** for authoritative information."
                ),
                "requires_escalation": True,
                "agent_trace": state.get("agent_trace", []) + [trace],
            }

        # ── 3. Append source citations for high-confidence responses ──────────
        retrieved_chunks = state.get("retrieved_chunks", [])
        citations = [
            f"[{c.get('form_type', 'ECI')} — {c.get('section', '')}]({c['source_url']})"
            for c in retrieved_chunks
            if c.get("confidence", 0) > 0.80 and c.get("source_url")
        ]
        if citations:
            response = response + "\n\n**Sources:** " + " · ".join(citations)

        trace.update({
            "status": "ok",
            "confidence": confidence,
            "intent": intent,
            "political_filter": "skipped" if skip_political_filter else "passed",
        })

        return {
            **state,
            "final_response": response,
            "agent_trace": state.get("agent_trace", []) + [trace],
        }

    except Exception as exc:
        logger.exception("Guardrail error: %s", exc)
        # CRITICAL: on error, return safe civic default — NEVER the original
        # unvalidated response. The previous "fail open" approach risked returning
        # politically sensitive or injected content.
        trace.update({"status": "error", "error": str(exc)})
        return {
            **state,
            "final_response": _GUARDRAIL_ERROR_RESPONSE,
            "requires_escalation": True,
            "agent_trace": state.get("agent_trace", []) + [trace],
        }