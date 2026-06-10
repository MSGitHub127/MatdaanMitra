from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Dict, Any
import logging

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
    Update voter document checklist for a session.
    Uses Firestore dot-notation update (not set+merge) to avoid
    overwriting other voterProfile fields.
    """
    try:
        import firebase_admin  # noqa
        from firebase_admin import firestore

        db = firestore.client()
        doc_ref = db.collection("sessions").document(session_id)

        # update() with dot-notation key correctly writes to the nested field
        # without touching other voterProfile fields.
        # set() with merge=True would require a nested dict, not a dotted key.
        doc_ref.update({
            "voterProfile.checklist": request.checklist,
            "updatedAt": firestore.SERVER_TIMESTAMP,
        })

        return ChecklistResponse(checklist=request.checklist)

    except Exception as e:
        logger.error(f"Error updating checklist for session {session_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update checklist. Please try again later.",
        )