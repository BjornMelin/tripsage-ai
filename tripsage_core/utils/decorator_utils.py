"""Utility decorators for TripSage Core.

This module provides decorators used across the TripSage codebase for standardized
error handling and client initialization patterns.
"""

import asyncio
import functools
import inspect
import time
from collections.abc import Callable
from typing import Any, TypeVar, cast

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


def with_error_handling(
    operation_name: str | None = None,
    expected_errors: tuple[Exception, ...] | None = None,
    log_extra_func: Callable[..., dict[str, Any]] | None = None,
    reraise_errors: tuple[Exception, ...] | None = None,
    default_return: Any | None = None,
) -> Callable[[F], F]:
    """Enhanced decorator for standardized error handling with comprehensive features.

    This decorator provides advanced error handling with configurable parameters,
    proper logging, performance metrics, and support for both sync and async functions.
    It follows the latest best practices for Python error handling decorators.

    Args:
        operation_name: Custom operation name for logging (defaults to function name)
        expected_errors: Tuple of expected exceptions to handle gracefully
        log_extra_func: Function to generate additional logging context
        reraise_errors: Tuple of exceptions to always re-raise
        default_return: Default value to return for expected errors
            (for dict-returning functions)

    Returns:
        Decorator function that applies error handling to the target function

    Example:
        ```python
        # Basic usage
        @with_error_handling()
        async def fetch_user_data(user_id: str) -> Dict[str, Any]:
            # Function implementation
            pass

        # Advanced usage with custom configuration
        @with_error_handling(
            operation_name="user_authentication",
            expected_errors=(CoreValidationError, CoreAuthenticationError),
            log_extra_func=lambda *args, **kwargs: {"user_id": kwargs.get("user_id")},
            reraise_errors=(CoreDatabaseError,),
            default_return={"error": "Authentication failed"}
        )
        async def authenticate_user(user_id: str, password: str) -> Dict[str, Any]:
            # Function implementation
            pass
        ```
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

        # Check if the function is a coroutine function (async)
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
                        except Exception as context_error:
                            logger.warning(
                                f"Failed to generate logging context: {context_error}"
                            )

                    # Log operation start
                    logger.info(
                        f"Starting operation: {operation_name}",
                        extra={"operation": operation_name, **extra_context},
                    )

                    # Call the original async function
                    result = await func(*args, **kwargs)

                    # Log successful completion with execution time
                    execution_time = time.time() - start_time
                    logger.info(
                        f"Operation completed successfully: {operation_name}",
                        extra={
                            "operation": operation_name,
                            "execution_time_ms": round(execution_time * 1000, 2),
                            **extra_context,
                        },
                    )

                    return result

                except reraise_errors as e:
                    # Always re-raise critical errors
                    execution_time = time.time() - start_time
                    logger.critical(
                        f"Critical error in {operation_name}: {e!s}",
                        extra={
                            "operation": operation_name,
                            "error_type": type(e).__name__,
                            "execution_time_ms": round(execution_time * 1000, 2),
                            **extra_context,
                        },
                    )
                    log_exception(e, operation_name)
                    raise

                except expected_errors as e:
                    # Handle expected errors gracefully
                    execution_time = time.time() - start_time
                    logger.warning(
                        f"Expected error in {operation_name}: {e!s}",
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
                    logger.error(
                        f"Unexpected error in {operation_name}: {e!s}",
                        extra={
                            "operation": operation_name,
                            "error_type": type(e).__name__,
                            "execution_time_ms": round(execution_time * 1000, 2),
                            **extra_context,
                        },
                    )
                    log_exception(e, operation_name)

                    # Wrap unexpected errors in CoreServiceError
                    service_error = CoreServiceError(
                        message=f"Operation failed: {operation_name}",
                        code="OPERATION_FAILED",
                        details={
                            "original_error": str(e),
                            "operation": operation_name,
                            **extra_context,
                        },
                    )

                    # Check if function returns Dict (for agent tools)
                    signature = inspect.signature(func)
                    return_type = signature.return_annotation
                    return_type_str = str(return_type)

                    if "dict" in return_type_str.lower() or return_type is dict:
                        return service_error.to_dict()

                    # Re-raise the wrapped error
                    raise service_error from e

            return cast(F, async_wrapper)

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
                        except Exception as context_error:
                            logger.warning(
                                f"Failed to generate logging context: {context_error}"
                            )

                    # Log operation start
                    logger.info(
                        f"Starting operation: {operation_name}",
                        extra={"operation": operation_name, **extra_context},
                    )

                    # Call the original sync function
                    result = func(*args, **kwargs)

                    # Log successful completion with execution time
                    execution_time = time.time() - start_time
                    logger.info(
                        f"Operation completed successfully: {operation_name}",
                        extra={
                            "operation": operation_name,
                            "execution_time_ms": round(execution_time * 1000, 2),
                            **extra_context,
                        },
                    )

                    return result

                except reraise_errors as e:
                    # Always re-raise critical errors
                    execution_time = time.time() - start_time
                    logger.critical(
                        f"Critical error in {operation_name}: {e!s}",
                        extra={
                            "operation": operation_name,
                            "error_type": type(e).__name__,
                            "execution_time_ms": round(execution_time * 1000, 2),
                            **extra_context,
                        },
                    )
                    log_exception(e, operation_name)
                    raise

                except expected_errors as e:
                    # Handle expected errors gracefully
                    execution_time = time.time() - start_time
                    logger.warning(
                        f"Expected error in {operation_name}: {e!s}",
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
                    logger.error(
                        f"Unexpected error in {operation_name}: {e!s}",
                        extra={
                            "operation": operation_name,
                            "error_type": type(e).__name__,
                            "execution_time_ms": round(execution_time * 1000, 2),
                            **extra_context,
                        },
                    )
                    log_exception(e, operation_name)

                    # Wrap unexpected errors in CoreServiceError
                    service_error = CoreServiceError(
                        message=f"Operation failed: {operation_name}",
                        code="OPERATION_FAILED",
                        details={
                            "original_error": str(e),
                            "operation": operation_name,
                            **extra_context,
                        },
                    )

                    # Check if function returns Dict (for agent tools)
                    signature = inspect.signature(func)
                    return_type = signature.return_annotation
                    return_type_str = str(return_type)

                    if "dict" in return_type_str.lower() or return_type is dict:
                        return service_error.to_dict()

                    # Re-raise the wrapped error
                    raise service_error from e

            return cast(F, sync_wrapper)

    return decorator


def ensure_memory_client_initialized(func: F) -> F:
    """Decorator to ensure memory service is initialized.

    This decorator ensures that the memory service is initialized before
    the decorated function is called. This avoids redundant initialization
    calls in each function that uses the memory service.

    Args:
        func: Function to decorate (must be async)

    Returns:
        Decorated function with memory service initialization

    Example:
        ```python
        @function_tool
        @ensure_memory_client_initialized
        async def add_memory() -> Dict[str, Any]:
            # Memory service is already initialized here
            from tripsage_core.services.business.memory_service import MemoryService
            memory_service = MemoryService()
            result = await memory_service.add_memory(
                user_id="user-123",
                content="Trip preference"
            )
            return {"memory_id": result}
        ```
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
            logger.error(f"Error in {func_name}: {e!s}")
            log_exception(e)

            # Return error response in the expected format for agent tools
            # Only do this if the function returns a dict (for agent tools)
            signature = inspect.signature(func)
            if "Dict" in str(signature.return_annotation):
                return {"error": str(e)}
            # Re-raise for non-dict returning functions
            raise

    return cast(F, wrapper)


