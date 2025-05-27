"""
Tests for WebOperationsCache in tripsage/utils/cache.py.
"""

import json
from unittest.mock import AsyncMock, patch

import pytest

from tripsage.utils.cache import (
    CacheMetrics,
    ContentType,
    WebOperationsCache,
)


@pytest.fixture
def mock_redis():
    """Create a mock Redis client."""
    mock = AsyncMock()
    mock.get.return_value = None
    mock.set.return_value = True
    mock.delete.return_value = 1
    mock.keys.return_value = []
    mock.hincrby.return_value = 1
    mock.expire.return_value = True
    mock.hgetall.return_value = {
        b"hits": b"10",
        b"misses": b"5",
        b"sets": b"15",
        b"deletes": b"2",
    }
    mock.scan.return_value = (b"0", [])
    return mock


@pytest.fixture
def web_cache(mock_redis):
    """Create a WebOperationsCache instance with mocked Redis."""
    with patch("redis.asyncio.from_url", return_value=mock_redis):
        cache = WebOperationsCache(
            url="redis://localhost:6379/0",
            namespace="test-cache",
            sample_rate=1.0,  # Always collect metrics in tests
        )
        return cache


class TestWebOperationsCache:
    """Test suite for WebOperationsCache."""

    @pytest.mark.asyncio
    async def test_get_cache_hit(self, web_cache, mock_redis):
        """Test retrieving a value from cache that exists."""
        # Setup
        mock_redis.get.return_value = json.dumps({"data": "test"})

        # Execute
        result = await web_cache.get("test-key")

        # Verify
        mock_redis.get.assert_called_once_with("test-cache:test-key")
        assert result == {"data": "test"}
        mock_redis.hincrby.assert_called_with("test-cache:metrics:1h", "hits", 1)

    @pytest.mark.asyncio
    async def test_get_cache_miss(self, web_cache, mock_redis):
        """Test retrieving a value from cache that doesn't exist."""
        # Setup
        mock_redis.get.return_value = None

        # Execute
        result = await web_cache.get("test-key")

        # Verify
        assert result is None
        mock_redis.hincrby.assert_called_with("test-cache:metrics:1h", "misses", 1)

    @pytest.mark.asyncio
    async def test_set_with_content_type(self, web_cache, mock_redis):
        """Test setting a value with a specific content type."""
        # Execute
        await web_cache.set(
            "test-key", {"data": "test"}, content_type=ContentType.STATIC
        )

        # Verify
        mock_redis.set.assert_called_once()
        args, kwargs = mock_redis.set.call_args
        assert args[0] == "test-cache:test-key"
        assert json.loads(args[1]) == {"data": "test"}
        assert kwargs["ex"] == web_cache.ttl_settings[ContentType.STATIC]

    @pytest.mark.asyncio
    async def test_set_with_explicit_ttl(self, web_cache, mock_redis):
        """Test setting a value with an explicit TTL."""
        # Execute
        await web_cache.set("test-key", {"data": "test"}, ttl=60)

        # Verify
        mock_redis.set.assert_called_once()
        args, kwargs = mock_redis.set.call_args
        assert kwargs["ex"] == 60

    @pytest.mark.asyncio
    async def test_delete(self, web_cache, mock_redis):
        """Test deleting a value from cache."""
        # Execute
        result = await web_cache.delete("test-key")

        # Verify
        assert result is True
        mock_redis.delete.assert_called_once_with("test-cache:test-key")
        mock_redis.hincrby.assert_called_with("test-cache:metrics:1h", "deletes", 1)

    @pytest.mark.asyncio
    async def test_invalidate_pattern(self, web_cache, mock_redis):
        """Test invalidating keys by pattern."""
        # Setup
        mock_redis.keys.return_value = [b"test-cache:key1", b"test-cache:key2"]

        # Execute
        count = await web_cache.invalidate_pattern("key*")

        # Verify
        mock_redis.keys.assert_called_once_with("test-cache:key*")
        mock_redis.delete.assert_called_once_with(
            b"test-cache:key1", b"test-cache:key2"
        )
        assert count == 1  # Mock returns 1

    def test_generate_cache_key(self, web_cache):
        """Test generating a deterministic cache key."""
        # Execute
        key1 = web_cache.generate_cache_key("tool1", "query1", param1="value1")
        key2 = web_cache.generate_cache_key("tool1", "query1", param1="value1")
        key3 = web_cache.generate_cache_key("tool1", "query2", param1="value1")

        # Verify
        assert key1 == key2  # Same params should generate same key
        assert key1 != key3  # Different query should generate different key
        assert key1.startswith("test-cache:tool1:")  # Should include namespace and tool

    def test_get_ttl_for_content_type(self, web_cache):
        """Test retrieving TTL for different content types."""
        # Execute & Verify
        assert (
            web_cache.get_ttl_for_content_type(ContentType.REALTIME)
            == web_cache.ttl_settings[ContentType.REALTIME]
        )
        assert (
            web_cache.get_ttl_for_content_type(ContentType.STATIC)
            == web_cache.ttl_settings[ContentType.STATIC]
        )

    def test_determine_content_type_from_query(self, web_cache):
        """Test content type determination from query."""
        # Execute & Verify - Realtime queries
        assert (
            web_cache.determine_content_type("current weather in New York")
            == ContentType.REALTIME
        )
        assert (
            web_cache.determine_content_type("stock price of AAPL")
            == ContentType.REALTIME
        )

        # Time-sensitive queries
        assert (
            web_cache.determine_content_type("latest news about AI")
            == ContentType.TIME_SENSITIVE
        )
        assert (
            web_cache.determine_content_type("trending social media topics")
            == ContentType.TIME_SENSITIVE
        )

        # Static queries
        assert web_cache.determine_content_type("history of Rome") == ContentType.STATIC
        assert (
            web_cache.determine_content_type("how to make bread recipe")
            == ContentType.STATIC
        )

        # Default (daily) for queries that don't match specific patterns
        assert (
            web_cache.determine_content_type("Python programming") == ContentType.DAILY
        )

    def test_determine_content_type_from_domains(self, web_cache):
        """Test content type determination from domains."""
        # Execute & Verify - Realtime domains
        assert (
            web_cache.determine_content_type(
                "test query", domains=["weather.com", "example.com"]
            )
            == ContentType.REALTIME
        )

        # Time-sensitive domains
        assert (
            web_cache.determine_content_type(
                "test query", domains=["cnn.com", "example.com"]
            )
            == ContentType.TIME_SENSITIVE
        )

        # Static domains
        assert (
            web_cache.determine_content_type(
                "test query", domains=["wikipedia.org", "example.com"]
            )
            == ContentType.STATIC
        )

    @pytest.mark.asyncio
    async def test_get_stats(self, web_cache, mock_redis):
        """Test retrieving cache stats."""
        # Setup
        mock_redis.scan.side_effect = [(b"0", [b"key1", b"key2"])]
        mock_redis.get.return_value = b"test data"

        # Execute
        metrics = await web_cache.get_stats("1h")

        # Verify
        assert isinstance(metrics, CacheMetrics)
        assert metrics.hits == 10
        assert metrics.misses == 5
        assert metrics.key_count == 2

    @pytest.mark.asyncio
    async def test_should_track_metrics(self, web_cache):
        """Test the metrics sampling logic."""
        # Setup - sample_rate is 1.0 in fixture

        # Execute & Verify
        assert web_cache._should_track_metrics() is True

        # Change sample rate to 0
        web_cache.sample_rate = 0
        assert web_cache._should_track_metrics() is False
