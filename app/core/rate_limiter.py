import logging
from typing import Optional
from fastapi import HTTPException, Request, status
from app.core.dependencies import get_redis_memory

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    FastAPI dependency for Redis-backed rate limiting.
    Limits requests per client IP within a sliding or fixed time window.
    Fails open gracefully if Redis is unavailable.
    """

    def __init__(
        self,
        times: int = 30,
        seconds: int = 60,
        key_prefix: str = "ratelimit",
    ) -> None:
        self.times = times
        self.seconds = seconds
        self.key_prefix = key_prefix

    async def __call__(self, request: Request) -> None:
        redis_memory = get_redis_memory()
        cli = redis_memory.client
        if cli is None:
            # Redis is not configured or unavailable; fail open
            return

        # Extract client IP (handle proxies like Cloudflare/Nginx if present)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"

        # Unique key based on prefix, endpoint, and client IP
        endpoint_tag = request.url.path.strip("/").replace("/", "_") or "root"
        key = f"{self.key_prefix}:{endpoint_tag}:{client_ip}"

        try:
            current = cli.incr(key)
            if current == 1:
                cli.expire(key, self.seconds)

            ttl = cli.ttl(key)
            if ttl < 0:
                cli.expire(key, self.seconds)
                ttl = self.seconds

            if current > self.times:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded: {self.times} requests per {self.seconds}s. Please retry in {ttl} seconds.",
                    headers={
                        "Retry-After": str(ttl),
                        "X-RateLimit-Limit": str(self.times),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(ttl),
                    },
                )
        except HTTPException:
            raise
        except Exception as exc:
            # Fail-open: don't block legitimate users if Redis has a transient hiccup
            logger.warning(f"RateLimiter check encountered non-fatal error: {exc}")
