"""
Standalone tests for decorator functionality.

These tests validate the decorator logic without depending on
application configuration.
"""

import asyncio
import functools
import inspect
from typing import Any, Callable, Dict, TypeVar, cast

import pytest

# Clone essential decorator logic for testing
F = TypeVar("F", bound=Callable[..., Any])


def with_error_handling_standalone(func: F) -> F:
    """Simplified version of with_error_handling for testing."""
    # Check if the function is a coroutine function (async)
    if inspect.iscoroutinefunction(func):
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            """Async wrapper function with try-except block."""
            try:
                # Call the original async function
                return await func(*args, **kwargs)
            except Exception as e:
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
                # Check if function returns Dict (for agent tools)
                signature = inspect.signature(func)
                return_type = signature.return_annotation
                if "Dict" in str(return_type):
                    # Return error response in the expected format for agent tools
                    return {"error": str(e)}
                # Re-raise for non-dict returning functions
                raise
        
        return cast(F, sync_wrapper)


class TestStandaloneWithErrorHandling:
    """Tests for the standalone with_error_handling_standalone decorator."""

    @pytest.mark.asyncio
    async def test_async_function_success(self):
        """Test successful execution of async function with error handling."""

        @with_error_handling_standalone
        async def test_func(value: int) -> Dict[str, Any]:
            return {"result": value * 2}

        result = await test_func(5)
        assert result["result"] == 10

    @pytest.mark.asyncio
    async def test_async_function_error(self):
        """Test error handling in async function."""

        @with_error_handling_standalone
        async def test_func(value: int) -> Dict[str, Any]:
            if value < 0:
                raise ValueError("Value cannot be negative")
            return {"result": value * 2}

        result = await test_func(-5)
        assert "error" in result
        assert "Value cannot be negative" in result["error"]

    @pytest.mark.asyncio
    async def test_async_function_non_dict_error(self):
        """Test error handling in async function that doesn't return a dict."""

        @with_error_handling_standalone
        async def test_func(value: int) -> int:
            if value < 0:
                raise ValueError("Value cannot be negative")
            return value * 2

        # Should re-raise the exception
        with pytest.raises(ValueError, match="Value cannot be negative"):
            await test_func(-5)

    def test_sync_function_success(self):
        """Test successful execution of sync function with error handling."""

        @with_error_handling_standalone
        def test_func(value: int) -> Dict[str, Any]:
            return {"result": value * 2}

        result = test_func(5)
        assert result["result"] == 10

    def test_sync_function_error(self):
        """Test error handling in sync function."""

        @with_error_handling_standalone
        def test_func(value: int) -> Dict[str, Any]:
            if value < 0:
                raise ValueError("Value cannot be negative")
            return {"result": value * 2}

        result = test_func(-5)
        assert "error" in result
        assert "Value cannot be negative" in result["error"]

    def test_sync_function_non_dict_error(self):
        """Test error handling in sync function that doesn't return a dict."""

        @with_error_handling_standalone
        def test_func(value: int) -> int:
            if value < 0:
                raise ValueError("Value cannot be negative")
            return value * 2

        # Should re-raise the exception
        with pytest.raises(ValueError, match="Value cannot be negative"):
            test_func(-5)