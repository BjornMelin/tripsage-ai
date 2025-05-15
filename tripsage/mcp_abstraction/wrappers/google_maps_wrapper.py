"""
Google Maps MCP Wrapper implementation.

This wrapper provides a standardized interface for the Google Maps MCP client,
mapping user-friendly method names to actual Google Maps MCP client methods.
"""

from typing import Dict, List

from tripsage.clients.maps.google_maps_mcp_client import GoogleMapsMCPClient
from tripsage.config.mcp_settings import mcp_settings
from tripsage.mcp_abstraction.base_wrapper import BaseMCPWrapper


class GoogleMapsMCPWrapper(BaseMCPWrapper):
    """Wrapper for the Google Maps MCP client."""

    def __init__(
        self, client: GoogleMapsMCPClient = None, mcp_name: str = "google_maps"
    ):
        """
        Initialize the Google Maps MCP wrapper.

        Args:
            client: Optional pre-initialized client, will create one if None
            mcp_name: Name identifier for this MCP service
        """
        if client is None:
            # Create client from configuration
            config = mcp_settings.google_maps
            client = GoogleMapsMCPClient(
                endpoint=str(config.url),
                api_key=config.api_key.get_secret_value() if config.api_key else None,
            )
        super().__init__(client, mcp_name)

    def _build_method_map(self) -> Dict[str, str]:
        """
        Build mapping from standardized method names to actual client methods.

        Returns:
            Dictionary mapping standard names to actual client method names
        """
        return {
            # Geocoding
            "geocode": "geocode",
            "geocode_address": "geocode",
            "reverse_geocode": "reverse_geocode",
            "get_address_from_coordinates": "reverse_geocode",
            # Place search and details
            "search_places": "place_search",
            "place_search": "place_search",
            "find_places": "place_search",
            "get_place_details": "place_details",
            "place_details": "place_details",
            # Directions and routing
            "get_directions": "directions",
            "directions": "directions",
            "route": "directions",
            # Distance and time
            "distance_matrix": "distance_matrix",
            "get_distance": "distance_matrix",
            # Elevation
            "get_elevation": "elevation",
            "elevation": "elevation",
            # Timezone
            "get_timezone": "timezone",
            "timezone": "timezone",
        }

    def get_available_methods(self) -> List[str]:
        """
        Get list of available standardized method names.

        Returns:
            List of available method names
        """
        return list(self._method_map.keys())
