"""
Centralized exception system for TripSage.

This module provides a comprehensive exception hierarchy for all TripSage components,
including APIs, agents, services, and tools. It consolidates exception handling
from across the application into a single, consistent system.
"""

import functools
import traceback
from typing import Any, Awaitable, Callable, Dict, Optional, TypeVar, Union

from fastapi import status
from pydantic import BaseModel, Field

# Type variables for generic functions
T = TypeVar("T")
R = TypeVar("R")


class ErrorDetails(BaseModel):
    """Structured error details for enhanced debugging and logging."""

    service: Optional[str] = Field(None, description="Service that raised the error")
    operation: Optional[str] = Field(None, description="Operation that failed")
    resource_id: Optional[str] = Field(None, description="ID of the resource involved")
    user_id: Optional[str] = Field(None, description="User ID associated with error")
    request_id: Optional[str] = Field(None, description="Request ID for tracing")
    additional_context: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Additional context information"
    )


class CoreTripSageError(Exception):
    """
    Base exception for all TripSage errors.

    This is the root exception class that all TripSage-specific exceptions
    should inherit from. It provides a consistent interface for error handling
    across the entire application.
    """

    def __init__(
        self,
        message: str = "An unexpected error occurred",
        code: str = "INTERNAL_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Union[Dict[str, Any], ErrorDetails]] = None,
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

        # Convert dict to ErrorDetails if needed
        if isinstance(details, dict):
            self.details = ErrorDetails(**details)
        elif details is None:
            self.details = ErrorDetails()
        else:
            self.details = details

        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
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
        details: Optional[Union[Dict[str, Any], ErrorDetails]] = None,
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
        details: Optional[Union[Dict[str, Any], ErrorDetails]] = None,
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
        details: Optional[Union[Dict[str, Any], ErrorDetails]] = None,
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
        details: Optional[Union[Dict[str, Any], ErrorDetails]] = None,
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
        details: Optional[Union[Dict[str, Any], ErrorDetails]] = None,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        constraint: Optional[str] = None,
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
        # Add validation-specific details
        if details is None:
            details = ErrorDetails()
        elif isinstance(details, dict):
            details = ErrorDetails(**details)

        if field or value is not None or constraint:
            details.additional_context.update(
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
            details=details,
        )


# Service and Infrastructure Errors
class CoreConnectionError(CoreTripSageError):
    """Raised when a connection operation fails."""

    def __init__(
        self,
        message: str = "Connection operation failed",
        code: str = "CONNECTION_ERROR",
        details: Optional[Union[Dict[str, Any], ErrorDetails]] = None,
        connection_type: Optional[str] = None,
    ):
        """Initialize the CoreConnectionError.

        Args:
            message: Human-readable error message
            code: Machine-readable error code
            details: Additional error details
            connection_type: Type of connection that failed
        """
        # Add connection-specific details
        if details is None:
            details = ErrorDetails()
        elif isinstance(details, dict):
            details = ErrorDetails(**details)

        if connection_type:
            details.additional_context["connection_type"] = connection_type

        super().__init__(
            message=message,
            code=code,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details=details,
        )


class CoreServiceError(CoreTripSageError):
    """Raised when a service operation fails."""

    def __init__(
        self,
        message: str = "Service operation failed",
        code: str = "SERVICE_ERROR",
        details: Optional[Union[Dict[str, Any], ErrorDetails]] = None,
        service: Optional[str] = None,
    ):
        """Initialize the CoreServiceError.

        Args:
            message: Human-readable error message
            code: Machine-readable error code
            details: Additional error details
            service: Name of the service that failed
        """
        # Add service-specific details
        if details is None:
            details = ErrorDetails()
        elif isinstance(details, dict):
            details = ErrorDetails(**details)

        if service:
            details.service = service

        super().__init__(
            message=message,
            code=code,
            status_code=status.HTTP_502_BAD_GATEWAY,
            details=details,
        )


class CoreRateLimitError(CoreTripSageError):
    """Raised when a rate limit is exceeded."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        code: str = "RATE_LIMIT_EXCEEDED",
        details: Optional[Union[Dict[str, Any], ErrorDetails]] = None,
        retry_after: Optional[int] = None,
    ):
        """Initialize the CoreRateLimitError.

        Args:
            message: Human-readable error message
            code: Machine-readable error code
            details: Additional error details
            retry_after: Number of seconds to wait before retrying
        """
        # Add rate limit specific details
        if details is None:
            details = ErrorDetails()
        elif isinstance(details, dict):
            details = ErrorDetails(**details)

        if retry_after:
            details.additional_context["retry_after"] = retry_after

        super().__init__(
            message=message,
            code=code,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            details=details,
        )


class CoreKeyValidationError(CoreTripSageError):
    """Raised when a user-provided API key is invalid."""

    def __init__(
        self,
        message: str = "Invalid API key",
        code: str = "INVALID_API_KEY",
        details: Optional[Union[Dict[str, Any], ErrorDetails]] = None,
        key_service: Optional[str] = None,
    ):
        """Initialize the CoreKeyValidationError.

        Args:
            message: Human-readable error message
            code: Machine-readable error code
            details: Additional error details
            key_service: Name of the service the key is for
        """
        # Add key validation specific details
        if details is None:
            details = ErrorDetails()
        elif isinstance(details, dict):
            details = ErrorDetails(**details)

        if key_service:
            details.service = key_service

        super().__init__(
            message=message,
            code=code,
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details,
        )


# Database and Storage Errors
class CoreDatabaseError(CoreTripSageError):
    """Raised when a database operation fails."""

    def __init__(
        self,
        message: str = "Database operation failed",
        code: str = "DATABASE_ERROR",
        details: Optional[Union[Dict[str, Any], ErrorDetails]] = None,
        operation: Optional[str] = None,
        table: Optional[str] = None,
    ):
        """Initialize the CoreDatabaseError.

        Args:
            message: Human-readable error message
            code: Machine-readable error code
            details: Additional error details
            operation: Type of database operation that failed
            table: Name of the table involved
        """
        # Add database-specific details
        if details is None:
            details = ErrorDetails()
        elif isinstance(details, dict):
            details = ErrorDetails(**details)

        if operation:
            details.operation = operation
        if table:
            details.additional_context["table"] = table

        super().__init__(
            message=message,
            code=code,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details,
        )


# External API and Integration Errors
class CoreExternalAPIError(CoreTripSageError):
    """Raised when an external API call fails."""

    def __init__(
        self,
        message: str = "External API call failed",
        code: str = "EXTERNAL_API_ERROR",
        details: Optional[Union[Dict[str, Any], ErrorDetails]] = None,
        api_service: Optional[str] = None,
        api_status_code: Optional[int] = None,
        api_response: Optional[Dict[str, Any]] = None,
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
        # Add external API specific details
        if details is None:
            details = ErrorDetails()
        elif isinstance(details, dict):
            details = ErrorDetails(**details)

        if api_service:
            details.service = api_service
        if api_status_code or api_response:
            details.additional_context.update(
                {
                    "api_status_code": api_status_code,
                    "api_response": api_response,
                }
            )

        super().__init__(
            message=message,
            code=code,
            status_code=status.HTTP_502_BAD_GATEWAY,
            details=details,
        )


# Specialized MCP and Agent Errors
class CoreMCPError(CoreServiceError):
    """Raised when an MCP server operation fails."""

    def __init__(
        self,
        message: str = "MCP server operation failed",
        code: str = "MCP_ERROR",
        details: Optional[Union[Dict[str, Any], ErrorDetails]] = None,
        server: Optional[str] = None,
        tool: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
    ):
        """Initialize the CoreMCPError.

        Args:
            message: Human-readable error message
            code: Machine-readable error code
            details: Additional error details
            server: Name of the MCP server that failed
            tool: Name of the tool that failed
            params: Tool parameters that were used
        """
        # Add MCP-specific details
        if details is None:
            details = ErrorDetails()
        elif isinstance(details, dict):
            details = ErrorDetails(**details)

        if server:
            details.service = server
        if tool or params:
            details.additional_context.update(
                {
                    "tool": tool,
                    "params": params,
                }
            )

        super().__init__(
            message=message,
            code=code,
            details=details,
            service=server,
        )


class CoreAgentError(CoreServiceError):
    """Raised when an agent operation fails."""

    def __init__(
        self,
        message: str = "Agent operation failed",
        code: str = "AGENT_ERROR",
        details: Optional[Union[Dict[str, Any], ErrorDetails]] = None,
        agent_type: Optional[str] = None,
        operation: Optional[str] = None,
    ):
        """Initialize the CoreAgentError.

        Args:
            message: Human-readable error message
            code: Machine-readable error code
            details: Additional error details
            agent_type: Type of agent that failed
            operation: Operation the agent was performing
        """
        # Add agent-specific details
        if details is None:
            details = ErrorDetails()
        elif isinstance(details, dict):
            details = ErrorDetails(**details)

        if agent_type:
            details.service = agent_type
        if operation:
            details.operation = operation

        super().__init__(
            message=message,
            code=code,
            details=details,
            service=agent_type,
        )


# Utility Functions
def format_exception(exc: Exception) -> Dict[str, Any]:
    """Format an exception into a standardized structure.

    Args:
        exc: The exception to format

    Returns:
        A dictionary with exception information
    """
    if isinstance(exc, CoreTripSageError):
        return exc.to_dict()
    else:
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
) -> Dict[str, Any]:
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


def safe_execute(
    func: Callable[..., T], *args: Any, fallback: R = None, logger=None, **kwargs: Any
) -> Union[T, R]:
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
    except Exception as e:
        if logger:
            logger.error(f"Error executing {func.__name__}: {e}")
        return fallback


def with_error_handling(
    fallback: Any = None,
    logger=None,
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

    def decorator(func: Callable[..., Union[T, Awaitable[T]]]):
        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Union[T, Any]:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if logger:
                    logger.error(f"Error in {func.__name__}: {e}", exc_info=True)
                if re_raise:
                    raise
                return fallback

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Union[T, Any]:
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if logger:
                    logger.error(f"Error in {func.__name__}: {e}", exc_info=True)
                if re_raise:
                    raise
                return fallback

        # Determine if function is async
        if hasattr(func, "__code__") and func.__code__.co_flags & 0x80:  # CO_COROUTINE
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# Factory functions for common exceptions
def create_authentication_error(
    message: str = "Authentication failed", details: Optional[Dict[str, Any]] = None
) -> CoreAuthenticationError:
    """Create an authentication error with standard parameters."""
    return CoreAuthenticationError(message=message, details=details)


def create_authorization_error(
    message: str = "Access denied", details: Optional[Dict[str, Any]] = None
) -> CoreAuthorizationError:
    """Create an authorization error with standard parameters."""
    return CoreAuthorizationError(message=message, details=details)


def create_validation_error(
    message: str = "Validation failed", details: Optional[Dict[str, Any]] = None
) -> CoreValidationError:
    """Create a validation error with standard parameters."""
    return CoreValidationError(message=message, details=details)


def create_not_found_error(
    message: str = "Resource not found", details: Optional[Dict[str, Any]] = None
) -> CoreResourceNotFoundError:
    """Create a not found error with standard parameters."""
    return CoreResourceNotFoundError(message=message, details=details)


# Export all exception classes and utilities
__all__ = [
    # Base exception
    "CoreTripSageError",
    # Authentication and authorization
    "CoreAuthenticationError",
    "CoreAuthorizationError",
    # Resource and validation
    "CoreResourceNotFoundError",
    "CoreValidationError",
    # Service and infrastructure
    "CoreConnectionError",
    "CoreServiceError",
    "CoreRateLimitError",
    "CoreKeyValidationError",
    "CoreDatabaseError",
    "CoreExternalAPIError",
    # Specialized exceptions
    "CoreMCPError",
    "CoreAgentError",
    # Utility classes and functions
    "ErrorDetails",
    "format_exception",
    "create_error_response",
    "safe_execute",
    "with_error_handling",
    # Factory functions
    "create_authentication_error",
    "create_authorization_error",
    "create_validation_error",
    "create_not_found_error",
]
