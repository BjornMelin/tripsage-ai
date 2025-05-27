"""Tests for the cache_tools module."""

from unittest.mock import AsyncMock, patch

import pytest

from tripsage.mcp_abstraction.exceptions import TripSageMCPError
from tripsage.mcp_abstraction.wrappers.redis_wrapper import ContentType
from tripsage.utils.cache_tools import (
    CacheStats,
    cached,
    cached_daily,
    cached_realtime,
    cached_semi_static,
    cached_static,
    cached_time_sensitive,
    delete_cache,
    determine_content_type,
    generate_cache_key,
    get_cache,
    get_cache_stats,
    invalidate_pattern,
    set_cache,
)


@pytest.fixture
def mock_mcp_manager():
    """Create a patched MCP manager for testing."""
    with patch("tripsage.utils.cache_tools.mcp_manager") as mock_manager:
        mock_manager.invoke = AsyncMock()
        yield mock_manager


@pytest.mark.asyncio
async def test_get_cache_stats(mock_mcp_manager):
    """Test get_cache_stats function."""
    # Mock the response from the Redis MCP
    mock_metrics = AsyncMock()
    mock_metrics.hits = 10
    mock_metrics.misses = 5
    mock_metrics.sets = 20
    mock_metrics.deletes = 3
    mock_metrics.key_count = 30
    mock_metrics.total_size_bytes = 1024 * 1024  # 1 MB

    mock_mcp_manager.invoke.return_value = mock_metrics

    # Call the function
    result = await get_cache_stats(namespace="test", time_window="24h")

    # Verify the MCP manager was called correctly
    mock_mcp_manager.invoke.assert_called_once_with(
        mcp_name="redis", method_name="get_stats", params={"time_window": "24h"}
    )

    # Verify the results
    assert isinstance(result, CacheStats)
    assert result.hits == 10
    assert result.misses == 5
    assert result.hit_ratio == 10 / 15  # hits / (hits + misses)
    assert result.sets == 20
    assert result.deletes == 3
    assert result.key_count == 30
    assert result.size_mb == 1.0  # 1 MB
    assert result.time_window == "24h"


@pytest.mark.asyncio
async def test_get_cache_stats_error(mock_mcp_manager):
    """Test get_cache_stats function when an error occurs."""
    # Mock the response from the Redis MCP to raise an error
    mock_mcp_manager.invoke.side_effect = TripSageMCPError("Test error")

    # Call the function
    result = await get_cache_stats()

    # Verify the MCP manager was called correctly
    mock_mcp_manager.invoke.assert_called_once_with(
        mcp_name="redis", method_name="get_stats", params={"time_window": "1h"}
    )

    # Verify default stats are returned on error
    assert isinstance(result, CacheStats)
    assert result.hits == 0
    assert result.misses == 0
    assert result.hit_ratio == 0.0
    assert result.sets == 0
    assert result.deletes == 0
    assert result.key_count == 0
    assert result.size_mb == 0.0
    assert result.time_window == "1h"


@pytest.mark.asyncio
async def test_set_cache(mock_mcp_manager):
    """Test set_cache function."""
    # Mock the response from the Redis MCP
    mock_mcp_manager.invoke.return_value = True

    # Test data
    key = "test:key"
    value = {"foo": "bar"}
    ttl = 3600
    content_type = ContentType.DAILY

    # Call the function
    result = await set_cache(key, value, ttl, content_type, namespace="test")

    # Verify the MCP manager was called correctly
    mock_mcp_manager.invoke.assert_called_once_with(
        mcp_name="redis",
        method_name="set",
        params={
            "key": key,
            "value": value,
            "ttl": ttl,
            "content_type": content_type,
        },
    )

    # Verify the result
    assert result is True


