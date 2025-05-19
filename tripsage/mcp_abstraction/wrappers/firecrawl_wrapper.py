"""
Firecrawl MCP Wrapper implementation.

This wrapper provides a standardized interface for the Firecrawl MCP client,
mapping user-friendly method names to actual Firecrawl MCP client methods.
"""

from typing import Dict, List

from tripsage.clients.webcrawl.firecrawl_mcp_client import FirecrawlMCPClient
from tripsage.mcp_abstraction.base_wrapper import BaseMCPWrapper


class FirecrawlMCPWrapper(BaseMCPWrapper):
    """Wrapper for the Firecrawl MCP client."""

    def __init__(self, client: FirecrawlMCPClient = None, mcp_name: str = "firecrawl"):
        """
        Initialize the Firecrawl MCP wrapper.

        Args:
            client: Optional pre-initialized client, will create one if None
            mcp_name: Name identifier for this MCP service
        """
        if client is None:
            # Create client from configuration
            client = FirecrawlMCPClient()
        super().__init__(client, mcp_name)

    def _build_method_map(self) -> Dict[str, str]:
        """
        Build mapping from standardized method names to actual client methods.

        Returns:
            Dictionary mapping standard names to actual client method names
        """
        return {
            # Web scraping and crawling
            "scrape_url": "scrape",
            "scrape_page": "scrape",
            "crawl_website": "crawl",
            "crawl_site": "crawl",
            "extract_data": "extract",
            "extract_structured_data": "extract",
            "deep_research": "deep_research",
            "research_topic": "deep_research",
            # Alternative common names
            "web_scrape": "scrape",
            "website_crawl": "crawl",
            "parse_data": "extract",
        }

    def get_available_methods(self) -> List[str]:
        """
        Get list of available standardized method names.

        Returns:
            List of available method names
        """
        return list(self._method_map.keys())
