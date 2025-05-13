"""
Tests for memory tool decorators.

This module tests the decorators used in memory tools without dependencies.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.utils.decorators import ensure_memory_client_initialized, with_error_handling


@pytest.mark.asyncio
class TestDecorators:
    """Tests for memory tool decorators."""

    @pytest.fixture
    def mock_memory_client(self):
        """Mock memory client."""
        with patch("src.mcp.memory.client.memory_client") as mock_client:
            mock_client.initialize = AsyncMock()
            yield mock_client

    async def test_ensure_memory_client_initialized(self, mock_memory_client):
        """Test ensure_memory_client_initialized decorator."""

        # Define test function with decorator
        @ensure_memory_client_initialized
        async def test_func():
            return "success"

        # Call function
        result = await test_func()

        # Verify
        mock_memory_client.initialize.assert_called_once()
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

    async def test_combined_decorators(self, mock_memory_client):
        """Test both decorators together."""

        # Define test function with both decorators
        @with_error_handling
        @ensure_memory_client_initialized
        async def test_func():
            return "success"

        # Call function
        result = await test_func()

        # Verify
        mock_memory_client.initialize.assert_called_once()
        assert result == "success"

        # Test with error
        mock_memory_client.initialize.side_effect = ValueError("Init error")

        # Call function again
        result = await test_func()

        # Verify error is handled
        assert "error" in result
        assert result["error"] == "Init error"


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
