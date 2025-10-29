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


# Common recoverable errors for service operations
# Services can extend this tuple with service-specific errors if needed
RECOVERABLE_ERRORS = (
    CoreServiceError,
    CoreResourceNotFoundError,
    CoreValidationError,
    ConnectionError,
    TimeoutError,
    RuntimeError,
    ValueError,
    KeyError,
    TypeError,
)


__all__ = [
    # Common constants
    "RECOVERABLE_ERRORS",
    "CoreAgentError",
    # Authentication and authorization
    "CoreAuthenticationError",
    "CoreAuthorizationError",
    "CoreDatabaseError",
    "CoreExternalAPIError",
    "CoreKeyValidationError",
    # Specialized exceptions
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
