"""
profile.py — Voter profile checklist update route

PATCH /profile/{session_id}/checklist

Fix: The previous version called the synchronous Firestore doc_ref.update()
directly inside an async handler. This blocks the uvicorn event loop on
every call. All sync Firestore operations must be wrapped in run_in_executor
so they run on a thread-pool thread while the event loop stays free.

Also uses asyncio.get_running_loop() (Python 3.10+ idiomatic) instead of
the deprecated asyncio.get_event_loop().
"""

import asyncio
import logging
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from ..middleware.auth import verify_firebase_token

logger = logging.getLogger(__name__)

router = APIRouter()


class ChecklistUpdateRequest(BaseModel):
    checklist: Dict[str, bool]


class ChecklistResponse(BaseModel):
    checklist: Dict[str, bool]


@router.patch("/profile/{session_id}/checklist", response_model=ChecklistResponse)
async def update_checklist(
    session_id: str,
    request: ChecklistUpdateRequest,
    uid: str = Depends(verify_firebase_token),
):
    """
    Update the voter document checklist for a session in Firestore.

    Uses dot-notation update so only voterProfile.checklist is touched —
    all other voterProfile sub-fields are preserved.
    """
    try:
        import firebase_admin  # noqa: F401
        from firebase_admin import firestore

        db = firestore.client()

        def _sync_update():
            doc_ref = db.collection("sessions").document(session_id)
            doc_ref.update({
                "voterProfile.checklist": request.checklist,
                "updatedAt": firestore.SERVER_TIMESTAMP,
            })

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, _sync_update)

        return ChecklistResponse(checklist=request.checklist)

    except Exception as exc:
        logger.error("Error updating checklist for session %s: %s", session_id[-8:], exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update checklist. Please try again later.",
        )