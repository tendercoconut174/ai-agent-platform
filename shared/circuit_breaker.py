"""Circuit breaker to avoid cascading failures."""

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CircuitBreaker:
    """Simple circuit breaker: opens after failure_threshold failures, stays open for cooldown_seconds."""

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        cooldown_seconds: float = 60.0,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self._failures = 0
        self._last_failure_time: float | None = None
        self._lock = asyncio.Lock()

    @property
    def is_open(self) -> bool:
        """Circuit is open (blocking calls) if we hit threshold and cooldown hasn't passed."""
        if self._failures < self.failure_threshold:
            return False
        if self._last_failure_time is None:
            return True
        if time.monotonic() - self._last_failure_time >= self.cooldown_seconds:
            return False  # cooldown passed, allow half-open
        return True

    async def _record_success(self) -> None:
        async with self._lock:
            self._failures = 0

    async def _record_failure(self) -> None:
        async with self._lock:
            self._failures += 1
            self._last_failure_time = time.monotonic()
            if self._failures >= self.failure_threshold:
                logger.warning(
                    "[circuit_breaker] %s OPEN after %d failures. Cooldown %.0fs",
                    self.name,
                    self._failures,
                    self.cooldown_seconds,
                )

    def __call__(
        self,
        exceptions: tuple[type[Exception], ...] = (Exception,),
    ):
        """Decorator for async functions."""

        def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
            @wraps(func)
            async def wrapper(*args, **kwargs) -> T:
                if self.is_open:
                    raise RuntimeError(
                        f"Circuit breaker '{self.name}' is OPEN. "
                        f"Try again after {self.cooldown_seconds}s cooldown."
                    )
                try:
                    result = await func(*args, **kwargs)
                    await self._record_success()
                    return result
                except exceptions as e:
                    await self._record_failure()
                    raise e

            return wrapper

        return decorator


# Shared circuit breakers for key services
LLM_CIRCUIT = CircuitBreaker("llm", failure_threshold=5, cooldown_seconds=60.0)
WEB_SEARCH_CIRCUIT = CircuitBreaker("web_search", failure_threshold=5, cooldown_seconds=30.0)
