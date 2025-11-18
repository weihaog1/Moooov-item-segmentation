"""Retry utility with exponential backoff for async functions."""

import asyncio
import random
from functools import wraps
from typing import Callable, TypeVar, Any

T = TypeVar("T")


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: int = 2,
    exceptions: tuple = (asyncio.TimeoutError, ConnectionError, Exception),
):
    """
    Decorator for async functions with exponential backoff retry.

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds for exponential backoff
        exceptions: Tuple of exception types to catch and retry

    Returns:
        Decorated function with retry logic

    Example:
        @retry_with_backoff(max_retries=3, base_delay=2)
        async def fetch_data():
            # This will retry up to 3 times with exponential backoff
            return await api_call()
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)

                except exceptions as e:
                    last_exception = e

                    # If this was the last attempt, raise the exception
                    if attempt == max_retries:
                        raise

                    # Calculate delay with exponential backoff and jitter
                    # delay = base_delay * (2 ^ attempt) + random jitter
                    delay = base_delay * (2**attempt) + random.uniform(0, 1)

                    # Log retry attempt (optional, can be removed if too verbose)
                    print(
                        f"Retry attempt {attempt + 1}/{max_retries} after {delay:.1f}s "
                        f"for {func.__name__}: {type(e).__name__}"
                    )

                    # Wait before retry
                    await asyncio.sleep(delay)

            # This should never be reached, but just in case
            if last_exception:
                raise last_exception

        return wrapper

    return decorator
