from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, constr
import re
import logging

from ..middleware.auth import verify_firebase_token
from ...services.ero_locator import ero_locator_service

logger = logging.getLogger(__name__)

router = APIRouter()


class EROOfficeResponse(BaseModel):
    name: str
    address: str
    phone: str
    email: str
    distance_km: float
    directions_url: str
    latitude: float
    longitude: float


@router.get("/ero/{pincode}", response_model=EROOfficeResponse)
async def get_ero_location(
    pincode: str,
    uid: str = Depends(verify_firebase_token),
):
    """
    Get ERO office location by pincode.
    Uses Google Maps API to find nearest electoral office.
    """
    # Validate pincode format (6 digits)
    if not re.match(r'^\d{6}$', pincode):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid pincode format. Must be 6 digits.",
        )

    try:
        result = await ero_locator_service.find_ero_office(pincode)

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No ERO office found for this pincode. Please contact your state CEO office.",
            )

        return EROOfficeResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error finding ERO office: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to find ERO office. Please try again later.",
        )