@pytest.mark.asyncio
async def test_set_cache_with_namespace_addition(mock_mcp_manager):
    """Test set_cache function with namespace addition."""
    # Mock the response from the Redis MCP
    mock_mcp_manager.invoke.return_value = True

    # Test data
    key = "key"  # No namespace
    value = {"foo": "bar"}
    namespace = "test"

    # Call the function
    result = await set_cache(key, value, namespace=namespace)

    # Verify the namespace was added to the key
    mock_mcp_manager.invoke.assert_called_once()
    call_args = mock_mcp_manager.invoke.call_args[1]
    assert call_args["params"]["key"] == f"{namespace}:{key}"

    # Verify the result
    assert result is True


@pytest.mark.asyncio
async def test_set_cache_error(mock_mcp_manager):
    """Test set_cache function when an error occurs."""
    # Mock the response from the Redis MCP to raise an error
    mock_mcp_manager.invoke.side_effect = TripSageMCPError("Test error")

    # Call the function
    result = await set_cache("test:key", {"foo": "bar"})

    # Verify the MCP manager was called correctly
    mock_mcp_manager.invoke.assert_called_once()

    # Verify False is returned on error
    assert result is False


@pytest.mark.asyncio
async def test_get_cache(mock_mcp_manager):
    """Test get_cache function."""
    # Mock the response from the Redis MCP
    mock_value = {"foo": "bar"}
    mock_mcp_manager.invoke.return_value = mock_value

    # Test data
    key = "test:key"

    # Call the function
    result = await get_cache(key)

    # Verify the MCP manager was called correctly
    mock_mcp_manager.invoke.assert_called_once_with(
        mcp_name="redis", method_name="get", params={"key": key}
    )

    # Verify the result
    assert result == mock_value


@pytest.mark.asyncio
async def test_get_cache_with_namespace_addition(mock_mcp_manager):
    """Test get_cache function with namespace addition."""
    # Mock the response from the Redis MCP
    mock_value = {"foo": "bar"}
    mock_mcp_manager.invoke.return_value = mock_value

    # Test data
    key = "key"  # No namespace
    namespace = "test"

    # Call the function
    result = await get_cache(key, namespace=namespace)

    # Verify the namespace was added to the key
    mock_mcp_manager.invoke.assert_called_once()
    call_args = mock_mcp_manager.invoke.call_args[1]
    assert call_args["params"]["key"] == f"{namespace}:{key}"

    # Verify the result
    assert result == mock_value


@pytest.mark.asyncio
async def test_get_cache_error(mock_mcp_manager):
    """Test get_cache function when an error occurs."""
    # Mock the response from the Redis MCP to raise an error
    mock_mcp_manager.invoke.side_effect = TripSageMCPError("Test error")

    # Call the function
    result = await get_cache("test:key")

    # Verify the MCP manager was called correctly
    mock_mcp_manager.invoke.assert_called_once()

    # Verify None is returned on error
    assert result is None


@pytest.mark.asyncio
async def test_delete_cache(mock_mcp_manager):
    """Test delete_cache function."""
    # Mock the response from the Redis MCP
    mock_mcp_manager.invoke.return_value = True

    # Test data
    key = "test:key"

    # Call the function
    result = await delete_cache(key)

    # Verify the MCP manager was called correctly
    mock_mcp_manager.invoke.assert_called_once_with(
        mcp_name="redis", method_name="delete", params={"key": key}
    )

    # Verify the result
    assert result is True


@pytest.mark.asyncio
async def test_delete_cache_with_namespace_addition(mock_mcp_manager):
    """Test delete_cache function with namespace addition."""
    # Mock the response from the Redis MCP
    mock_mcp_manager.invoke.return_value = True

    # Test data
    key = "key"  # No namespace
    namespace = "test"

    # Call the function
    result = await delete_cache(key, namespace=namespace)

    # Verify the namespace was added to the key
    mock_mcp_manager.invoke.assert_called_once()
    call_args = mock_mcp_manager.invoke.call_args[1]
    assert call_args["params"]["key"] == f"{namespace}:{key}"

    # Verify the result
    assert result is True


