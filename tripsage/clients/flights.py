"""Flight MCP client implementation."""

from tripsage.clients.base import BaseMCPClient
from tripsage.tools.schemas.flights import (
    FlightBookingRequest,
    FlightBookingResponse,
    FlightSearchRequest,
    FlightSearchResponse,
)


class FlightMCPClient(BaseMCPClient[FlightSearchRequest, FlightSearchResponse]):
    """Client for Flight MCP services."""

    async def search_flights(
        self, request: FlightSearchRequest
    ) -> FlightSearchResponse:
        """Search for flights.

        Args:
            request: The flight search request.

        Returns:
            Flight search results.
        """
        return await self.call_mcp("search", request)

    async def book_flight(self, request: FlightBookingRequest) -> FlightBookingResponse:
        """Book a flight.

        Args:
            request: The flight booking request.

        Returns:
            Flight booking confirmation.
        """
        return await self.call_mcp("book", request)
