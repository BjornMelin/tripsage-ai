"""Test the source selection logic in WebCrawl MCP."""

import asyncio

# Add project root to Python path
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from src.mcp.webcrawl.handlers.extract_handler import (
    _extract_with_fallback,
    _select_source,
)
from src.mcp.webcrawl.sources.crawl4ai_source import Crawl4AISource
from src.mcp.webcrawl.sources.playwright_source import PlaywrightSource


class TestSourceSelection(unittest.TestCase):
    """Test the source selection logic in WebCrawl MCP."""

    def test_select_source_for_standard_site(self):
        """Test source selection for a standard website."""
        source = _select_source("https://example.com/travel/guide")
        self.assertIsInstance(source, Crawl4AISource)
        self.assertNotIsInstance(source, PlaywrightSource)

    def test_select_source_for_dynamic_site(self):
        """Test source selection for a dynamic website."""
        source = _select_source("https://booking.com/hotel/123")
        self.assertIsInstance(source, PlaywrightSource)
        self.assertNotIsInstance(source, Crawl4AISource)

    def test_select_source_for_authenticated_site(self):
        """Test source selection for a site requiring authentication."""
        source = _select_source("https://booking.com/reservations/123")
        self.assertIsInstance(source, PlaywrightSource)
        self.assertNotIsInstance(source, Crawl4AISource)

    def test_select_source_for_interactive_site(self):
        """Test source selection for an interactive site."""
        source = _select_source("https://airbnb.com/rooms/123")
        self.assertIsInstance(source, PlaywrightSource)
        self.assertNotIsInstance(source, Crawl4AISource)

    @patch(
        "src.mcp.webcrawl.sources.crawl4ai_source.Crawl4AISource.extract_page_content"
    )
    @patch(
        "src.mcp.webcrawl.sources.playwright_source.PlaywrightSource.extract_page_content"
    )
    @patch("src.mcp.webcrawl.handlers.extract_handler._select_source")
    async def test_fallback_to_playwright(
        self, mock_select, mock_playwright, mock_crawl4ai
    ):
        """Test fallback from Crawl4AI to Playwright."""
        # Mock _select_source to return Crawl4AI
        mock_select.return_value = Crawl4AISource()

        # Mock Crawl4AI to fail
        mock_crawl4ai.side_effect = Exception("Crawl4AI failed")

        # Mock Playwright to succeed
        mock_playwright.return_value = {
            "url": "test",
            "title": "Test",
            "content": "test content",
            "format": "text",
        }

        # Call fallback method
        options = {"format": "text"}
        result = await _extract_with_fallback("https://example.com", options)

        # Verify Playwright was called
        mock_playwright.assert_called_once()

        # Verify result is formatted correctly
        self.assertEqual(result["url"], "test")
        self.assertEqual(result["content"], "test content")

    @patch(
        "src.mcp.webcrawl.sources.crawl4ai_source.Crawl4AISource.extract_page_content"
    )
    @patch(
        "src.mcp.webcrawl.sources.playwright_source.PlaywrightSource.extract_page_content"
    )
    @patch("src.mcp.webcrawl.handlers.extract_handler._select_source")
    async def test_fallback_to_crawl4ai(
        self, mock_select, mock_playwright, mock_crawl4ai
    ):
        """Test fallback from Playwright to Crawl4AI."""
        # Mock _select_source to return Playwright
        mock_select.return_value = PlaywrightSource()

        # Mock Playwright to fail
        mock_playwright.side_effect = Exception("Playwright failed")

        # Mock Crawl4AI to succeed
        mock_crawl4ai.return_value = {
            "url": "test",
            "title": "Test",
            "content": "test content",
            "format": "text",
        }

        # Call fallback method
        options = {"format": "text"}
        result = await _extract_with_fallback("https://example.com", options)

        # Verify Crawl4AI was called
        mock_crawl4ai.assert_called_once()

        # Verify result is formatted correctly
        self.assertEqual(result["url"], "test")
        self.assertEqual(result["content"], "test content")


if __name__ == "__main__":
    # Run async tests
    loop = asyncio.get_event_loop()
    unittest.main(exit=False)
    loop.close()
