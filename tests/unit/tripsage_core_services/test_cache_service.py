"""
Comprehensive test suite for tripsage_core.services.infrastructure.cache_service module.

This module provides extensive tests for the cache service functionality,
including Redis/DragonflyDB operations, key management, TTL handling, and error scenarios.
"""

import asyncio
import json
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tripsage_core.services.infrastructure.cache_service import CacheService


class TestCacheServiceInitialization:
    """Test CacheService initialization and configuration."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings for testing."""
        settings = MagicMock()
        settings.dragonfly.url = "redis://localhost:6379/0"
        settings.dragonfly.ttl_short = 300
        settings.dragonfly.ttl_medium = 3600
        settings.dragonfly.ttl_long = 86400
        return settings

    def test_cache_service_initialization(self, mock_settings):
        """Test that CacheService initializes correctly."""
        cache_service = CacheService(mock_settings)
        assert cache_service.settings == mock_settings
        assert cache_service.redis is None  # Not connected yet

    def test_cache_service_initialization_with_custom_settings(self):
        """Test CacheService with custom settings."""
        custom_settings = MagicMock()
        custom_settings.dragonfly.url = "redis://custom:6380/1"
        custom_settings.dragonfly.ttl_short = 60
        custom_settings.dragonfly.ttl_medium = 600
        custom_settings.dragonfly.ttl_long = 3600

        cache_service = CacheService(custom_settings)
        assert cache_service.settings == custom_settings


class TestCacheConnectionManagement:
    """Test cache connection management."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings for testing."""
        settings = MagicMock()
        settings.dragonfly.url = "redis://localhost:6379/0"
        settings.dragonfly.ttl_short = 300
        settings.dragonfly.ttl_medium = 3600
        settings.dragonfly.ttl_long = 86400
        return settings

    @pytest.mark.asyncio
    async def test_connect_success(self, mock_settings):
        """Test successful connection to cache."""
        with patch(
            "tripsage_core.services.infrastructure.cache_service.aioredis"
        ) as mock_aioredis:
            mock_redis = AsyncMock()
            mock_aioredis.from_url.return_value = mock_redis

            cache_service = CacheService(mock_settings)
            await cache_service.connect()

            assert cache_service.redis == mock_redis
            mock_aioredis.from_url.assert_called_once_with(
                mock_settings.dragonfly.url, decode_responses=True
            )

    @pytest.mark.asyncio
    async def test_connect_failure(self, mock_settings):
        """Test connection failure handling."""
        with patch(
            "tripsage_core.services.infrastructure.cache_service.aioredis"
        ) as mock_aioredis:
            mock_aioredis.from_url.side_effect = Exception("Connection failed")

            cache_service = CacheService(mock_settings)

            with pytest.raises(Exception, match="Connection failed"):
                await cache_service.connect()

    @pytest.mark.asyncio
    async def test_disconnect_success(self, mock_settings):
        """Test successful disconnection from cache."""
        with patch(
            "tripsage_core.services.infrastructure.cache_service.aioredis"
        ) as mock_aioredis:
            mock_redis = AsyncMock()
            mock_aioredis.from_url.return_value = mock_redis

            cache_service = CacheService(mock_settings)
            await cache_service.connect()
            await cache_service.disconnect()

            mock_redis.close.assert_called_once()
            mock_redis.wait_closed.assert_called_once()
            assert cache_service.redis is None

    @pytest.mark.asyncio
    async def test_disconnect_without_connection(self, mock_settings):
        """Test disconnection when not connected."""
        cache_service = CacheService(mock_settings)

        # Should not raise an error
        await cache_service.disconnect()
        assert cache_service.redis is None

    @pytest.mark.asyncio
    async def test_health_check_connected(self, mock_settings):
        """Test health check when connected."""
        with patch(
            "tripsage_core.services.infrastructure.cache_service.aioredis"
        ) as mock_aioredis:
            mock_redis = AsyncMock()
            mock_redis.ping.return_value = True
            mock_aioredis.from_url.return_value = mock_redis

            cache_service = CacheService(mock_settings)
            await cache_service.connect()

            result = await cache_service.health_check()
            assert result["status"] == "healthy"
            assert result["connected"] is True
            mock_redis.ping.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_check_not_connected(self, mock_settings):
        """Test health check when not connected."""
        cache_service = CacheService(mock_settings)

        result = await cache_service.health_check()
        assert result["status"] == "unhealthy"
        assert result["connected"] is False


