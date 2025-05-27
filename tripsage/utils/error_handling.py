"""
Error handling utilities for TripSage.

This module provides standardized error handling functionality for the TripSage
application, including custom exception classes and error processing functions.
"""

import functools
import traceback
from typing import Any, Awaitable, Callable, Dict, Optional, TypeVar, Union, cast

from .logging import get_logger

logger = get_logger(__name__)

# Type variable for function return type
T = TypeVar("T")
R = TypeVar("R")
F = TypeVar("F", bound=Callable[..., Any])


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


class MCPError(TripSageError):
    """Error raised for MCP server failures."""

    def __init__(
        self,
        message: str,
        server: str,
        tool: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
        category: str = "unknown",
        status_code: Optional[int] = None,
    ):
        """Initialize the MCPError.

        Args:
            message: Error message
            server: Name of the MCP server that failed
            tool: Name of the tool that failed, if applicable
            params: Tool parameters, if applicable
            category: Error category for better classification
            status_code: HTTP status code, if applicable
        """
        details = {
            "server": server,
            "tool": tool,
            "params": params,
            "category": category,
            "status_code": status_code,
        }
        super().__init__(message, details)
        self.server = server
        self.tool = tool
        self.params = params
        self.category = category
        self.status_code = status_code

    def __str__(self) -> str:
        """Get string representation of the error.

        Returns:
            Formatted error message
        """
        return (
            f"{self.server} error ({self.category}): {self.message} "
            f"when calling tool '{self.tool}'"
        )


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
        self.service = service
        self.status_code = status_code
        self.response = response

    def __str__(self) -> str:
        """Get string representation of the error.

        Returns:
            Formatted error message
        """
        if self.status_code:
            return f"{self.service} API error ({self.status_code}): {self.message}"
        return f"{self.service} API error: {self.message}"


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
        self.field = field
        self.value = value
        self.constraint = constraint


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
        self.operation = operation
        self.query = query
        self.params = params


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
    log = logger if logger_name is None else get_logger(logger_name)

    if isinstance(exc, MCPError):
        log.error(
            "MCP Error: %s\nServer: %s\nTool: %s\nCategory: %s\nParams: %s",
            exc.message,
            exc.server,
            exc.tool,
            exc.category,
            exc.params,
            exc_info=True,
        )
    elif isinstance(exc, APIError):
        log.error(
            "API Error: %s\nService: %s\nStatus Code: %s\nResponse: %s",
            exc.message,
            exc.service,
            exc.status_code,
            exc.response,
            exc_info=True,
        )
    elif isinstance(exc, TripSageError):
        # Use warning level for expected application errors
        log.warning(
            "Application error: %s - %s",
            exc.__class__.__name__,
            exc.message,
            extra={"details": exc.details},
        )
    else:
        # Use error level for unexpected system errors
        log.error(
            "System error: %s - %s",
            exc.__class__.__name__,
            str(exc),
            exc_info=True,
        )


def safe_execute(
    func: Callable[..., T], *args: Any, fallback: R = None, **kwargs: Any
) -> T | R:
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
        return cast(T, fallback)


def with_error_handling(
    func: Callable[..., Union[T, Awaitable[T]]]
) -> Callable[..., Union[T, Awaitable[T]]]:
    """Decorator to add error handling to functions.

    Args:
        func: The function to wrap with error handling

    Returns:
        Wrapped function with error handling
    """
    
    @functools.wraps(func)
    def sync_wrapper(*args: Any, **kwargs: Any) -> T:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            log_exception(e)
            # Return a default error response for sync functions
            if hasattr(func, '__annotations__') and func.__annotations__.get('return'):
                # Return empty dict for dict returns, empty list for list returns
                return_type = func.__annotations__['return']
                if 'Dict' in str(return_type):
                    return cast(T, {"status": "error", "error": str(e)})
                elif 'List' in str(return_type):
                    return cast(T, [])
            return cast(T, {"status": "error", "error": str(e)})
    
    @functools.wraps(func)
    async def async_wrapper(*args: Any, **kwargs: Any) -> T:
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            log_exception(e)
            # Return a default error response for async functions
            if hasattr(func, '__annotations__') and func.__annotations__.get('return'):
                # Return empty dict for dict returns, empty list for list returns
                return_type = func.__annotations__['return']
                if 'Dict' in str(return_type):
                    return cast(T, {"status": "error", "error": str(e)})
                elif 'List' in str(return_type):
                    return cast(T, [])
            return cast(T, {"status": "error", "error": str(e)})
    
    # Check if the function is a coroutine function
    if hasattr(func, '__code__') and func.__code__.co_flags & 0x80:  # CO_COROUTINE
        return async_wrapper
    else:
        # Check if function returns an awaitable
        return_annotation = getattr(func, '__annotations__', {}).get('return')
        if return_annotation and 'Awaitable' in str(return_annotation):
            return async_wrapper
        return sync_wrapper
