"""Wrapper for Google Maps MCP client."""

from typing import Dict, List, Optional

from tripsage.clients.maps.google_maps_mcp_client import GoogleMapsMCPClient
from tripsage.utils.logging import get_module_logger

from ..base_wrapper import BaseMCPWrapper

logger = get_module_logger(__name__)


class GoogleMapsMCPWrapper(BaseMCPWrapper[GoogleMapsMCPClient]):
    """Wrapper for Google Maps MCP client with standardized interface."""

    def __init__(
        self,
        client: Optional[GoogleMapsMCPClient] = None,
        mcp_name: str = "google_maps",
    ):
        """Initialize the Google Maps MCP wrapper.

        Args:
            client: Optional pre-existing client instance
            mcp_name: Unique identifier for this MCP
        """
        if client is None:
            # GoogleMapsMCPClient is typically a singleton
            # so we get the existing instance
            client = GoogleMapsMCPClient.get_client()

        super().__init__(client, mcp_name)

    def _build_method_map(self) -> Dict[str, str]:
        """Build mapping from standardized method names to client methods."""
        return {
            # Core location services
            "geocode": "geocode",
            "reverse_geocode": "reverse_geocode",
            # Place search and details
            "search_places": "search_places",
            "get_place_details": "get_place_details",
            "search_places_nearby": "search_places_nearby",
            "search_places_text": "search_places_text",
            # Directions and routing
            "get_directions": "get_directions",
            "get_distance_matrix": "get_distance_matrix",
            # Additional services
            "get_timezone": "get_timezone",
            "get_elevation": "get_elevation",
            # Photos (if available)
            "get_place_photo": "get_place_photo",
        }

    def get_available_methods(self) -> List[str]:
        """Get list of available methods for this MCP."""
        return list(self._method_map.keys())