@pytest.mark.asyncio
async def test_delete_cache_error(mock_mcp_manager):
    """Test delete_cache function when an error occurs."""
    # Mock the response from the Redis MCP to raise an error
    mock_mcp_manager.invoke.side_effect = TripSageMCPError("Test error")

    # Call the function
    result = await delete_cache("test:key")

    # Verify the MCP manager was called correctly
    mock_mcp_manager.invoke.assert_called_once()

    # Verify False is returned on error
    assert result is False


@pytest.mark.asyncio
async def test_invalidate_pattern(mock_mcp_manager):
    """Test invalidate_pattern function."""
    # Mock the response from the Redis MCP
    mock_mcp_manager.invoke.return_value = 5  # 5 keys deleted

    # Test data
    pattern = "test:*"

    # Call the function
    result = await invalidate_pattern(pattern)

    # Verify the MCP manager was called correctly
    mock_mcp_manager.invoke.assert_called_once_with(
        mcp_name="redis", method_name="invalidate_pattern", params={"pattern": pattern}
    )

    # Verify the result
    assert result == 5


@pytest.mark.asyncio
async def test_invalidate_pattern_with_namespace_addition(mock_mcp_manager):
    """Test invalidate_pattern function with namespace addition."""
    # Mock the response from the Redis MCP
    mock_mcp_manager.invoke.return_value = 5  # 5 keys deleted

    # Test data
    pattern = "*"  # No namespace
    namespace = "test"

    # Call the function
    result = await invalidate_pattern(pattern, namespace=namespace)

    # Verify the namespace was added to the pattern
    mock_mcp_manager.invoke.assert_called_once()
    call_args = mock_mcp_manager.invoke.call_args[1]
    assert call_args["params"]["pattern"] == f"{namespace}:{pattern}"

    # Verify the result
    assert result == 5


@pytest.mark.asyncio
async def test_invalidate_pattern_error(mock_mcp_manager):
    """Test invalidate_pattern function when an error occurs."""
    # Mock the response from the Redis MCP to raise an error
    mock_mcp_manager.invoke.side_effect = TripSageMCPError("Test error")

    # Call the function
    result = await invalidate_pattern("test:*")

    # Verify the MCP manager was called correctly
    mock_mcp_manager.invoke.assert_called_once()

    # Verify 0 is returned on error
    assert result == 0


def test_generate_cache_key():
    """Test generate_cache_key function."""
    # Test data
    prefix = "test"
    query = "example query"
    args = ["arg1", "arg2"]
    kwargs = {"param1": "value1", "param2": "value2"}

    # Call the function
    result = generate_cache_key(prefix, query, args, **kwargs)

    # Verify it starts with the prefix
    assert result.startswith(f"{prefix}:")

    # Verify deterministic behavior (same inputs should produce the same key)
    result2 = generate_cache_key(prefix, query, args, **kwargs)
    assert result == result2

    # Verify different inputs produce different keys
    result3 = generate_cache_key(prefix, "different query", args, **kwargs)
    assert result != result3


def test_determine_content_type():
    """Test determine_content_type function."""
    # Test realtime keywords
    assert determine_content_type("current weather in London") == ContentType.REALTIME
    assert determine_content_type("stock price for AAPL") == ContentType.REALTIME

    # Test time-sensitive keywords
    assert (
        determine_content_type("breaking news today") == ContentType.REALTIME
    )  # "breaking" is realtime
    assert (
        determine_content_type("latest news on climate change") == ContentType.REALTIME
    )  # "latest" is realtime
    assert determine_content_type("trending topics") == ContentType.TIME_SENSITIVE

    # Test static keywords
    assert determine_content_type("history of the Roman Empire") == ContentType.STATIC
    assert determine_content_type("python tutorial") == ContentType.STATIC

    # Test domains
    assert (
        determine_content_type("example query", domains=["weather.com"])
        == ContentType.REALTIME
    )
    assert (
        determine_content_type("example query", domains=["cnn.com"])
        == ContentType.TIME_SENSITIVE
    )
    assert (
        determine_content_type("example query", domains=["wikipedia.org"])
        == ContentType.STATIC
    )

    # Test source
    assert (
        determine_content_type("example query", source="finance.yahoo.com")
        == ContentType.REALTIME
    )
    assert (
        determine_content_type("example query", source="bbc.com/news")
        == ContentType.TIME_SENSITIVE
    )
    assert (
        determine_content_type("example query", source="docs.python.org")
        == ContentType.STATIC
    )

    # Test default
    assert determine_content_type("neutral query with no keywords") == ContentType.DAILY


