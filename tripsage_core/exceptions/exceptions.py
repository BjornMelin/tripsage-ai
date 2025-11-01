"""Centralized exception system for TripSage.

This module provides a exception hierarchy for all TripSage components,
including APIs, agents, services, and tools. It consolidates exception handling
from across the application into a single, consistent system.
"""

import functools
import inspect
import logging
import traceback
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar, cast

from fastapi import status
from pydantic import BaseModel, Field


# Type variables for generic functions
T = TypeVar("T")
R = TypeVar("R")


class ErrorDetails(BaseModel):
    """Structured error details for enhanced debugging and logging."""

    service: str | None = Field(None, description="Service that raised the error")
    operation: str | None = Field(None, description="Operation that failed")
    resource_id: str | None = Field(None, description="ID of the resource involved")
    user_id: str | None = Field(None, description="User ID associated with error")
    request_id: str | None = Field(None, description="Request ID for tracing")
    additional_context: dict[str, Any] = Field(
        default_factory=dict, description="Additional context information"
    )


def _ensure_error_details(
    details: dict[str, Any] | ErrorDetails | None,
) -> ErrorDetails:
    """Normalize optional details into an ErrorDetails instance."""
    if isinstance(details, ErrorDetails):
        return details

    if details is None:
        return ErrorDetails(
            service=None,
            operation=None,
            resource_id=None,
            user_id=None,
            request_id=None,
            additional_context={},
        )

    return ErrorDetails(**details)


