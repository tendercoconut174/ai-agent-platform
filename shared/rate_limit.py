"""In-memory rate limiter for API endpoints."""

from __future__ import annotations

import asyncio
import logging
import os
import time
from collections import defaultdict
from typing import Optional

from starlette.requests import Request

logger = logging.getLogger(__name__)


class InMemoryRateLimiter:
    """Simple sliding-window rate limiter. Key -> (timestamps)."""

    def __init__(self, requests_per_minute: int = 60, window_seconds: float = 60.0):
        self.rpm = requests_per_minute
        self.window = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def is_allowed(self, key: str = "default") -> bool:
        """Check if request is allowed. Records the request if allowed."""
        async with self._lock:
            now = time.monotonic()
            cutoff = now - self.window
            self._requests[key] = [t for t in self._requests[key] if t > cutoff]
            if len(self._requests[key]) >= self.rpm:
                return False
            self._requests[key].append(now)
            return True


def get_client_key(request: Optional[Request] = None) -> str:
    """Get rate limit key from request (IP or forwarded)."""
    if request is None:
        return "default"
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if hasattr(request, "client") and request.client:
        return getattr(request.client, "host", "default")
    return "default"


# Global limiter - 60 req/min per IP by default
DEFAULT_RPM = int(os.getenv("RATE_LIMIT_RPM", "60"))
_limiter = InMemoryRateLimiter(requests_per_minute=DEFAULT_RPM)


async def rate_limit_dep(request: Request) -> None:
    """FastAPI dependency for rate limiting by client IP."""
    key = get_client_key(request)
    if not await _limiter.is_allowed(key):
        logger.warning("[rate_limit] Rate limit exceeded | key=%s", key[:20])
        from fastapi import HTTPException
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again later.")
