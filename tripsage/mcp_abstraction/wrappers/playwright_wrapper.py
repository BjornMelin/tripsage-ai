"""
Playwright MCP Wrapper implementation.

This wrapper provides a standardized interface for the Playwright MCP client,
mapping user-friendly method names to actual Playwright MCP client methods.
"""

from typing import Dict, List

from tripsage.mcp_abstraction.base_wrapper import BaseMCPWrapper
from tripsage.tools.browser.playwright_mcp_client import PlaywrightMCPClient


class PlaywrightMCPWrapper(BaseMCPWrapper):
    """Wrapper for the Playwright MCP client."""

    def __init__(
        self, client: PlaywrightMCPClient = None, mcp_name: str = "playwright"
    ):
        """
        Initialize the Playwright MCP wrapper.

        Args:
            client: Optional pre-initialized client, will create one if None
            mcp_name: Name identifier for this MCP service
        """
        if client is None:
            # Create client from configuration
            client = PlaywrightMCPClient()
        super().__init__(client, mcp_name)

    def _build_method_map(self) -> Dict[str, str]:
        """
        Build mapping from standardized method names to actual client methods.

        Returns:
            Dictionary mapping standard names to actual client method names
        """
        return {
            # Navigation
            "navigate": "navigate",
            # Content extraction
            "get_visible_text": "get_visible_text",
            "get_visible_html": "get_visible_html",
            # Screenshots
            "take_screenshot": "take_screenshot",
            # Interactions
            "click": "click",
            "fill": "fill",
            # Session management
            "close": "close",
            # General execution
            "execute_command": "execute_raw_command",
        }

    def get_available_methods(self) -> List[str]:
        """
        Get list of available standardized method names.

        Returns:
            List of available method names
        """
        return list(self._method_map.keys())
