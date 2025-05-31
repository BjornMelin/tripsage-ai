"""
Error handling utilities for TripSage Core.

This module provides standardized error handling functionality for the TripSage
application, building on top of the core exception system.
"""

from typing import Any, Callable, Dict, Optional, TypeVar, Union

from tripsage_core.exceptions import (
    CoreDatabaseError,
    CoreExternalAPIError,
    CoreMCPError,
    CoreTripSageError,
    CoreValidationError,
    ErrorDetails,
)
from tripsage_core.exceptions import (
    safe_execute as core_safe_execute,
)
from tripsage_core.exceptions import (
    with_error_handling as core_with_error_handling,
)
from tripsage_core.utils.logging_utils import get_logger

logger = get_logger(__name__)

# Type variable for function return type
T = TypeVar("T")
R = TypeVar("R")
F = TypeVar("F", bound=Callable[..., Any])


def log_exception(exc: Exception, logger_name: Optional[str] = None) -> None:
    """Log an exception with appropriate level and details.

    Args:
        exc: The exception to log
        logger_name: Optional specific logger name to use
    """
    log = logger if logger_name is None else get_logger(logger_name)

    if isinstance(exc, CoreMCPError):
        # Extract MCP-specific details from the core exception
        details = exc.details.additional_context
        log.error(
            "MCP Error: %s\nServer: %s\nTool: %s\nParams: %s",
            exc.message,
            exc.details.service,
            details.get("tool"),
            details.get("params"),
            exc_info=True,
        )
    elif isinstance(exc, CoreExternalAPIError):
        # Extract API-specific details from the core exception
        details = exc.details.additional_context
        log.error(
            "API Error: %s\nService: %s\nAPI Status Code: %s\nAPI Response: %s",
            exc.message,
            exc.details.service,
            details.get("api_status_code"),
            details.get("api_response"),
            exc_info=True,
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
            exc_info=True,
        )


def safe_execute_with_logging(
    func: Callable[..., T], *args: Any, fallback: R = None, **kwargs: Any
) -> Union[T, R]:
    """Execute a function with error handling and TripSage logging.

    Args:
        func: The function to execute
        *args: Arguments to pass to the function
        fallback: Value to return if execution fails
        **kwargs: Keyword arguments to pass to the function

    Returns:
        The function result or fallback value
    """
    return core_safe_execute(func, *args, fallback=fallback, logger=logger, **kwargs)


def with_error_handling_and_logging(
    fallback: Any = None,
    logger_instance: Optional[Any] = None,
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
        logger=logger_instance or logger,
        re_raise=re_raise,
    )


# Factory functions for creating specific TripSage exceptions
def create_mcp_error(
    message: str,
    server: str,
    tool: Optional[str] = None,
    params: Optional[Dict[str, Any]] = None,
    category: str = "unknown",
    status_code: Optional[int] = None,
) -> CoreMCPError:
    """Create an MCP error with TripSage-specific formatting.

    Args:
        message: Error message
        server: Name of the MCP server that failed
        tool: Name of the tool that failed, if applicable
        params: Tool parameters, if applicable
        category: Error category for better classification
        status_code: HTTP status code, if applicable

    Returns:
        CoreMCPError instance
    """
    details = ErrorDetails(
        service=server,
        additional_context={
            "tool": tool,
            "params": params,
            "category": category,
            "status_code": status_code,
        },
    )

    return CoreMCPError(
        message=message,
        code=f"MCP_{category.upper()}_ERROR",
        details=details,
        server=server,
        tool=tool,
        params=params,
    )


def create_api_error(
    message: str,
    service: str,
    status_code: Optional[int] = None,
    response: Optional[Dict[str, Any]] = None,
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
    field: Optional[str] = None,
    value: Optional[Any] = None,
    constraint: Optional[str] = None,
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
    operation: Optional[str] = None,
    query: Optional[str] = None,
    params: Optional[Dict[str, Any]] = None,
    table: Optional[str] = None,
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


# Backward compatibility alias
TripSageError = CoreTripSageError


# Enhanced error context manager for TripSage operations
class TripSageErrorContext:
    """Context manager for enhanced error handling in TripSage operations."""

    def __init__(
        self,
        operation: str,
        service: Optional[str] = None,
        user_id: Optional[str] = None,
        request_id: Optional[str] = None,
        logger_instance: Optional[Any] = None,
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
            f"Starting operation: {self.operation}",
            extra={
                "service": self.service,
                "user_id": self.user_id,
                "request_id": self.request_id,
            },
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the error context and handle any exceptions."""
        if exc_type is not None:
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
            log_exception(exc_val, logger_name)

        else:
            self.logger.debug(
                f"Completed operation: {self.operation}",
                extra={
                    "service": self.service,
                    "user_id": self.user_id,
                    "request_id": self.request_id,
                },
            )

        # Don't suppress the exception
        return False


__all__ = [
    "TripSageError",  # Backward compatibility alias
    "log_exception",
    "safe_execute_with_logging",
    "with_error_handling_and_logging",
    "create_mcp_error",
    "create_api_error",
    "create_validation_error",
    "create_database_error",
    "TripSageErrorContext",
]
