"""
Crawl4AI MCP Wrapper implementation.

This wrapper provides a standardized interface for the Crawl4AI MCP client,
mapping user-friendly method names to actual Crawl4AI MCP client methods.
"""

from typing import Dict, List

from tripsage.clients.webcrawl.crawl4ai_mcp_client import Crawl4AIMCPClient
from tripsage.mcp_abstraction.base_wrapper import BaseMCPWrapper


class Crawl4AIMCPWrapper(BaseMCPWrapper):
    """Wrapper for the Crawl4AI MCP client."""

    def __init__(self, client: Crawl4AIMCPClient = None, mcp_name: str = "crawl4ai"):
        """
        Initialize the Crawl4AI MCP wrapper.

        Args:
            client: Optional pre-initialized client, will create one if None
            mcp_name: Name identifier for this MCP service
        """
        if client is None:
            # Create client from configuration
            client = Crawl4AIMCPClient()
        super().__init__(client, mcp_name)

    def _build_method_map(self) -> Dict[str, str]:
        """
        Build mapping from standardized method names to actual client methods.

        Returns:
            Dictionary mapping standard names to actual client method names
        """
        return {
            # Primary crawling methods
            "crawl_url": "crawl",
            "crawl_page": "crawl",
            "execute_js": "execute_js",
            "execute_javascript": "execute_js",
            "answer_question": "answer_question",
            "ask_question": "answer_question",
            # Alternative names for crawling
            "extract_content": "crawl",
            "scrape_page": "crawl",
            "process_page": "crawl",
            # JavaScript execution variants
            "run_javascript": "execute_js",
            "inject_js": "execute_js",
            # Question-answering alternatives
            "qa_from_url": "answer_question",
            "query_content": "answer_question",
        }

    def get_available_methods(self) -> List[str]:
        """
        Get list of available standardized method names.

        Returns:
            List of available method names
        """
        return list(self._method_map.keys())
