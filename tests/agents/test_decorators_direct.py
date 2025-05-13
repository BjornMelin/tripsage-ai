"""
Direct tests for decorators functionality.

This module directly tests the decorator patterns used in memory tools.
"""

import asyncio
import functools
from typing import Any, Callable, Dict, TypeVar, cast
from unittest.mock import AsyncMock, MagicMock

import pytest

# Define our own versions of the decorators for testing
F = TypeVar("F", bound=Callable[..., Any])


def ensure_memory_client_initialized(func: F) -> F:
    """Decorator to ensure memory client is initialized."""

    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        """Wrapper function that initializes memory client."""
        try:
            # Initialize the memory client once
            await memory_client.initialize()
            # Call the original function
            return await func(*args, **kwargs)
        except Exception as e:
            # Error handling will happen in the with_error_handling decorator
            raise e

    return cast(F, wrapper)


def with_error_handling(func: F) -> F:
    """Decorator to handle errors consistently in memory functions."""

    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Wrapper function that handles errors."""
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            return {"error": str(e)}

    return cast(F, wrapper)


@pytest.mark.asyncio
class TestDecorators:
    """Tests for decorators."""

    @pytest.fixture
    def setup_memory_client(self):
        """Setup mock memory client."""
        global memory_client
        memory_client = MagicMock()
        memory_client.initialize = AsyncMock()
        yield memory_client

    async def test_ensure_memory_client_initialized(self, setup_memory_client):
        """Test ensure_memory_client_initialized decorator."""

        # Define test function with decorator
        @ensure_memory_client_initialized
        async def test_func():
            return "success"

        # Call function
        result = await test_func()

        # Verify
        memory_client.initialize.assert_called_once()
        assert result == "success"

    async def test_with_error_handling(self):
        """Test with_error_handling decorator."""

        # Define test function that raises exception
        @with_error_handling
        async def failing_func():
            raise ValueError("Test error")

        # Call function
        result = await failing_func()

        # Verify error is handled
        assert "error" in result
        assert result["error"] == "Test error"

    async def test_combined_decorators(self, setup_memory_client):
        """Test both decorators together."""

        # Define test function with both decorators
        @with_error_handling
        @ensure_memory_client_initialized
        async def test_func():
            return "success"

        # Call function
        result = await test_func()

        # Verify
        memory_client.initialize.assert_called_once()
        assert result == "success"

        # Test with error
        memory_client.initialize.side_effect = ValueError("Init error")

        # Call function again
        result = await test_func()

        # Verify error is handled
        assert "error" in result
        assert result["error"] == "Init error"

    async def test_function_tool_pattern(self, setup_memory_client):
        """Test the function_tool pattern that our refactor uses."""
        # Reset any side effects from previous tests
        setup_memory_client.initialize.side_effect = None

        # Mock the function_tool decorator
        def function_tool(func):
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                # In reality, this would register with OpenAI SDK
                return await func(*args, **kwargs)

            return wrapper

        # Create a typical memory tool with both our decorators
        @function_tool
        @with_error_handling
        @ensure_memory_client_initialized
        async def get_knowledge_graph():
            """Test memory tool."""
            # This is what our memory tool would do
            return {"entities": [], "relations": []}

        # Call the function and check result
        result = await get_knowledge_graph()

        # Should have data without errors
        assert "entities" in result
        assert "relations" in result
        assert "error" not in result

        # Now make it fail
        setup_memory_client.initialize.side_effect = ValueError("Init failed")

        # Call again and check error handling
        result = await get_knowledge_graph()

        # Should have error info
        assert "error" in result
        assert result["error"] == "Init failed"


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