class TestBasicCacheOperations:
    """Test basic cache operations (get, set, delete)."""

    @pytest.fixture
    def cache_service(self):
        """Create a cache service with mocked Redis."""
        settings = MagicMock()
        settings.dragonfly.url = "redis://localhost:6379/0"
        settings.dragonfly.ttl_short = 300
        settings.dragonfly.ttl_medium = 3600
        settings.dragonfly.ttl_long = 86400

        cache_service = CacheService(settings)
        cache_service.redis = AsyncMock()
        return cache_service

    @pytest.mark.asyncio
    async def test_set_string_value(self, cache_service):
        """Test setting a string value in cache."""
        cache_service.redis.set.return_value = True

        result = await cache_service.set("test_key", "test_value", ttl=300)

        assert result is True
        cache_service.redis.set.assert_called_once_with(
            "test_key", "test_value", ex=300
        )

    @pytest.mark.asyncio
    async def test_set_json_value(self, cache_service):
        """Test setting a JSON-serializable value in cache."""
        cache_service.redis.set.return_value = True
        test_data = {"name": "test", "value": 123}

        result = await cache_service.set("test_key", test_data, ttl=300)

        assert result is True
        expected_json = json.dumps(test_data)
        cache_service.redis.set.assert_called_once_with(
            "test_key", expected_json, ex=300
        )

    @pytest.mark.asyncio
    async def test_get_string_value(self, cache_service):
        """Test getting a string value from cache."""
        cache_service.redis.get.return_value = "test_value"

        result = await cache_service.get("test_key")

        assert result == "test_value"
        cache_service.redis.get.assert_called_once_with("test_key")

    @pytest.mark.asyncio
    async def test_get_json_value(self, cache_service):
        """Test getting a JSON value from cache."""
        test_data = {"name": "test", "value": 123}
        cache_service.redis.get.return_value = json.dumps(test_data)

        result = await cache_service.get("test_key", parse_json=True)

        assert result == test_data
        cache_service.redis.get.assert_called_once_with("test_key")

    @pytest.mark.asyncio
    async def test_get_nonexistent_key(self, cache_service):
        """Test getting a nonexistent key returns None."""
        cache_service.redis.get.return_value = None

        result = await cache_service.get("nonexistent_key")

        assert result is None
        cache_service.redis.get.assert_called_once_with("nonexistent_key")

    @pytest.mark.asyncio
    async def test_delete_key(self, cache_service):
        """Test deleting a key from cache."""
        cache_service.redis.delete.return_value = 1

        result = await cache_service.delete("test_key")

        assert result is True
        cache_service.redis.delete.assert_called_once_with("test_key")

    @pytest.mark.asyncio
    async def test_delete_nonexistent_key(self, cache_service):
        """Test deleting a nonexistent key."""
        cache_service.redis.delete.return_value = 0

        result = await cache_service.delete("nonexistent_key")

        assert result is False
        cache_service.redis.delete.assert_called_once_with("nonexistent_key")

    @pytest.mark.asyncio
    async def test_exists_key(self, cache_service):
        """Test checking if a key exists."""
        cache_service.redis.exists.return_value = 1

        result = await cache_service.exists("test_key")

        assert result is True
        cache_service.redis.exists.assert_called_once_with("test_key")

    @pytest.mark.asyncio
    async def test_exists_nonexistent_key(self, cache_service):
        """Test checking if a nonexistent key exists."""
        cache_service.redis.exists.return_value = 0

        result = await cache_service.exists("nonexistent_key")

        assert result is False
        cache_service.redis.exists.assert_called_once_with("nonexistent_key")


