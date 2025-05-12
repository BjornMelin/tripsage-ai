"""
WebCrawl MCP module for the TripSage travel planning system.

This module provides a client for the WebCrawl MCP server, which offers
web scraping, crawling, searching, and extraction capabilities.
"""

from .client import WebCrawlMCPClient
from .models import (
    CheckCrawlStatusParams,
    CrawlParams,
    CrawlResponse,
    CrawlStatusResponse,
    DeepResearchParams,
    DeepResearchResponse,
    ExtractParams,
    ExtractResponse,
    GenerateLLMsTxtParams,
    GenerateLLMsTxtResponse,
    MapParams,
    MapResponse,
    ScrapeOptions,
    ScrapeParams,
    ScrapeResponse,
    SearchParams,
    SearchResponse,
    SearchResult,
    WebAction,
)


def get_client() -> WebCrawlMCPClient:
    """Get a configured WebCrawl MCP client.

    Returns:
        A configured WebCrawl MCP client
    """
    return WebCrawlMCPClient()


__all__ = [
    # Client
    "WebCrawlMCPClient",
    "get_client",
    # Parameter models
    "WebAction",
    "ScrapeParams",
    "MapParams",
    "CrawlParams",
    "CheckCrawlStatusParams",
    "ScrapeOptions",
    "SearchParams",
    "ExtractParams",
    "DeepResearchParams",
    "GenerateLLMsTxtParams",
    # Response models
    "ScrapeResponse",
    "MapResponse",
    "CrawlResponse",
    "CrawlStatusResponse",
    "SearchResult",
    "SearchResponse",
    "ExtractResponse",
    "DeepResearchResponse",
    "GenerateLLMsTxtResponse",
]
