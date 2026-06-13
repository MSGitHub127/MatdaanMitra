"""
rate_limit.py — Redis-backed rate limiting

Fixes (production audit):

P1 — REDIS CONNECTION LEAK (CRITICAL)
    Previous: both RateLimitMiddleware.dispatch() and check_rate_limit() called
    aioredis.from_url() inside an async-with block on EVERY request. The /chat
    route executed two of these per request (middleware + dependency).
    Under 50 concurrent users → 100 new TCP handshakes/second.
    Cloud Memorystore default connection limit = 1,000; ceiling hit at ~100 users.

    Fix: Both layers now call _get_redis(request) which borrows a connection from
    the shared ConnectionPool stored on app.state.redis_pool (created in lifespan).
    No new TCP connections are opened after startup. Pool size = 20 (configured
    in main.py lifespan), shared across all concurrent requests on the instance.

P5 — RATE LIMITS ARE DEV-TUNED
    Previous: 30 req/min per user on all routes. Each POST /chat invokes Gemini Pro
    (~0.01–0.05 USD) + Vertex AI embeddings. At 30 req/min, one user can generate
    ~$0.50–1.50/min in Vertex AI costs.

    Fix: Route-specific limits:
      /chat              → 10 req/min  (Gemini Pro + Vertex AI — expensive)
      /grievance/letter  → 5 req/min   (PDF generation — CPU + storage)
      /tts               → 20 req/min  (Sarvam AI TTS — moderate cost)
      /voter/*           → 40 req/min  (lightweight ECI lookup)
      /ero/*             → 40 req/min  (lightweight Mapbox geocode)
      all others         → 30 req/min  (default)
    IP-level global cap unchanged at 100 req/min.

    check_rate_limit() accepts an optional limit parameter; callers that want
    the non-default limit pass it explicitly.
"""

import time
import logging
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from ...config.settings import settings

logger = logging.getLogger(__name__)

# Paths that bypass rate limiting entirely
_SKIP_PATHS = {"/health", "/docs", "/openapi.json", "/redoc"}

# Route-specific per-user request caps (requests per 60 seconds)
_ROUTE_LIMITS: dict[str, int] = {
    "/chat":              10,   # Gemini Pro + Vertex AI
    "/grievance/letter":   5,   # PDF generation
    "/tts":               20,   # Sarvam AI TTS
}
_DEFAULT_USER_LIMIT = 30


# ── Shared pool accessor ──────────────────────────────────────────────────────

async def _get_redis(request: Request):
    """
    Return an AsyncRedis client backed by the shared connection pool.
    The pool is created once in main.py lifespan; no new TCP connections
    are opened on each call — only a logical checkout from the pool.

    Returns None if the pool was not initialised (Redis unavailable at startup).
    """
    pool = getattr(request.app.state, "redis_pool", None)
    if pool is None:
        return None
    from redis.asyncio import Redis as AsyncRedis
    return AsyncRedis(connection_pool=pool)


# ── Layer 1: ASGI Middleware (IP-based global throttle) ───────────────────────

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    IP-based rate limiter applied globally before route handlers.
    Caps at 100 requests/minute per client IP.
    Fails open — if Redis is down or pool is None, requests pass through.
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
            r = await _get_redis(request)
            if r is None:
                raise RuntimeError("Redis pool not available")

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
                logger.warning(
                    "IP rate limit exceeded: ip=%s count=%d", client_ip, count
                )
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={"detail": "Too many requests. Please slow down."},
                    headers={"Retry-After": "60"},
                )
        except Exception as exc:
            # Fail open — never block users because Redis is unreachable
            logger.error("RateLimitMiddleware Redis error (failing open): %s", exc)

        return await call_next(request)


# ── Layer 2: Per-user dependency (UID-based, route-aware) ─────────────────────

async def check_rate_limit(
    request: Request,
    uid: str,
    limit: int | None = None,
) -> None:
    """
    FastAPI dependency for per-user rate limiting.
    Must be called after Firebase token verification so the UID is available.

    Args:
        request: the FastAPI Request object (needed for pool access + path).
        uid:     the Firebase UID resolved by verify_firebase_token.
        limit:   override the per-route default. If None, uses _ROUTE_LIMITS
                 for the current path or falls back to _DEFAULT_USER_LIMIT.

    Usage:
        # Default (uses _ROUTE_LIMITS lookup):
        await check_rate_limit(raw_request, uid)

        # Explicit override:
        await check_rate_limit(raw_request, uid, limit=5)
    """
    path = request.url.path
    effective_limit = limit if limit is not None else _ROUTE_LIMITS.get(path, _DEFAULT_USER_LIMIT)
    key = f"user_rate:{uid}:{path}"

    try:
        r = await _get_redis(request)
        if r is None:
            raise RuntimeError("Redis pool not available")

        now = time.time()
        window_start = now - 60.0

        pipe = r.pipeline()
        pipe.zremrangebyscore(key, 0, window_start)
        pipe.zadd(key, {str(now): now})
        pipe.expire(key, 60)
        pipe.zcard(key)
        results = await pipe.execute()
        count: int = results[3]

        if count > effective_limit:
            logger.warning(
                "User rate limit exceeded: uid=%s path=%s count=%d limit=%d",
                uid, path, count, effective_limit,
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    f"Rate limit exceeded ({effective_limit} req/min). "
                    "Please wait before sending another request."
                ),
                headers={"Retry-After": "60"},
            )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("check_rate_limit Redis error (failing open): %s", exc)