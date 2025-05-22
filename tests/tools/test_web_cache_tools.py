"""Tests for the web cache tools."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tripsage.mcp_abstraction.wrappers.redis_wrapper import ContentType
from tripsage.tools.web_tools import (
    WEB_CACHE_NAMESPACE,
    CachedWebSearchTool,
    batch_web_search,
    get_web_cache_stats,
    invalidate_web_cache_for_query,
    web_cached,
)


class TestCachedWebSearchTool:
    """Test the CachedWebSearchTool."""

    @pytest.fixture
    def mock_websearch_tool(self):
        """Create a mock WebSearchTool."""
        with patch("tripsage.tools.web_tools.WebSearchTool") as mock:
            # Mock the _run method
            mock.return_value._run = AsyncMock()
            mock.return_value._run.return_value = {
                "search_results": [
                    {
                        "title": "Test Result",
                        "link": "https://example.com",
                        "snippet": "This is a test result.",
                    }
                ]
            }
            yield mock

    @pytest.fixture
    def cached_tool(self, mock_websearch_tool):
        """Create a CachedWebSearchTool."""
        return CachedWebSearchTool(namespace=WEB_CACHE_NAMESPACE)

    @pytest.mark.asyncio
    async def test_run_with_cache_hit(self, cached_tool):
        """Test _run with a cache hit."""
        # Mock the get_cache method
        with patch("tripsage.tools.web_tools.get_cache") as mock_get:
            # Simulate cache hit
            mock_get.return_value = {
                "search_results": [
                    {
                        "title": "Cached Result",
                        "link": "https://example.com",
                        "snippet": "This is a cached result.",
                    }
                ]
            }

            # Mock the cache_lock context manager
            with patch("tripsage.tools.web_tools.cache_lock") as mock_lock:
                # Configure the context manager's __aenter__ method
                mock_lock.return_value.__aenter__ = AsyncMock()
                mock_lock.return_value.__aexit__ = AsyncMock()

                # Call the method
                result = await cached_tool._run("test query")

                # Check that get_cache was called and super()._run was not called
                mock_get.assert_called_once()
                cached_tool._run.assert_not_called()

                # Check the result
                assert result["search_results"][0]["title"] == "Cached Result"

    @pytest.mark.asyncio
    async def test_run_with_cache_miss(self, cached_tool):
        """Test _run with a cache miss."""
        # Mock the cache-related methods
        with (
            patch("tripsage.tools.web_tools.get_cache") as mock_get,
            patch("tripsage.tools.web_tools.set_cache") as mock_set,
            patch("tripsage.tools.web_tools.cache_lock") as mock_lock,
            patch.object(cached_tool, "_prefetch_related_queries") as mock_prefetch,
        ):
            # Simulate cache miss
            mock_get.return_value = None

            # Configure the lock context manager
            mock_lock.return_value.__aenter__ = AsyncMock()
            mock_lock.return_value.__aexit__ = AsyncMock()

            # Mock the parent class's _run method
            with patch.object(
                cached_tool, "_run", side_effect=AsyncMock()
            ) as mock_super_run:
                # Set up the mock to return test data
                mock_super_run.return_value = {
                    "search_results": [
                        {
                            "title": "Fresh Result",
                            "link": "https://example.com",
                            "snippet": "This is a fresh result.",
                        }
                    ]
                }

                # Call the method
                result = await cached_tool._run("test query")

                # Check that get_cache was called
                mock_get.assert_called_once()

                # Check that set_cache was called
                mock_set.assert_called_once()

                # Check that prefetch was called
                mock_prefetch.assert_called_once()

                # Check the result
                assert result["search_results"][0]["title"] == "Fresh Result"

    @pytest.mark.asyncio
    async def test_determine_content_type(self, cached_tool):
        """Test the _determine_content_type method."""
        # Test with a realtime query
        result = cached_tool._determine_content_type("current weather")
        assert result == ContentType.REALTIME

        # Test with domains
        result = cached_tool._determine_content_type(
            "test",
            {
                "search_results": [
                    {"link": "https://cnn.com/article"},
                    {"link": "https://nytimes.com/article"},
                ]
            },
        )
        assert result == ContentType.TIME_SENSITIVE


class TestBatchWebSearch:
    """Test the batch_web_search function."""

    @pytest.mark.asyncio
    async def test_batch_web_search_with_cache(self):
        """Test batch_web_search with cache hits."""
        # Mock the cache and search methods
        with (
            patch("tripsage.tools.web_tools.batch_cache_get") as mock_get,
            patch("tripsage.tools.web_tools.CachedWebSearchTool") as mock_tool,
        ):
            # Simulate some cache hits and some misses
            mock_get.return_value = [
                {"result": "cached1"},  # Hit
                None,  # Miss
                {"result": "cached3"},  # Hit
            ]

            # Mock the CachedWebSearchTool
            instance = mock_tool.return_value
            instance._run = AsyncMock()
            instance._run.return_value = {"result": "fresh"}

            # Call the function
            results = await batch_web_search(["query1", "query2", "query3"])

            # Check that batch_cache_get was called
            mock_get.assert_called_once()

            # Check that search was called once for the miss
            instance._run.assert_called_once_with("query2", skip_cache=True)

            # Check the results
            assert len(results) == 3
            assert results[0]["result"] == "cached1"
            assert results[1]["result"] == "fresh"
            assert results[2]["result"] == "cached3"


class TestWebCacheDecorators:
    """Test the web cache decorators."""

    @pytest.mark.asyncio
    async def test_web_cached_decorator(self):
        """Test the web_cached decorator."""
        # Mock the cached decorator
        with patch("tripsage.tools.web_tools.cached") as mock_cached:
            # Configure the mock
            mock_cached.return_value = lambda func: func

            # Use the decorator
            web_cached(ContentType.DAILY)

            # Check that cached was called with the correct parameters
            mock_cached.assert_called_once_with(
                content_type=ContentType.DAILY,
                ttl=None,
                namespace=WEB_CACHE_NAMESPACE,
            )


class TestWebCacheManagement:
    """Test the web cache management functions."""

    @pytest.mark.asyncio
    async def test_get_web_cache_stats(self):
        """Test getting web cache statistics."""
        # Mock the get_cache_stats function
        with patch("tripsage.tools.web_tools.get_cache_stats") as mock_stats:
            # Configure the mock
            mock_stats.return_value = MagicMock()

            # Call the function
            await get_web_cache_stats()

            # Check that get_cache_stats was called with the correct parameters
            mock_stats.assert_called_once_with(
                namespace=WEB_CACHE_NAMESPACE,
                time_window="1h",
            )

    @pytest.mark.asyncio
    async def test_invalidate_web_cache_for_query(self):
        """Test invalidating web cache for a query."""
        # Mock the invalidate_pattern function
        with patch("tripsage.tools.web_tools.invalidate_pattern") as mock_invalidate:
            # Configure the mock
            mock_invalidate.return_value = 5

            # Call the function
            count = await invalidate_web_cache_for_query("test query")

            # Check that invalidate_pattern was called
            mock_invalidate.assert_called_once()

            # Check the result
            assert count == 5