class CoreTripSageError(Exception):
    """Base exception for all TripSage errors.

    This is the root exception class that all TripSage-specific exceptions
    should inherit from. It provides a consistent interface for error handling
    across the entire application.
    """

    def __init__(
        self,
        message: str = "An unexpected error occurred",
        code: str = "INTERNAL_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: dict[str, Any] | ErrorDetails | None = None,
    ):
        """Initialize the CoreTripSageError.

        Args:
            message: Human-readable error message
            code: Machine-readable error code (uppercase with underscores)
            status_code: HTTP status code using fastapi.status constants
            details: Additional error details as dict or ErrorDetails instance
        """
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = _ensure_error_details(details)

        super().__init__(self.message)

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary for API responses.

        Returns:
            Dictionary representation of the exception
        """
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "code": self.code,
            "status_code": self.status_code,
            "details": self.details.model_dump(exclude_none=True),
        }

    def __str__(self) -> str:
        """String representation of the exception."""
        return f"{self.code}: {self.message}"

    def __repr__(self) -> str:
        """Detailed representation of the exception."""
        return (
            f"{self.__class__.__name__}(message='{self.message}', "
            f"code='{self.code}', status_code={self.status_code})"
        )


# Authentication and Authorization Errors
class CoreAuthenticationError(CoreTripSageError):
    """Raised when authentication fails."""

    def __init__(
        self,
        message: str = "Authentication failed",
        code: str = "AUTHENTICATION_ERROR",
        details: dict[str, Any] | ErrorDetails | None = None,
    ):
        """Initialize the CoreAuthenticationError.

        Args:
            message: Human-readable error message
            code: Machine-readable error code
            details: Additional error details
        """
        super().__init__(
            message=message,
            code=code,
            status_code=status.HTTP_401_UNAUTHORIZED,
            details=details,
        )


class CoreAuthorizationError(CoreTripSageError):
    """Raised when a user is not authorized to perform an action."""

    def __init__(
        self,
        message: str = "You are not authorized to perform this action",
        code: str = "AUTHORIZATION_ERROR",
        details: dict[str, Any] | ErrorDetails | None = None,
    ):
        """Initialize the CoreAuthorizationError.

        Args:
            message: Human-readable error message
            code: Machine-readable error code
            details: Additional error details
        """
        super().__init__(
            message=message,
            code=code,
            status_code=status.HTTP_403_FORBIDDEN,
            details=details,
        )


class CoreSecurityError(CoreTripSageError):
    """Raised when a security violation or security-related error occurs."""

    def __init__(
        self,
        message: str = "Security violation detected",
        code: str = "SECURITY_ERROR",
        details: dict[str, Any] | ErrorDetails | None = None,
    ):
        """Initialize the CoreSecurityError.

        Args:
            message: Human-readable error message
            code: Machine-readable error code
            details: Additional error details
        """
        super().__init__(
            message=message,
            code=code,
            status_code=status.HTTP_403_FORBIDDEN,
            details=details,
        )


# Resource and Validation Errors
class CoreResourceNotFoundError(CoreTripSageError):
    """Raised when a requested resource is not found."""

    def __init__(
        self,
        message: str = "Resource not found",
        code: str = "RESOURCE_NOT_FOUND",
        details: dict[str, Any] | ErrorDetails | None = None,
    ):
        """Initialize the CoreResourceNotFoundError.

        Args:
            message: Human-readable error message
            code: Machine-readable error code
            details: Additional error details
        """
        super().__init__(
            message=message,
            code=code,
            status_code=status.HTTP_404_NOT_FOUND,
            details=details,
        )


class CoreValidationError(CoreTripSageError):
    """Raised when input validation fails."""

    def __init__(
        self,
        message: str = "Validation error",
        code: str = "VALIDATION_ERROR",
        *,
        details: dict[str, Any] | ErrorDetails | None = None,
        field: str | None = None,
        value: Any | None = None,
        constraint: str | None = None,
    ):
        """Initialize the CoreValidationError.

        Args:
            message: Human-readable error message
            code: Machine-readable error code
            details: Additional error details
            field: Name of the field that failed validation
            value: The invalid value
            constraint: Description of the constraint that was violated
        """
        details_model = _ensure_error_details(details)

        if field or value is not None or constraint:
            details_model.additional_context.update(
                {
                    "field": field,
                    "value": value,
                    "constraint": constraint,
                }
            )

        super().__init__(
            message=message,
            code=code,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details_model,
        )


# Service and Infrastructure Errors
class CoreConnectionError(CoreTripSageError):
    """Raised when a connection operation fails."""

    def __init__(
        self,
        message: str = "Connection operation failed",
        code: str = "CONNECTION_ERROR",
        details: dict[str, Any] | ErrorDetails | None = None,
        connection_type: str | None = None,
    ):
        """Initialize the CoreConnectionError.

        Args:
            message: Human-readable error message
            code: Machine-readable error code
            details: Additional error details
            connection_type: Type of connection that failed
        """
        details_model = _ensure_error_details(details)

        if connection_type:
            details_model.additional_context["connection_type"] = connection_type

        super().__init__(
            message=message,
            code=code,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details=details_model,
        )


class CoreServiceError(CoreTripSageError):
    """Raised when a service operation fails."""

    def __init__(
        self,
        message: str = "Service operation failed",
        code: str = "SERVICE_ERROR",
        details: dict[str, Any] | ErrorDetails | None = None,
        service: str | None = None,
    ):
        """Initialize the CoreServiceError.

        Args:
            message: Human-readable error message
            code: Machine-readable error code
            details: Additional error details
            service: Name of the service that failed
        """
        details_model = _ensure_error_details(details)

        if service:
            details_model.service = service

        super().__init__(
            message=message,
            code=code,
            status_code=status.HTTP_502_BAD_GATEWAY,
            details=details_model,
        )


class CoreRateLimitError(CoreTripSageError):
    """Raised when a rate limit is exceeded."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        code: str = "RATE_LIMIT_EXCEEDED",
        details: dict[str, Any] | ErrorDetails | None = None,
        retry_after: int | None = None,
    ):
        """Initialize the CoreRateLimitError.

        Args:
            message: Human-readable error message
            code: Machine-readable error code
            details: Additional error details
            retry_after: Number of seconds to wait before retrying
        """
        details_model = _ensure_error_details(details)

        if retry_after:
            details_model.additional_context["retry_after"] = retry_after

        super().__init__(
            message=message,
            code=code,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            details=details_model,
        )


