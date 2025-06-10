"""
Clean, focused test suite for CacheService.

Tests core functionality with proper mocking and realistic scenarios.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tripsage_core.exceptions.exceptions import CoreServiceError
from tripsage_core.services.infrastructure.cache_service import CacheService


@pytest.fixture
def mock_settings():
    """Create mock settings for testing."""
    settings = MagicMock()
    settings.dragonfly.url = "redis://localhost:6379/0"
    settings.dragonfly.password = "test_password"
    settings.dragonfly.max_connections = 10
    settings.dragonfly.ttl_short = 300
    settings.dragonfly.ttl_medium = 3600
    settings.dragonfly.ttl_long = 86400
    return settings


@pytest.fixture
def cache_service(mock_settings):
    """Create a CacheService instance with mocked settings."""
    return CacheService(mock_settings)


@pytest.fixture
def mock_redis_client():
    """Create a mock Redis client."""
    client = AsyncMock()
    client.ping.return_value = True
    client.set.return_value = True
    client.setex.return_value = True  # For string operations
    client.get.return_value = None
    client.delete.return_value = 1
    client.exists.return_value = 1
    client.expire.return_value = True
    client.ttl.return_value = 3600
    client.incr.return_value = 1
    client.decr.return_value = 0
    client.mget.return_value = [None]
    client.mset.return_value = True
    client.keys.return_value = []
    client.flushdb.return_value = True
    client.info.return_value = {"redis_version": "7.0.0"}
    client.close.return_value = None
    return client


class TestCacheServiceBasics:
    """Test basic CacheService functionality."""

    def test_initialization(self, mock_settings):
        """Test that CacheService initializes correctly."""
        service = CacheService(mock_settings)
        assert service.settings == mock_settings
        assert not service.is_connected
        assert service._client is None

    def test_initialization_without_settings(self):
        """Test CacheService with default settings."""
        with patch(
            "tripsage_core.services.infrastructure.cache_service.get_settings"
        ) as mock_get_settings:
            mock_get_settings.return_value = MagicMock()
            service = CacheService()
            assert service.settings is not None


class TestConnectionManagement:
    """Test connection management functionality."""

    @pytest.mark.asyncio
    async def test_connect_success(self, cache_service, mock_redis_client):
        """Test successful connection to DragonflyDB."""
        with (
            patch("redis.asyncio.ConnectionPool.from_url") as mock_pool,
            patch("redis.asyncio.Redis") as mock_redis,
        ):
            mock_pool.return_value = MagicMock()
            mock_redis.return_value = mock_redis_client

            await cache_service.connect()

            assert cache_service.is_connected
            mock_redis_client.ping.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_failure(self, cache_service):
        """Test connection failure handling."""
        with (
            patch("redis.asyncio.ConnectionPool.from_url"),
            patch("redis.asyncio.Redis") as mock_redis,
        ):
            mock_client = AsyncMock()
            mock_client.ping.side_effect = Exception("Connection failed")
            mock_redis.return_value = mock_client

            with pytest.raises(CoreServiceError) as exc_info:
                await cache_service.connect()

            assert exc_info.value.code == "CACHE_CONNECTION_FAILED"
            assert not cache_service.is_connected

    @pytest.mark.asyncio
    async def test_disconnect(self, cache_service, mock_redis_client):
        """Test disconnection from DragonflyDB."""
        # Set up connected state
        cache_service._client = mock_redis_client
        cache_service._connection_pool = AsyncMock()
        cache_service._is_connected = True

        await cache_service.disconnect()

        assert not cache_service.is_connected
        assert cache_service._client is None
        mock_redis_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_ensure_connected_when_disconnected(
        self, cache_service, mock_redis_client
    ):
        """Test ensure_connected when not connected."""
        with patch.object(cache_service, "connect") as mock_connect:
            await cache_service.ensure_connected()
            mock_connect.assert_called_once()


class TestJSONOperations:
    """Test JSON-based cache operations."""

    @pytest.mark.asyncio
    async def test_set_json_success(self, cache_service, mock_redis_client):
        """Test setting JSON values."""
        cache_service._client = mock_redis_client
        cache_service._is_connected = True

        test_data = {"key": "value", "number": 42}
        result = await cache_service.set_json("test_key", test_data, ttl=3600)

        assert result is True
        mock_redis_client.set.assert_called_once_with(
            "test_key", json.dumps(test_data, default=str), ex=3600
        )

    @pytest.mark.asyncio
    async def test_set_json_with_default_ttl(self, cache_service, mock_redis_client):
        """Test setting JSON values with default TTL."""
        cache_service._client = mock_redis_client
        cache_service._is_connected = True

        test_data = {"key": "value"}
        await cache_service.set_json("test_key", test_data)

        mock_redis_client.set.assert_called_once_with(
            "test_key",
            json.dumps(test_data, default=str),
            ex=3600,  # default medium TTL
        )

    @pytest.mark.asyncio
    async def test_get_json_success(self, cache_service, mock_redis_client):
        """Test getting JSON values."""
        cache_service._client = mock_redis_client
        cache_service._is_connected = True

        test_data = {"key": "value", "number": 42}
        mock_redis_client.get.return_value = json.dumps(test_data)

        result = await cache_service.get_json("test_key")

        assert result == test_data
        mock_redis_client.get.assert_called_once_with("test_key")

    @pytest.mark.asyncio
    async def test_get_json_not_found(self, cache_service, mock_redis_client):
        """Test getting non-existent JSON values."""
        cache_service._client = mock_redis_client
        cache_service._is_connected = True

        mock_redis_client.get.return_value = None

        result = await cache_service.get_json(
            "nonexistent_key", default={"default": "value"}
        )

        assert result == {"default": "value"}

    @pytest.mark.asyncio
    async def test_get_json_invalid_json(self, cache_service, mock_redis_client):
        """Test handling invalid JSON data."""
        cache_service._client = mock_redis_client
        cache_service._is_connected = True

        mock_redis_client.get.return_value = "invalid json data"

        result = await cache_service.get_json("test_key", default="default_value")

        assert result == "default_value"


class TestStringOperations:
    """Test string-based cache operations."""

    @pytest.mark.asyncio
    async def test_set_string(self, cache_service, mock_redis_client):
        """Test setting string values."""
        cache_service._client = mock_redis_client
        cache_service._is_connected = True

        result = await cache_service.set("test_key", "test_value", ttl=1800)

        assert result is True
        mock_redis_client.setex.assert_called_once_with("test_key", 1800, "test_value")

    @pytest.mark.asyncio
    async def test_get_string(self, cache_service, mock_redis_client):
        """Test getting string values."""
        cache_service._client = mock_redis_client
        cache_service._is_connected = True

        mock_redis_client.get.return_value = b"test_value"

        result = await cache_service.get("test_key")

        assert result == "test_value"
        mock_redis_client.get.assert_called_once_with("test_key")


class TestKeyOperations:
    """Test key management operations."""

    @pytest.mark.asyncio
    async def test_delete_keys(self, cache_service, mock_redis_client):
        """Test deleting keys."""
        cache_service._client = mock_redis_client
        cache_service._is_connected = True

        mock_redis_client.delete.return_value = 2

        result = await cache_service.delete("key1", "key2")

        assert result == 2
        mock_redis_client.delete.assert_called_once_with("key1", "key2")

    @pytest.mark.asyncio
    async def test_exists_keys(self, cache_service, mock_redis_client):
        """Test checking key existence."""
        cache_service._client = mock_redis_client
        cache_service._is_connected = True

        mock_redis_client.exists.return_value = 1

        result = await cache_service.exists("test_key")

        assert result == 1
        mock_redis_client.exists.assert_called_once_with("test_key")

    @pytest.mark.asyncio
    async def test_expire_key(self, cache_service, mock_redis_client):
        """Test setting key expiration."""
        cache_service._client = mock_redis_client
        cache_service._is_connected = True

        result = await cache_service.expire("test_key", 3600)

        assert result is True
        mock_redis_client.expire.assert_called_once_with("test_key", 3600)

    @pytest.mark.asyncio
    async def test_ttl_key(self, cache_service, mock_redis_client):
        """Test getting key TTL."""
        cache_service._client = mock_redis_client
        cache_service._is_connected = True

        mock_redis_client.ttl.return_value = 1800

        result = await cache_service.ttl("test_key")

        assert result == 1800
        mock_redis_client.ttl.assert_called_once_with("test_key")


class TestBatchOperations:
    """Test batch operations."""

    @pytest.mark.asyncio
    async def test_mget_multiple_keys(self, cache_service, mock_redis_client):
        """Test getting multiple keys."""
        cache_service._client = mock_redis_client
        cache_service._is_connected = True

        mock_redis_client.mget.return_value = [b"value1", None, b"value3"]

        result = await cache_service.mget(["key1", "key2", "key3"])

        assert result == ["value1", None, "value3"]
        mock_redis_client.mget.assert_called_once_with(["key1", "key2", "key3"])

    @pytest.mark.asyncio
    async def test_mset_multiple_keys(self, cache_service, mock_redis_client):
        """Test setting multiple keys."""
        cache_service._client = mock_redis_client
        cache_service._is_connected = True

        mapping = {"key1": "value1", "key2": "value2"}
        result = await cache_service.mset(mapping)

        assert result is True
        mock_redis_client.mset.assert_called_once_with(mapping)


class TestHealthAndMaintenance:
    """Test health check and maintenance operations."""

    @pytest.mark.asyncio
    async def test_health_check_connected(self, cache_service, mock_redis_client):
        """Test health check when connected."""
        cache_service._client = mock_redis_client
        cache_service._is_connected = True

        result = await cache_service.health_check()

        assert result is True
        mock_redis_client.ping.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_check_disconnected(self, cache_service):
        """Test health check when disconnected."""
        result = await cache_service.health_check()

        assert result is False

    @pytest.mark.asyncio
    async def test_flushdb(self, cache_service, mock_redis_client):
        """Test flushing database."""
        cache_service._client = mock_redis_client
        cache_service._is_connected = True

        result = await cache_service.flushdb()

        assert result is True
        mock_redis_client.flushdb.assert_called_once()


class TestConvenienceMethods:
    """Test convenience methods for different TTL durations."""

    @pytest.mark.asyncio
    async def test_set_short_ttl(self, cache_service, mock_redis_client):
        """Test setting value with short TTL."""
        cache_service._client = mock_redis_client
        cache_service._is_connected = True

        test_data = {"key": "value"}
        result = await cache_service.set_short("test_key", test_data)

        assert result is True
        mock_redis_client.set.assert_called_once_with(
            "test_key",
            json.dumps(test_data, default=str),
            ex=300,  # short TTL
        )

    @pytest.mark.asyncio
    async def test_set_medium_ttl(self, cache_service, mock_redis_client):
        """Test setting value with medium TTL."""
        cache_service._client = mock_redis_client
        cache_service._is_connected = True

        test_data = {"key": "value"}
        result = await cache_service.set_medium("test_key", test_data)

        assert result is True
        mock_redis_client.set.assert_called_once_with(
            "test_key",
            json.dumps(test_data, default=str),
            ex=3600,  # medium TTL
        )

    @pytest.mark.asyncio
    async def test_set_long_ttl(self, cache_service, mock_redis_client):
        """Test setting value with long TTL."""
        cache_service._client = mock_redis_client
        cache_service._is_connected = True

        test_data = {"key": "value"}
        result = await cache_service.set_long("test_key", test_data)

        assert result is True
        mock_redis_client.set.assert_called_once_with(
            "test_key",
            json.dumps(test_data, default=str),
            ex=86400,  # long TTL
        )


class TestErrorHandling:
    """Test error handling scenarios."""

    @pytest.mark.asyncio
    async def test_set_json_error(self, cache_service, mock_redis_client):
        """Test error handling in set_json."""
        cache_service._client = mock_redis_client
        cache_service._is_connected = True

        mock_redis_client.set.side_effect = Exception("Redis error")

        with pytest.raises(CoreServiceError) as exc_info:
            await cache_service.set_json("test_key", {"data": "value"})

        assert exc_info.value.code == "CACHE_SET_FAILED"

    @pytest.mark.asyncio
    async def test_get_json_error(self, cache_service, mock_redis_client):
        """Test error handling in get_json."""
        cache_service._client = mock_redis_client
        cache_service._is_connected = True

        mock_redis_client.get.side_effect = Exception("Redis error")

        with pytest.raises(CoreServiceError) as exc_info:
            await cache_service.get_json("test_key")

        assert exc_info.value.code == "CACHE_GET_FAILED"
