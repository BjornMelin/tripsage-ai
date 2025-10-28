"""Error handling utilities for TripSage Core.

This module provides standardized error handling functionality for the TripSage
application, building on top of the core exception system.
"""

import functools
import inspect
import logging
import types
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar, cast

from tripsage_core.exceptions import (
    CoreDatabaseError,
    CoreExternalAPIError,
    CoreTripSageError,
    CoreValidationError,
    safe_execute as core_safe_execute,
    with_error_handling as core_with_error_handling,
)
from tripsage_core.utils.logging_utils import get_logger


logger = get_logger(__name__)

# Type variable for function return type
T = TypeVar("T")
R = TypeVar("R")
F = TypeVar("F", bound=Callable[..., Any])


def log_exception(exc: Exception, logger_name: str | None = None) -> None:
    """Log an exception with appropriate level and details.

    Args:
        exc: The exception to log
        logger_name: Optional specific logger name to use
    """
    log = logger if logger_name is None else get_logger(logger_name)

    if isinstance(exc, CoreExternalAPIError):
        # Extract API-specific details from the core exception
        details = exc.details.additional_context or {}
        log.error(
            "API Error: %s\nService: %s\nAPI Status Code: %s\nAPI Response: %s",
            exc.message,
            exc.details.service,
            details.get("api_status_code"),
            details.get("api_response"),
        )
    elif isinstance(exc, CoreTripSageError):
        # Use warning level for expected application errors
        log.warning(
            "Application error: %s - %s",
            exc.__class__.__name__,
            exc.message,
            extra={"details": exc.details.model_dump(exclude_none=True)},
        )
    else:
        # Use error level for unexpected system errors
        log.error(
            "System error: %s - %s",
            exc.__class__.__name__,
            str(exc),
        )


def safe_execute_with_logging[T, R](
    func: Callable[..., T], *args: Any, fallback: R = None, **kwargs: Any
) -> T | R:
    """Execute a function with error handling and TripSage logging.

    Args:
        func: The function to execute
        *args: Arguments to pass to the function
        fallback: Value to return if execution fails
        **kwargs: Keyword arguments to pass to the function

    Returns:
        The function result or fallback value
    """
    return core_safe_execute(
        func,
        *args,
        fallback=fallback,
        logger=None,
        **kwargs,
    )


def with_error_handling_and_logging(
    fallback: Any = None,
    logger_instance: Any | None = None,
    re_raise: bool = False,
):
    """Decorator to add error handling with TripSage logging to functions.

    Args:
        fallback: Default value to return on error
        logger_instance: Optional logger for error reporting (defaults to TripSage)
        re_raise: Whether to re-raise the exception after logging

    Returns:
        Decorator function
    """
    return core_with_error_handling(
        fallback=fallback,
        logger=cast(logging.Logger | None, None),
        re_raise=re_raise,
    )


# Factory functions for creating specific TripSage exceptions


def create_api_error(
    message: str,
    service: str,
    status_code: int | None = None,
    response: dict[str, Any] | None = None,
) -> CoreExternalAPIError:
    """Create an API error with TripSage-specific formatting.

    Args:
        message: Error message
        service: Name of the API service that failed
        status_code: HTTP status code if applicable
        response: Raw API response if available

    Returns:
        CoreExternalAPIError instance
    """
    return CoreExternalAPIError(
        message=message,
        code=f"{service.upper()}_API_ERROR",
        api_service=service,
        api_status_code=status_code,
        api_response=response,
    )


def create_validation_error(
    message: str,
    field: str | None = None,
    value: Any | None = None,
    constraint: str | None = None,
) -> CoreValidationError:
    """Create a validation error with TripSage-specific formatting.

    Args:
        message: Error message
        field: Name of the field that failed validation
        value: The invalid value
        constraint: Description of the constraint that was violated

    Returns:
        CoreValidationError instance
    """
    return CoreValidationError(
        message=message,
        field=field,
        value=value,
        constraint=constraint,
    )


def create_database_error(
    message: str,
    operation: str | None = None,
    query: str | None = None,
    params: dict[str, Any] | None = None,
    table: str | None = None,
) -> CoreDatabaseError:
    """Create a database error with TripSage-specific formatting.

    Args:
        message: Error message
        operation: Type of database operation that failed
        query: The query that failed, if applicable
        params: Query parameters, if applicable
        table: Name of the table involved

    Returns:
        CoreDatabaseError instance
    """
    return CoreDatabaseError(
        message=message,
        operation=operation,
        table=table,
    )


