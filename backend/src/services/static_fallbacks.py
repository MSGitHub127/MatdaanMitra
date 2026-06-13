"""
static_fallbacks.py — Resilient local fallbacks for MatdaanMitra

This module is the last line of defence when every external API is unreachable.
It provides three independent fallback layers, each with no network dependency:

Layer 1 — Static voter-registration guidance
    Curated ECI content covering all major form types, common documents,
    and grievance paths.  Returned by rag_retrieval_node when both Vertex AI
    and Firestore are unavailable.

Layer 2 — Keyword intent classifier (multilingual)
    Extended version of the classifier in intent.py, with Hindi transliterations
    and common Hinglish patterns added.  Covers all 9 intent categories.

Layer 3 — NVSP referral helpers
    Generates deep-link URLs and structured referral responses for every
    voter-lookup scenario.  Used by voter_search.py and live_lookup.py when
    the ECI API is unreachable or returns 403.

Design rules
------------
- Zero imports outside the standard library at module level.
  (Allows safe import even in heavily sandboxed test environments.)
- Every public function returns a result, never raises.
- All text content is sourced from official ECI publications.
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Layer 1 — Static voter-registration guidance corpus
# ─────────────────────────────────────────────────────────────────────────────

# Each entry mirrors the RetrievedChunk TypedDict from agents/state.py so it
# can drop in wherever a real Firestore chunk would appear.

_STATIC_CORPUS: list[dict[str, Any]] = [
    # ── Form 6 ────────────────────────────────────────────────────────────────
    {
        "chunk_id":   "form6_eligibility",
        "form_type":  "Form 6",
        "section":    "Eligibility",
        "confidence": 0.91,
        "source_url": "https://voters.eci.gov.in/download/Form_6.pdf",
        "text": (
            "**Form 6 — New Voter Registration**: Any Indian citizen who will be "
            "**18 years or older** on the qualifying date (1st January of the reference "
            "year) and is ordinarily resident at their stated address may apply. "
            "Submit the form to the Electoral Registration Officer (ERO) of your "
            "constituency, or online at voters.eci.gov.in. Applications can be made "
            "year-round; they are processed on a rolling basis."
        ),
    },
    {
        "chunk_id":   "form6_documents",
        "form_type":  "Form 6",
        "section":    "Documents",
        "confidence": 0.90,
        "source_url": "https://voters.eci.gov.in/download/Form_6.pdf",
        "text": (
            "**Documents required for Form 6 (new registration)**:\n"
            "- **Proof of age**: Aadhaar card, birth certificate, school-leaving "
            "certificate, or passport.\n"
            "- **Proof of address**: Aadhaar card, utility bill (not older than 1 year), "
            "bank or post-office passbook, or rent/lease agreement.\n"
            "- **One recent passport-size photograph**.\n"
            "Photocopies of documents are acceptable; originals are not retained."
        ),
    },
    {
        "chunk_id":   "form6_overseas",
        "form_type":  "Form 6A",
        "section":    "Overseas Indians",
        "confidence": 0.88,
        "source_url": "https://voters.eci.gov.in/download/Form_6A.pdf",
        "text": (
            "**Form 6A — Overseas Voter Registration**: Indian citizens residing "
            "outside India who hold a valid Indian passport may register in their "
            "home constituency using Form 6A. Required documents: copy of passport "
            "(bio-data and address pages) and a declaration of absence from India "
            "on the qualifying date."
        ),
    },
    # ── Form 7 ────────────────────────────────────────────────────────────────
    {
        "chunk_id":   "form7_deletion",
        "form_type":  "Form 7",
        "section":    "Deletion / Objection",
        "confidence": 0.87,
        "source_url": "https://voters.eci.gov.in/download/Form_7.pdf",
        "text": (
            "**Form 7 — Objection to inclusion or deletion from electoral roll**: "
            "File Form 7 to remove a deceased voter, a duplicate entry, or a voter "
            "who has shifted permanently out of the constituency. You must provide "
            "the EPIC number of the entry to be removed and a documented reason. "
            "The ERO will issue a notice to the concerned person before deletion."
        ),
    },
    # ── Form 8 ────────────────────────────────────────────────────────────────
    {
        "chunk_id":   "form8_correction",
        "form_type":  "Form 8",
        "section":    "Correction",
        "confidence": 0.89,
        "source_url": "https://voters.eci.gov.in/download/Form_8.pdf",
        "text": (
            "**Form 8 — Correction of entries in electoral roll**: Use Form 8 to "
            "correct name spelling, date of birth, photograph, or address within "
            "the **same constituency**. Attach self-attested copies of supporting "
            "documents (e.g. Aadhaar for name, birth certificate for DOB). "
            "Submit to your ERO or online at voters.eci.gov.in. "
            "Corrections are reflected in the next published supplement roll."
        ),
    },
    {
        "chunk_id":   "form8a_transposition",
        "form_type":  "Form 8A",
        "section":    "Address Change",
        "confidence": 0.88,
        "source_url": "https://voters.eci.gov.in/download/Form_8A.pdf",
        "text": (
            "**Form 8A — Transposition (address change within same constituency)**: "
            "If you have moved to a **new address within the same constituency**, "
            "file Form 8A with proof of new address. "
            "If you have moved to a **different constituency**, file Form 6 "
            "(new registration at new address) and Form 7 (deletion from old roll). "
            "Do not file Form 8A for inter-constituency moves."
        ),
    },
    # ── Grievance ──────────────────────────────────────────────────────────────
    {
        "chunk_id":   "grievance_missing_name",
        "form_type":  "Grievance",
        "section":    "Missing Name",
        "confidence": 0.86,
        "source_url": "https://nvsp.in/grievance",
        "text": (
            "**If your name is missing from the electoral roll**: First verify your "
            "EPIC number at electoralsearch.eci.gov.in. If absent, file Form 6 for "
            "fresh registration. If you registered recently (within 90 days), your "
            "name may be in the pending supplement roll — contact your ERO for status. "
            "You may also call the National Voter Helpline at **1950** (toll-free, "
            "available in 13 languages)."
        ),
    },
    {
        "chunk_id":   "grievance_wrong_entry",
        "form_type":  "Grievance",
        "section":    "Wrong Entry",
        "confidence": 0.85,
        "source_url": "https://nvsp.in/grievance",
        "text": (
            "**If your electoral roll entry has an error** (wrong name spelling, "
            "wrong DOB, wrong address, or wrong photograph): File Form 8 (correction) "
            "at your ERO or online at voters.eci.gov.in/VoterRegistration. "
            "Attach self-attested documents supporting the correct information. "
            "Track your application status using the reference number provided. "
            "Escalate unresolved corrections to the District Election Officer."
        ),
    },
    # ── Deadlines ──────────────────────────────────────────────────────────────
    {
        "chunk_id":   "deadlines_general",
        "form_type":  "General",
        "section":    "Deadlines",
        "confidence": 0.82,
        "source_url": "https://eci.gov.in",
        "text": (
            "**Voter registration deadlines**: The ECI publishes the electoral roll "
            "on 1st January each year. Applications for the published roll close "
            "approximately 30 days before publication (typically late November). "
            "However, you may register at any time — names added after the cutoff "
            "appear in supplement rolls published before the next election. "
            "Election-specific registration cutoffs are announced in the official "
            "Model Code of Conduct notification. Check eci.gov.in for current dates."
        ),
    },
    # ── ERO location ──────────────────────────────────────────────────────────
    {
        "chunk_id":   "ero_find",
        "form_type":  "General",
        "section":    "ERO Location",
        "confidence": 0.84,
        "source_url": "https://electoralsearch.eci.gov.in",
        "text": (
            "**Finding your Electoral Registration Officer (ERO)**: Use the ERO "
            "locator at electoralsearch.eci.gov.in or enter your pincode in the "
            "Matdaan Mitra ERO locator. Your Booth Level Officer (BLO) is the "
            "field officer assigned to your polling booth — they visit homes during "
            "house-to-house verification drives and can assist with on-the-spot "
            "registration. The National Voter Helpline **1950** can also provide "
            "your nearest ERO contact."
        ),
    },
]

# Build a quick lookup by chunk_id for O(1) access
_CORPUS_BY_ID: dict[str, dict[str, Any]] = {c["chunk_id"]: c for c in _STATIC_CORPUS}

# Intent → list of chunk_ids that are most relevant
_INTENT_CHUNK_MAP: dict[str, list[str]] = {
    "form_guidance":     ["form6_eligibility", "form6_documents", "form8a_transposition", "form8_correction", "form7_deletion", "form6_overseas"],
    "document_check":   ["form6_documents", "form6_eligibility"],
    "voter_lookup":     ["grievance_missing_name"],
    "ero_location":     ["ero_find"],
    "grievance_help":   ["grievance_wrong_entry", "grievance_missing_name"],
    "deadline_query":   ["deadlines_general"],
    "profile_collection": ["form6_eligibility"],
    "off_topic":        [],
    "unknown":          ["form6_eligibility", "ero_find"],
}


def get_static_chunks(
    intent: str | None = None,
    chunk_ids: list[str] | None = None,
    top_k: int = 4,
) -> list[dict[str, Any]]:
    """
    Return static corpus chunks relevant to the given intent or chunk IDs.

    Priority: explicit chunk_ids > intent mapping > first top_k chunks.
    Never raises — returns [] on any unexpected input.

    Args:
        intent:    Intent category from intent_node (e.g. "form_guidance").
        chunk_ids: Explicit list of chunk IDs (e.g. from a keyword search).
        top_k:     Maximum number of chunks to return.

    Returns:
        List of RetrievedChunk-compatible dicts, max length top_k.
    """
    try:
        if chunk_ids:
            return [_CORPUS_BY_ID[cid] for cid in chunk_ids
                    if cid in _CORPUS_BY_ID][:top_k]

        if intent and intent in _INTENT_CHUNK_MAP:
            ids = _INTENT_CHUNK_MAP[intent]
            return [_CORPUS_BY_ID[cid] for cid in ids
                    if cid in _CORPUS_BY_ID][:top_k]

        # Generic fallback: return the first top_k chunks
        return _STATIC_CORPUS[:top_k]

    except Exception as exc:
        logger.error("get_static_chunks error: %s", exc)
        return []


# ─────────────────────────────────────────────────────────────────────────────
# Layer 2 — Multilingual keyword intent classifier
# ─────────────────────────────────────────────────────────────────────────────

# Rule order matters: more specific rules first to avoid false positives.
# Each tuple: (intent_category, [keyword_patterns], confidence)

_KEYWORD_RULES: list[tuple[str, list[str], float]] = [
    # ── Voter lookup ──────────────────────────────────────────────────────────
    (
        "voter_lookup",
        [
            # English
            "epic", "voter id", "voter card", "voter number", "voter list",
            "check status", "enrolled", "roll number", "electoral roll",
            "search voter", "find my name",
            # Hindi transliteration
            "matdata pehchan", "matdata id", "naam check", "naam dhundh",
            "voter list mein naam", "naam hai ya nahi",
        ],
        0.74,
    ),
    # ── ERO location ──────────────────────────────────────────────────────────
    (
        "ero_location",
        [
            # English
            "ero", "ero office", "blo", "booth level officer", "polling office",
            "booth officer", "where is", "nearest office", "find office",
            "election office", "registration center", "voter help center",
            # Hindi transliteration
            "nirvachan adhikari", "booth adhikari", "matdan kendra",
            "ero kahan hai", "registration office kahan",
        ],
        0.74,
    ),
    # ── Deadline query (before form_guidance: "registration" overlap) ─────────
    (
        "deadline_query",
        [
            "deadline", "last date", "cutoff", "by when", "how many days",
            "phase", "schedule", "when is", "till when", "date of",
            "registration close", "election date",
            # Hindi
            "antim tithi", "kab tak", "phase kab", "anushuchi",
        ],
        0.74,
    ),
    # ── Form guidance ──────────────────────────────────────────────────────────
    (
        "form_guidance",
        [
            "form 6", "form 7", "form 8", "form 6a", "form 8a",
            "register", "registration", "enroll", "enrolment",
            "how to apply", "new voter", "fresh registration",
            "apply online", "apply for voter", "voters.eci",
            # Hindi
            "form kaise", "registration kaise", "register karna",
            "matdata banna", "nayi registration", "form 6 kaise",
        ],
        0.73,
    ),
    # ── Document check ────────────────────────────────────────────────────────
    (
        "document_check",
        [
            "document", "aadhaar", "aadhar", "proof", "certificate",
            "photo", "id proof", "address proof", "what do i need",
            "which documents", "required documents", "kaunsa document",
            # Hindi
            "dastavej", "pramaan patra", "kya chahiye", "kaun se dastavej",
            "pahchaan pramaan", "pata pramaan",
        ],
        0.73,
    ),
    # ── Grievance ─────────────────────────────────────────────────────────────
    (
        "grievance_help",
        [
            "missing", "not found", "wrong", "error", "complaint",
            "grievance", "problem", "issue", "deleted", "removed",
            "name not there", "spelling mistake", "wrong address",
            "wrong photo", "change name",
            # Hindi
            "naam nahi hai", "galat naam", "shikayat", "problem hai",
            "naam delete", "galat jaankari", "photo galat",
        ],
        0.74,
    ),
    # ── Profile collection ────────────────────────────────────────────────────
    (
        "profile_collection",
        [
            "my name", "i am from", "i live in", "my pincode",
            "my state", "my address", "mera naam", "main rehta",
            "mera pincode", "mera address", "main hoon",
        ],
        0.70,
    ),
]

# Compiled regex cache for speed
_COMPILED_RULES: list[tuple[str, re.Pattern, float]] = [
    (intent, re.compile("|".join(re.escape(kw) for kw in keywords), re.IGNORECASE), conf)
    for intent, keywords, conf in _KEYWORD_RULES
]


def keyword_classify(message: str) -> tuple[str, float]:
    """
    Classify message intent using keyword pattern matching.

    Returns (intent_category, confidence_score).
    Confidence is deliberately set below the 0.75 guardrail threshold so
    keyword-classified responses are always flagged for escalation if needed.

    Covers English, Hindi transliterations, and common Hinglish patterns.
    Never raises.
    """
    if not message:
        return "unknown", 0.40

    try:
        for intent, pattern, confidence in _COMPILED_RULES:
            if pattern.search(message):
                logger.debug("Keyword intent: %s (conf=%.2f)", intent, confidence)
                return intent, confidence
        return "unknown", 0.40
    except Exception as exc:
        logger.error("keyword_classify error: %s", exc)
        return "unknown", 0.40


# ─────────────────────────────────────────────────────────────────────────────
# Layer 3 — NVSP referral helpers
# ─────────────────────────────────────────────────────────────────────────────

_NVSP_BASE = "https://electoralsearch.eci.gov.in"
_ECI_VOTERS_PORTAL = "https://voters.eci.gov.in"


def nvsp_redirect_response(
    epic: str | None = None,
    reason: str = "api_unavailable",
    name: str | None = None,
    state: str | None = None,
) -> dict[str, Any]:
    """
    Build a structured NVSP redirect response for voter lookup failures.

    The frontend renders this as a 'Verify on NVSP.in' card with a deep-link
    button.  The response never crashes the pipeline — all fields have defaults.

    Args:
        epic:   EPIC number to pre-fill in the NVSP URL.
        reason: Machine-readable failure reason for analytics.
        name:   Voter name hint (used to build a name-search fallback URL).
        state:  State name hint for the referral message.

    Returns:
        dict compatible with the VoterLookupResult shape in voter_search.py.
    """
    try:
        # Build the deepest useful URL we can
        if epic:
            epic_clean = re.sub(r"\s+", "", epic.upper())
            nvsp_url = f"{_NVSP_BASE}/?epicno={epic_clean}"
        elif name and state:
            # Name + state search (less precise but better than homepage)
            nvsp_url = (
                f"{_NVSP_BASE}/?name={name.strip()[:40]}"
                f"&state={state.strip()[:30]}"
            )
        else:
            nvsp_url = _NVSP_BASE

        state_note = f" in {state}" if state else ""
        message = (
            f"Live voter lookup is temporarily unavailable. "
            f"Please verify your registration directly on the official "
            f"NVSP portal{state_note}. Your data on the portal is always "
            f"authoritative."
        )

        return {
            "found":          None,
            "nvsp_redirect":  True,
            "nvsp_url":       nvsp_url,
            "epic_number":    epic,
            "reason":         reason,
            "message":        message,
            "helpline":       "1950",
            "helpline_note":  "National Voter Helpline — toll-free, 13 languages",
        }
    except Exception as exc:
        logger.error("nvsp_redirect_response error: %s", exc)
        return {
            "found":         None,
            "nvsp_redirect": True,
            "nvsp_url":      _NVSP_BASE,
            "reason":        "internal_error",
            "message":       "Please verify at electoralsearch.eci.gov.in or call 1950.",
        }


def registration_link(form: str = "6") -> str:
    """
    Return the direct URL to start a voter registration form on the ECI portal.

    Args:
        form: Form number as string — "6", "7", "8", "8A", "6A".

    Returns:
        URL string — falls back to voters portal homepage on unknown form.
    """
    _FORM_PATHS: dict[str, str] = {
        "6":  "/VoterRegistration/form6",
        "7":  "/VoterRegistration/form7",
        "8":  "/VoterRegistration/form8",
        "8A": "/VoterRegistration/form8a",
        "6A": "/VoterRegistration/form6a",
    }
    path = _FORM_PATHS.get(form.upper().strip(), "")
    return f"{_ECI_VOTERS_PORTAL}{path}" if path else _ECI_VOTERS_PORTAL


# ─────────────────────────────────────────────────────────────────────────────
# Fallback registry — dependency → fallback function
# ─────────────────────────────────────────────────────────────────────────────

class FallbackRegistry:
    """
    Tracks which external services are degraded and routes callers to the
    appropriate local fallback without a try/except at each call site.

    Usage (in agents/nodes or services):
        from ...services.static_fallbacks import fallback_registry

        if fallback_registry.is_degraded("vertex_ai"):
            chunks = get_static_chunks(intent=state["intent"])
        else:
            chunks = await vector_search_service.search(embedding)
            if chunks is None:
                fallback_registry.mark_degraded("vertex_ai")
                chunks = get_static_chunks(intent=state["intent"])
    """

    def __init__(self) -> None:
        self._degraded: set[str] = set()
        self._lock = __import__("threading").Lock()

    def mark_degraded(self, service: str) -> None:
        with self._lock:
            if service not in self._degraded:
                logger.warning("FallbackRegistry: marking '%s' as degraded", service)
                self._degraded.add(service)

    def mark_recovered(self, service: str) -> None:
        with self._lock:
            if service in self._degraded:
                logger.info("FallbackRegistry: '%s' recovered", service)
                self._degraded.discard(service)

    def is_degraded(self, service: str) -> bool:
        return service in self._degraded

    @property
    def degraded_services(self) -> list[str]:
        return sorted(self._degraded)


# Module-level singleton — import this in agent nodes and services
fallback_registry = FallbackRegistry()
