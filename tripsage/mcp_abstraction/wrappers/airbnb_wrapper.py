"""
Airbnb MCP Wrapper implementation.

This wrapper provides a standardized interface for the Airbnb MCP client.
"""

from typing import List, Optional

from tripsage.clients.airbnb_mcp_client import AirbnbMCPClient
from tripsage.mcp_abstraction.base_wrapper import BaseMCPWrapper
from tripsage_core.config.base_app_settings import settings


class AirbnbMCPWrapper(BaseMCPWrapper):
    """Wrapper for the Airbnb MCP client."""

    def __init__(self, client: Optional[AirbnbMCPClient] = None):
        """
        Initialize the Airbnb MCP wrapper.

        Args:
            client: Optional pre-initialized client, will create one if None
        """
        if client is None:
            # Create client from configuration
            config = settings.airbnb
            if not config.enabled:
                raise ValueError("Airbnb MCP is not enabled in configuration")

            client = AirbnbMCPClient(
                endpoint=str(config.url),
                timeout=config.timeout,
                use_cache=config.retry_attempts > 0,
                cache_ttl=config.retry_backoff * 60,  # Convert to seconds
            )

        super().__init__(client, mcp_name="airbnb")

    def get_available_methods(self) -> List[str]:
        """
        Get list of available method names.

        Returns:
            List of available method names
        """
        return [
            # Search operations
            "search_listings",
            "search_accommodations",
            "search",
            # Listing details
            "get_listing_details",
            "get_listing",
            "get_details",
            "get_accommodation_details",
            # Availability operations
            "check_availability",
            "check_listing_availability",
        ]
