"""
Utility decorators for TripSage.

This module provides decorators used across the TripSage codebase for standardized
error handling and client initialization patterns.
"""

import asyncio
import functools
import inspect
from typing import Any, Callable, TypeVar, cast

from tripsage.utils.error_handling import log_exception
from tripsage.utils.logging import get_logger

logger = get_logger(__name__)

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


def ensure_memory_client_initialized(func: F) -> F:
    """Decorator to ensure memory service is initialized.

    This decorator ensures that the memory service is initialized before
    the decorated function is called. This avoids redundant initialization
    calls in each function that uses the memory service.

    Args:
        func: Function to decorate (must be async)

    Returns:
        Decorated function with memory service initialization

    Example:
        ```python
        @function_tool
        @ensure_memory_client_initialized
        async def add_memory() -> Dict[str, Any]:
            # Memory service is already initialized here
            from tripsage.services.memory_service import memory_service
            result = await memory_service.add("user-123", "Trip preference")
            return {"memory_id": result}
        ```
    """
    if not inspect.iscoroutinefunction(func):
        raise TypeError(
            f"ensure_memory_client_initialized can only be used with async functions. "
            f"{func.__name__} is not async."
        )

    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        """Wrapper function that initializes memory service."""
        try:
            # Import here to avoid circular imports
            from tripsage.services.memory_service import memory_service

            # Initialize the memory service if not already initialized
            if not memory_service._initialized:
                await memory_service.initialize()

            # Call the original function
            return await func(*args, **kwargs)
        except Exception as e:
            # Get function name for better error logging
            func_name = func.__name__
            logger.error(f"Error in {func_name}: {str(e)}")
            log_exception(e)

            # Return error response in the expected format for agent tools
            # Only do this if the function returns a dict (for agent tools)
            signature = inspect.signature(func)
            if "Dict" in str(signature.return_annotation):
                return {"error": str(e)}
            # Re-raise for non-dict returning functions
            raise

    return cast(F, wrapper)


# Retry decorator for network operations
def retry_on_failure(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,)
) -> Callable[[F], F]:
    """Decorator to retry failed operations with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff_factor: Factor to multiply delay by after each retry
        exceptions: Tuple of exceptions to catch and retry

    Returns:
        Decorated function with retry logic
    """
    def decorator(func: F) -> F:
        if inspect.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                last_exception = None
                current_delay = delay
                
                for attempt in range(max_attempts):
                    try:
                        return await func(*args, **kwargs)
                    except exceptions as e:
                        last_exception = e
                        if attempt < max_attempts - 1:
                            logger.warning(
                                f"{func.__name__} failed (attempt {attempt + 1}/{max_attempts}): {e}"
                            )
                            await asyncio.sleep(current_delay)
                            current_delay *= backoff_factor
                        else:
                            logger.error(f"{func.__name__} failed after {max_attempts} attempts")
                            raise
                
                if last_exception:
                    raise last_exception
                    
            return cast(F, async_wrapper)
        else:
            @functools.wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                last_exception = None
                current_delay = delay
                
                for attempt in range(max_attempts):
                    try:
                        return func(*args, **kwargs)
                    except exceptions as e:
                        last_exception = e
                        if attempt < max_attempts - 1:
                            logger.warning(
                                f"{func.__name__} failed (attempt {attempt + 1}/{max_attempts}): {e}"
                            )
                            import time
                            time.sleep(current_delay)
                            current_delay *= backoff_factor
                        else:
                            logger.error(f"{func.__name__} failed after {max_attempts} attempts")
                            raise
                
                if last_exception:
                    raise last_exception
                    
            return cast(F, sync_wrapper)
    
    return decorator


__all__ = [
    "ensure_memory_client_initialized", 
    "with_error_handling",
    "retry_on_failure"
]