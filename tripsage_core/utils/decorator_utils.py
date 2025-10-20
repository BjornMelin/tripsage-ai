"""Utility decorators for TripSage Core.

This module provides decorators used across the TripSage codebase for standardized
error handling and client initialization patterns.

Pylint directives:
- disable=import-error: third-party libs resolved at runtime via uv
- disable=too-many-statements: decorators centralize error policy by design
- disable=no-else-return: clarity preferred in some branches
"""
# pylint: disable=import-error, too-many-statements, no-else-return

import functools
import inspect
import logging
import time
from collections.abc import Callable
from typing import Any, TypeVar, cast

from tenacity import (
    RetryCallState,
    RetryError,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from tripsage_core.exceptions import (
    CoreAuthenticationError,
    CoreDatabaseError,
    CoreServiceError,
    CoreValidationError,
)
from tripsage_core.utils.logging_utils import get_logger

from .error_handling_utils import log_exception


logger = get_logger(__name__)

# Type definitions for better type checking
F = TypeVar("F", bound=Callable[..., Any])


def _wants_error_dict_async(func: Callable[..., Any]) -> bool:
    """Async functions: treat missing or exact ``dict`` annotation as dict."""
    ra = inspect.signature(func).return_annotation
    return (ra is inspect.Signature.empty) or (ra is dict)


def _wants_error_dict_sync(func: Callable[..., Any]) -> bool:
    """Sync functions: only exact ``dict`` annotation returns dict."""
    ra = inspect.signature(func).return_annotation
    return ra is dict


def with_error_handling(
    operation_name: str | None = None,
    expected_errors: tuple[type[Exception], ...] | None = None,
    log_extra_func: Callable[..., dict[str, Any]] | None = None,
    reraise_errors: tuple[type[BaseException], ...] | None = None,
    default_return: Any | None = None,
) -> Callable[[F], F]:
    """Decorator for standardized error handling.

    Args:
        operation_name: Custom operation name for logging (defaults to function name)
        expected_errors: Tuple of expected exceptions to handle gracefully
        log_extra_func: Function to generate additional logging context
        reraise_errors: Tuple of exceptions to always re-raise
        default_return: Default value to return for expected errors
            (for dict-returning functions)

    Returns:
        Decorator function that applies error handling to the target function
    """

    def decorator(func: F) -> F:
        # Set defaults
        nonlocal operation_name, expected_errors, reraise_errors
        if operation_name is None:
            operation_name = func.__name__

        if expected_errors is None:
            expected_errors = (
                CoreValidationError,
                CoreAuthenticationError,
                CoreServiceError,
            )

        if reraise_errors is None:
            reraise_errors = (CoreDatabaseError, SystemExit, KeyboardInterrupt)

        # Narrow types for static checkers
        exp_errors: tuple[type[Exception], ...] = expected_errors
        rer_errors: tuple[type[BaseException], ...] = reraise_errors

        # Check if the function is a coroutine function (async)
        # Async coroutine functions
        if inspect.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                """Enhanced async wrapper with comprehensive error handling."""
                start_time = time.time()
                extra_context = {}

                try:
                    # Generate additional logging context if function provided
                    if log_extra_func:
                        try:
                            extra_context = log_extra_func(*args, **kwargs)
                        except Exception as context_error:  # noqa: BLE001
                            logger.warning(
                                "Failed to generate logging context: %s", context_error
                            )

                    # Log operation start
                    logger.info(
                        "Starting operation: %s",
                        operation_name,
                        extra={"operation": operation_name, **extra_context},
                    )

                    # Call the original async function
                    result = await func(*args, **kwargs)

                    # Log successful completion with execution time
                    execution_time = time.time() - start_time
                    logger.info(
                        "Operation completed successfully: %s",
                        operation_name,
                        extra={
                            "operation": operation_name,
                            "execution_time_ms": round(execution_time * 1000, 2),
                            **extra_context,
                        },
                    )

                    return result

                except rer_errors as e:
                    # Always re-raise critical errors
                    execution_time = time.time() - start_time
                    logger.critical(
                        "Critical error in %s: %s",
                        operation_name,
                        e,
                        extra={
                            "operation": operation_name,
                            "error_type": type(e).__name__,
                            "execution_time_ms": round(execution_time * 1000, 2),
                            **extra_context,
                        },
                    )
                    # Avoid passing BaseException-derived objects to log_exception
                    raise

                except exp_errors as e:
                    # Handle expected errors gracefully
                    execution_time = time.time() - start_time
                    logger.warning(
                        "Expected error in %s: %s",
                        operation_name,
                        e,
                        extra={
                            "operation": operation_name,
                            "error_type": type(e).__name__,
                            "error_code": getattr(e, "code", "UNKNOWN"),
                            "execution_time_ms": round(execution_time * 1000, 2),
                            **extra_context,
                        },
                    )

                    # Check if function returns Dict (for agent tools)
                    signature = inspect.signature(func)
                    return_type = signature.return_annotation
                    return_type_str = str(return_type)

                    if "dict" in return_type_str.lower() or return_type is dict:
                        if default_return is not None:
                            return default_return
                        return {
                            "error": str(e),
                            "error_code": getattr(e, "code", "UNKNOWN"),
                        }

                    raise  # Re-raise for non-dict returning functions

                except Exception as e:
                    # Handle unexpected errors
                    execution_time = time.time() - start_time
                    logger.exception(
                        "Unexpected error in %s",
                        operation_name,
                        extra={
                            "operation": operation_name,
                            "error_type": type(e).__name__,
                            "execution_time_ms": round(execution_time * 1000, 2),
                            **extra_context,
                        },
                    )
                    log_exception(cast(Exception, e), operation_name)

                    # Preserve original error context; avoid wrapping

                    # Check if function returns Dict (for agent tools)
                    if _wants_error_dict_async(func):
                        # Preserve original error message for callers that expect it
                        return {"error": str(e)}

                    # Re-raise the original error for non-dict returns
                    raise

            return cast(F, async_wrapper)

        # Async generator functions
        elif inspect.isasyncgenfunction(func):

            @functools.wraps(func)
            async def async_gen_wrapper(*args: Any, **kwargs: Any) -> Any:
                """Consume async generator safely so `await` calls do not error.

                Returns an empty dict for compatibility with tests that call
                `await` on decorated async generators.
                """
                try:
                    async for _ in func(*args, **kwargs):
                        pass
                    return {}
                except Exception as e:
                    log_exception(e, func.__name__)
                    if _wants_error_dict_async(func):
                        return {"error": str(e)}
                    raise

            return cast(F, async_gen_wrapper)

        # For synchronous functions
        else:

            @functools.wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                """Enhanced sync wrapper with comprehensive error handling."""
                start_time = time.time()
                extra_context = {}

                try:
                    # Generate additional logging context if function provided
                    if log_extra_func:
                        try:
                            extra_context = log_extra_func(*args, **kwargs)
                        except Exception as context_error:  # noqa: BLE001
                            logger.warning(
                                "Failed to generate logging context: %s", context_error
                            )

                    # Log operation start
                    logger.info(
                        "Starting operation: %s",
                        operation_name,
                        extra={"operation": operation_name, **extra_context},
                    )

                    # Call the original sync function
                    result = func(*args, **kwargs)

                    # Log successful completion with execution time
                    execution_time = time.time() - start_time
                    logger.info(
                        "Operation completed successfully: %s",
                        operation_name,
                        extra={
                            "operation": operation_name,
                            "execution_time_ms": round(execution_time * 1000, 2),
                            **extra_context,
                        },
                    )

                    return result

                except rer_errors as e:
                    # Always re-raise critical errors
                    execution_time = time.time() - start_time
                    logger.critical(
                        "Critical error in %s: %s",
                        operation_name,
                        e,
                        extra={
                            "operation": operation_name,
                            "error_type": type(e).__name__,
                            "execution_time_ms": round(execution_time * 1000, 2),
                            **extra_context,
                        },
                    )
                    # Skip log_exception for BaseException-derived types
                    raise

                except exp_errors as e:
                    # Handle expected errors gracefully
                    execution_time = time.time() - start_time
                    logger.warning(
                        "Expected error in %s: %s",
                        operation_name,
                        e,
                        extra={
                            "operation": operation_name,
                            "error_type": type(e).__name__,
                            "error_code": getattr(e, "code", "UNKNOWN"),
                            "execution_time_ms": round(execution_time * 1000, 2),
                            **extra_context,
                        },
                    )

                    # Check if function returns Dict (for agent tools)
                    signature = inspect.signature(func)
                    return_type = signature.return_annotation
                    return_type_str = str(return_type)

                    if "dict" in return_type_str.lower() or return_type is dict:
                        if default_return is not None:
                            return default_return
                        return {
                            "error": str(e),
                            "error_code": getattr(e, "code", "UNKNOWN"),
                        }

                    # Re-raise for non-dict returning functions
                    raise

                except Exception as e:
                    # Handle unexpected errors
                    execution_time = time.time() - start_time
                    logger.exception(
                        "Unexpected error in %s",
                        operation_name,
                        extra={
                            "operation": operation_name,
                            "error_type": type(e).__name__,
                            "execution_time_ms": round(execution_time * 1000, 2),
                            **extra_context,
                        },
                    )
                    log_exception(e, operation_name)

                    # Preserve original error context; avoid wrapping

                    if _wants_error_dict_sync(func):
                        return {"error": str(e)}

                    raise  # Re-raise the original error

            return cast(F, sync_wrapper)

    return decorator


def ensure_memory_client_initialized[F: Callable[..., Any]](func: F) -> F:
    """Decorator to ensure memory service is initialized.

    Args:
        func: Function to decorate (must be async)

    Returns:
        Decorated function with memory service initialization
    """
    if not inspect.iscoroutinefunction(func):
        raise TypeError(
            f"ensure_memory_client_initialized can only be used with async "
            f"functions. {func.__name__} is not async."
        )

    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        """Wrapper function that initializes memory service."""
        try:
            # Note: The Core memory service has automatic initialization
            # via dependency injection in the service layer, so explicit
            # initialization is no longer needed here.

            # Call the original function
            return await func(*args, **kwargs)
        except Exception as e:
            # Get function name for better error logging
            func_name = func.__name__
            logger.exception("Error in %s", func_name)
            log_exception(e)

            # Return error response for dict-returning async functions
            if inspect.signature(func).return_annotation is dict:
                return {"error": str(e)}
            raise  # Re-raise for non-dict returning functions

    return cast(F, wrapper)


def retry_on_failure(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[F], F]:
    """Retry failed operations with exponential backoff using Tenacity.

    Args:
        max_attempts: Maximum number of attempts (including the first call)
        delay: Initial delay (seconds) before the first retry
        backoff_factor: Multiplicative backoff factor per retry
        exceptions: Exception types that should trigger a retry

    Returns:
        Decorator that applies retry logic to the target function.
    """
    # Build a Tenacity wait policy matching prior semantics (no jitter).
    wait_policy = wait_exponential(multiplier=delay, min=delay, exp_base=backoff_factor)

    def _log_retry(retry_state: RetryCallState) -> None:
        # Log at WARNING on retry, ERROR on final failure for visibility.
        attempt = retry_state.attempt_number
        fn_name = getattr(retry_state.fn, "__name__", str(retry_state.fn))
        exc = retry_state.outcome.exception() if retry_state.outcome else None
        if exc is not None:
            level = logging.WARNING if attempt < max_attempts else logging.ERROR
            logger.log(
                level,
                "%s failed (attempt %s/%s): %s",
                fn_name,
                attempt,
                max_attempts,
                exc,
            )

    def decorator(func: F) -> F:
        policy = retry(
            reraise=False,
            stop=stop_after_attempt(max_attempts),
            retry=retry_if_exception_type(exceptions),
            wait=wait_policy,
            before_sleep=_log_retry,
        )

        if inspect.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapped(*args: Any, **kwargs: Any) -> Any:
                wrapped = policy(func)  # type: ignore[no-untyped-call]
                try:
                    return await wrapped(*args, **kwargs)  # type: ignore[misc]
                except RetryError as re:  # pragma: no cover - exercised via tests
                    logger.exception(
                        "%s failed after %s attempts", func.__name__, max_attempts
                    )
                    exc = (
                        cast(BaseException, re.last_attempt.exception())
                        if re.last_attempt
                        else re
                    )
                    raise exc from None

            return cast(F, async_wrapped)

        @functools.wraps(func)
        def sync_wrapped(*args: Any, **kwargs: Any) -> Any:
            wrapped = policy(func)  # type: ignore[no-untyped-call]
            try:
                return wrapped(*args, **kwargs)  # type: ignore[misc]
            except RetryError as re:  # pragma: no cover - exercised via tests
                logger.exception(
                    "%s failed after %s attempts", func.__name__, max_attempts
                )
                exc = (
                    cast(BaseException, re.last_attempt.exception())
                    if re.last_attempt
                    else re
                )
                raise exc from None

        return cast(F, sync_wrapped)

    return decorator


__all__ = [
    "ensure_memory_client_initialized",
    "retry_on_failure",
    "with_error_handling",
]
