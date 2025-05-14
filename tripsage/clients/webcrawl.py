"""Webcrawl MCP client implementation."""

from typing import Any

from tripsage.clients.base import BaseMCPClient
from tripsage.tools.schemas.webcrawl import (
    WebCrawlRequest,
    WebCrawlResponse,
    WebScrapeRequest,
    WebScrapeResponse,
    WebSearchRequest,
    WebSearchResponse,
)


class WebcrawlMCPClient(BaseMCPClient[Any, Any]):
    """Client for Webcrawl MCP services."""

    async def search(self, request: WebSearchRequest) -> WebSearchResponse:
        """Search the web.

        Args:
            request: The web search request.

        Returns:
            Web search results.
        """
        return await self.call_mcp("search", request)

    async def crawl(self, request: WebCrawlRequest) -> WebCrawlResponse:
        """Crawl web pages.

        Args:
            request: The web crawl request.

        Returns:
            Web crawl results.
        """
        return await self.call_mcp("crawl", request)

    async def scrape(self, request: WebScrapeRequest) -> WebScrapeResponse:
        """Scrape a web page.

        Args:
            request: The web scrape request.

        Returns:
            Web scrape results.
        """
        return await self.call_mcp("scrape", request)