@pytest.mark.asyncio
async def test_cached_decorator():
    """Test cached decorator."""
    # Create a mock function to decorate
    with (
        patch("tripsage.utils.cache_tools.get_cache") as mock_get_cache,
        patch("tripsage.utils.cache_tools.set_cache") as mock_set_cache,
        patch("tripsage.utils.settings.settings") as mock_settings,
    ):
        mock_settings.use_cache = True
        mock_get_cache.return_value = None  # Cache miss
        mock_set_cache.return_value = True

        # Define a test function
        @cached(content_type=ContentType.DAILY, ttl=3600)
        async def test_func(arg1, arg2, kwarg1=None):
            """Test function."""
            return f"{arg1}-{arg2}-{kwarg1}"

        # Call the function
        result = await test_func("foo", "bar", kwarg1="baz")

        # Verify the function returned the correct result
        assert result == "foo-bar-baz"

        # Verify the cache was checked
        mock_get_cache.assert_called_once()

        # Verify the result was cached
        mock_set_cache.assert_called_once()
        set_cache_args = mock_set_cache.call_args[0]
        set_cache_kwargs = mock_set_cache.call_args[1]
        assert set_cache_args[1] == "foo-bar-baz"  # Value
        assert set_cache_kwargs["ttl"] == 3600
        assert set_cache_kwargs["content_type"] == ContentType.DAILY


@pytest.mark.asyncio
async def test_cached_decorator_cache_hit():
    """Test cached decorator with a cache hit."""
    # Create a mock function to decorate
    with (
        patch("tripsage.utils.cache_tools.get_cache") as mock_get_cache,
        patch("tripsage.utils.cache_tools.set_cache") as mock_set_cache,
        patch("tripsage.utils.settings.settings") as mock_settings,
    ):
        mock_settings.use_cache = True
        mock_get_cache.return_value = "cached-result"  # Cache hit
        mock_set_cache.return_value = True

        # Define a test function
        @cached(content_type=ContentType.DAILY)
        async def test_func(arg1, arg2):
            """Test function."""
            # This should not be called due to cache hit
            return f"{arg1}-{arg2}"

        # Call the function
        result = await test_func("foo", "bar")

        # Verify the cached result was returned
        assert result == "cached-result"

        # Verify the cache was checked
        mock_get_cache.assert_called_once()

        # Verify the result was not cached again
        mock_set_cache.assert_not_called()


@pytest.mark.asyncio
async def test_cached_decorator_with_skip_cache():
    """Test cached decorator with skip_cache parameter."""
    # Create a mock function to decorate
    with (
        patch("tripsage.utils.cache_tools.get_cache") as mock_get_cache,
        patch("tripsage.utils.cache_tools.set_cache") as mock_set_cache,
        patch("tripsage.utils.settings.settings") as mock_settings,
    ):
        mock_settings.use_cache = True

        # Define a test function
        @cached(content_type=ContentType.DAILY)
        async def test_func(arg1, arg2, skip_cache=False):
            """Test function."""
            return f"{arg1}-{arg2}"

        # Call the function with skip_cache=True
        result = await test_func("foo", "bar", skip_cache=True)

        # Verify the function returned the correct result
        assert result == "foo-bar"

        # Verify the cache was not checked
        mock_get_cache.assert_not_called()

        # Verify the result was not cached
        mock_set_cache.assert_not_called()