class TestTTLManagement:
    """Test TTL (Time To Live) management."""

    @pytest.fixture
    def cache_service(self):
        """Create a cache service with mocked Redis."""
        settings = MagicMock()
        settings.dragonfly.url = "redis://localhost:6379/0"
        settings.dragonfly.ttl_short = 300
        settings.dragonfly.ttl_medium = 3600
        settings.dragonfly.ttl_long = 86400

        cache_service = CacheService(settings)
        cache_service.redis = AsyncMock()
        return cache_service

    @pytest.mark.asyncio
    async def test_set_with_short_ttl(self, cache_service):
        """Test setting value with short TTL."""
        cache_service.redis.set.return_value = True

        result = await cache_service.set("test_key", "value", ttl="short")

        assert result is True
        cache_service.redis.set.assert_called_once_with("test_key", "value", ex=300)

    @pytest.mark.asyncio
    async def test_set_with_medium_ttl(self, cache_service):
        """Test setting value with medium TTL."""
        cache_service.redis.set.return_value = True

        result = await cache_service.set("test_key", "value", ttl="medium")

        assert result is True
        cache_service.redis.set.assert_called_once_with("test_key", "value", ex=3600)

    @pytest.mark.asyncio
    async def test_set_with_long_ttl(self, cache_service):
        """Test setting value with long TTL."""
        cache_service.redis.set.return_value = True

        result = await cache_service.set("test_key", "value", ttl="long")

        assert result is True
        cache_service.redis.set.assert_called_once_with("test_key", "value", ex=86400)

    @pytest.mark.asyncio
    async def test_set_with_custom_ttl(self, cache_service):
        """Test setting value with custom TTL."""
        cache_service.redis.set.return_value = True

        result = await cache_service.set("test_key", "value", ttl=1800)

        assert result is True
        cache_service.redis.set.assert_called_once_with("test_key", "value", ex=1800)

    @pytest.mark.asyncio
    async def test_set_without_ttl(self, cache_service):
        """Test setting value without TTL (persistent)."""
        cache_service.redis.set.return_value = True

        result = await cache_service.set("test_key", "value")

        assert result is True
        cache_service.redis.set.assert_called_once_with("test_key", "value", ex=None)

    @pytest.mark.asyncio
    async def test_get_ttl(self, cache_service):
        """Test getting TTL of a key."""
        cache_service.redis.ttl.return_value = 300

        result = await cache_service.get_ttl("test_key")

        assert result == 300
        cache_service.redis.ttl.assert_called_once_with("test_key")

    @pytest.mark.asyncio
    async def test_expire_key(self, cache_service):
        """Test setting expiration on an existing key."""
        cache_service.redis.expire.return_value = True

        result = await cache_service.expire("test_key", 600)

        assert result is True
        cache_service.redis.expire.assert_called_once_with("test_key", 600)


class TestBulkOperations:
    """Test bulk cache operations."""

    @pytest.fixture
    def cache_service(self):
        """Create a cache service with mocked Redis."""
        settings = MagicMock()
        settings.dragonfly.url = "redis://localhost:6379/0"
        settings.dragonfly.ttl_short = 300
        settings.dragonfly.ttl_medium = 3600
        settings.dragonfly.ttl_long = 86400

        cache_service = CacheService(settings)
        cache_service.redis = AsyncMock()
        return cache_service

    @pytest.mark.asyncio
    async def test_mget_multiple_keys(self, cache_service):
        """Test getting multiple keys at once."""
        cache_service.redis.mget.return_value = ["value1", "value2", None]

        result = await cache_service.mget(["key1", "key2", "key3"])

        expected = {"key1": "value1", "key2": "value2", "key3": None}
        assert result == expected
        cache_service.redis.mget.assert_called_once_with(["key1", "key2", "key3"])

    @pytest.mark.asyncio
    async def test_mset_multiple_keys(self, cache_service):
        """Test setting multiple keys at once."""
        cache_service.redis.mset.return_value = True

        data = {"key1": "value1", "key2": "value2", "key3": "value3"}
        result = await cache_service.mset(data)

        assert result is True
        cache_service.redis.mset.assert_called_once_with(data)

    @pytest.mark.asyncio
    async def test_delete_multiple_keys(self, cache_service):
        """Test deleting multiple keys at once."""
        cache_service.redis.delete.return_value = 3

        result = await cache_service.delete_many(["key1", "key2", "key3"])

        assert result == 3
        cache_service.redis.delete.assert_called_once_with("key1", "key2", "key3")

    @pytest.mark.asyncio
    async def test_get_keys_by_pattern(self, cache_service):
        """Test getting keys by pattern."""
        cache_service.redis.keys.return_value = ["user:1", "user:2", "user:3"]

        result = await cache_service.get_keys("user:*")

        assert result == ["user:1", "user:2", "user:3"]
        cache_service.redis.keys.assert_called_once_with("user:*")

    @pytest.mark.asyncio
    async def test_flush_all_keys(self, cache_service):
        """Test flushing all keys from cache."""
        cache_service.redis.flushdb.return_value = True

        result = await cache_service.flush_all()

        assert result is True
        cache_service.redis.flushdb.assert_called_once()


