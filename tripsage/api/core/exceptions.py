"""Exception handling for the TripSage API.

This module defines custom exceptions for the TripSage API and provides
utility functions for error handling.
"""

from typing import Any, Dict, Optional


class TripSageException(Exception):
    """Base exception for TripSage API.
    
    All custom exceptions should inherit from this class.
    """
    
    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: str = "internal_error",
        details: Optional[Dict[str, Any]] = None,
    ):
        """Initialize TripSageException.
        
        Args:
            message: Human-readable error message
            status_code: HTTP status code
            error_code: Machine-readable error code
            details: Additional error details
        """
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class NotFoundError(TripSageException):
    """Raised when a resource is not found."""
    
    def __init__(
        self,
        message: str = "Resource not found",
        error_code: str = "not_found",
        details: Optional[Dict[str, Any]] = None,
    ):
        """Initialize NotFoundError.
        
        Args:
            message: Human-readable error message
            error_code: Machine-readable error code
            details: Additional error details
        """
        super().__init__(
            message=message,
            status_code=404,
            error_code=error_code,
            details=details,
        )


class AuthenticationError(TripSageException):
    """Raised when authentication fails."""
    
    def __init__(
        self,
        message: str = "Authentication failed",
        error_code: str = "authentication_failed",
        details: Optional[Dict[str, Any]] = None,
    ):
        """Initialize AuthenticationError.
        
        Args:
            message: Human-readable error message
            error_code: Machine-readable error code
            details: Additional error details
        """
        super().__init__(
            message=message,
            status_code=401,
            error_code=error_code,
            details=details,
        )


class AuthorizationError(TripSageException):
    """Raised when a user is not authorized to access a resource."""
    
    def __init__(
        self,
        message: str = "Not authorized",
        error_code: str = "not_authorized",
        details: Optional[Dict[str, Any]] = None,
    ):
        """Initialize AuthorizationError.
        
        Args:
            message: Human-readable error message
            error_code: Machine-readable error code
            details: Additional error details
        """
        super().__init__(
            message=message,
            status_code=403,
            error_code=error_code,
            details=details,
        )


class ValidationError(TripSageException):
    """Raised when data validation fails."""
    
    def __init__(
        self,
        message: str = "Validation error",
        error_code: str = "validation_error",
        details: Optional[Dict[str, Any]] = None,
    ):
        """Initialize ValidationError.
        
        Args:
            message: Human-readable error message
            error_code: Machine-readable error code
            details: Additional error details
        """
        super().__init__(
            message=message,
            status_code=422,
            error_code=error_code,
            details=details,
        )


class RateLimitError(TripSageException):
    """Raised when a rate limit is exceeded."""
    
    def __init__(
        self,
        message: str = "Rate limit exceeded",
        error_code: str = "rate_limit_exceeded",
        details: Optional[Dict[str, Any]] = None,
    ):
        """Initialize RateLimitError.
        
        Args:
            message: Human-readable error message
            error_code: Machine-readable error code
            details: Additional error details
        """
        super().__init__(
            message=message,
            status_code=429,
            error_code=error_code,
            details=details,
        )


class MCPError(TripSageException):
    """Raised when an MCP service encounters an error."""
    
    def __init__(
        self,
        message: str = "MCP service error",
        error_code: str = "mcp_service_error",
        details: Optional[Dict[str, Any]] = None,
    ):
        """Initialize MCPError.
        
        Args:
            message: Human-readable error message
            error_code: Machine-readable error code
            details: Additional error details
        """
        super().__init__(
            message=message,
            status_code=500,
            error_code=error_code,
            details=details,
        )


class APIKeyError(TripSageException):
    """Raised when there's an issue with an API key."""
    
    def __init__(
        self,
        message: str = "Invalid or expired API key",
        error_code: str = "api_key_error",
        details: Optional[Dict[str, Any]] = None,
    ):
        """Initialize APIKeyError.
        
        Args:
            message: Human-readable error message
            error_code: Machine-readable error code
            details: Additional error details
        """
        super().__init__(
            message=message,
            status_code=401,
            error_code=error_code,
            details=details,
        )