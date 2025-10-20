"""Airbnb MCP Client implementation.

This client provides the interface for interacting with the OpenBnB MCP Server
for Airbnb accommodation searches and listing details.
"""

import asyncio
from typing import Any

import httpx
from pydantic import BaseModel, Field

from tripsage_core.utils.logging_utils import get_logger


logger = get_logger(__name__)


class AirbnbSearchParams(BaseModel):
    """Parameters for Airbnb search."""

    location: str = Field(..., description="Location to search")
    placeId: str | None = Field(None, description="Specific place ID")
    checkin: str | None = Field(None, description="Check-in date (YYYY-MM-DD)")
    checkout: str | None = Field(None, description="Check-out date (YYYY-MM-DD)")
    adults: int | None = Field(1, description="Number of adults")
    children: int | None = Field(0, description="Number of children")
    infants: int | None = Field(0, description="Number of infants")
    pets: int | None = Field(0, description="Number of pets")
    minPrice: int | None = Field(None, description="Minimum price per night")
    maxPrice: int | None = Field(None, description="Maximum price per night")
    cursor: str | None = Field(None, description="Pagination cursor")
    ignoreRobotsText: bool | None = Field(
        False, description="Ignore robots.txt (development only)"
    )


class AirbnbListingDetailsParams(BaseModel):
    """Parameters for fetching Airbnb listing details."""

    id: str = Field(..., description="Listing ID")
    checkin: str | None = Field(None, description="Check-in date for pricing")
    checkout: str | None = Field(None, description="Check-out date for pricing")
    adults: int | None = Field(1, description="Number of adults for pricing")
    children: int | None = Field(0, description="Number of children for pricing")
    infants: int | None = Field(0, description="Number of infants for pricing")
    pets: int | None = Field(0, description="Number of pets for pricing")


class AirbnbMCPClient:
    """Client for interacting with the Airbnb MCP Server (OpenBnB)."""

    def __init__(
        self,
        endpoint: str = "http://localhost:3000",
        timeout: int = 30,
        use_cache: bool = True,
        cache_ttl: int = 1800,  # 30 minutes
    ):
        """Initialize the Airbnb MCP client.

        Args:
            endpoint: The MCP server endpoint URL
            timeout: Request timeout in seconds
            use_cache: Whether to use caching
            cache_ttl: Cache time-to-live in seconds
        """
        self.endpoint = endpoint.rstrip("/")
        self.timeout = timeout
        self.use_cache = use_cache
        self.cache_ttl = cache_ttl
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()

    async def connect(self):
        """Connect to the MCP server."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.endpoint, timeout=self.timeout
            )
            logger.info(f"Connected to Airbnb MCP server at {self.endpoint}")

    async def disconnect(self):
        """Disconnect from the MCP server."""
        if self._client:
            await self._client.aclose()
            self._client = None
            logger.info("Disconnected from Airbnb MCP server")

    async def _invoke_tool(
        self, tool_name: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Invoke a tool on the MCP server.

        Args:
            tool_name: Name of the tool to invoke
            params: Parameters for the tool

        Returns:
            The tool's response

        Raises:
            httpx.HTTPError: If the request fails
            ValueError: If the response is invalid
        """
        if not self._client:
            await self.connect()

        try:
            response = await self._client.post(
                "/invoke",
                json={"tool": tool_name, "params": params},
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()

            result = response.json()
            if "error" in result:
                raise ValueError(f"MCP server error: {result['error']}")

            return result.get("result", {})

        except httpx.HTTPError as e:
            logger.error(f"HTTP error invoking {tool_name}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error invoking {tool_name}: {e}")
            raise

    async def search_accommodations(
        self,
        location: str,
        checkin: str | None = None,
        checkout: str | None = None,
        adults: int = 1,
        children: int = 0,
        infants: int = 0,
        pets: int = 0,
        min_price: int | None = None,
        max_price: int | None = None,
        cursor: str | None = None,
    ) -> list[dict[str, Any]]:
        """Search for Airbnb accommodations.

        Args:
            location: Location to search
            checkin: Check-in date (YYYY-MM-DD)
            checkout: Check-out date (YYYY-MM-DD)
            adults: Number of adults
            children: Number of children
            infants: Number of infants
            pets: Number of pets
            min_price: Minimum price per night
            max_price: Maximum price per night
            cursor: Pagination cursor

        Returns:
            List of accommodation listings
        """
        params = AirbnbSearchParams(
            location=location,
            checkin=checkin,
            checkout=checkout,
            adults=adults,
            children=children,
            infants=infants,
            pets=pets,
            minPrice=min_price,
            maxPrice=max_price,
            cursor=cursor,
        )

        logger.info(f"Searching Airbnb accommodations in {location}")
        result = await self._invoke_tool(
            "airbnb_search", params.model_dump(exclude_none=True)
        )

        listings = result.get("listings", [])
        logger.info(f"Found {len(listings)} Airbnb listings")

        return listings

    async def get_listing_details(
        self,
        listing_id: str,
        checkin: str | None = None,
        checkout: str | None = None,
        adults: int = 1,
        children: int = 0,
        infants: int = 0,
        pets: int = 0,
    ) -> dict[str, Any]:
        """Get detailed information for a specific Airbnb listing.

        Args:
            listing_id: The Airbnb listing ID
            checkin: Check-in date for pricing accuracy
            checkout: Check-out date for pricing accuracy
            adults: Number of adults for pricing
            children: Number of children for pricing
            infants: Number of infants for pricing
            pets: Number of pets for pricing

        Returns:
            Detailed listing information
        """
        params = AirbnbListingDetailsParams(
            id=listing_id,
            checkin=checkin,
            checkout=checkout,
            adults=adults,
            children=children,
            infants=infants,
            pets=pets,
        )

        logger.info(f"Fetching details for Airbnb listing {listing_id}")
        result = await self._invoke_tool(
            "airbnb_listing_details", params.model_dump(exclude_none=True)
        )

        return result

    async def batch_search(
        self, search_requests: list[dict[str, Any]]
    ) -> list[list[dict[str, Any]]]:
        """Perform multiple searches in parallel.

        Args:
            search_requests: List of search parameter dictionaries

        Returns:
            List of search results for each request
        """
        tasks = [self.search_accommodations(**request) for request in search_requests]
        return await asyncio.gather(*tasks)

    async def batch_get_details(
        self, detail_requests: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Get details for multiple listings in parallel.

        Args:
            detail_requests: List of detail request parameter dictionaries

        Returns:
            List of listing details
        """
        tasks = [self.get_listing_details(**request) for request in detail_requests]
        return await asyncio.gather(*tasks)

    def is_connected(self) -> bool:
        """Check if the client is connected to the MCP server."""
        return self._client is not None

    async def health_check(self) -> bool:
        """Check if the MCP server is healthy and responding.

        Returns:
            True if the server is healthy, False otherwise
        """
        try:
            if not self._client:
                await self.connect()

            response = await self._client.get("/health")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