class TestCacheKeyGeneration:
    """Test cache key generation and namespacing."""

    @pytest.fixture
    def cache_service(self):
        """Create a cache service with mocked Redis."""
        settings = MagicMock()
        settings.dragonfly.url = "redis://localhost:6379/0"
        settings.dragonfly.ttl_short = 300
        settings.dragonfly.ttl_medium = 3600
        settings.dragonfly.ttl_long = 86400

        cache_service = CacheService(settings)
        cache_service.redis = AsyncMock()
        return cache_service

    def test_generate_cache_key_simple(self, cache_service):
        """Test generating a simple cache key."""
        key = cache_service.generate_key("user", "123")
        assert key == "user:123"

    def test_generate_cache_key_multiple_parts(self, cache_service):
        """Test generating cache key with multiple parts."""
        key = cache_service.generate_key("user", "123", "profile", "settings")
        assert key == "user:123:profile:settings"

    def test_generate_cache_key_with_prefix(self, cache_service):
        """Test generating cache key with prefix."""
        key = cache_service.generate_key("user", "123", prefix="tripsage")
        assert key == "tripsage:user:123"

    def test_generate_cache_key_empty_parts(self, cache_service):
        """Test generating cache key with empty parts."""
        key = cache_service.generate_key("user", "", "profile")
        assert key == "user::profile"

    def test_generate_cache_key_numeric_parts(self, cache_service):
        """Test generating cache key with numeric parts."""
        key = cache_service.generate_key("user", 123, "session", 456)
        assert key == "user:123:session:456"


class TestCacheStatistics:
    """Test cache statistics and monitoring."""

    @pytest.fixture
    def cache_service(self):
        """Create a cache service with mocked Redis."""
        settings = MagicMock()
        settings.dragonfly.url = "redis://localhost:6379/0"
        settings.dragonfly.ttl_short = 300
        settings.dragonfly.ttl_medium = 3600
        settings.dragonfly.ttl_long = 86400

        cache_service = CacheService(settings)
        cache_service.redis = AsyncMock()
        return cache_service

    @pytest.mark.asyncio
    async def test_get_cache_info(self, cache_service):
        """Test getting cache information."""
        mock_info = {
            "used_memory": "1024000",
            "used_memory_human": "1000K",
            "connected_clients": "5",
            "keyspace_hits": "1000",
            "keyspace_misses": "100",
        }
        cache_service.redis.info.return_value = mock_info

        result = await cache_service.get_info()

        assert result == mock_info
        cache_service.redis.info.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_cache_size(self, cache_service):
        """Test getting cache size."""
        cache_service.redis.dbsize.return_value = 1000

        result = await cache_service.get_size()

        assert result == 1000
        cache_service.redis.dbsize.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_memory_usage(self, cache_service):
        """Test getting memory usage."""
        mock_info = {"used_memory": "2048000"}
        cache_service.redis.info.return_value = mock_info

        result = await cache_service.get_memory_usage()

        assert result == "2048000"
        cache_service.redis.info.assert_called_once_with("memory")