# Error context manager for TripSage operations
class TripSageErrorContext:
    """Context manager for enhanced error handling in TripSage operations."""

    def __init__(
        self,
        operation: str,
        service: str | None = None,
        user_id: str | None = None,
        request_id: str | None = None,
        logger_instance: Any | None = None,
    ):
        """Initialize the error context.

        Args:
            operation: Name of the operation being performed
            service: Name of the service performing the operation
            user_id: User ID associated with the operation
            request_id: Request ID for tracing
            logger_instance: Optional logger instance
        """
        self.operation = operation
        self.service = service
        self.user_id = user_id
        self.request_id = request_id
        self.logger = logger_instance or logger

    def __enter__(self):
        """Enter the error context."""
        self.logger.debug(
            "Starting operation: %s",
            self.operation,
            extra={
                "service": self.service,
                "user_id": self.user_id,
                "request_id": self.request_id,
            },
        )
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> bool:
        """Exit the error context and handle any exceptions."""
        if exc_type is not None and exc_val is not None:
            # Enhance the exception with context information
            if isinstance(exc_val, CoreTripSageError):
                exc_val.details.operation = self.operation
                if self.service:
                    exc_val.details.service = self.service
                if self.user_id:
                    exc_val.details.user_id = self.user_id
                if self.request_id:
                    exc_val.details.request_id = self.request_id

            # Log the exception with context
            logger_name = getattr(self.logger, "name", None)
            if isinstance(exc_val, Exception):
                log_exception(cast(Exception, exc_val), logger_name)

        else:
            self.logger.debug(
                "Completed operation: %s",
                self.operation,
                extra={
                    "service": self.service,
                    "user_id": self.user_id,
                    "request_id": self.request_id,
                },
            )

        # Don't suppress the exception
        return False


def tripsage_safe_execute(
    exception_class: type[CoreTripSageError] = CoreTripSageError,
    fallback: Any = None,
    logger_instance: Any | None = None,
    re_raise: bool = False,
):
    """Decorator to add TripSage error handling with CoreTripSageError raising.

    This decorator consolidates the common pattern of try/except blocks with logging
    and CoreTripSageError raising found throughout the codebase.

    Args:
        exception_class: The CoreTripSageError subclass to raise on failure
        fallback: Value to return if execution fails (only if re_raise=False)
        logger_instance: Optional logger for error reporting
                         (defaults to TripSage logger)
        re_raise: Whether to re-raise the original exception after logging

    Returns:
        Decorator function
    """

    def decorator(func: Callable[..., T] | Callable[..., Awaitable[T]]):
        log = logger_instance or logger

        if inspect.iscoroutinefunction(func):
            async_func = cast(Callable[..., Awaitable[T]], func)

            @functools.wraps(async_func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> T | Any:
                try:
                    return await async_func(*args, **kwargs)
                except Exception as e:
                    log_exception(e, getattr(log, "name", None))
                    if re_raise:
                        raise
                    if fallback is not None:
                        return fallback
                    # Raise CoreTripSageError with context
                    raise exception_class(
                        message=f"Error in {async_func.__name__}: {e!s}",
                        details={
                            "operation": async_func.__name__,
                            "original_exception": e.__class__.__name__,
                        },
                    ) from e

            return async_wrapper

        sync_func = cast(Callable[..., T], func)

        @functools.wraps(sync_func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> T | Any:
            try:
                return sync_func(*args, **kwargs)
            except Exception as e:
                log_exception(e, getattr(log, "name", None))
                if re_raise:
                    raise
                if fallback is not None:
                    return fallback
                # Raise CoreTripSageError with context
                raise exception_class(
                    message=f"Error in {sync_func.__name__}: {e!s}",
                    details={
                        "operation": sync_func.__name__,
                        "original_exception": e.__class__.__name__,
                    },
                ) from e

        return sync_wrapper

    return decorator


__all__ = [
    "TripSageErrorContext",
    "create_api_error",
    "create_database_error",
    "create_validation_error",
    "log_exception",
    "safe_execute_with_logging",
    "tripsage_safe_execute",
    "with_error_handling_and_logging",
]
