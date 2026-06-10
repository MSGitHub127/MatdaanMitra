"""
grievance.py — Grievance letter PDF generation route

POST /grievance/letter
  Loads voter profile from Firestore, fills a formal complaint letter
  template, generates a PDF using PyMuPDF, and returns it as a download.

The generated letter is print-ready and matches the format expected
by ERO/BLO offices and state CEO complaint cells.
"""

import asyncio
import io
import logging
import textwrap
from datetime import datetime, timezone
from typing import Any

import fitz  # PyMuPDF
from fastapi import APIRouter, HTTPException, Request, status, Depends
from fastapi.responses import Response
from pydantic import BaseModel

from ..middleware.auth import verify_firebase_token

logger = logging.getLogger(__name__)
router = APIRouter()

# ── Issue type catalogue ──────────────────────────────────────────────────────

ISSUE_TYPES: dict[str, dict[str, str]] = {
    "missing_name": {
        "subject": "Complaint Regarding Non-Inclusion of Name in Electoral Roll",
        "body": (
            "I wish to bring to your kind notice that my name has not been included "
            "in the electoral roll for the assembly constituency of {constituency}, "
            "despite meeting all eligibility criteria and being ordinarily resident at "
            "the address mentioned below. I have been residing at this address since "
            "{since_year} and my details are as follows:\n\n"
            "I request you to please investigate this matter and include my name in "
            "the electoral roll at the earliest. I am ready to provide any additional "
            "documents or appear in person for verification if required."
        ),
    },
    "wrong_details": {
        "subject": "Complaint Regarding Incorrect Details in Electoral Roll",
        "body": (
            "I wish to inform you that my entry in the electoral roll for the "
            "assembly constituency of {constituency} contains incorrect details. "
            "The discrepancy is causing difficulties and needs immediate rectification "
            "to ensure that my voter record accurately reflects my identity.\n\n"
            "I request you to kindly verify the above details against my supporting "
            "documents and make the necessary corrections. I am attaching copies of "
            "relevant identity proof for your reference."
        ),
    },
    "address_update": {
        "subject": "Request for Address Update in Electoral Roll",
        "body": (
            "I wish to inform you that I have recently changed my address within the "
            "same assembly constituency of {constituency}. My current address, as "
            "mentioned below, is different from the address recorded in the electoral "
            "roll. I request you to kindly update my address in the electoral roll "
            "to reflect my current residence.\n\n"
            "I am enclosing proof of new address (Aadhaar / utility bill) for verification."
        ),
    },
    "duplicate_entry": {
        "subject": "Complaint Regarding Duplicate Entry in Electoral Roll",
        "body": (
            "I wish to draw your attention to the fact that my name appears to have "
            "been entered twice in the electoral roll, possibly due to a previous "
            "address and my current address in the constituency of {constituency}. "
            "This duplicate entry needs to be resolved to comply with the "
            "Representation of the People Act.\n\n"
            "I request you to please verify and remove the duplicate entry, retaining "
            "only the record corresponding to my current address."
        ),
    },
    "other": {
        "subject": "Complaint Regarding Voter Registration Issue",
        "body": (
            "I wish to bring to your attention an issue with my voter registration "
            "in the electoral roll of {constituency} assembly constituency. "
            "The details of my concern are described herein.\n\n"
            "I request you to look into this matter and take the necessary corrective "
            "action at the earliest. I am available for any verification or clarification "
            "that may be required."
        ),
    },
}


# ── Request model ─────────────────────────────────────────────────────────────

class GrievanceLetterRequest(BaseModel):
    session_id:  str
    issue_type:  str = "missing_name"
    description: str = ""  # Optional additional details from user


# ── Firestore profile loader ──────────────────────────────────────────────────

async def _get_voter_profile(session_id: str) -> dict[str, Any]:
    try:
        import firebase_admin  # noqa
        from firebase_admin import firestore

        db = firestore.client()

        def _sync():
            doc = db.collection("sessions").document(session_id).get()
            return doc.to_dict().get("voterProfile", {}) if doc.exists else {}

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _sync)
    except Exception as exc:
        logger.warning("Could not load profile for %s: %s", session_id[-8:], exc)
        return {}


# ── PDF generation ────────────────────────────────────────────────────────────

def _wrap(text: str, width: int = 88) -> list[str]:
    lines: list[str] = []
    for para in text.split("\n"):
        if para.strip():
            lines.extend(textwrap.wrap(para, width=width))
        else:
            lines.append("")
    return lines


