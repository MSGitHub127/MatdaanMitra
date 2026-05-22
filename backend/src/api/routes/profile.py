from fastapi import APIRouter, HTTPException, status
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
    uid: str = verify_firebase_token,
):
    """
    Update voter document checklist.
    Persists to Firestore.
    """
    try:
        import firebase_admin
        from firebase_admin import firestore

        db = firestore.client()

        # Update checklist in Firestore
        doc_ref = db.collection("sessions").document(session_id)
        doc_ref.set(
            {
                "voterProfile.checklist": request.checklist,
                "updatedAt": firestore.SERVER_TIMESTAMP,
            },
            merge=True,
        )

        return ChecklistResponse(checklist=request.checklist)

    except Exception as e:
        logger.error(f"Error updating checklist: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update checklist. Please try again later.",
        )
