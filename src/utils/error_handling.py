"""
Error handling utilities for TripSage.

This module provides standardized error handling functionality for the TripSage
application, including custom exception classes and error processing functions.
"""

import traceback
from typing import Any, Dict, List, Optional, Type, Union

from .logging import get_module_logger

logger = get_module_logger(__name__)


class TripSageError(Exception):
    """Base exception class for all TripSage errors."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """Initialize the TripSageError.

        Args:
            message: Error message
            details: Additional error details as a dictionary
        """
        self.message = message
        self.details = details or {}
        super().__init__(message)


class APIError(TripSageError):
    """Error raised when an external API call fails."""

    def __init__(
        self,
        message: str,
        service: str,
        status_code: Optional[int] = None,
        response: Optional[Dict[str, Any]] = None,
    ):
        """Initialize the APIError.

        Args:
            message: Error message
            service: Name of the API service that failed
            status_code: HTTP status code if applicable
            response: Raw API response if available
        """
        details = {"service": service, "status_code": status_code, "response": response}
        super().__init__(message, details)


class ValidationError(TripSageError):
    """Error raised for validation failures."""

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        constraint: Optional[str] = None,
    ):
        """Initialize the ValidationError.

        Args:
            message: Error message
            field: Name of the field that failed validation
            value: The invalid value
            constraint: Description of the constraint that was violated
        """
        details = {"field": field, "value": value, "constraint": constraint}
        super().__init__(message, details)


class DatabaseError(TripSageError):
    """Error raised for database operation failures."""

    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        query: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
    ):
        """Initialize the DatabaseError.

        Args:
            message: Error message
            operation: Type of database operation that failed
            query: The query that failed, if applicable
            params: Query parameters, if applicable
        """
        details = {"operation": operation, "query": query, "params": params}
        super().__init__(message, details)


class MCPError(TripSageError):
    """Error raised for MCP server failures."""

    def __init__(
        self,
        message: str,
        server: str,
        tool: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
    ):
        """Initialize the MCPError.

        Args:
            message: Error message
            server: Name of the MCP server that failed
            tool: Name of the tool that failed, if applicable
            params: Tool parameters, if applicable
        """
        details = {"server": server, "tool": tool, "params": params}
        super().__init__(message, details)


def format_exception(exc: Exception) -> Dict[str, Any]:
    """Format an exception into a standardized structure.

    Args:
        exc: The exception to format

    Returns:
        A dictionary with exception information
    """
    if isinstance(exc, TripSageError):
        result = {
            "error": exc.__class__.__name__,
            "message": exc.message,
            "details": exc.details,
        }
    else:
        result = {
            "error": exc.__class__.__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        }

    return result


def log_exception(exc: Exception, logger_name: Optional[str] = None) -> None:
    """Log an exception with appropriate level and details.

    Args:
        exc: The exception to log
        logger_name: Optional specific logger name to use
    """
    log = logger if logger_name is None else get_module_logger(logger_name)

    error_data = format_exception(exc)

    if isinstance(exc, TripSageError):
        # Use warning level for expected application errors
        log.warning(
            "Application error: %s - %s",
            error_data["error"],
            error_data["message"],
            extra={"details": error_data["details"]},
        )
    else:
        # Use error level for unexpected system errors
        log.error(
            "System error: %s - %s",
            error_data["error"],
            error_data["message"],
            exc_info=True,
        )


def safe_execute(func, *args, fallback=None, **kwargs):
    """Execute a function with error handling.

    Args:
        func: The function to execute
        *args: Arguments to pass to the function
        fallback: Value to return if execution fails
        **kwargs: Keyword arguments to pass to the function

    Returns:
        The function result or fallback value
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        log_exception(e)
        return fallback