class CoreKeyValidationError(CoreTripSageError):
    """Raised when a user-provided API key is invalid."""

    def __init__(
        self,
        message: str = "Invalid API key",
        code: str = "INVALID_API_KEY",
        details: dict[str, Any] | ErrorDetails | None = None,
        key_service: str | None = None,
    ):
        """Initialize the CoreKeyValidationError.

        Args:
            message: Human-readable error message
            code: Machine-readable error code
            details: Additional error details
            key_service: Name of the service the key is for
        """
        details_model = _ensure_error_details(details)

        if key_service:
            details_model.service = key_service

        super().__init__(
            message=message,
            code=code,
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details_model,
        )


# Database and Storage Errors
class CoreDatabaseError(CoreTripSageError):
    """Raised when a database operation fails."""

    def __init__(
        self,
        message: str = "Database operation failed",
        code: str = "DATABASE_ERROR",
        *,
        details: dict[str, Any] | ErrorDetails | None = None,
        operation: str | None = None,
        table: str | None = None,
    ):
        """Initialize the CoreDatabaseError.

        Args:
            message: Human-readable error message
            code: Machine-readable error code
            details: Additional error details
            operation: Type of database operation that failed
            table: Name of the table involved
        """
        details_model = _ensure_error_details(details)

        if operation:
            details_model.operation = operation
        if table:
            details_model.additional_context["table"] = table

        super().__init__(
            message=message,
            code=code,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details_model,
        )


# External API and Integration Errors
class CoreExternalAPIError(CoreTripSageError):
    """Raised when an external API call fails."""

    def __init__(
        self,
        message: str = "External API call failed",
        code: str = "EXTERNAL_API_ERROR",
        *,
        details: dict[str, Any] | ErrorDetails | None = None,
        api_service: str | None = None,
        api_status_code: int | None = None,
        api_response: dict[str, Any] | None = None,
    ):
        """Initialize the CoreExternalAPIError.

        Args:
            message: Human-readable error message
            code: Machine-readable error code
            details: Additional error details
            api_service: Name of the external API service
            api_status_code: Status code returned by the external API
            api_response: Response body from the external API
        """
        details_model = _ensure_error_details(details)

        if api_service:
            details_model.service = api_service
        if api_status_code is not None or api_response is not None:
            details_model.additional_context.update(
                {
                    "api_status_code": api_status_code,
                    "api_response": api_response,
                }
            )

        super().__init__(
            message=message,
            code=code,
            status_code=status.HTTP_502_BAD_GATEWAY,
            details=details_model,
        )


class CoreAgentError(CoreServiceError):
    """Raised when an agent operation fails."""

    def __init__(
        self,
        message: str = "Agent operation failed",
        code: str = "AGENT_ERROR",
        *,
        details: dict[str, Any] | ErrorDetails | None = None,
        agent_type: str | None = None,
        operation: str | None = None,
    ):
        """Initialize the CoreAgentError.

        Args:
            message: Human-readable error message
            code: Machine-readable error code
            details: Additional error details
            agent_type: Type of agent that failed
            operation: Operation the agent was performing
        """
        details_model = _ensure_error_details(details)

        if agent_type:
            details_model.service = agent_type
        if operation:
            details_model.operation = operation

        super().__init__(
            message=message,
            code=code,
            details=details_model,
            service=agent_type,
        )


# Utility Functions
def format_exception(exc: Exception) -> dict[str, Any]:
    """Format an exception into a standardized structure.

    Args:
        exc: The exception to format

    Returns:
        A dictionary with exception information
    """
    if isinstance(exc, CoreTripSageError):
        return exc.to_dict()
    return {
        "error": exc.__class__.__name__,
        "message": str(exc),
        "code": "SYSTEM_ERROR",
        "status_code": 500,
        "details": {
            "traceback": traceback.format_exc(),
        },
    }


