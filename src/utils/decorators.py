"""
Utility decorators for TripSage.

This module provides decorators used across the TripSage codebase for client
initialization and other common patterns that specifically depend on MCP clients.
"""

import functools
import inspect
from typing import Any, Callable, TypeVar, cast

# Import error handling decorator from separated module
from src.utils.error_decorators import with_error_handling

# Lazy import of memory_client to avoid circular imports
from src.utils.error_handling import log_exception
from src.utils.logging import get_module_logger

logger = get_module_logger(__name__)

# Type definitions for better type checking
F = TypeVar("F", bound=Callable[..., Any])


def ensure_memory_client_initialized(func: F) -> F:
    """Decorator to ensure memory client is initialized.

    This decorator ensures that the memory client is initialized before
    the decorated function is called. This avoids redundant initialization
    calls in each function that uses the memory client.

    Args:
        func: Function to decorate (must be async)

    Returns:
        Decorated function with memory client initialization

    Example:
        ```python
        @function_tool
        @ensure_memory_client_initialized
        async def get_knowledge_graph() -> Dict[str, Any]:
            # Client is already initialized here
            graph_data = await memory_client.read_graph()
            return {"entities": graph_data.get("entities", [])}
        ```
    """
    if not inspect.iscoroutinefunction(func):
        raise TypeError(
            f"ensure_memory_client_initialized can only be used with async functions. "
            f"{func.__name__} is not async."
        )

    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        """Wrapper function that initializes memory client."""
        try:
            # Import here to avoid circular imports
            from src.mcp.memory.client import memory_client
            
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
            signature = inspect.signature(func)
            if "Dict" in str(signature.return_annotation):
                return {"error": str(e)}
            # Re-raise for non-dict returning functions
            raise

    return cast(F, wrapper)


# Re-export with_error_handling to maintain backward compatibility
__all__ = ["ensure_memory_client_initialized", "with_error_handling"]
