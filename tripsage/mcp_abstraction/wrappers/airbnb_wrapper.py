"""
Airbnb MCP Wrapper implementation.

This wrapper provides a standardized interface for the Airbnb MCP client,
mapping user-friendly method names to actual Airbnb MCP client methods.
"""

from typing import Dict, List

from tripsage.clients.airbnb_mcp_client import AirbnbMCPClient
from tripsage.config.app_settings import settings
from tripsage.mcp_abstraction.base_wrapper import BaseMCPWrapper


class AirbnbMCPWrapper(BaseMCPWrapper):
    """Wrapper for the Airbnb MCP client."""

    def __init__(self, client: AirbnbMCPClient = None, mcp_name: str = "airbnb"):
        """
        Initialize the Airbnb MCP wrapper.

        Args:
            client: Optional pre-initialized client, will create one if None
            mcp_name: Name identifier for this MCP service
        """
        if client is None:
            # Create client from configuration
            config = settings.airbnb
            if config.enabled:
                client = AirbnbMCPClient(
                    endpoint=str(config.url),
                    timeout=config.timeout,
                    use_cache=config.retry_attempts > 0,
                    cache_ttl=config.retry_backoff * 60,  # Convert to seconds
                )
            else:
                raise ValueError("Airbnb MCP is not enabled in configuration")
        super().__init__(client, mcp_name)

    def _build_method_map(self) -> Dict[str, str]:
        """
        Build mapping from standardized method names to actual client methods.

        Returns:
            Dictionary mapping standard names to actual client method names
        """
        return {
            # Search operations
            "search_listings": "search_accommodations",
            "search_accommodations": "search_accommodations",
            "search": "search_accommodations",
            # Listing details
            "get_listing_details": "get_listing_details",
            "get_listing": "get_listing_details",
            "get_details": "get_listing_details",
            "get_accommodation_details": "get_listing_details",
            # Availability operations (part of listing details)
            "check_availability": "get_listing_details",
            "check_listing_availability": "get_listing_details",
        }

    def get_available_methods(self) -> List[str]:
        """
        Get list of available standardized method names.

        Returns:
            List of available method names
        """
        return list(self._method_map.keys())
