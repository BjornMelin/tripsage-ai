"""
Tests for utility decorators.

This module tests the decorators in src/utils/decorators.py, ensuring they work
correctly with both synchronous and asynchronous functions.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.utils.decorators import ensure_memory_client_initialized, with_error_handling


class TestWithErrorHandling:
    """Tests for the with_error_handling decorator."""

    @pytest.mark.asyncio
    async def test_async_function_success(self):
        """Test successful execution of async function with error handling."""

        @with_error_handling
        async def test_func(value: int) -> dict:
            return {"result": value * 2}

        result = await test_func(5)
        assert result["result"] == 10

    @pytest.mark.asyncio
    async def test_async_function_error(self):
        """Test error handling in async function."""

        @with_error_handling
        async def test_func(value: int) -> dict:
            if value < 0:
                raise ValueError("Value cannot be negative")
            return {"result": value * 2}

        result = await test_func(-5)
        assert "error" in result
        assert "Value cannot be negative" in result["error"]

    @pytest.mark.asyncio
    async def test_async_function_non_dict_error(self):
        """Test error handling in async function that doesn't return a dict."""

        @with_error_handling
        async def test_func(value: int) -> int:
            if value < 0:
                raise ValueError("Value cannot be negative")
            return value * 2

        # Should re-raise the exception
        with pytest.raises(ValueError, match="Value cannot be negative"):
            await test_func(-5)

    def test_sync_function_success(self):
        """Test successful execution of sync function with error handling."""

        @with_error_handling
        def test_func(value: int) -> dict:
            return {"result": value * 2}

        result = test_func(5)
        assert result["result"] == 10

    def test_sync_function_error(self):
        """Test error handling in sync function."""

        @with_error_handling
        def test_func(value: int) -> dict:
            if value < 0:
                raise ValueError("Value cannot be negative")
            return {"result": value * 2}

        result = test_func(-5)
        assert "error" in result
        assert "Value cannot be negative" in result["error"]

    def test_sync_function_non_dict_error(self):
        """Test error handling in sync function that doesn't return a dict."""

        @with_error_handling
        def test_func(value: int) -> int:
            if value < 0:
                raise ValueError("Value cannot be negative")
            return value * 2

        # Should re-raise the exception
        with pytest.raises(ValueError, match="Value cannot be negative"):
            test_func(-5)


@pytest.mark.asyncio
class TestEnsureMemoryClientInitialized:
    """Tests for the ensure_memory_client_initialized decorator."""

    @pytest.fixture
    def setup_mock_memory_client(self):
        """Set up mock memory client."""
        with patch("src.utils.decorators.memory_client") as mock_client:
            mock_client.initialize = AsyncMock()
            yield mock_client

    async def test_initialization_called(self, setup_mock_memory_client):
        """Test that memory client is initialized."""
        mock_client = setup_mock_memory_client

        @ensure_memory_client_initialized
        async def test_func() -> dict:
            return {"success": True}

        result = await test_func()
        mock_client.initialize.assert_called_once()
        assert result["success"] is True

    async def test_initialization_error(self, setup_mock_memory_client):
        """Test error handling when initialization fails."""
        mock_client = setup_mock_memory_client
        mock_client.initialize.side_effect = Exception("Initialization failed")

        @ensure_memory_client_initialized
        async def test_func() -> dict:
            return {"success": True}

        result = await test_func()
        assert "error" in result
        assert "Initialization failed" in result["error"]

    def test_sync_function_error(self):
        """Test that decorator raises error when used with sync function."""

        with pytest.raises(TypeError, match="can only be used with async functions"):
            @ensure_memory_client_initialized
            def test_func() -> dict:
                return {"success": True}