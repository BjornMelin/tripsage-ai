"""Tests for the Redis MCP wrapper."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tripsage.mcp_abstraction.wrappers.redis_wrapper import (
    ContentType,
    RedisMCPClient,
    RedisMCPWrapper,
)
from tripsage.utils.cache_tools import (
    batch_cache_set,
    cache_lock,
    cached,
    get_cache,
    set_cache,
)


class TestRedisMCPClient:
    """Test the Redis MCP client."""

    @pytest.fixture
    def redis_client(self):
        """Create a Redis MCP client."""
        client = RedisMCPClient(
            host="localhost",
            port=6379,
            db=0,
            namespace="test",
            default_ttl=3600,
        )
        # Mock the internal Redis client
        client._redis = AsyncMock()
        return client

    @pytest.mark.asyncio
    async def test_get(self, redis_client):
        """Test getting a value from Redis."""
        # Mock the Redis get method
        redis_client._redis.get.return_value = '{"key": "value"}'

        # Call the method
        result = await redis_client.get("test-key")

        # Check that the Redis get method was called correctly
        redis_client._redis.get.assert_called_once_with("test:test-key")

        # Check the result
        assert result == {"key": "value"}

    @pytest.mark.asyncio
    async def test_set(self, redis_client):
        """Test setting a value in Redis."""
        # Mock the Redis set method
        redis_client._redis.set.return_value = True

        # Call the method
        result = await redis_client.set("test-key", {"key": "value"}, ttl=60)

        # Check that the Redis set method was called correctly
        redis_client._redis.set.assert_called_once_with(
            "test:test-key", '{"key": "value"}', ex=60
        )

        # Check the result
        assert result is True

    @pytest.mark.asyncio
    async def test_delete(self, redis_client):
        """Test deleting a value from Redis."""
        # Mock the Redis delete method
        redis_client._redis.delete.return_value = 1

        # Call the method
        result = await redis_client.delete("test-key")

        # Check that the Redis delete method was called correctly
        redis_client._redis.delete.assert_called_once_with("test:test-key")

        # Check the result
        assert result is True

    @pytest.mark.asyncio
    async def test_invalidate_pattern(self, redis_client):
        """Test invalidating keys by pattern."""
        # Mock the Redis keys and delete methods
        redis_client._redis.keys.return_value = ["test:key1", "test:key2"]
        redis_client._redis.delete.return_value = 2

        # Call the method
        result = await redis_client.invalidate_pattern("key*")

        # Check that the Redis methods were called correctly
        redis_client._redis.keys.assert_called_once_with("test:key*")
        redis_client._redis.delete.assert_called_once_with("test:key1", "test:key2")

        # Check the result
        assert result == 2

    @pytest.mark.asyncio
    async def test_acquire_lock(self, redis_client):
        """Test acquiring a distributed lock."""
        # Mock the Redis set method
        redis_client._redis.set.return_value = True

        # Call the method
        success, token = await redis_client.acquire_lock("test-lock", timeout=10)

        # Check that the Redis set method was called correctly
        redis_client._redis.set.assert_called_once_with(
            "test:lock:test-lock", token, nx=True, ex=10
        )

        # Check the result
        assert success is True
        assert token is not None

    @pytest.mark.asyncio
    async def test_release_lock(self, redis_client):
        """Test releasing a distributed lock."""
        # Mock the Redis eval method
        redis_client._redis.eval.return_value = 1

        # Call the method
        result = await redis_client.release_lock("test-lock", "token123")

        # Check that the Redis eval method was called correctly
        redis_client._redis.eval.assert_called_once()

        # Check the result
        assert result is True

    @pytest.mark.asyncio
    async def test_pipeline_execute(self, redis_client):
        """Test executing a pipeline of commands."""
        # Create a mock pipeline
        pipeline_mock = AsyncMock()
        redis_client._redis.pipeline.return_value = pipeline_mock

        # Mock the pipeline execute method
        pipeline_mock.execute.return_value = [True, "value"]

        # Define commands
        commands = [
            {"command": "set", "args": ["key1", "value1"]},
            {"command": "get", "args": ["key2"]},
        ]

        # Call the method
        results = await redis_client.pipeline_execute(commands)

        # Check that the Redis pipeline methods were called correctly
        redis_client._redis.pipeline.assert_called_once()
        pipeline_mock.execute.assert_called_once()

        # Check the results
        assert results == [True, "value"]

    @pytest.mark.asyncio
    async def test_prefetch_keys(self, redis_client):
        """Test prefetching keys into Redis cache memory."""
        # Mock the Redis scan and pipeline methods
        redis_client.scan = AsyncMock()
        redis_client.scan.return_value = (0, ["test:key1", "test:key2"])

        pipeline_mock = AsyncMock()
        redis_client._redis.pipeline.return_value = pipeline_mock

        # Call the method
        result = await redis_client.prefetch_keys("key*", limit=10)

        # Check that the Redis methods were called correctly
        redis_client.scan.assert_called_once()
        redis_client._redis.pipeline.assert_called_once()

        # Check the result
        assert result == 2


class TestRedisMCPWrapper:
    """Test the Redis MCP wrapper."""

    @pytest.fixture
    def redis_wrapper(self):
        """Create a Redis MCP wrapper with a mock client."""
        client = MagicMock()
        return RedisMCPWrapper(client, "redis")

    def test_build_method_map(self, redis_wrapper):
        """Test building the method map."""
        method_map = redis_wrapper._build_method_map()

        # Check that key methods are in the map
        assert "get" in method_map
        assert "set" in method_map
        assert "delete" in method_map
        assert "acquire_lock" in method_map
        assert "release_lock" in method_map
        assert "pipeline_execute" in method_map
        assert "prefetch_keys" in method_map

    @pytest.mark.asyncio
    async def test_invoke_get(self, redis_wrapper):
        """Test invoking the get method."""
        # Mock the client get method
        redis_wrapper._client.get = AsyncMock()
        redis_wrapper._client.get.return_value = {"key": "value"}

        # Call the method
        result = await redis_wrapper.invoke("get", {"key": "test-key"})

        # Check that the client method was called correctly
        redis_wrapper._client.get.assert_called_once_with("test-key")

        # Check the result
        assert result == {"key": "value"}

    @pytest.mark.asyncio
    async def test_invoke_set(self, redis_wrapper):
        """Test invoking the set method."""
        # Mock the client set method
        redis_wrapper._client.set = AsyncMock()
        redis_wrapper._client.set.return_value = True

        # Call the method
        result = await redis_wrapper.invoke(
            "set", {"key": "test-key", "value": {"data": "test"}, "ttl": 60}
        )

        # Check that the client method was called correctly
        redis_wrapper._client.set.assert_called_once_with(
            "test-key", {"data": "test"}, ttl=60, content_type=None, nx=False, xx=False
        )

        # Check the result
        assert result is True


class TestCacheTools:
    """Test the cache tools module."""

    @pytest.fixture
    def mock_mcp_manager(self):
        """Create a mock MCP manager."""
        with patch("tripsage.utils.cache_tools.mcp_manager") as mock:
            yield mock

    @pytest.mark.asyncio
    async def test_get_cache(self, mock_mcp_manager):
        """Test getting a value from the cache."""
        # Mock the MCP manager invoke method
        mock_mcp_manager.invoke = AsyncMock()
        mock_mcp_manager.invoke.return_value = {"key": "value"}

        # Call the method
        result = await get_cache("test-key")

        # Check that the MCP manager invoke method was called correctly
        mock_mcp_manager.invoke.assert_called_once_with(
            mcp_name="redis",
            method_name="get",
            params={"key": "tripsage:test-key"},
        )

        # Check the result
        assert result == {"key": "value"}

    @pytest.mark.asyncio
    async def test_set_cache(self, mock_mcp_manager):
        """Test setting a value in the cache."""
        # Mock the MCP manager invoke method
        mock_mcp_manager.invoke = AsyncMock()
        mock_mcp_manager.invoke.return_value = True

        # Call the method
        result = await set_cache(
            "test-key", {"data": "test"}, ttl=60, content_type=ContentType.DAILY
        )

        # Check that the MCP manager invoke method was called correctly
        mock_mcp_manager.invoke.assert_called_once_with(
            mcp_name="redis",
            method_name="set",
            params={
                "key": "tripsage:test-key",
                "value": {"data": "test"},
                "ttl": 60,
                "content_type": ContentType.DAILY,
                "nx": False,
                "xx": False,
            },
        )

        # Check the result
        assert result is True

    @pytest.mark.asyncio
    async def test_batch_cache_set(self, mock_mcp_manager):
        """Test setting multiple values in the cache."""
        # Mock the MCP manager invoke method
        mock_mcp_manager.invoke = AsyncMock()
        mock_mcp_manager.invoke.return_value = [True, True]

        # Call the method
        result = await batch_cache_set(
            [
                {
                    "key": "key1",
                    "value": "value1",
                    "ttl": 60,
                    "content_type": ContentType.DAILY,
                },
                {
                    "key": "key2",
                    "value": "value2",
                },
            ]
        )

        # Check that the MCP manager invoke method was called correctly
        mock_mcp_manager.invoke.assert_called_once_with(
            mcp_name="redis",
            method_name="pipeline_execute",
            params={
                "commands": [
                    {
                        "command": "set",
                        "args": ["tripsage:key1", "value1"],
                        "kwargs": {"ex": 60, "content_type": ContentType.DAILY},
                    },
                    {
                        "command": "set",
                        "args": ["tripsage:key2", "value2"],
                        "kwargs": {"ex": None, "content_type": None},
                    },
                ]
            },
        )

        # Check the result
        assert result == [True, True]

    @pytest.mark.asyncio
    async def test_cache_lock(self, mock_mcp_manager):
        """Test using the cache lock context manager."""
        # Mock the acquire and release lock methods
        mock_mcp_manager.invoke = AsyncMock()
        mock_mcp_manager.invoke.side_effect = [
            (True, "token123"),  # acquire_lock result
            True,  # release_lock result
        ]

        # Use the cache lock context manager
        async with cache_lock("test-lock", timeout=10) as acquired:
            # Check that the lock was acquired
            assert acquired is True

            # Check that acquire_lock was called correctly
            mock_mcp_manager.invoke.assert_called_once_with(
                mcp_name="redis",
                method_name="acquire_lock",
                params={
                    "lock_name": "test-lock",
                    "timeout": 10,
                    "retry_delay": 0.1,
                    "retry_count": 50,
                },
            )

        # Check that release_lock was called correctly
        assert mock_mcp_manager.invoke.call_count == 2
        mock_mcp_manager.invoke.assert_called_with(
            mcp_name="redis",
            method_name="release_lock",
            params={
                "lock_name": "test-lock",
                "lock_token": "token123",
            },
        )

    @pytest.mark.asyncio
    async def test_cached_decorator(self, mock_mcp_manager):
        """Test the cached decorator."""
        # Mock the get_cache and set_cache methods
        mock_mcp_manager.invoke = AsyncMock()
        mock_mcp_manager.invoke.side_effect = [
            None,  # get_cache returns None (cache miss)
            True,  # set_cache returns True
        ]

        # Define a test function with the cached decorator
        @cached(content_type=ContentType.DAILY)
        async def test_function(arg1, arg2):
            return f"{arg1}:{arg2}"

        # Call the decorated function
        result = await test_function("test", 123)

        # Check that get_cache and set_cache were called correctly
        assert mock_mcp_manager.invoke.call_count == 2

        # Check the result
        assert result == "test:123"


@pytest.mark.asyncio
class TestContentAwareCaching:
    """Test content-aware caching."""

    def test_determine_content_type(self):
        """Test determining content type from query and domains."""
        # Test with realtime keywords
        assert (
            determine_content_type("current weather in New York")
            == ContentType.REALTIME
        )

        # Test with time-sensitive keywords
        assert (
            determine_content_type("latest news about AI") == ContentType.TIME_SENSITIVE
        )

        # Test with static keywords
        assert (
            determine_content_type("history of the Roman Empire") == ContentType.STATIC
        )

        # Test with domains
        assert (
            determine_content_type("query", domains=["weather.com"])
            == ContentType.REALTIME
        )
        assert (
            determine_content_type("query", domains=["cnn.com"])
            == ContentType.TIME_SENSITIVE
        )
        assert (
            determine_content_type("query", domains=["wikipedia.org"])
            == ContentType.STATIC
        )
