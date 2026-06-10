from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, constr
import re
import logging

from ..middleware.auth import verify_firebase_token
from ...services.voter_search import voter_search_service

logger = logging.getLogger(__name__)

router = APIRouter()


class VoterStatusResponse(BaseModel):
    epic_number: str
    name: str
    father_name: str
    age: int
    gender: str
    address: str
    polling_station: str
    assembly_constituency: str
    parliamentary_constituency: str
    status: str


@router.get("/voter/{epic_number}", response_model=VoterStatusResponse)
async def get_voter_status(
    epic_number: str,
    uid: str = Depends(verify_firebase_token),
):
    """
    Get voter status by EPIC number.
    Calls real ECI API to fetch current registration status.
    """
    # Validate EPIC format (typically 10 alphanumeric characters)
    if not re.match(r'^[A-Za-z0-9]{10}$', epic_number):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid EPIC number format. Must be 10 alphanumeric characters.",
        )

    try:
        result = await voter_search_service.search_by_epic(epic_number)

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Voter not found. Please verify your EPIC number.",
            )

        return VoterStatusResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching voter status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch voter status. Please try again later.",
        )