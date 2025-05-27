"""
Basic tests for decorator functionality.
"""

import functools
from typing import Any, Callable, TypeVar, cast

import pytest

# Define a simplified version of the decorator for testing
F = TypeVar("F", bound=Callable[..., Any])


def test_error_handling_decorator(func: F) -> F:
    """Simplified version of the error handling decorator for testing."""

    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        """Wrapper function that adds try-except block."""
        try:
            # Call the original function
            return await func(*args, **kwargs)
        except Exception as e:
            # Return error response in the expected format for agent tools
            return {"error": str(e)}

    return cast(F, wrapper)


@pytest.mark.asyncio
class TestBasicDecorators:
    """Tests for the basic decorator functionality."""

    @test_error_handling_decorator
    async def sample_function(self, arg1, arg2=None):
        """Sample function that uses the decorator."""
        if arg1 == "error":
            raise ValueError("Test error")
        if arg1 == "exception":
            raise Exception("General exception")
        return {"success": True, "arg1": arg1, "arg2": arg2}

    async def test_normal_execution(self):
        """Test that the decorator allows normal execution."""
        result = await self.sample_function("test", arg2="value")
        assert result["success"] is True
        assert result["arg1"] == "test"
        assert result["arg2"] == "value"

    async def test_value_error_handling(self):
        """Test that the decorator handles ValueError."""
        result = await self.sample_function("error")
        assert "error" in result
        assert "Test error" in result["error"]
        assert "success" not in result

    async def test_general_exception_handling(self):
        """Test that the decorator handles general exceptions."""
        result = await self.sample_function("exception")
        assert "error" in result
        assert "General exception" in result["error"]
        assert "success" not in result
