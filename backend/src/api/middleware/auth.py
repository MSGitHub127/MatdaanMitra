"""
auth.py — Firebase Admin SDK initialisation + JWT verification middleware

Fix: Previously called firebase_admin.initialize_app() at module import time.
If the service account file is absent (CI, dev without credentials), this
raises an exception that crashes FastAPI startup — even /health becomes
unreachable.

Lazy init: the SDK is only initialised on the first verify_firebase_token
call. The app starts cleanly without credentials; unauthenticated routes
(/health) stay reachable. Auth routes return a clean 503 when unconfigured.
"""

import logging
from typing import Optional

import firebase_admin
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from firebase_admin import auth, credentials

from ...config.settings import settings

logger = logging.getLogger(__name__)

security = HTTPBearer()

_firebase_initialised = False


def _ensure_firebase() -> bool:
    """
    Lazily initialise Firebase Admin SDK.
    Returns True if the SDK is ready; False if credentials are absent.
    Never raises.
    """
    global _firebase_initialised

    if _firebase_initialised:
        return True

    if firebase_admin._apps:
        # Already initialised elsewhere (e.g. grievance.py / chat.py startup)
        _firebase_initialised = True
        return True

    if not settings.firebase_service_account_path:
        logger.warning(
            "FIREBASE_SERVICE_ACCOUNT_PATH not set — auth endpoints will return 503"
        )
        return False

    try:
        cred = credentials.Certificate(settings.firebase_service_account_path)
        firebase_admin.initialize_app(cred)
        _firebase_initialised = True
        logger.info("Firebase Admin SDK initialised")
        return True
    except Exception as exc:
        logger.error("Failed to initialise Firebase Admin SDK: %s", exc)
        return False


async def verify_firebase_token(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> Optional[str]:
    """
    Verify a Firebase ID token and return the user's UID.
    Raises HTTPException on invalid / expired tokens.
    """
    if not _ensure_firebase():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service is not configured.",
        )

    token = credentials.credentials

    try:
        decoded = auth.verify_id_token(token)
        uid = decoded.get("uid")
        if not uid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing UID",
            )
        return uid

    except auth.ExpiredIdTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired. Please refresh and try again.",
        )
    except auth.InvalidIdTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Token verification error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed.",
        )