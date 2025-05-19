"""Accommodation MCP client implementation."""

from tripsage.clients.base import BaseMCPClient
from tripsage.tools.schemas.accommodations import (
    AccommodationBookingRequest,
    AccommodationBookingResponse,
    AccommodationSearchRequest,
    AccommodationSearchResponse,
)


class AccommodationMCPClient(
    BaseMCPClient[AccommodationSearchRequest, AccommodationSearchResponse]
):
    """Client for Accommodation MCP services."""

    async def search_accommodations(
        self, request: AccommodationSearchRequest
    ) -> AccommodationSearchResponse:
        """Search for accommodations.

        Args:
            request: The accommodation search request.

        Returns:
            Accommodation search results.
        """
        return await self.call_mcp("search", request)

    async def book_accommodation(
        self, request: AccommodationBookingRequest
    ) -> AccommodationBookingResponse:
        """Book an accommodation.

        Args:
            request: The accommodation booking request.

        Returns:
            Accommodation booking confirmation.
        """
        return await self.call_mcp("book", request)
