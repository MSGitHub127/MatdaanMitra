"""
rate_limit.py — Redis-backed rate limiting

Two layers:
  1. RateLimitMiddleware  — ASGI middleware, IP-based global throttle (100 req/min).
                            Runs before auth, so it can't do per-user limiting.
  2. check_rate_limit     — FastAPI dependency, per-user limiting (30 req/min).
                            Used on individual routes after Firebase auth resolves the UID.
"""

import time
import logging
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import redis.asyncio as aioredis

from ...config.settings import settings

logger = logging.getLogger(__name__)

# Paths that bypass rate limiting entirely
_SKIP_PATHS = {"/health", "/docs", "/openapi.json", "/redoc"}


# ── Layer 1: ASGI Middleware (IP-based) ───────────────────────────────────────

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    IP-based rate limiter applied globally before route handlers.
    Caps at 100 requests/minute per client IP.
    Fails open — if Redis is down, requests are allowed through.
    """

    MAX_REQUESTS_PER_MINUTE = 100

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        if request.url.path in _SKIP_PATHS:
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        key = f"ip_rate:{client_ip}"

        try:
            async with aioredis.from_url(settings.redis_url, decode_responses=True) as r:
                now = time.time()
                window_start = now - 60.0

                pipe = r.pipeline()
                pipe.zremrangebyscore(key, 0, window_start)
                pipe.zadd(key, {str(now): now})
                pipe.expire(key, 60)
                pipe.zcard(key)
                results = await pipe.execute()
                count: int = results[3]

            if count > self.MAX_REQUESTS_PER_MINUTE:
                logger.warning("IP rate limit exceeded: %s (%d req/min)", client_ip, count)
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={"detail": "Too many requests. Please slow down."},
                    headers={"Retry-After": "60"},
                )
        except Exception as exc:
            # Fail open — never block users because Redis is unreachable
            logger.error("RateLimitMiddleware Redis error (failing open): %s", exc)

        return await call_next(request)


# ── Layer 2: Per-user dependency (UID-based) ──────────────────────────────────

async def check_rate_limit(request: Request, uid: str) -> None:
    """
    FastAPI dependency for per-user rate limiting (30 req/min).
    Must be called after Firebase token verification so the UID is available.

    Usage in a route:
        @router.post("/chat")
        async def chat(request: ChatRequest, uid: str = verify_firebase_token):
            await check_rate_limit(request, uid)
            ...
    """
    key = f"user_rate:{uid}:{request.url.path}"

    try:
        async with aioredis.from_url(settings.redis_url, decode_responses=True) as r:
            now = time.time()
            window_start = now - 60.0

            pipe = r.pipeline()
            pipe.zremrangebyscore(key, 0, window_start)
            pipe.zadd(key, {str(now): now})
            pipe.expire(key, 60)
            pipe.zcard(key)
            results = await pipe.execute()
            count: int = results[3]

        if count > 30:
            logger.warning("User rate limit exceeded: uid=%s path=%s", uid, request.url.path)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please wait before sending another request.",
                headers={"Retry-After": "60"},
            )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("check_rate_limit Redis error (failing open): %s", exc)