@pytest.mark.asyncio
async def test_cached_decorator_with_caching_disabled():
    """Test cached decorator with caching disabled."""
    # Create a mock function to decorate
    with (
        patch("tripsage.utils.cache_tools.get_cache") as mock_get_cache,
        patch("tripsage.utils.cache_tools.set_cache") as mock_set_cache,
        patch("tripsage.utils.settings.settings") as mock_settings,
    ):
        mock_settings.use_cache = False  # Caching disabled

        # Define a test function
        @cached(content_type=ContentType.DAILY)
        async def test_func(arg1, arg2):
            """Test function."""
            return f"{arg1}-{arg2}"

        # Call the function
        result = await test_func("foo", "bar")

        # Verify the function returned the correct result
        assert result == "foo-bar"

        # Verify the cache was not checked
        mock_get_cache.assert_not_called()

        # Verify the result was not cached
        mock_set_cache.assert_not_called()


@pytest.mark.asyncio
async def test_cached_decorator_invalidate():
    """Test the invalidate method of cached decorator."""
    # Create a mock function to decorate
    with (
        patch("tripsage.utils.cache_tools.delete_cache") as mock_delete_cache,
        patch("tripsage.utils.settings.settings") as mock_settings,
    ):
        mock_settings.use_cache = True
        mock_delete_cache.return_value = True

        # Define a test function
        @cached()
        async def test_func(arg1, arg2):
            """Test function."""
            return f"{arg1}-{arg2}"

        # Call the invalidate method
        result = await test_func.invalidate("foo", "bar")

        # Verify the cache entry was deleted
        assert result is True
        mock_delete_cache.assert_called_once()


@pytest.mark.asyncio
async def test_cached_decorator_invalidate_all():
    """Test the invalidate_all method of cached decorator."""
    # Create a mock function to decorate
    with (
        patch(
            "tripsage.utils.cache_tools.invalidate_pattern"
        ) as mock_invalidate_pattern,
        patch("tripsage.utils.settings.settings") as mock_settings,
    ):
        mock_settings.use_cache = True
        mock_invalidate_pattern.return_value = 5  # 5 keys deleted

        # Define a test function
        @cached()
        async def test_func(arg1, arg2):
            """Test function."""
            return f"{arg1}-{arg2}"

        # Call the invalidate_all method
        result = await test_func.invalidate_all()

        # Verify all cache entries were deleted
        assert result == 5
        mock_invalidate_pattern.assert_called_once()


@pytest.mark.asyncio
async def test_content_specific_decorators():
    """Test content-specific cache decorators."""
    # Create a mock function to decorate
    with (
        patch("tripsage.utils.cache_tools.get_cache") as mock_get_cache,
        patch("tripsage.utils.cache_tools.set_cache") as mock_set_cache,
        patch("tripsage.utils.settings.settings") as mock_settings,
    ):
        mock_settings.use_cache = True
        mock_get_cache.return_value = None  # Cache miss
        mock_set_cache.return_value = True

        # Test each content-specific decorator
        decorators = [
            (cached_realtime, ContentType.REALTIME),
            (cached_time_sensitive, ContentType.TIME_SENSITIVE),
            (cached_daily, ContentType.DAILY),
            (cached_semi_static, ContentType.SEMI_STATIC),
            (cached_static, ContentType.STATIC),
        ]

        for decorator, expected_content_type in decorators:
            mock_set_cache.reset_mock()

            # Define a test function
            @decorator(ttl=3600)
            async def test_func():
                """Test function."""
                return "result"

            # Call the function
            result = await test_func()

            # Verify the function returned the correct result
            assert result == "result"

            # Verify the result was cached with the correct content type
            mock_set_cache.assert_called_once()
            set_cache_kwargs = mock_set_cache.call_args[1]
            assert set_cache_kwargs["content_type"] == expected_content_type
            assert set_cache_kwargs["ttl"] == 3600
