"""
WebCrawl MCP module
"""

from .client import WebCrawlMCPClient


def get_client() -> WebCrawlMCPClient:
    """Get a configured WebCrawl MCP client.

    Returns:
        A configured WebCrawl MCP client
    """
    return WebCrawlMCPClient()
