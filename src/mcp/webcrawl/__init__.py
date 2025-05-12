"""
WebCrawl MCP module for the TripSage travel planning system.

This module provides a client for accessing web crawling capabilities through
external MCPs (Crawl4AI and Firecrawl) rather than a custom server implementation.
"""

from .client import WebCrawlMCPClient
from .models import (
    ExtractParams,
    ExtractResponse,
    ScrapeOptions,
    ScrapeParams,
    ScrapeResponse,
    SearchParams,
    SearchResponse,
)


def get_client() -> WebCrawlMCPClient:
    """Get a configured WebCrawl MCP client.

    Returns:
        A configured WebCrawl MCP client
    """
    from .client import webcrawl_client
    return webcrawl_client


__all__ = [
    # Client
    "WebCrawlMCPClient",
    "get_client",
    # Common parameter models
    "ScrapeOptions",
    "ScrapeParams",
    "SearchParams",
    "ExtractParams",
    # Common response models
    "ScrapeResponse",
    "SearchResponse",
    "ExtractResponse",
]