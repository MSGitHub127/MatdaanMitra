"""
voter.py — Voter status lookup route

GET /voter/{epic_number}

Fixes applied:
  1. Removed unused `constr` import (dropped in Pydantic v2 — caused ImportError
     on startup with pydantic>=2.0).

  2. EPIC regex was '^[A-Za-z0-9]{10}$' — too strict. Valid Indian EPICs are
     2–3 letters + 7–8 digits (9–11 chars total, not always exactly 10).
     Aligned with voter_search.py's own validation: '^[A-Z]{2,3}\\d{7,8}$'.

  3. VoterStatusResponse(**result) crashed with Pydantic ValidationError whenever
     the ECI API is blocked and voter_search returns an nvsp_redirect payload
     (which lacks name/father_name/age/etc.). Removed the rigid response model
     and returned the raw dict instead — the frontend VoterStatus type handles
     all three shapes (found=True, nvsp_redirect=True, found=False).
"""

import re
import logging

from fastapi import APIRouter, Depends, HTTPException, status

from ..middleware.auth import verify_firebase_token
from ...services.voter_search import voter_search_service

logger = logging.getLogger(__name__)

router = APIRouter()

# 2–3 uppercase letters + 7–8 digits (accepts lowercase; service normalises)
_EPIC_RE = re.compile(r'^[A-Za-z]{2,3}\d{7,8}$')


@router.get("/voter/{epic_number}")
async def get_voter_status(
    epic_number: str,
    uid: str = Depends(verify_firebase_token),
):
    """
    Look up a voter by EPIC number.

    Returns one of:
      - Full voter record         (found=True,  nvsp_redirect=False)
      - NVSP redirect payload     (nvsp_redirect=True — ECI API is blocked)
      - Not-found record          (found=False, nvsp_redirect=False)

    The frontend VoterStatus TypeScript type models all three shapes.
    """
    if not _EPIC_RE.match(epic_number):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Invalid EPIC number format. "
                "Expected 2–3 letters followed by 7–8 digits (e.g. MH01234567)."
            ),
        )

    try:
        result = await voter_search_service.search_by_epic(epic_number)

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Voter not found. Please verify your EPIC number.",
            )

        # Return raw dict — all three result shapes are handled by the frontend
        return result

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error fetching voter status for %s: %s", epic_number[:5] + "***", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch voter status. Please try again later.",
        )