"""
Unit tests for TripSage Core Cache Service.

Tests the cache service functionality with mocked DragonflyDB/Redis client.
"""

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch

import pytest

from tripsage_core.config.base_app_settings import CoreAppSettings
from tripsage_core.exceptions.exceptions import CoreServiceError
from tripsage_core.services.infrastructure.cache_service import (
    CacheService,
    get_cache_service,
)


class TestCacheService:
    """Test suite for CacheService."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = Mock(spec=CoreAppSettings)
        settings.dragonfly = Mock()
        settings.dragonfly.url = "redis://localhost:6379/0"
        settings.dragonfly.ttl_short = 300
        settings.dragonfly.ttl_medium = 3600
        settings.dragonfly.ttl_long = 86400
        settings.dragonfly.max_connections = 10000
        settings.dragonfly.thread_count = 4
        return settings

    @pytest.fixture
    def mock_redis_client(self):
        """Create a mock Redis/DragonflyDB client."""
        client = AsyncMock()
        client.ping = AsyncMock(return_value=True)
        client.get = AsyncMock(return_value=None)
        client.set = AsyncMock(return_value=True)
        client.delete = AsyncMock(return_value=1)
        client.exists = AsyncMock(return_value=1)
        client.expire = AsyncMock(return_value=True)
        client.ttl = AsyncMock(return_value=300)
        client.mget = AsyncMock(return_value=[None, None])
        client.mset = AsyncMock(return_value=True)
        client.scan = AsyncMock(return_value=(0, []))
        client.incr = AsyncMock(return_value=1)
        client.decr = AsyncMock(return_value=1)
        client.info = AsyncMock(return_value={"used_memory": 1024000})
        client.flushdb = AsyncMock(return_value=True)
        client.close = AsyncMock()
        return client

    @pytest.fixture
    def cache_service(self, mock_settings, mock_redis_client):
        """Create a CacheService instance with mocked dependencies."""
        mock_pool = Mock()
        with (
            patch("redis.asyncio.ConnectionPool.from_url", return_value=mock_pool),
            patch("redis.asyncio.Redis", return_value=mock_redis_client),
        ):
            service = CacheService(settings=mock_settings)
            service._client = mock_redis_client
            service._connected = True
            service._is_connected = True
            return service

    @pytest.mark.asyncio
    async def test_connect_success(self, mock_settings, mock_redis_client):
        """Test successful cache connection."""
        mock_pool = Mock()
        with (
            patch("redis.asyncio.ConnectionPool.from_url", return_value=mock_pool),
            patch("redis.asyncio.Redis", return_value=mock_redis_client),
        ):
            service = CacheService(settings=mock_settings)

            await service.connect()

            assert service.is_connected
            assert service._client is not None
            mock_redis_client.ping.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_failure(self, mock_settings, mock_redis_client):
        """Test cache connection failure."""
        mock_redis_client.ping.side_effect = Exception("Connection failed")

        with patch("redis.asyncio.from_url", return_value=mock_redis_client):
            service = CacheService(settings=mock_settings)

            with pytest.raises(CoreServiceError, match="Failed to connect to cache"):
                await service.connect()

    @pytest.mark.asyncio
    async def test_set_json_success(self, cache_service, mock_redis_client):
        """Test successful JSON value setting."""
        test_data = {
            "name": "Test",
            "value": 123,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        result = await cache_service.set_json("test:key", test_data, ttl=600)

        assert result is True
        mock_redis_client.set.assert_called_once()
        # Verify JSON serialization
        call_args = mock_redis_client.set.call_args
        assert json.loads(call_args[0][1]) == test_data
        assert call_args[1]["ex"] == 600

    @pytest.mark.asyncio
    async def test_get_json_success(self, cache_service, mock_redis_client):
        """Test successful JSON value retrieval."""
        test_data = {"name": "Test", "value": 123}
        mock_redis_client.get.return_value = json.dumps(test_data)

        result = await cache_service.get_json("test:key")

        assert result == test_data
        mock_redis_client.get.assert_called_with("test:key")

    @pytest.mark.asyncio
    async def test_get_json_miss(self, cache_service, mock_redis_client):
        """Test JSON retrieval when key doesn't exist."""
        mock_redis_client.get.return_value = None
        default_value = {"default": True}

        result = await cache_service.get_json("missing:key", default=default_value)

        assert result == default_value

    @pytest.mark.asyncio
    async def test_set_string_success(self, cache_service, mock_redis_client):
        """Test successful string value setting."""
        result = await cache_service.set("test:string", "Hello World", ttl=300)

        assert result is True
        mock_redis_client.set.assert_called_with("test:string", "Hello World", ex=300)

    @pytest.mark.asyncio
    async def test_get_string_success(self, cache_service, mock_redis_client):
        """Test successful string value retrieval."""
        mock_redis_client.get.return_value = "Hello World"

        result = await cache_service.get("test:string")

        assert result == "Hello World"

    @pytest.mark.asyncio
    async def test_delete_keys_success(self, cache_service, mock_redis_client):
        """Test successful key deletion."""
        mock_redis_client.delete.return_value = 2

        result = await cache_service.delete("key1", "key2")

        assert result == 2
        mock_redis_client.delete.assert_called_with("key1", "key2")

    @pytest.mark.asyncio
    async def test_exists_keys(self, cache_service, mock_redis_client):
        """Test key existence check."""
        mock_redis_client.exists.return_value = 1

        result = await cache_service.exists("test:key")

        assert result == 1

    @pytest.mark.asyncio
    async def test_expire_key(self, cache_service, mock_redis_client):
        """Test setting key expiration."""
        result = await cache_service.expire("test:key", 600)

        assert result is True
        mock_redis_client.expire.assert_called_with("test:key", 600)

    @pytest.mark.asyncio
    async def test_ttl_key(self, cache_service, mock_redis_client):
        """Test getting key TTL."""
        mock_redis_client.ttl.return_value = 300

        result = await cache_service.ttl("test:key")

        assert result == 300

    @pytest.mark.asyncio
    async def test_incr_success(self, cache_service, mock_redis_client):
        """Test incrementing a counter."""
        mock_redis_client.incr.return_value = 5

        result = await cache_service.incr("counter:test")

        assert result == 5

    @pytest.mark.asyncio
    async def test_decr_success(self, cache_service, mock_redis_client):
        """Test decrementing a counter."""
        mock_redis_client.decr.return_value = 3

        result = await cache_service.decr("counter:test")

        assert result == 3

    @pytest.mark.asyncio
    async def test_mget_success(self, cache_service, mock_redis_client):
        """Test multiple key retrieval."""
        mock_redis_client.mget.return_value = ["value1", "value2", None]

        result = await cache_service.mget(["key1", "key2", "key3"])

        assert result == ["value1", "value2", None]

    @pytest.mark.asyncio
    async def test_mset_success(self, cache_service, mock_redis_client):
        """Test multiple key setting."""
        mapping = {"key1": "value1", "key2": "value2"}

        result = await cache_service.mset(mapping)

        assert result is True
        mock_redis_client.mset.assert_called_with(mapping)

    @pytest.mark.asyncio
    async def test_keys_pattern(self, cache_service, mock_redis_client):
        """Test retrieving keys by pattern."""
        mock_redis_client.scan = AsyncMock(
            side_effect=[(123, ["user:1", "user:2"]), (0, ["user:3"])]
        )

        result = await cache_service.keys("user:*")

        assert result == ["user:1", "user:2", "user:3"]

    @pytest.mark.asyncio
    async def test_delete_pattern(self, cache_service, mock_redis_client):
        """Test deleting keys by pattern."""
        mock_redis_client.scan = AsyncMock(
            side_effect=[(123, ["temp:1", "temp:2"]), (0, ["temp:3"])]
        )
        mock_redis_client.delete.return_value = 3

        result = await cache_service.delete_pattern("temp:*")

        assert result == 3

    @pytest.mark.asyncio
    async def test_flushdb(self, cache_service, mock_redis_client):
        """Test flushing the database."""
        result = await cache_service.flushdb()

        assert result is True
        mock_redis_client.flushdb.assert_called_once()

    @pytest.mark.asyncio
    async def test_info(self, cache_service, mock_redis_client):
        """Test getting cache info."""
        expected_info = {
            "used_memory": 1024000,
            "connected_clients": 5,
            "uptime_in_seconds": 3600,
        }
        mock_redis_client.info.return_value = expected_info

        result = await cache_service.info()

        assert result == expected_info

    @pytest.mark.asyncio
    async def test_health_check_success(self, cache_service, mock_redis_client):
        """Test successful health check."""
        result = await cache_service.health_check()

        assert result is True
        mock_redis_client.ping.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_check_failure(self, cache_service, mock_redis_client):
        """Test health check failure."""
        mock_redis_client.ping.side_effect = Exception("Connection lost")

        result = await cache_service.health_check()

        assert result is False

    @pytest.mark.asyncio
    async def test_disconnect(self, cache_service, mock_redis_client):
        """Test disconnecting from cache."""
        await cache_service.disconnect()

        assert not cache_service.is_connected
        assert cache_service._client is None
        mock_redis_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_ensure_connected_when_not_connected(self, cache_service):
        """Test ensure_connected when not connected."""
        cache_service._connected = False

        with patch.object(
            cache_service, "connect", new_callable=AsyncMock
        ) as mock_connect:
            await cache_service.ensure_connected()
            mock_connect.assert_called_once()

    # NOTE: Cache service doesn't currently check feature_flags.enable_caching
    # This test is commented out until that functionality is added
    # @pytest.mark.asyncio
    # async def test_operation_when_disabled(self, mock_settings):
    #     """Test operations when cache is disabled."""
    #     mock_settings.feature_flags = Mock()
    #     mock_settings.feature_flags.enable_caching = False
    #     service = CacheService(settings=mock_settings)
    #
    #     # Operations should return default values when disabled
    #     result = await service.get("test:key")
    #     assert result is None
    #
    #     result = await service.set("test:key", "value")
    #     assert result is False

    @pytest.mark.asyncio
    async def test_get_cache_service_function(self, mock_settings, mock_redis_client):
        """Test the get_cache_service dependency function."""
        mock_pool = Mock()
        with (
            patch(
                "tripsage_core.services.infrastructure.cache_service.get_settings",
                return_value=mock_settings,
            ),
            patch("redis.asyncio.ConnectionPool.from_url", return_value=mock_pool),
            patch("redis.asyncio.Redis", return_value=mock_redis_client),
            patch(
                "tripsage_core.services.infrastructure.cache_service._cache_service",
                None,
            ),
        ):
            service = await get_cache_service()
            assert isinstance(service, CacheService)

    @pytest.mark.asyncio
    async def test_error_handling(self, cache_service, mock_redis_client):
        """Test error handling for cache operations."""
        mock_redis_client.get.side_effect = Exception("Redis error")

        with pytest.raises(CoreServiceError, match="Cache operation failed"):
            await cache_service.get("test:key")
