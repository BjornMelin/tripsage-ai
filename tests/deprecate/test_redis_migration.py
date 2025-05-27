"""Tests for Redis migration from MCP to direct SDK integration."""

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
        # Reset Redis service connection state
        redis_service._connected = False
        redis_service._client = None
        yield
        feature_flags.redis_integration = original_mode
        redis_service._connected = False
        redis_service._client = None

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
            # Note: get might be called multiple times due to JSON decoding attempts

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

    @pytest.mark.asyncio
    async def test_redis_service_connection(self):
        """Test Redis service connection management."""
        # Test initial state
        assert not redis_service.is_connected

        # Mock connection pool and successful connection
        with (
            patch("redis.asyncio.ConnectionPool.from_url"),
            patch("redis.asyncio.Redis") as mock_redis_class,
        ):
            mock_client = AsyncMock()
            mock_client.ping = AsyncMock(return_value=True)
            mock_client.aclose = AsyncMock()
            mock_redis_class.return_value = mock_client

            # Test connection
            await redis_service.connect()
            assert redis_service.is_connected

            # Test disconnect
            await redis_service.close()
            assert not redis_service.is_connected

    @pytest.mark.asyncio
    async def test_redis_service_error_handling(self):
        """Test Redis service error handling."""
        with (
            patch("redis.asyncio.ConnectionPool.from_url"),
            patch("redis.asyncio.Redis") as mock_redis_class,
        ):
            mock_client = AsyncMock()
            mock_client.ping = AsyncMock(side_effect=Exception("Connection failed"))
            mock_redis_class.return_value = mock_client

            # Test connection error handling
            with pytest.raises(Exception, match="Connection failed"):
                await redis_service.connect()

            assert not redis_service.is_connected


class TestFeatureFlags:
    """Test feature flags functionality."""

    def test_feature_flag_defaults(self):
        """Test default feature flag values."""
        flags = feature_flags

        # Week 1 services should default to MCP initially
        assert flags.redis_integration == IntegrationMode.MCP
        assert flags.supabase_integration == IntegrationMode.MCP

        # Already migrated services should be DIRECT
        assert flags.crawl4ai_integration == IntegrationMode.DIRECT
        assert flags.playwright_integration == IntegrationMode.DIRECT

    def test_migration_status_reporting(self):
        """Test migration status reporting."""
        status = feature_flags.get_migration_status()

        assert "services" in status
        assert "summary" in status
        assert "total_services" in status["summary"]
        assert "direct_sdk" in status["summary"]
        assert "mcp_wrapper" in status["summary"]
        assert "migration_percentage" in status["summary"]

    def test_service_mode_helpers(self):
        """Test service mode helper methods."""
        # Test getting integration mode
        mode = feature_flags.get_integration_mode("redis")
        assert isinstance(mode, IntegrationMode)

        # Test setting integration mode
        original_mode = feature_flags.redis_integration
        feature_flags.set_integration_mode("redis", IntegrationMode.DIRECT)
        assert feature_flags.redis_integration == IntegrationMode.DIRECT

        # Reset
        feature_flags.redis_integration = original_mode
