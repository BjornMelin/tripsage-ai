"""
Tests for web_tools.py - CachedWebSearchTool and related utilities.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from openai.types.beta.assistant_tools_web_search import WebSearchTool

from tripsage.tools.web_tools import (
    CachedWebSearchTool,
    get_web_cache_stats,
    invalidate_web_cache_for_query,
    web_cached,
)
from tripsage.utils.cache import ContentType, WebOperationsCache


@pytest.fixture
def mock_cache():
    """Create a mock WebOperationsCache."""
    mock = AsyncMock(spec=WebOperationsCache)
    mock.get.return_value = None
    mock.set.return_value = True
    mock.generate_cache_key.return_value = "test-key"
    mock.determine_content_type.return_value = ContentType.DAILY
    mock.get_stats.return_value = MagicMock(
        hits=10, misses=5, key_count=15, total_size_bytes=1024 * 1024
    )
    mock.invalidate_pattern.return_value = 3
    mock.web_cached = lambda content_type: lambda func: func
    return mock


@pytest.fixture
def mock_websearch_tool():
    """Create a mock for the parent WebSearchTool."""
    with patch.object(WebSearchTool, "_run") as mock_run:
        mock_run.return_value = {
            "search_results": [
                {
                    "title": "Test Result",
                    "link": "https://example.com/test",
                    "snippet": "This is a test search result",
                }
            ]
        }
        yield mock_run


class TestCachedWebSearchTool:
    """Test suite for CachedWebSearchTool."""

    def test_init(self, mock_cache):
        """Test initialization of CachedWebSearchTool."""
        # Execute
        tool = CachedWebSearchTool(
            allowed_domains=["example.com"],
            blocked_domains=["blocked.com"],
            cache=mock_cache,
        )

        # Verify
        assert tool.allowed_domains == ["example.com"]
        assert tool.blocked_domains == ["blocked.com"]
        assert tool.cache is mock_cache

    @pytest.mark.asyncio
    async def test_run_cache_hit(self, mock_cache, mock_websearch_tool):
        """Test _run method with a cache hit."""
        # Setup
        cached_result = {
            "search_results": [
                {
                    "title": "Cached Result",
                    "link": "https://example.com/cached",
                    "snippet": "This is a cached result",
                }
            ]
        }
        mock_cache.get.return_value = cached_result

        # Execute
        tool = CachedWebSearchTool(cache=mock_cache)
        result = await tool._run("test query")

        # Verify
        mock_cache.get.assert_called_once_with("test-key")
        mock_websearch_tool.assert_not_called()
        assert result == cached_result

    @pytest.mark.asyncio
    async def test_run_cache_miss(self, mock_cache, mock_websearch_tool):
        """Test _run method with a cache miss."""
        # Setup
        search_result = {
            "search_results": [
                {
                    "title": "Fresh Result",
                    "link": "https://example.com/fresh",
                    "snippet": "This is a fresh result",
                }
            ]
        }
        mock_cache.get.return_value = None
        mock_websearch_tool.return_value = search_result

        # Execute
        tool = CachedWebSearchTool(cache=mock_cache)
        result = await tool._run("test query")

        # Verify
        mock_cache.get.assert_called_once_with("test-key")
        mock_websearch_tool.assert_called_once_with("test query")
        mock_cache.set.assert_called_once()
        assert result == search_result

    @pytest.mark.asyncio
    async def test_run_skip_cache(self, mock_cache, mock_websearch_tool):
        """Test _run method with skip_cache=True."""
        # Setup
        search_result = {
            "search_results": [
                {
                    "title": "Fresh Result",
                    "link": "https://example.com/fresh",
                    "snippet": "This is a fresh result",
                }
            ]
        }
        mock_websearch_tool.return_value = search_result

        # Execute
        tool = CachedWebSearchTool(cache=mock_cache)
        result = await tool._run("test query", skip_cache=True)

        # Verify
        mock_cache.get.assert_not_called()
        mock_websearch_tool.assert_called_once_with("test query")
        assert result == search_result

    @pytest.mark.asyncio
    async def test_run_error_handling(self, mock_cache, mock_websearch_tool):
        """Test _run method with an error in the parent method."""
        # Setup
        mock_websearch_tool.side_effect = Exception("Test error")

        # Execute
        tool = CachedWebSearchTool(cache=mock_cache)
        result = await tool._run("test query")

        # Verify
        assert "error" in result
        assert "status" in result
        assert result["status"] == "error"
        assert "message" in result["error"]
        assert "Test error" in result["error"]["message"]

    def test_determine_content_type(self, mock_cache):
        """Test _determine_content_type method."""
        # Setup
        tool = CachedWebSearchTool(cache=mock_cache)
        search_result = {
            "search_results": [
                {"link": "https://example.com/news"},
                {"link": "https://wikipedia.org/wiki/Test"},
            ]
        }

        # Execute
        content_type = tool._determine_content_type("test query", search_result)

        # Verify
        mock_cache.determine_content_type.assert_called_once_with(
            query="test query", domains=["example.com", "wikipedia.org"]
        )
        assert content_type == ContentType.DAILY


class TestWebToolsUtilities:
    """Test suite for web_tools utility functions."""

    @pytest.mark.asyncio
    async def test_get_web_cache_stats(self, mock_cache):
        """Test get_web_cache_stats function."""
        # Setup
        with patch("tripsage.tools.web_tools.web_cache", mock_cache):
            # Execute
            stats = await get_web_cache_stats("24h")

            # Verify
            mock_cache.get_stats.assert_called_once_with("24h")
            assert stats.cache_hits == 10
            assert stats.cache_misses == 5
            assert stats.hit_ratio == 10 / 15  # hits / (hits + misses)
            assert stats.key_count == 15
            assert stats.size_mb == 1.0  # 1MB
            assert stats.time_window == "24h"

    @pytest.mark.asyncio
    async def test_invalidate_web_cache_for_query(self, mock_cache):
        """Test invalidate_web_cache_for_query function."""
        # Setup
        with patch("tripsage.tools.web_tools.web_cache", mock_cache):
            # Execute
            count = await invalidate_web_cache_for_query("test query")

            # Verify
            mock_cache.invalidate_pattern.assert_called_once()
            assert "*" in mock_cache.invalidate_pattern.call_args[0][0]
            assert count == 3  # Mock returns 3

    @pytest.mark.asyncio
    async def test_web_cached_decorator(self, mock_cache):
        """Test web_cached decorator."""
        # Setup
        with patch("tripsage.tools.web_tools.web_cache", mock_cache):
            # Define a test function
            @web_cached(content_type=ContentType.STATIC)
            async def test_func(arg1, arg2):
                return f"{arg1} {arg2}"

            # Execute
            # Just verify it's callable, the actual caching behavior is
            # tested in the WebOperationsCache tests
            assert callable(test_func)