def create_error_response(
    exc: Exception, include_traceback: bool = False
) -> dict[str, Any]:
    """Create a standardized error response for API endpoints.

    Args:
        exc: The exception to create a response for
        include_traceback: Whether to include traceback for debugging

    Returns:
        Standardized error response dictionary
    """
    error_data = format_exception(exc)

    if not include_traceback and "traceback" in error_data.get("details", {}):
        error_data["details"].pop("traceback", None)

    return error_data


def safe_execute[T, R](
    func: Callable[..., T],
    *args: Any,
    fallback: R = None,
    logger: logging.Logger | None = None,
    **kwargs: Any,
) -> T | R:
    """Execute a function with error handling and optional fallback.

    Args:
        func: The function to execute
        *args: Arguments to pass to the function
        fallback: Value to return if execution fails
        logger: Optional logger to use for error logging
        **kwargs: Keyword arguments to pass to the function

    Returns:
        The function result or fallback value
    """
    try:
        return func(*args, **kwargs)
    except Exception:
        if logger:
            logger.exception("Error executing %s", func.__name__)
        return fallback


def with_error_handling(
    fallback: Any = None,
    logger: logging.Logger | None = None,
    re_raise: bool = False,
):
    """Decorator to add error handling to functions.

    Args:
        fallback: Default value to return on error
        logger: Optional logger for error reporting
        re_raise: Whether to re-raise the exception after logging

    Returns:
        Decorator function
    """

    def decorator(func: Callable[..., T] | Callable[..., Awaitable[T]]):
        if inspect.iscoroutinefunction(func):
            async_func = cast(Callable[..., Awaitable[T]], func)

            @functools.wraps(async_func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> T | Any:
                try:
                    return await async_func(*args, **kwargs)
                except Exception:
                    if logger:
                        logger.exception(
                            "Error in %s", async_func.__name__, exc_info=True
                        )
                    if re_raise:
                        raise
                    return fallback

            return async_wrapper

        sync_func = cast(Callable[..., T], func)

        @functools.wraps(sync_func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> T | Any:
            try:
                return sync_func(*args, **kwargs)
            except Exception:
                if logger:
                    logger.exception("Error in %s", sync_func.__name__, exc_info=True)
                if re_raise:
                    raise
                return fallback

        return sync_wrapper

    return decorator


# Factory functions for common exceptions
def create_authentication_error(
    message: str = "Authentication failed", details: dict[str, Any] | None = None
) -> CoreAuthenticationError:
    """Create an authentication error with standard parameters."""
    return CoreAuthenticationError(message=message, details=details)


def create_authorization_error(
    message: str = "Access denied", details: dict[str, Any] | None = None
) -> CoreAuthorizationError:
    """Create an authorization error with standard parameters."""
    return CoreAuthorizationError(message=message, details=details)


def create_validation_error(
    message: str = "Validation failed", details: dict[str, Any] | None = None
) -> CoreValidationError:
    """Create a validation error with standard parameters."""
    return CoreValidationError(message=message, details=details)


def create_not_found_error(
    message: str = "Resource not found", details: dict[str, Any] | None = None
) -> CoreResourceNotFoundError:
    """Create a not found error with standard parameters."""
    return CoreResourceNotFoundError(message=message, details=details)


# Export all exception classes and utilities
__all__ = [
    "CoreAgentError",
    # Authentication and authorization
    "CoreAuthenticationError",
    "CoreAuthorizationError",
    # Service and infrastructure
    "CoreConnectionError",
    "CoreDatabaseError",
    "CoreExternalAPIError",
    "CoreKeyValidationError",
    # Specialized exceptions
    "CoreRateLimitError",
    # Resource and validation
    "CoreResourceNotFoundError",
    "CoreServiceError",
    # Base exception
    "CoreTripSageError",
    "CoreValidationError",
    # Utility classes and functions
    "ErrorDetails",
    # Factory functions
    "create_authentication_error",
    "create_authorization_error",
    "create_error_response",
    "create_not_found_error",
    "create_validation_error",
    "format_exception",
    "safe_execute",
    "with_error_handling",
]
