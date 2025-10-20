"""TripSage Core Exceptions.

This module provides a centralized exception system for the entire TripSage application.
All exceptions inherit from CoreTripSageError and provide consistent error handling
with structured details, HTTP status codes, and machine-readable error codes.
"""

from tripsage_core.exceptions.exceptions import (
    CoreAgentError,
    # Authentication and authorization
    CoreAuthenticationError,
    CoreAuthorizationError,
    CoreDatabaseError,
    CoreExternalAPIError,
    CoreKeyValidationError,
    # Specialized exceptions
    CoreMCPError,
    CoreRateLimitError,
    # Resource and validation
    CoreResourceNotFoundError,
    CoreSecurityError,
    # Service and infrastructure
    CoreServiceError,
    # Base exception
    CoreTripSageError,
    CoreValidationError,
    # Utility classes and functions
    ErrorDetails,
    create_error_response,
    format_exception,
    safe_execute,
    with_error_handling,
)


__all__ = [
    # Base exception
    "CoreTripSageError",
    # Authentication and authorization
    "CoreAuthenticationError",
    "CoreAuthorizationError",
    "CoreSecurityError",
    # Resource and validation
    "CoreResourceNotFoundError",
    "CoreValidationError",
    # Service and infrastructure
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
]