def _generate_letter_pdf(profile: dict[str, Any], issue_type: str, description: str) -> bytes:
    """
    Build a formal A4 complaint letter using PyMuPDF text primitives.
    Returns PDF bytes ready for download.
    """
    issue = ISSUE_TYPES.get(issue_type, ISSUE_TYPES["other"])

    name         = profile.get("name", "Applicant")
    epic         = profile.get("epic_number", "N/A")
    constituency = profile.get("current_state", "Your Constituency")
    pincode      = profile.get("current_pincode", "")
    address      = f"Pincode: {pincode}" if pincode else "Address on file"
    date_str     = datetime.now(timezone.utc).strftime("%d %B %Y")

    body_template = issue["body"]
    body_text = body_template.format(
        constituency=constituency,
        since_year=str(datetime.now().year - 1),
    )
    if description:
        body_text += f"\n\nAdditional details provided by applicant:\n{description}"

    # ── Document setup ────────────────────────────────────────────────────────
    doc  = fitz.open()
    page = doc.new_page(width=595, height=842)   # A4

    LEFT  = 72
    RIGHT = 523
    y     = 70

    # ── Helper functions ──────────────────────────────────────────────────────
    def line(text: str, x: int = LEFT, size: float = 11.0, bold: bool = False, color: tuple = (0, 0, 0)):
        nonlocal y
        page.insert_text(
            (x, y), text,
            fontsize=size,
            fontname="hebo" if bold else "helv",
            color=color,
        )
        y += size + 5

    def rule(y_pos: int = None, color: tuple = (0.7, 0.7, 0.7)):
        pos = y_pos if y_pos is not None else y
        page.draw_line((LEFT, pos), (RIGHT, pos), color=color, width=0.6)

    def skip(n: int = 10):
        nonlocal y
        y += n

    # ── Header ────────────────────────────────────────────────────────────────
    line("मतदान मित्र  |  MATDAAN MITRA", size=15, bold=True, color=(0.98, 0.45, 0.09))
    line("AI-Powered Voter Assistance Platform  ·  Powered by ECI Guidelines", size=8.5, color=(0.5, 0.5, 0.5))
    rule()
    skip(14)

    # ── Date (right-aligned) ──────────────────────────────────────────────────
    line(f"Date: {date_str}", x=RIGHT - 130, size=10.5)
    skip(4)

    # ── Addressee block ───────────────────────────────────────────────────────
    line("To,", bold=True)
    line("The Electoral Registration Officer")
    line(f"{constituency} Assembly Constituency")
    skip(12)

    # ── Subject ───────────────────────────────────────────────────────────────
    line(f"Subject: {issue['subject']}", bold=True, size=10.5)
    rule(color=(0.85, 0.85, 0.85))
    skip(14)

    # ── Salutation ────────────────────────────────────────────────────────────
    line("Respected Sir/Madam,")
    skip(8)

    # ── Opening ───────────────────────────────────────────────────────────────
    opening = (
        f"I, {name}, holding EPIC number {epic}, am ordinarily resident at "
        f"{address}, and am writing to bring the following matter to your attention:"
    )
    for l in _wrap(opening):
        line(l, size=10.5)
    skip(8)

    # ── Body paragraphs ───────────────────────────────────────────────────────
    for l in _wrap(body_text):
        line(l, size=10.5)
    skip(14)

    # ── Supporting docs list ──────────────────────────────────────────────────
    line("Enclosures:", bold=True, size=10.5)
    for doc_item in [
        "1. Self-attested copy of Aadhaar Card",
        "2. Proof of address (utility bill / bank passbook)",
        "3. Passport-size photograph",
        "4. Copy of existing EPIC card (if applicable)",
    ]:
        line(f"  {doc_item}", size=10.0, color=(0.2, 0.2, 0.2))
    skip(18)

    # ── Sign-off ──────────────────────────────────────────────────────────────
    line("Thanking you,")
    skip(6)
    line("Yours faithfully,")
    skip(36)  # Signature space

    line(name, bold=True)
    line(f"EPIC No.: {epic}", size=10.5)
    line(f"{address}", size=10.5)
    skip(10)

    # ── Official helpline reminder ─────────────────────────────────────────────
    rule()
    skip(6)
    page.insert_text(
        (LEFT, y),
        "National Voter Helpline: 1950  ·  Online: voters.eci.gov.in  ·  "
        "Generated by MatdaanMitra — Official ECI Data Only",
        fontsize=7.5,
        color=(0.55, 0.55, 0.55),
    )

    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


# ── Route ─────────────────────────────────────────────────────────────────────

@router.post("/grievance/letter")
async def generate_grievance_letter(
    request: GrievanceLetterRequest,
    uid: str = Depends(verify_firebase_token),
):
    """
    Generate a pre-filled grievance complaint letter PDF.
    Downloads as 'voter_complaint_letter.pdf'.
    """
    if request.issue_type not in ISSUE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid issue_type. Choose from: {', '.join(ISSUE_TYPES.keys())}",
        )

    profile = await _get_voter_profile(request.session_id)

    try:
        pdf_bytes = _generate_letter_pdf(
            profile=profile,
            issue_type=request.issue_type,
            description=request.description,
        )
    except Exception as exc:
        logger.exception("PDF generation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate letter. Please try again.",
        )

    filename = f"voter_complaint_{request.issue_type}_{datetime.now().strftime('%Y%m%d')}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length":      str(len(pdf_bytes)),
        },
    )