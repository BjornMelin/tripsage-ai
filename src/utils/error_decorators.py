"""
Error handling decorators for TripSage.

This module provides decorators for standardized error handling across
the TripSage codebase, including proper logging and error response formatting.
"""

import functools
import inspect
from typing import Any, Callable, TypeVar, cast

from src.utils.error_handling import log_exception
from src.utils.logging import get_module_logger

logger = get_module_logger(__name__)

# Type definitions for better type checking
F = TypeVar("F", bound=Callable[..., Any])


def with_error_handling(func: F) -> F:
    """Decorator to standardize error handling for both sync and async functions.

    This decorator provides standard error handling, including proper logging
    and error response formatting. It automatically detects whether the decorated
    function is synchronous or asynchronous and applies the appropriate wrapper.

    Args:
        func: Function to decorate (can be sync or async)

    Returns:
        Decorated function with standardized error handling

    Example:
        ```python
        # With async function
        @function_tool
        @with_error_handling
        async def get_current_time_tool(timezone: str) -> Dict[str, Any]:
            result = await time_client.get_current_time(timezone)
            return {"current_time": result.get("current_time", "")}

        # With sync function
        @with_error_handling
        def calculate_score(data: Dict[str, Any]) -> Dict[str, Any]:
            score = data["value"] * 2
            return {"score": score}
        ```
    """
    # Check if the function is a coroutine function (async)
    if inspect.iscoroutinefunction(func):

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            """Async wrapper function with try-except block."""
            try:
                # Call the original async function
                return await func(*args, **kwargs)
            except Exception as e:
                # Get function name for better error logging
                func_name = func.__name__
                logger.error(f"Error in {func_name}: {str(e)}")
                log_exception(e)

                # Check if function returns Dict (for agent tools)
                signature = inspect.signature(func)
                return_type = signature.return_annotation
                if "Dict" in str(return_type):
                    # Return error response in the expected format for agent tools
                    return {"error": str(e)}
                # Re-raise for non-dict returning functions
                raise

        return cast(F, async_wrapper)

    # For synchronous functions
    else:

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            """Sync wrapper function with try-except block."""
            try:
                # Call the original sync function
                return func(*args, **kwargs)
            except Exception as e:
                # Get function name for better error logging
                func_name = func.__name__
                logger.error(f"Error in {func_name}: {str(e)}")
                log_exception(e)

                # Check if function returns Dict (for agent tools)
                signature = inspect.signature(func)
                return_type = signature.return_annotation
                if "Dict" in str(return_type):
                    # Return error response in the expected format for agent tools
                    return {"error": str(e)}
                # Re-raise for non-dict returning functions
                raise

        return cast(F, sync_wrapper)
