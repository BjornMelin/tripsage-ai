"""
Web Search Tool MCP Wrapper implementation.

This wrapper provides a standardized interface for the CachedWebSearchTool,
mapping user-friendly method names to the tool's search method.
"""

from typing import Dict, List

from tripsage.mcp_abstraction.base_wrapper import BaseMCPWrapper
from tripsage.tools.web_tools import CachedWebSearchTool


class CachedWebSearchToolWrapper(BaseMCPWrapper):
    """Wrapper for the CachedWebSearchTool."""

    def __init__(
        self, client: CachedWebSearchTool = None, mcp_name: str = "web_search"
    ):
        """
        Initialize the Web Search Tool wrapper.

        Args:
            client: Optional pre-initialized tool, will create one if None
            mcp_name: Name identifier for this MCP service
        """
        if client is None:
            # Create client from configuration
            client = CachedWebSearchTool()
        super().__init__(client, mcp_name)

    def _build_method_map(self) -> Dict[str, str]:
        """
        Build mapping from standardized method names to actual tool methods.

        Returns:
            Dictionary mapping standard names to actual client method names
        """
        return {
            # Primary search method
            "perform_search": "__call__",  # WebSearchTool uses __call__ method
            "search": "__call__",
            "web_search": "__call__",
            "search_web": "__call__",
            # Alternative names for search operations
            "query": "__call__",
            "lookup": "__call__",
            "find": "__call__",
            "internet_search": "__call__",
            "google": "__call__",  # Common colloquial name
            "search_online": "__call__",
        }

    def get_available_methods(self) -> List[str]:
        """
        Get list of available standardized method names.

        Returns:
            List of available method names
        """
        return list(self._method_map.keys())
