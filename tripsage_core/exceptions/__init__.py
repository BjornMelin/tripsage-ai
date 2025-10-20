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
    "CoreAgentError",
    # Authentication and authorization
    "CoreAuthenticationError",
    "CoreAuthorizationError",
    "CoreDatabaseError",
    "CoreExternalAPIError",
    "CoreKeyValidationError",
    # Specialized exceptions
    "CoreMCPError",
    "CoreRateLimitError",
    # Resource and validation
    "CoreResourceNotFoundError",
    "CoreSecurityError",
    # Service and infrastructure
    "CoreServiceError",
    # Base exception
    "CoreTripSageError",
    "CoreValidationError",
    # Utility classes and functions
    "ErrorDetails",
    "create_error_response",
    "format_exception",
    "safe_execute",
    "with_error_handling",
]
