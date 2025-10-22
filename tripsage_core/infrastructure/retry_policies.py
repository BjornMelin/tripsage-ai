"""Shared Tenacity retry policies.

This module centralizes retry configurations for common TripSage use cases to
avoid bespoke wrappers and ensure consistent behavior across services.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable

# pylint: disable=import-error
from tenacity import (
    AsyncRetrying,
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    stop_after_delay,
    stop_any,
    wait_random_exponential,
)


logger = logging.getLogger(__name__)


def httpx_async_retry(
    *,
    attempts: int = 3,
    max_delay: float = 10.0,
    include_status_error: bool = False,
):
    """Return a Tenacity decorator for httpx async calls.

    Args:
        attempts: Maximum attempts including the first call.
        max_delay: Maximum backoff delay in seconds.
        include_status_error: When True, retry ``httpx.HTTPStatusError`` too.

    Returns:
        A configured ``@retry`` decorator for async httpx operations.
    """
    import httpx  # local import to avoid hard dep at import-time

    ex_list: list[type[BaseException]] = [
        httpx.TimeoutException,
        httpx.ConnectError,
    ]
    if include_status_error:
        ex_list.append(httpx.HTTPStatusError)
    excs: tuple[type[BaseException], ...] = tuple(ex_list)

    return retry(
        stop=stop_any(stop_after_attempt(attempts), stop_after_delay(30)),
        wait=wait_random_exponential(min=1, max=max_delay),
        retry=retry_if_exception_type(excs),
        reraise=True,
        before_sleep=before_sleep_log(logger, logging.WARNING, exc_info=True),
    )


def httpx_block_retry(
    *,
    attempts: int = 3,
    max_delay: float = 10.0,
    include_status_error: bool = False,
) -> AsyncRetrying:
    """Return an ``AsyncRetrying`` controller for block-style async code.

    Args:
        attempts: Maximum attempts including the first call.
        max_delay: Maximum backoff delay in seconds.
        include_status_error: When True, retry ``httpx.HTTPStatusError`` too.

    Returns:
        ``AsyncRetrying`` controller configured for httpx operations.
    """
    import httpx  # safe: only in paths that use httpx

    ex_list: list[type[BaseException]] = [
        httpx.TimeoutException,
        httpx.ConnectError,
    ]
    if include_status_error:
        ex_list.append(httpx.HTTPStatusError)
    excs: tuple[type[BaseException], ...] = tuple(ex_list)

    return AsyncRetrying(
        stop=stop_any(stop_after_attempt(attempts), stop_after_delay(30)),
        wait=wait_random_exponential(min=1, max=max_delay),
        retry=retry_if_exception_type(excs),
        reraise=True,
        before_sleep=before_sleep_log(logger, logging.WARNING, exc_info=True),
    )


def generic_retry(
    *,
    attempts: int = 3,
    max_delay: float = 10.0,
    exceptions: Iterable[type[BaseException]] = (Exception,),
):
    """Return a Tenacity decorator for generic sync code.

    Args:
        attempts: Maximum attempts including the first call.
        max_delay: Maximum backoff delay in seconds.
        exceptions: Exception types to retry.

    Returns:
        A configured ``@retry`` decorator for synchronous operations.
    """
    return retry(
        stop=stop_after_attempt(attempts),
        wait=wait_random_exponential(min=1, max=max_delay),
        retry=retry_if_exception_type(tuple(exceptions)),
        reraise=True,
        before_sleep=before_sleep_log(logger, logging.WARNING, exc_info=True),
    )


__all__ = [
    "generic_retry",
    "httpx_async_retry",
    "httpx_block_retry",
]
