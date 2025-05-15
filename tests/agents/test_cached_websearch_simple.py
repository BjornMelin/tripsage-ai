"""
Simplified tests for CachedWebSearchTool integration.

This module tests the basic functionality of CachedWebSearchTool
without requiring the full settings infrastructure.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents import WebSearchTool
from tripsage.tools.web_tools import CachedWebSearchTool
from tripsage.utils.cache import ContentType


class TestCachedWebSearchSimple:
    """Simple tests for cached web search."""

    def test_cached_websearch_inherits_from_websearch(self):
        """Test that CachedWebSearchTool inherits from WebSearchTool."""
        assert issubclass(CachedWebSearchTool, WebSearchTool)

    @patch("tripsage.tools.web_tools.web_cache")
    def test_cached_websearch_initialization(self, mock_cache):
        """Test that CachedWebSearchTool can be initialized."""
        # Create the tool
        tool = CachedWebSearchTool()

        # Verify it has the expected attributes
        assert hasattr(tool, "cache")
        assert hasattr(tool, "user_location")
        assert hasattr(tool, "search_context_size")

        # Verify default values
        assert tool.user_location is None
        assert tool.search_context_size == "medium"

    @pytest.mark.asyncio
    @patch("tripsage.tools.web_tools.web_cache")
    async def test_cached_websearch_cache_hit(self, mock_cache):
        """Test that CachedWebSearchTool returns cached results when available."""
        # Mock cache to return a cached result
        mock_cache.get = AsyncMock(return_value={"cached": True})
        mock_cache.generate_cache_key = MagicMock(return_value="test_key")

        # Create the tool
        tool = CachedWebSearchTool(cache=mock_cache)

        # Mock the parent _run method
        with patch.object(WebSearchTool, "_run") as mock_parent_run:
            # Run a search
            result = await tool._run("test query")

            # Verify cache was checked
            mock_cache.get.assert_called_once()

            # Verify parent _run was NOT called (cache hit)
            mock_parent_run.assert_not_called()

            # Verify result is from cache
            assert result == {"cached": True}

    @pytest.mark.asyncio
    @patch("tripsage.tools.web_tools.web_cache")
    async def test_cached_websearch_cache_miss(self, mock_cache):
        """Test that CachedWebSearchTool calls parent when cache miss."""
        # Mock cache to return None (cache miss)
        mock_cache.get = AsyncMock(return_value=None)
        mock_cache.set = AsyncMock()
        mock_cache.generate_cache_key = MagicMock(return_value="test_key")
        mock_cache.determine_content_type = MagicMock(return_value=ContentType.DAILY)

        # Create the tool
        tool = CachedWebSearchTool(cache=mock_cache)

        # Mock the parent _run method
        with patch.object(
            WebSearchTool, "_run", new_callable=AsyncMock
        ) as mock_parent_run:
            mock_parent_run.return_value = {"search_results": ["test"]}

            # Run a search
            result = await tool._run("test query")

            # Verify cache was checked
            mock_cache.get.assert_called_once()

            # Verify parent _run WAS called (cache miss)
            mock_parent_run.assert_called_once_with("test query")

            # Verify result was cached
            mock_cache.set.assert_called_once()

            # Verify result is from parent
            assert result == {"search_results": ["test"]}

    @pytest.mark.asyncio
    @patch("tripsage.tools.web_tools.web_cache")
    async def test_cached_websearch_skip_cache(self, mock_cache):
        """Test that CachedWebSearchTool skips cache when requested."""
        # Create the tool
        tool = CachedWebSearchTool(cache=mock_cache)

        # Mock the parent _run method
        with patch.object(
            WebSearchTool, "_run", new_callable=AsyncMock
        ) as mock_parent_run:
            mock_parent_run.return_value = {"search_results": ["test"]}

            # Run a search with skip_cache=True
            result = await tool._run("test query", skip_cache=True)

            # Verify cache was NOT checked
            mock_cache.get.assert_not_called()

            # Verify parent _run WAS called
            mock_parent_run.assert_called_once_with("test query", skip_cache=True)

            # Verify result was NOT cached
            mock_cache.set.assert_not_called()

            # Verify result is from parent
            assert result == {"search_results": ["test"]}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