# Retry decorator for network operations
def retry_on_failure(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,),
) -> Callable[[F], F]:
    """Decorator to retry failed operations with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff_factor: Factor to multiply delay by after each retry
        exceptions: Tuple of exceptions to catch and retry

    Returns:
        Decorated function with retry logic
    """

    def decorator(func: F) -> F:
        if inspect.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                last_exception = None
                current_delay = delay

                for attempt in range(max_attempts):
                    try:
                        return await func(*args, **kwargs)
                    except exceptions as e:
                        last_exception = e
                        if attempt < max_attempts - 1:
                            logger.warning(
                                f"{func.__name__} failed "
                                f"(attempt {attempt + 1}/{max_attempts}): {e}"
                            )
                            await asyncio.sleep(current_delay)
                            current_delay *= backoff_factor
                        else:
                            logger.error(
                                f"{func.__name__} failed after {max_attempts} attempts"
                            )
                            raise

                if last_exception:
                    raise last_exception

            return cast(F, async_wrapper)
        else:

            @functools.wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                last_exception = None
                current_delay = delay

                for attempt in range(max_attempts):
                    try:
                        return func(*args, **kwargs)
                    except exceptions as e:
                        last_exception = e
                        if attempt < max_attempts - 1:
                            logger.warning(
                                f"{func.__name__} failed "
                                f"(attempt {attempt + 1}/{max_attempts}): {e}"
                            )
                            import time

                            time.sleep(current_delay)
                            current_delay *= backoff_factor
                        else:
                            logger.error(
                                f"{func.__name__} failed after {max_attempts} attempts"
                            )
                            raise

                if last_exception:
                    raise last_exception

            return cast(F, sync_wrapper)

    return decorator


__all__ = [
    "ensure_memory_client_initialized",
    "retry_on_failure",
    "with_error_handling",
]
