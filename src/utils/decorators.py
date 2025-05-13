"""
Utility decorators for TripSage.

This module provides decorators used across the TripSage codebase.
"""

import functools
import inspect
from typing import Any, Callable, TypeVar, cast

from src.mcp.memory.client import memory_client
from src.utils.error_handling import log_exception
from src.utils.logging import get_module_logger

logger = get_module_logger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


def ensure_memory_client_initialized(func: F) -> F:
    """Decorator to ensure memory client is initialized.

    This decorator ensures that the memory client is initialized before
    the decorated function is called. This avoids redundant initialization
    calls in each function that uses the memory client.

    Args:
        func: Function to decorate

    Returns:
        Decorated function
    """

    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        """Wrapper function that initializes memory client."""
        try:
            # Initialize the memory client once
            await memory_client.initialize()

            # Call the original function
            return await func(*args, **kwargs)
        except Exception as e:
            # Get function name for better error logging
            func_name = func.__name__
            logger.error(f"Error in {func_name}: {str(e)}")
            log_exception(e)

            # Return error response in the expected format for agent tools
            # Only do this if the function returns a dict (for agent tools)
            if inspect.iscoroutinefunction(func):
                signature = inspect.signature(func)
                if "Dict" in str(signature.return_annotation):
                    return {"error": str(e)}
            # Re-raise for non-dict returning functions
            raise

    return cast(F, wrapper)


def with_error_handling(func: F) -> F:
    """Decorator to standardize error handling.

    This decorator provides standard error handling for functions, including
    proper logging and error response formatting for agent tools.

    Args:
        func: Function to decorate

    Returns:
        Decorated function
    """

    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        """Wrapper function that adds try-except block."""
        try:
            # Call the original function
            return await func(*args, **kwargs)
        except Exception as e:
            # Get function name for better error logging
            func_name = func.__name__
            logger.error(f"Error in {func_name}: {str(e)}")
            log_exception(e)

            # Return error response in the expected format for agent tools
            return {"error": str(e)}

    return cast(F, wrapper)
