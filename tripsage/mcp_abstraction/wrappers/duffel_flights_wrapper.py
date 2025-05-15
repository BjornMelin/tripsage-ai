"""
Duffel Flights MCP Wrapper implementation.

This wrapper provides a standardized interface for the Duffel Flights MCP client,
mapping user-friendly method names to actual Duffel Flights MCP client methods.
"""

from typing import Dict, List

from src.mcp.flights.client import FlightsMCPClient
from tripsage.config.mcp_settings import mcp_settings
from tripsage.mcp_abstraction.base_wrapper import BaseMCPWrapper


class DuffelFlightsMCPWrapper(BaseMCPWrapper):
    """Wrapper for the Duffel Flights MCP client."""

    def __init__(
        self, client: FlightsMCPClient = None, mcp_name: str = "duffel_flights"
    ):
        """
        Initialize the Duffel Flights MCP wrapper.

        Args:
            client: Optional pre-initialized client, will create one if None
            mcp_name: Name identifier for this MCP service
        """
        if client is None:
            # Create client from configuration
            config = mcp_settings.duffel_flights
            if config.enabled:
                client = FlightsMCPClient(
                    endpoint=str(config.url),
                    api_key=(
                        config.api_key.get_secret_value() if config.api_key else None
                    ),
                    timeout=config.timeout,
                    use_cache=config.retry_attempts > 0,
                    cache_ttl=config.retry_backoff * 60,  # Convert to seconds
                    server_name="Duffel Flights",
                )
            else:
                raise ValueError("Duffel Flights MCP is not enabled in configuration")
        super().__init__(client, mcp_name)

    def _build_method_map(self) -> Dict[str, str]:
        """
        Build mapping from standardized method names to actual client methods.

        Returns:
            Dictionary mapping standard names to actual client method names
        """
        return {
            # Search operations
            "search_flights": "search_flights",
            "search_flight_offers": "search_flights",
            "search_multi_city": "search_multi_city",
            # Airport operations
            "get_airports": "get_airports",
            "search_airports": "get_airports",
            # Offer operations
            "get_offer_details": "get_offer_details",
            "get_flight_offer": "get_offer_details",
            # Price operations
            "get_flight_prices": "get_flight_prices",
            "get_price_history": "get_flight_prices",
            "track_prices": "track_prices",
            "track_flight_prices": "track_prices",
            # Booking operations (may not be supported by ravinahp/flights-mcp)
            "create_order": "create_order",
            "book_flight": "create_order",
            "book_order": "create_order",
            "create_order_quote": "create_order",
            # Order operations
            "get_order": "get_order",
            "get_order_details": "get_order",
        }

    def get_available_methods(self) -> List[str]:
        """
        Get list of available standardized method names.

        Returns:
            List of available method names
        """
        return list(self._method_map.keys())
