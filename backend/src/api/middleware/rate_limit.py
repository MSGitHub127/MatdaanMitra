from fastapi import HTTPException, status, Request
from typing import Optional
import redis
import time
import logging
from ..config.settings import settings

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Sliding window rate limiter using Redis.
    30 requests/minute per Firebase UID.
    """

    def __init__(self):
        self.redis_client = redis.from_url(settings.redis_url, decode_responses=True)
        self.max_requests = 30
        self.window_seconds = 60

    async def check(self, uid: str, endpoint: str) -> bool:
        """
        Check if the user has exceeded the rate limit.
        Returns True if allowed, False if rate limit exceeded.
        """
        try:
            key = f"rate:{uid}:{endpoint}"
            now = time.time()
            window_start = now - self.window_seconds

            # Remove old entries
            self.redis_client.zremrangebyscore(key, 0, window_start)

            # Add current request
            self.redis_client.zadd(key, {str(now): now})

            # Set expiration
            self.redis_client.expire(key, self.window_seconds)

            # Count requests in window
            count = self.redis_client.zcard(key)

            if count > self.max_requests:
                logger.warning(f"Rate limit exceeded for user {uid} on {endpoint}")
                return False

            return True

        except Exception as e:
            logger.error(f"Rate limiter error: {e}")
            # Fail open - allow request if Redis is down
            return True


# Singleton instance
rate_limiter = RateLimiter()


async def check_rate_limit(request: Request, uid: str):
    """FastAPI dependency to check rate limits."""
    endpoint = request.url.path

    if not await rate_limiter.check(uid, endpoint):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please wait before asking again.",
            headers={"Retry-After": "60"},
        )
