"""Tests for Redis migration from MCP to direct SDK integration."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from tripsage.config.feature_flags import IntegrationMode, feature_flags
from tripsage.services.redis_service import redis_service
from tripsage.utils.cache_tools import get_cache, set_cache


class TestRedisMigration:
    """Test Redis migration functionality."""

    @pytest.fixture(autouse=True)
    async def setup(self):
        """Setup test environment."""
        # Reset feature flags to known state
        original_mode = feature_flags.redis_integration
        yield
        feature_flags.redis_integration = original_mode

    @pytest.mark.asyncio
    async def test_feature_flag_switching(self):
        """Test switching between MCP and direct Redis modes."""
        # Test MCP mode
        feature_flags.redis_integration = IntegrationMode.MCP
        assert feature_flags.redis_integration == IntegrationMode.MCP

        # Test direct mode
        feature_flags.redis_integration = IntegrationMode.DIRECT
        assert feature_flags.redis_integration == IntegrationMode.DIRECT

    @pytest.mark.asyncio
    async def test_direct_redis_operations(self):
        """Test direct Redis operations."""
        # Use direct mode
        feature_flags.redis_integration = IntegrationMode.DIRECT

        # Mock Redis connection
        with patch.object(redis_service, "_client") as mock_client:
            mock_client.ping = AsyncMock(return_value=True)
            mock_client.set = AsyncMock(return_value=True)
            mock_client.get = AsyncMock(return_value=b"test_value")
            mock_client.delete = AsyncMock(return_value=1)

            # Mark as connected
            redis_service._connected = True

            # Test set operation
            result = await set_cache("test_key", "test_value", ttl=300)
            assert result is True
            mock_client.set.assert_called_once()

            # Test get operation
            result = await get_cache("test_key")
            assert result == "test_value"
            mock_client.get.assert_called_once()

            # Test direct Redis service delete operation
            result = await redis_service.delete("test_key")
            assert result == 1
            mock_client.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_tools_integration(self):
        """Test cache tools integration with direct Redis service."""
        # Use direct mode for testing cache tools
        feature_flags.redis_integration = IntegrationMode.DIRECT

        # Mock Redis service for cache tools
        with patch.object(redis_service, "_client") as mock_client:
            mock_client.ping = AsyncMock(return_value=True)
            mock_client.set = AsyncMock(return_value=True)
            mock_client.get = AsyncMock(return_value=b'{"test": "data"}')
            
            # Mark as connected
            redis_service._connected = True

            # Test JSON cache operations
            test_data = {"test": "data"}
            result = await set_cache("json_key", test_data, ttl=300)
            assert result is True

            # Test get JSON operation
            result = await get_cache("json_key")
            assert result == test_data
            assert result == "test_value"

            # Test delete operation
            result = await cache_service.delete("test_key")
            assert result == 1

            # Verify MCP calls
            assert mock_mcp.invoke.call_count == 3

    @pytest.mark.asyncio
    async def test_performance_comparison(self):
        """Test performance difference between MCP and direct modes."""
        import time

        # Mock implementations with different delays
        with patch.object(redis_service, "_client") as mock_client:
            # Direct Redis - fast response
            mock_client.ping = AsyncMock(return_value=True)
            mock_client.set = AsyncMock(return_value=True)
            mock_client.get = AsyncMock(return_value=b"test_value")

            redis_service._connected = True

            with patch("tripsage.services.cache_service.MCPManager") as mock_mcp_class:
                mock_mcp = AsyncMock()
                mock_mcp_class.return_value = mock_mcp

                # MCP - slower response (simulated network overhead)
                async def slow_mcp_invoke(*args, **kwargs):
                    await asyncio.sleep(0.01)  # 10ms delay
                    return True

                mock_mcp.invoke = slow_mcp_invoke

                # Test direct mode performance
                feature_flags.redis_integration = IntegrationMode.DIRECT
                start_time = time.perf_counter()

                for _ in range(10):
                    await cache_service.set(f"key_{_}", f"value_{_}")

                direct_time = time.perf_counter() - start_time

                # Test MCP mode performance
                feature_flags.redis_integration = IntegrationMode.MCP
                start_time = time.perf_counter()

                for _ in range(10):
                    await cache_service.set(f"key_{_}", f"value_{_}")

                mcp_time = time.perf_counter() - start_time

                # Direct should be significantly faster
                improvement = (mcp_time - direct_time) / mcp_time * 100
                assert improvement > 50, (
                    f"Expected >50% improvement, got {improvement:.1f}%"
                )

    @pytest.mark.asyncio
    async def test_json_operations(self):
        """Test JSON cache operations."""
        feature_flags.redis_integration = IntegrationMode.DIRECT

        with patch.object(redis_service, "_client") as mock_client:
            mock_client.ping = AsyncMock(return_value=True)
            mock_client.set = AsyncMock(return_value=True)
            mock_client.get = AsyncMock(return_value=b'{"key": "value", "number": 42}')

            redis_service._connected = True

            # Test JSON set
            test_data = {"key": "value", "number": 42}
            result = await cache_service.set_json("json_key", test_data)
            assert result is True

            # Test JSON get
            result = await cache_service.get_json("json_key")
            assert result == test_data

    @pytest.mark.asyncio
    async def test_integration_status(self):
        """Test integration status reporting."""
        # Test direct mode status
        feature_flags.redis_integration = IntegrationMode.DIRECT
        status = await cache_service.get_integration_status()

        assert status["integration_mode"] == "direct"
        assert status["is_direct"] is True
        assert status["is_mcp"] is False

        # Test MCP mode status
        feature_flags.redis_integration = IntegrationMode.MCP
        status = await cache_service.get_integration_status()

        assert status["integration_mode"] == "mcp"
        assert status["is_direct"] is False
        assert status["is_mcp"] is True

    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test error handling in both modes."""
        # Test direct mode error handling
        feature_flags.redis_integration = IntegrationMode.DIRECT

        with patch.object(redis_service, "_client") as mock_client:
            mock_client.set = AsyncMock(side_effect=Exception("Connection error"))
            redis_service._connected = True

            # Should handle error gracefully
            result = await cache_service.set("error_key", "value")
            # Depending on implementation, might return False or raise
            # This tests that it doesn't crash the application
            assert isinstance(result, (bool, type(None)))

    @pytest.mark.asyncio
    async def test_pipeline_operations(self):
        """Test pipeline operations (direct mode only)."""
        feature_flags.redis_integration = IntegrationMode.DIRECT

        with patch.object(redis_service, "_client") as mock_client:
            mock_pipeline = AsyncMock()
            mock_client.pipeline = AsyncMock(return_value=mock_pipeline)
            mock_pipeline.__aenter__ = AsyncMock(return_value=mock_pipeline)
            mock_pipeline.__aexit__ = AsyncMock(return_value=None)

            redis_service._connected = True

            # Test pipeline context
            async with cache_service.pipeline() as pipe:
                assert pipe is not None

    @pytest.mark.asyncio
    async def test_migration_compatibility(self):
        """Test that existing cache_tools functions work with new service."""
        from tripsage.utils.cache_tools import delete_cache, get_cache, set_cache

        feature_flags.redis_integration = IntegrationMode.DIRECT

        with patch.object(redis_service, "_client") as mock_client:
            mock_client.ping = AsyncMock(return_value=True)
            mock_client.set = AsyncMock(return_value=True)
            mock_client.get = AsyncMock(return_value=b"compatibility_test")
            mock_client.delete = AsyncMock(return_value=1)

            redis_service._connected = True

            # Test backward compatibility
            result = await set_cache("compat_key", "compatibility_test")
            assert result is True

            result = await get_cache("compat_key")
            assert result == "compatibility_test"

            result = await delete_cache("compat_key")
            assert result is True
