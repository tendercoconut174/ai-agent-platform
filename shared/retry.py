"""Retry utilities with exponential backoff."""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import TypeVar

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


def retry_async(
    max_attempts: int = 3,
    min_wait: float = 1.0,
    max_wait: float = 30.0,
    exceptions: tuple[type[Exception], ...] = (Exception,),
):
    """Decorator for async functions with exponential backoff retry."""

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            last_exc = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exc = e
                    if attempt == max_attempts:
                        raise
                    wait = min(max_wait, min_wait * (2 ** (attempt - 1)))
                    logger.warning(
                        "[retry] %s attempt %d/%d failed: %s. Retrying in %.1fs",
                        func.__name__,
                        attempt,
                        max_attempts,
                        e,
                        wait,
                    )
                    await asyncio.sleep(wait)
            raise last_exc  # type: ignore

        return wrapper

    return decorator


def retry_sync(
    max_attempts: int = 3,
    min_wait: float = 1.0,
    max_wait: float = 30.0,
    exceptions: tuple[type[Exception], ...] = (Exception,),
):
    """Decorator for sync functions with exponential backoff retry."""

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            r = retry(
                stop=stop_after_attempt(max_attempts),
                wait=wait_exponential(multiplier=min_wait, max=max_wait),
                retry=retry_if_exception_type(exceptions),
                reraise=True,
            )
            return r(func)(*args, **kwargs)

        return wrapper

    return decorator
