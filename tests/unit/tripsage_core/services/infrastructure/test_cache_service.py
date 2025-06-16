"""
Comprehensive tests for TripSage Core Cache Service.

This module provides comprehensive test coverage for cache service functionality
including connection management, JSON/string operations, batch operations,
pattern-based operations, TTL management, atomic operations, and error handling.
"""

import asyncio
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch

import pytest

from tripsage_core.config import Settings
from tripsage_core.exceptions.exceptions import CoreServiceError
from tripsage_core.services.infrastructure.cache_service import (
    CacheService,
    get_cache_service,
)


class TestCacheService:
    """Comprehensive test suite for CacheService."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = Mock(spec=Settings)
        settings.redis_url = "redis://localhost:6379/0"
        settings.cache_ttl_short = 300
        settings.cache_ttl_medium = 3600
        settings.cache_ttl_long = 86400
        settings.redis_max_connections = 10000
        return settings

    @pytest.fixture
    def mock_redis_client(self):
        """Create a comprehensive mock Redis/DragonflyDB client."""
        client = AsyncMock()

        # Basic operations
        client.ping = AsyncMock(return_value=True)
        client.get = AsyncMock(return_value=None)
        client.set = AsyncMock(return_value=True)
        client.setex = AsyncMock(return_value=True)
        client.delete = AsyncMock(return_value=1)
        client.exists = AsyncMock(return_value=1)
        client.expire = AsyncMock(return_value=True)
        client.ttl = AsyncMock(return_value=300)

        # Batch operations
        client.mget = AsyncMock(return_value=[None, None])
        client.mset = AsyncMock(return_value=True)

        # Pattern operations
        client.keys = AsyncMock(return_value=[])

        # Atomic operations
        client.incr = AsyncMock(return_value=1)
        client.decr = AsyncMock(return_value=1)

        # Info and management
        client.info = AsyncMock(return_value="redis_version:6.2.0\nused_memory:1024000")
        client.flushdb = AsyncMock(return_value=True)

        # Connection management
        client.close = AsyncMock()

        # Pipeline support
        client.pipeline = Mock(return_value=AsyncMock())

        return client

    @pytest.fixture
    def mock_connection_pool(self):
        """Create a mock connection pool."""
        pool = Mock()
        pool.disconnect = AsyncMock()
        return pool

    @pytest.fixture
    def cache_service(self, mock_settings, mock_redis_client, mock_connection_pool):
        """Create a CacheService instance with mocked dependencies."""
        with (
            patch(
                "redis.asyncio.ConnectionPool.from_url",
                return_value=mock_connection_pool,
            ),
            patch("redis.asyncio.Redis", return_value=mock_redis_client),
        ):
            service = CacheService(settings=mock_settings)
            service._client = mock_redis_client
            service._connection_pool = mock_connection_pool
            service._is_connected = True
            return service

    # Connection Management Tests

    @pytest.mark.asyncio
    async def test_connect_success(
        self, mock_settings, mock_redis_client, mock_connection_pool
    ):
        """Test successful cache connection."""
        with (
            patch(
                "redis.asyncio.ConnectionPool.from_url",
                return_value=mock_connection_pool,
            ),
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

        with (
            patch("redis.asyncio.ConnectionPool.from_url"),
            patch("redis.asyncio.Redis", return_value=mock_redis_client),
        ):
            service = CacheService(settings=mock_settings)

            with pytest.raises(
                CoreServiceError, match="Failed to connect to cache service"
            ):
                await service.connect()

    @pytest.mark.asyncio
    async def test_connect_already_connected(self, cache_service):
        """Test connecting when already connected."""
        initial_client = cache_service._client

        await cache_service.connect()

        # Should not change the client
        assert cache_service._client is initial_client

    @pytest.mark.asyncio
    async def test_disconnect_success(
        self, cache_service, mock_redis_client, mock_connection_pool
    ):
        """Test successful disconnection."""
        await cache_service.disconnect()

        assert not cache_service.is_connected
        assert cache_service._client is None
        assert cache_service._connection_pool is None
        mock_redis_client.close.assert_called_once()
        mock_connection_pool.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_disconnect_with_errors(
        self, cache_service, mock_redis_client, mock_connection_pool
    ):
        """Test disconnection with errors."""
        mock_redis_client.close.side_effect = Exception("Close error")
        mock_connection_pool.disconnect.side_effect = Exception("Pool disconnect error")

        # Should not raise exception
        await cache_service.disconnect()

        assert not cache_service.is_connected

    @pytest.mark.asyncio
    async def test_ensure_connected_when_not_connected(self, cache_service):
        """Test ensure_connected when not connected."""
        cache_service._is_connected = False

        with patch.object(
            cache_service, "connect", new_callable=AsyncMock
        ) as mock_connect:
            await cache_service.ensure_connected()
            mock_connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_ensure_connected_when_connected(self, cache_service):
        """Test ensure_connected when already connected."""
        with patch.object(
            cache_service, "connect", new_callable=AsyncMock
        ) as mock_connect:
            await cache_service.ensure_connected()
            mock_connect.assert_not_called()

    # JSON Operations Tests

    @pytest.mark.asyncio
    async def test_set_json_success(self, cache_service, mock_redis_client):
        """Test successful JSON value setting."""
        test_data = {
            "name": "Test",
            "value": 123,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "nested": {"key": "value"},
            "list": [1, 2, 3],
        }

        result = await cache_service.set_json("test:key", test_data, ttl=600)

        assert result is True
        mock_redis_client.set.assert_called_once()

        # Verify JSON serialization
        call_args = mock_redis_client.set.call_args
        assert call_args[0][0] == "test:key"
        assert json.loads(call_args[0][1]) == test_data
        assert call_args[1]["ex"] == 600

    @pytest.mark.asyncio
    async def test_set_json_with_default_ttl(
        self, cache_service, mock_redis_client, mock_settings
    ):
        """Test JSON setting with default TTL."""
        test_data = {"key": "value"}

        result = await cache_service.set_json("test:key", test_data)

        assert result is True
        call_args = mock_redis_client.set.call_args
        assert call_args[1]["ex"] == mock_settings.dragonfly.ttl_medium

    @pytest.mark.asyncio
    async def test_set_json_with_complex_data(self, cache_service, mock_redis_client):
        """Test JSON setting with complex data types."""
        test_data = {
            "datetime": datetime.now(timezone.utc),
            "none_value": None,
            "boolean": True,
            "float": 3.14159,
        }

        result = await cache_service.set_json("test:key", test_data)

        assert result is True
        # Verify it uses default str serialization for datetime
        call_args = mock_redis_client.set.call_args
        serialized_data = json.loads(call_args[0][1])
        assert isinstance(serialized_data["datetime"], str)

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
    async def test_get_json_invalid_json(self, cache_service, mock_redis_client):
        """Test JSON retrieval with invalid JSON data."""
        mock_redis_client.get.return_value = "invalid json data"
        default_value = {"default": True}

        result = await cache_service.get_json("test:key", default=default_value)

        assert result == default_value

    @pytest.mark.asyncio
    async def test_get_json_no_default(self, cache_service, mock_redis_client):
        """Test JSON retrieval with no default value."""
        mock_redis_client.get.return_value = None

        result = await cache_service.get_json("missing:key")

        assert result is None

    # String Operations Tests

    @pytest.mark.asyncio
    async def test_set_string_success(self, cache_service, mock_redis_client):
        """Test successful string value setting."""
        result = await cache_service.set("test:string", "Hello World", ttl=300)

        assert result is True
        mock_redis_client.setex.assert_called_with("test:string", 300, "Hello World")

    @pytest.mark.asyncio
    async def test_set_string_with_default_ttl(
        self, cache_service, mock_redis_client, mock_settings
    ):
        """Test string setting with default TTL."""
        result = await cache_service.set("test:string", "Hello World")

        assert result is True
        mock_redis_client.setex.assert_called_with(
            "test:string", mock_settings.dragonfly.ttl_medium, "Hello World"
        )

    @pytest.mark.asyncio
    async def test_get_string_success(self, cache_service, mock_redis_client):
        """Test successful string value retrieval."""
        mock_redis_client.get.return_value = b"Hello World"

        result = await cache_service.get("test:string")

        assert result == "Hello World"

    @pytest.mark.asyncio
    async def test_get_string_miss(self, cache_service, mock_redis_client):
        """Test string retrieval when key doesn't exist."""
        mock_redis_client.get.return_value = None

        result = await cache_service.get("missing:string")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_string_empty(self, cache_service, mock_redis_client):
        """Test string retrieval with empty value."""
        mock_redis_client.get.return_value = b""

        result = await cache_service.get("empty:string")

        assert result == ""

    # Key Operations Tests

    @pytest.mark.asyncio
    async def test_delete_single_key(self, cache_service, mock_redis_client):
        """Test deleting a single key."""
        mock_redis_client.delete.return_value = 1

        result = await cache_service.delete("test:key")

        assert result == 1
        mock_redis_client.delete.assert_called_with("test:key")

    @pytest.mark.asyncio
    async def test_delete_multiple_keys(self, cache_service, mock_redis_client):
        """Test deleting multiple keys."""
        mock_redis_client.delete.return_value = 2

        result = await cache_service.delete("key1", "key2", "key3")

        assert result == 2
        mock_redis_client.delete.assert_called_with("key1", "key2", "key3")

    @pytest.mark.asyncio
    async def test_exists_single_key(self, cache_service, mock_redis_client):
        """Test checking single key existence."""
        mock_redis_client.exists.return_value = 1

        result = await cache_service.exists("test:key")

        assert result == 1
        mock_redis_client.exists.assert_called_with("test:key")

    @pytest.mark.asyncio
    async def test_exists_multiple_keys(self, cache_service, mock_redis_client):
        """Test checking multiple key existence."""
        mock_redis_client.exists.return_value = 2

        result = await cache_service.exists("key1", "key2", "key3")

        assert result == 2
        mock_redis_client.exists.assert_called_with("key1", "key2", "key3")

    @pytest.mark.asyncio
    async def test_expire_key_success(self, cache_service, mock_redis_client):
        """Test setting key expiration."""
        mock_redis_client.expire.return_value = True

        result = await cache_service.expire("test:key", 600)

        assert result is True
        mock_redis_client.expire.assert_called_with("test:key", 600)

    @pytest.mark.asyncio
    async def test_expire_key_not_found(self, cache_service, mock_redis_client):
        """Test setting expiration on non-existent key."""
        mock_redis_client.expire.return_value = False

        result = await cache_service.expire("missing:key", 600)

        assert result is False

    @pytest.mark.asyncio
    async def test_ttl_key_with_expiration(self, cache_service, mock_redis_client):
        """Test getting TTL for key with expiration."""
        mock_redis_client.ttl.return_value = 300

        result = await cache_service.ttl("test:key")

        assert result == 300

    @pytest.mark.asyncio
    async def test_ttl_key_no_expiration(self, cache_service, mock_redis_client):
        """Test getting TTL for key without expiration."""
        mock_redis_client.ttl.return_value = -1

        result = await cache_service.ttl("test:key")

        assert result == -1

    @pytest.mark.asyncio
    async def test_ttl_key_not_found(self, cache_service, mock_redis_client):
        """Test getting TTL for non-existent key."""
        mock_redis_client.ttl.return_value = -2

        result = await cache_service.ttl("missing:key")

        assert result == -2

    @pytest.mark.asyncio
    async def test_ttl_error_handling(self, cache_service, mock_redis_client):
        """Test TTL error handling."""
        mock_redis_client.ttl.side_effect = Exception("TTL error")

        result = await cache_service.ttl("test:key")

        assert result == -2

    # Atomic Operations Tests

    @pytest.mark.asyncio
    async def test_incr_success(self, cache_service, mock_redis_client):
        """Test incrementing a counter."""
        mock_redis_client.incr.return_value = 5

        result = await cache_service.incr("counter:test")

        assert result == 5
        mock_redis_client.incr.assert_called_with("counter:test")

    @pytest.mark.asyncio
    async def test_incr_error_handling(self, cache_service, mock_redis_client):
        """Test increment error handling."""
        mock_redis_client.incr.side_effect = Exception("Increment error")

        result = await cache_service.incr("counter:test")

        assert result is None

    @pytest.mark.asyncio
    async def test_decr_success(self, cache_service, mock_redis_client):
        """Test decrementing a counter."""
        mock_redis_client.decr.return_value = 3

        result = await cache_service.decr("counter:test")

        assert result == 3
        mock_redis_client.decr.assert_called_with("counter:test")

    @pytest.mark.asyncio
    async def test_decr_error_handling(self, cache_service, mock_redis_client):
        """Test decrement error handling."""
        mock_redis_client.decr.side_effect = Exception("Decrement error")

        result = await cache_service.decr("counter:test")

        assert result is None

    # Batch Operations Tests

    @pytest.mark.asyncio
    async def test_pipeline_creation(self, cache_service, mock_redis_client):
        """Test creating a pipeline."""
        mock_pipeline = AsyncMock()
        mock_redis_client.pipeline.return_value = mock_pipeline

        pipeline = cache_service.pipeline()

        assert pipeline is mock_pipeline
        mock_redis_client.pipeline.assert_called_once()

    @pytest.mark.asyncio
    async def test_pipeline_not_connected(self, mock_settings):
        """Test pipeline creation when not connected."""
        service = CacheService(settings=mock_settings)

        with pytest.raises(CoreServiceError, match="Cache service not connected"):
            service.pipeline()

    @pytest.mark.asyncio
    async def test_mget_success(self, cache_service, mock_redis_client):
        """Test multiple key retrieval."""
        mock_redis_client.mget.return_value = [b"value1", b"value2", None]

        result = await cache_service.mget(["key1", "key2", "key3"])

        assert result == ["value1", "value2", None]
        mock_redis_client.mget.assert_called_with(["key1", "key2", "key3"])

    @pytest.mark.asyncio
    async def test_mget_all_missing(self, cache_service, mock_redis_client):
        """Test mget with all missing keys."""
        mock_redis_client.mget.return_value = [None, None, None]

        result = await cache_service.mget(["missing1", "missing2", "missing3"])

        assert result == [None, None, None]

    @pytest.mark.asyncio
    async def test_mset_success(self, cache_service, mock_redis_client):
        """Test multiple key setting."""
        mapping = {"key1": "value1", "key2": "value2"}
        mock_redis_client.mset.return_value = True

        result = await cache_service.mset(mapping)

        assert result is True
        mock_redis_client.mset.assert_called_with(mapping)

    @pytest.mark.asyncio
    async def test_mset_empty_mapping(self, cache_service, mock_redis_client):
        """Test mset with empty mapping."""
        result = await cache_service.mset({})

        assert result is True
        mock_redis_client.mset.assert_called_with({})

    # Pattern-based Operations Tests

    @pytest.mark.asyncio
    async def test_keys_pattern_success(self, cache_service, mock_redis_client):
        """Test retrieving keys by pattern."""
        mock_redis_client.keys.return_value = [b"user:1", b"user:2", b"user:3"]

        result = await cache_service.keys("user:*")

        assert result == ["user:1", "user:2", "user:3"]
        mock_redis_client.keys.assert_called_with("user:*")

    @pytest.mark.asyncio
    async def test_keys_pattern_no_matches(self, cache_service, mock_redis_client):
        """Test retrieving keys with no matches."""
        mock_redis_client.keys.return_value = []

        result = await cache_service.keys("nonexistent:*")

        assert result == []

    @pytest.mark.asyncio
    async def test_keys_default_pattern(self, cache_service, mock_redis_client):
        """Test retrieving keys with default pattern."""
        mock_redis_client.keys.return_value = [b"key1", b"key2"]

        result = await cache_service.keys()

        assert result == ["key1", "key2"]
        mock_redis_client.keys.assert_called_with("*")

    @pytest.mark.asyncio
    async def test_keys_error_handling(self, cache_service, mock_redis_client):
        """Test keys pattern error handling."""
        mock_redis_client.keys.side_effect = Exception("Keys error")

        result = await cache_service.keys("test:*")

        assert result == []

    @pytest.mark.asyncio
    async def test_delete_pattern_success(self, cache_service, mock_redis_client):
        """Test deleting keys by pattern."""
        mock_redis_client.keys.return_value = [b"temp:1", b"temp:2", b"temp:3"]
        mock_redis_client.delete.return_value = 3

        result = await cache_service.delete_pattern("temp:*")

        assert result == 3
        mock_redis_client.keys.assert_called_with("temp:*")
        mock_redis_client.delete.assert_called_with("temp:1", "temp:2", "temp:3")

    @pytest.mark.asyncio
    async def test_delete_pattern_no_matches(self, cache_service, mock_redis_client):
        """Test deleting pattern with no matches."""
        mock_redis_client.keys.return_value = []

        result = await cache_service.delete_pattern("nonexistent:*")

        assert result == 0
        mock_redis_client.delete.assert_not_called()

    # Cache Management Tests

    @pytest.mark.asyncio
    async def test_flushdb_success(self, cache_service, mock_redis_client):
        """Test flushing the database."""
        mock_redis_client.flushdb.return_value = True

        result = await cache_service.flushdb()

        assert result is True
        mock_redis_client.flushdb.assert_called_once()

    @pytest.mark.asyncio
    async def test_flushdb_failure(self, cache_service, mock_redis_client):
        """Test flushdb failure."""
        mock_redis_client.flushdb.side_effect = Exception("Flush error")

        result = await cache_service.flushdb()

        assert result is False

    @pytest.mark.asyncio
    async def test_info_success(self, cache_service, mock_redis_client):
        """Test getting cache info."""
        info_string = "redis_version:6.2.0\nused_memory:1024000\nconnected_clients:5"
        mock_redis_client.info.return_value = info_string

        result = await cache_service.info()

        expected_result = {
            "redis_version": "6.2.0",
            "used_memory": "1024000",
            "connected_clients": "5",
        }
        assert result == expected_result

    @pytest.mark.asyncio
    async def test_info_with_section(self, cache_service, mock_redis_client):
        """Test getting cache info for specific section."""
        info_string = "used_memory:1024000\nused_memory_peak:2048000"
        mock_redis_client.info.return_value = info_string

        result = await cache_service.info("memory")

        mock_redis_client.info.assert_called_with("memory")
        assert "used_memory" in result

    @pytest.mark.asyncio
    async def test_info_error_handling(self, cache_service, mock_redis_client):
        """Test info error handling."""
        mock_redis_client.info.side_effect = Exception("Info error")

        result = await cache_service.info()

        assert result == {}

    @pytest.mark.asyncio
    async def test_info_malformed_response(self, cache_service, mock_redis_client):
        """Test info with malformed response."""
        info_string = "# Comments\ninvalid_line_without_colon\nvalid:line"
        mock_redis_client.info.return_value = info_string

        result = await cache_service.info()

        assert result == {"valid": "line"}

    # Health Check Tests

    @pytest.mark.asyncio
    async def test_health_check_success(self, cache_service, mock_redis_client):
        """Test successful health check."""
        mock_redis_client.ping.return_value = True

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
    async def test_health_check_not_connected(self, mock_settings):
        """Test health check when not connected."""
        service = CacheService(settings=mock_settings)

        result = await service.health_check()

        assert result is False

    # Convenience Methods Tests

    @pytest.mark.asyncio
    async def test_set_short_ttl(self, cache_service, mock_redis_client, mock_settings):
        """Test setting value with short TTL."""
        test_data = {"key": "value"}

        result = await cache_service.set_short("test:key", test_data)

        assert result is True
        call_args = mock_redis_client.set.call_args
        assert call_args[1]["ex"] == mock_settings.dragonfly.ttl_short

    @pytest.mark.asyncio
    async def test_set_medium_ttl(
        self, cache_service, mock_redis_client, mock_settings
    ):
        """Test setting value with medium TTL."""
        test_data = {"key": "value"}

        result = await cache_service.set_medium("test:key", test_data)

        assert result is True
        call_args = mock_redis_client.set.call_args
        assert call_args[1]["ex"] == mock_settings.dragonfly.ttl_medium

    @pytest.mark.asyncio
    async def test_set_long_ttl(self, cache_service, mock_redis_client, mock_settings):
        """Test setting value with long TTL."""
        test_data = {"key": "value"}

        result = await cache_service.set_long("test:key", test_data)

        assert result is True
        call_args = mock_redis_client.set.call_args
        assert call_args[1]["ex"] == mock_settings.dragonfly.ttl_long

    # Error Handling Tests

    @pytest.mark.asyncio
    async def test_set_json_error_handling(self, cache_service, mock_redis_client):
        """Test set_json error handling."""
        mock_redis_client.set.side_effect = Exception("Set error")

        with pytest.raises(CoreServiceError, match="Failed to set cache value"):
            await cache_service.set_json("test:key", {"data": "value"})

    @pytest.mark.asyncio
    async def test_get_json_error_handling(self, cache_service, mock_redis_client):
        """Test get_json error handling."""
        mock_redis_client.get.side_effect = Exception("Get error")

        with pytest.raises(CoreServiceError, match="Failed to get cache value"):
            await cache_service.get_json("test:key")

    @pytest.mark.asyncio
    async def test_set_string_error_handling(self, cache_service, mock_redis_client):
        """Test set string error handling."""
        mock_redis_client.setex.side_effect = Exception("Set error")

        with pytest.raises(CoreServiceError, match="Failed to set cache key"):
            await cache_service.set("test:key", "value")

    @pytest.mark.asyncio
    async def test_get_string_error_handling(self, cache_service, mock_redis_client):
        """Test get string error handling."""
        mock_redis_client.get.side_effect = Exception("Get error")

        with pytest.raises(CoreServiceError, match="Failed to get cache key"):
            await cache_service.get("test:key")

    @pytest.mark.asyncio
    async def test_delete_error_handling(self, cache_service, mock_redis_client):
        """Test delete error handling."""
        mock_redis_client.delete.side_effect = Exception("Delete error")

        with pytest.raises(CoreServiceError, match="Failed to delete cache keys"):
            await cache_service.delete("test:key")

    @pytest.mark.asyncio
    async def test_exists_error_handling(self, cache_service, mock_redis_client):
        """Test exists error handling."""
        mock_redis_client.exists.side_effect = Exception("Exists error")

        with pytest.raises(
            CoreServiceError, match="Failed to check cache key existence"
        ):
            await cache_service.exists("test:key")

    @pytest.mark.asyncio
    async def test_expire_error_handling(self, cache_service, mock_redis_client):
        """Test expire error handling."""
        mock_redis_client.expire.side_effect = Exception("Expire error")

        with pytest.raises(CoreServiceError, match="Failed to set expiration"):
            await cache_service.expire("test:key", 600)

    @pytest.mark.asyncio
    async def test_mget_error_handling(self, cache_service, mock_redis_client):
        """Test mget error handling."""
        mock_redis_client.mget.side_effect = Exception("Mget error")

        with pytest.raises(CoreServiceError, match="Failed to get multiple cache keys"):
            await cache_service.mget(["key1", "key2"])

    @pytest.mark.asyncio
    async def test_mset_error_handling(self, cache_service, mock_redis_client):
        """Test mset error handling."""
        mock_redis_client.mset.side_effect = Exception("Mset error")

        with pytest.raises(CoreServiceError, match="Failed to set multiple cache keys"):
            await cache_service.mset({"key1": "value1"})

    # Dependency Injection Tests

    @pytest.mark.asyncio
    async def test_get_cache_service_function(
        self, mock_settings, mock_redis_client, mock_connection_pool
    ):
        """Test the get_cache_service dependency function."""
        with (
            patch(
                "tripsage_core.services.infrastructure.cache_service.get_settings",
                return_value=mock_settings,
            ),
            patch(
                "redis.asyncio.ConnectionPool.from_url",
                return_value=mock_connection_pool,
            ),
            patch("redis.asyncio.Redis", return_value=mock_redis_client),
            patch(
                "tripsage_core.services.infrastructure.cache_service._cache_service",
                None,
            ),
        ):
            service = await get_cache_service()
            assert isinstance(service, CacheService)

    @pytest.mark.asyncio
    async def test_get_cache_service_singleton(
        self, mock_settings, mock_redis_client, mock_connection_pool
    ):
        """Test that get_cache_service returns singleton instance."""
        with (
            patch(
                "tripsage_core.services.infrastructure.cache_service.get_settings",
                return_value=mock_settings,
            ),
            patch(
                "redis.asyncio.ConnectionPool.from_url",
                return_value=mock_connection_pool,
            ),
            patch("redis.asyncio.Redis", return_value=mock_redis_client),
            patch(
                "tripsage_core.services.infrastructure.cache_service._cache_service",
                None,
            ),
        ):
            service1 = await get_cache_service()
            service2 = await get_cache_service()
            assert service1 is service2

    # Performance and Concurrency Tests

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, cache_service, mock_redis_client):
        """Test concurrent cache operations."""
        mock_redis_client.get.return_value = b"test_value"
        mock_redis_client.set.return_value = True
        mock_redis_client.delete.return_value = 1

        # Execute multiple operations concurrently
        tasks = [
            cache_service.get("key1"),
            cache_service.set("key2", "value2"),
            cache_service.delete("key3"),
            cache_service.exists("key4"),
        ]

        results = await asyncio.gather(*tasks)

        assert len(results) == 4
        assert results[0] == "test_value"  # get result
        assert results[1] is True  # set result
        assert results[2] == 1  # delete result
        assert results[3] == 1  # exists result

    @pytest.mark.asyncio
    async def test_large_data_handling(self, cache_service, mock_redis_client):
        """Test handling of large data."""
        large_data = {"data": "x" * 1000000}  # 1MB of data

        result = await cache_service.set_json("large:key", large_data)

        assert result is True
        # Verify the data was serialized correctly
        call_args = mock_redis_client.set.call_args
        assert len(call_args[0][1]) > 1000000

    @pytest.mark.asyncio
    async def test_many_keys_batch_operation(self, cache_service, mock_redis_client):
        """Test batch operations with many keys."""
        keys = [f"key:{i}" for i in range(1000)]
        mock_redis_client.mget.return_value = [b"value"] * 1000

        result = await cache_service.mget(keys)

        assert len(result) == 1000
        assert all(value == "value" for value in result)

    # Edge Cases Tests

    @pytest.mark.asyncio
    async def test_empty_key_handling(self, cache_service, mock_redis_client):
        """Test handling of empty keys."""
        result = await cache_service.set("", "value")

        assert result is True
        mock_redis_client.setex.assert_called_with(
            "", mock_redis_client.setex.call_args[0][1], "value"
        )

    @pytest.mark.asyncio
    async def test_none_value_json_handling(self, cache_service, mock_redis_client):
        """Test handling of None values in JSON."""
        result = await cache_service.set_json("test:key", None)

        assert result is True
        call_args = mock_redis_client.set.call_args
        assert call_args[0][1] == "null"

    @pytest.mark.asyncio
    async def test_special_characters_in_keys(self, cache_service, mock_redis_client):
        """Test handling of special characters in keys."""
        special_key = "test:key:with:colons:and-dashes_and_underscores"

        result = await cache_service.set(special_key, "value")

        assert result is True
        mock_redis_client.setex.assert_called_with(
            special_key, mock_redis_client.setex.call_args[0][1], "value"
        )

    @pytest.mark.asyncio
    async def test_unicode_data_handling(self, cache_service, mock_redis_client):
        """Test handling of unicode data."""
        unicode_data = {
            "message": "Hello 世界! 🌍",
            "emoji": "🎉🎊🎈",
            "accents": "café, naïve, résumé",
        }

        result = await cache_service.set_json("unicode:key", unicode_data)

        assert result is True
        call_args = mock_redis_client.set.call_args
        # Verify unicode is properly serialized
        serialized_data = json.loads(call_args[0][1])
        assert serialized_data["message"] == "Hello 世界! 🌍"

    @pytest.mark.asyncio
    async def test_zero_ttl_handling(self, cache_service, mock_redis_client):
        """Test handling of zero TTL."""
        result = await cache_service.set_json("test:key", {"data": "value"}, ttl=0)

        assert result is True
        call_args = mock_redis_client.set.call_args
        assert call_args[1]["ex"] == 0

    @pytest.mark.asyncio
    async def test_negative_ttl_handling(self, cache_service, mock_redis_client):
        """Test handling of negative TTL."""
        # Redis should handle negative TTL gracefully
        result = await cache_service.set_json("test:key", {"data": "value"}, ttl=-1)

        assert result is True
        call_args = mock_redis_client.set.call_args
        assert call_args[1]["ex"] == -1
