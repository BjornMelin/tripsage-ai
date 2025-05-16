"""
Tests for calendar tools' decorator functionality.

This module tests the error handling decorator in calendar tools.
"""

import pytest

from tripsage.utils.decorators import with_error_handling


@pytest.mark.asyncio
class TestErrorHandlingDecorator:
    """Tests for the error handling decorator."""

    @with_error_handling
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