class TestErrorHandling:
    """Test error handling and edge cases."""

    @pytest.fixture
    def cache_service(self):
        """Create a cache service with mocked Redis."""
        settings = MagicMock()
        settings.dragonfly.url = "redis://localhost:6379/0"
        settings.dragonfly.ttl_short = 300
        settings.dragonfly.ttl_medium = 3600
        settings.dragonfly.ttl_long = 86400

        cache_service = CacheService(settings)
        cache_service.redis = AsyncMock()
        return cache_service

    @pytest.mark.asyncio
    async def test_operation_without_connection(self, cache_service):
        """Test operations when not connected to Redis."""
        cache_service.redis = None

        # Operations should handle gracefully
        result = await cache_service.get("test_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_set_operation_redis_error(self, cache_service):
        """Test set operation with Redis error."""
        cache_service.redis.set.side_effect = Exception("Redis error")

        result = await cache_service.set("test_key", "value")
        assert result is False

    @pytest.mark.asyncio
    async def test_get_operation_redis_error(self, cache_service):
        """Test get operation with Redis error."""
        cache_service.redis.get.side_effect = Exception("Redis error")

        result = await cache_service.get("test_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_operation_redis_error(self, cache_service):
        """Test delete operation with Redis error."""
        cache_service.redis.delete.side_effect = Exception("Redis error")

        result = await cache_service.delete("test_key")
        assert result is False

    @pytest.mark.asyncio
    async def test_json_serialization_error(self, cache_service):
        """Test handling of JSON serialization errors."""
        cache_service.redis.set.return_value = True

        # Object that can't be JSON serialized
        class NonSerializable:
            def __init__(self):
                self.value = lambda x: x

        result = await cache_service.set("test_key", NonSerializable())
        assert result is False

    @pytest.mark.asyncio
    async def test_json_deserialization_error(self, cache_service):
        """Test handling of JSON deserialization errors."""
        cache_service.redis.get.return_value = "invalid json {"

        result = await cache_service.get("test_key", parse_json=True)
        assert result == "invalid json {"  # Returns raw string on parse error


class TestConcurrency:
    """Test concurrent cache operations."""

    @pytest.fixture
    def cache_service(self):
        """Create a cache service with mocked Redis."""
        settings = MagicMock()
        settings.dragonfly.url = "redis://localhost:6379/0"
        settings.dragonfly.ttl_short = 300
        settings.dragonfly.ttl_medium = 3600
        settings.dragonfly.ttl_long = 86400

        cache_service = CacheService(settings)
        cache_service.redis = AsyncMock()
        return cache_service

    @pytest.mark.asyncio
    async def test_concurrent_set_operations(self, cache_service):
        """Test concurrent set operations."""
        cache_service.redis.set.return_value = True

        # Perform multiple set operations concurrently
        tasks = [cache_service.set(f"key_{i}", f"value_{i}") for i in range(10)]

        results = await asyncio.gather(*tasks)

        # All operations should succeed
        assert all(results)
        assert cache_service.redis.set.call_count == 10

    @pytest.mark.asyncio
    async def test_concurrent_get_operations(self, cache_service):
        """Test concurrent get operations."""
        cache_service.redis.get.return_value = "test_value"

        # Perform multiple get operations concurrently
        tasks = [cache_service.get(f"key_{i}") for i in range(10)]

        results = await asyncio.gather(*tasks)

        # All operations should return the same value
        assert all(result == "test_value" for result in results)
        assert cache_service.redis.get.call_count == 10

    @pytest.mark.asyncio
    async def test_concurrent_mixed_operations(self, cache_service):
        """Test concurrent mixed operations."""
        cache_service.redis.set.return_value = True
        cache_service.redis.get.return_value = "test_value"
        cache_service.redis.delete.return_value = 1

        # Mix of different operations
        tasks = [
            cache_service.set("key_1", "value_1"),
            cache_service.get("key_2"),
            cache_service.delete("key_3"),
            cache_service.exists("key_4"),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All operations should complete without exceptions
        assert len(results) == 4
        assert not any(isinstance(r, Exception) for r in results)


class TestCachePatterns:
    """Test common caching patterns and use cases."""

    @pytest.fixture
    def cache_service(self):
        """Create a cache service with mocked Redis."""
        settings = MagicMock()
        settings.dragonfly.url = "redis://localhost:6379/0"
        settings.dragonfly.ttl_short = 300
        settings.dragonfly.ttl_medium = 3600
        settings.dragonfly.ttl_long = 86400

        cache_service = CacheService(settings)
        cache_service.redis = AsyncMock()
        return cache_service

    @pytest.mark.asyncio
    async def test_cache_aside_pattern(self, cache_service):
        """Test cache-aside pattern implementation."""
        cache_service.redis.get.return_value = None  # Cache miss
        cache_service.redis.set.return_value = True

        # Simulate cache-aside pattern
        async def get_user_data(user_id: str) -> Dict[str, Any]:
            cache_key = f"user:{user_id}"

            # Try to get from cache first
            cached_data = await cache_service.get(cache_key, parse_json=True)
            if cached_data:
                return cached_data

            # Simulate database fetch
            user_data = {
                "id": user_id,
                "name": "Test User",
                "email": "test@example.com",
            }

            # Store in cache
            await cache_service.set(cache_key, user_data, ttl="medium")

            return user_data

        result = await get_user_data("123")

        assert result["id"] == "123"
        assert result["name"] == "Test User"
        cache_service.redis.get.assert_called_once()
        cache_service.redis.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_write_through_pattern(self, cache_service):
        """Test write-through pattern implementation."""
        cache_service.redis.set.return_value = True

        # Simulate write-through pattern
        async def update_user_data(user_id: str, data: Dict[str, Any]) -> bool:
            cache_key = f"user:{user_id}"

            # Update database (simulated)
            database_updated = True

            if database_updated:
                # Update cache immediately
                await cache_service.set(cache_key, data, ttl="medium")
                return True

            return False

        user_data = {
            "id": "123",
            "name": "Updated User",
            "email": "updated@example.com",
        }
        result = await update_user_data("123", user_data)

        assert result is True
        cache_service.redis.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_write_behind_pattern(self, cache_service):
        """Test write-behind pattern implementation."""
        cache_service.redis.set.return_value = True
        cache_service.redis.lpush.return_value = 1

        # Simulate write-behind pattern
        async def queue_user_update(user_id: str, data: Dict[str, Any]) -> bool:
            cache_key = f"user:{user_id}"
            queue_key = "user_updates_queue"

            # Update cache immediately
            await cache_service.set(cache_key, data, ttl="medium")

            # Queue for background database update
            update_item = json.dumps({"user_id": user_id, "data": data})
            await cache_service.redis.lpush(queue_key, update_item)

            return True

        user_data = {"id": "123", "name": "Queued User", "email": "queued@example.com"}
        result = await queue_user_update("123", user_data)

        assert result is True
        cache_service.redis.set.assert_called_once()
        cache_service.redis.lpush.assert_called_once()


class TestPerformance:
    """Test performance characteristics."""

    @pytest.fixture
    def cache_service(self):
        """Create a cache service with mocked Redis."""
        settings = MagicMock()
        settings.dragonfly.url = "redis://localhost:6379/0"
        settings.dragonfly.ttl_short = 300
        settings.dragonfly.ttl_medium = 3600
        settings.dragonfly.ttl_long = 86400

        cache_service = CacheService(settings)
        cache_service.redis = AsyncMock()
        return cache_service

    @pytest.mark.asyncio
    async def test_operation_speed(self, cache_service):
        """Test that cache operations complete quickly."""
        import time

        cache_service.redis.set.return_value = True
        cache_service.redis.get.return_value = "test_value"

        start_time = time.time()

        # Perform many operations
        for i in range(100):
            await cache_service.set(f"key_{i}", f"value_{i}")
            await cache_service.get(f"key_{i}")

        end_time = time.time()
        total_time = end_time - start_time

        # Should complete quickly (mocked operations)
        assert total_time < 1.0  # Less than 1 second

    @pytest.mark.asyncio
    async def test_memory_efficiency(self, cache_service):
        """Test memory efficiency of cache operations."""
        cache_service.redis.set.return_value = True

        # Create large dataset
        large_data = {"data": ["item"] * 1000}

        # Should handle large data efficiently
        result = await cache_service.set("large_key", large_data)
        assert result is True
