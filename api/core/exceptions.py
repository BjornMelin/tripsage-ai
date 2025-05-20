"""
Custom exceptions for the TripSage API.

This module defines the custom exceptions used throughout the API.
"""

from typing import Any, Dict, Optional

from fastapi import status


class TripSageError(Exception):
    """Base exception for all TripSage API errors."""

    def __init__(
        self,
        message: str = "An unexpected error occurred",
        code: str = "INTERNAL_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Initialize the exception.

        Args:
            message: Human-readable error message
            code: Machine-readable error code
            status_code: HTTP status code
            details: Additional error details
        """
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class AuthenticationError(TripSageError):
    """Raised when authentication fails."""

    def __init__(
        self,
        message: str = "Authentication failed",
        code: str = "AUTHENTICATION_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ):
        """Initialize the exception.

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


class AuthorizationError(TripSageError):
    """Raised when a user is not authorized to perform an action."""

    def __init__(
        self,
        message: str = "You are not authorized to perform this action",
        code: str = "AUTHORIZATION_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ):
        """Initialize the exception.

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


class ResourceNotFoundError(TripSageError):
    """Raised when a requested resource is not found."""

    def __init__(
        self,
        message: str = "Resource not found",
        code: str = "RESOURCE_NOT_FOUND",
        details: Optional[Dict[str, Any]] = None,
    ):
        """Initialize the exception.

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


class ValidationError(TripSageError):
    """Raised when input validation fails."""

    def __init__(
        self,
        message: str = "Validation error",
        code: str = "VALIDATION_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ):
        """Initialize the exception.

        Args:
            message: Human-readable error message
            code: Machine-readable error code
            details: Additional error details
        """
        super().__init__(
            message=message,
            code=code,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details,
        )


class MCPServiceError(TripSageError):
    """Raised when an MCP service operation fails."""

    def __init__(
        self,
        message: str = "Service operation failed",
        code: str = "SERVICE_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ):
        """Initialize the exception.

        Args:
            message: Human-readable error message
            code: Machine-readable error code
            details: Additional error details
        """
        super().__init__(
            message=message,
            code=code,
            status_code=status.HTTP_502_BAD_GATEWAY,
            details=details,
        )


class RateLimitError(TripSageError):
    """Raised when a rate limit is exceeded."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        code: str = "RATE_LIMIT_EXCEEDED",
        details: Optional[Dict[str, Any]] = None,
    ):
        """Initialize the exception.

        Args:
            message: Human-readable error message
            code: Machine-readable error code
            details: Additional error details
        """
        super().__init__(
            message=message,
            code=code,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            details=details,
        )


class KeyValidationError(TripSageError):
    """Raised when a user-provided API key is invalid."""

    def __init__(
        self,
        message: str = "Invalid API key",
        code: str = "INVALID_API_KEY",
        details: Optional[Dict[str, Any]] = None,
    ):
        """Initialize the exception.

        Args:
            message: Human-readable error message
            code: Machine-readable error code
            details: Additional error details
        """
        super().__init__(
            message=message,
            code=code,
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details,
        )
