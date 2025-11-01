"""Shared Tenacity retry policies.

This module centralizes retry configurations for common TripSage use cases to
avoid bespoke wrappers and ensure consistent behavior across services.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable

from tenacity import (
    AsyncRetrying,
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    stop_after_delay,
    stop_any,
    wait_fixed,
    wait_incrementing,
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


def tripsage_retry(
    *,
    attempts: int = 3,
    max_delay: float = 10.0,
    exceptions: Iterable[type[BaseException]] | None = None,
    backoff_strategy: str = "exponential",
    include_httpx_errors: bool = False,
    include_status_errors: bool = False,
    reraise: bool = True,
    log_level: int = logging.WARNING,
):
    """Unified TripSage retry decorator with configurable strategies.

    This decorator provides a centralized retry mechanism for all TripSage services,
    supporting different backoff strategies and exception types.

    Args:
        attempts: Maximum attempts including the first call.
        max_delay: Maximum backoff delay in seconds.
        exceptions: Custom exception types to retry. If None, uses default set.
        backoff_strategy: Backoff strategy - "exponential", "fixed", "linear".
        include_httpx_errors: Include httpx network errors
                              (TimeoutException, ConnectError).
        include_status_errors: Include httpx HTTPStatusError.
        reraise: Whether to re-raise the last exception after all retries.
        log_level: Logging level for retry attempts.

    Returns:
        Configured @retry decorator.
    """
    import httpx  # local import to avoid hard dep

    # Build exception list
    ex_list: list[type[BaseException]] = []
    if exceptions:
        ex_list.extend(exceptions)
    else:
        # Default exceptions
        ex_list.extend([ConnectionError, TimeoutError, RuntimeError])

    if include_httpx_errors:
        ex_list.extend([httpx.TimeoutException, httpx.ConnectError])

    if include_status_errors:
        ex_list.append(httpx.HTTPStatusError)

    excs = tuple(ex_list)

    # Choose wait strategy using tenacity primitives (no lambdas)
    if backoff_strategy == "exponential":
        wait_strategy = wait_random_exponential(min=1, max=max_delay)
    elif backoff_strategy == "fixed":
        wait_strategy = wait_fixed(max_delay)
    elif backoff_strategy == "linear":
        # Linear backoff capped at max_delay
        wait_strategy = wait_incrementing(start=1, increment=2, max=max_delay)
    else:
        wait_strategy = wait_random_exponential(min=1, max=max_delay)

    return retry(
        stop=stop_any(
            stop_after_attempt(attempts), stop_after_delay(60)
        ),  # Max 60s total
        wait=wait_strategy,
        retry=retry_if_exception_type(excs),
        reraise=reraise,
        before_sleep=before_sleep_log(logger, log_level, exc_info=True),
    )


__all__ = [
    "generic_retry",
    "httpx_async_retry",
    "httpx_block_retry",
    "tripsage_retry",
]
