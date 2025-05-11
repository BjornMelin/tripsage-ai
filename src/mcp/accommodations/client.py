"""
Airbnb MCP client for the TripSage travel planning system.

This module provides a client for the Airbnb MCP server, which allows searching
for accommodations and retrieving detailed listing information.
"""

from datetime import date
from typing import Any, Dict, Optional, Union

from ...utils.config import get_config
from ...utils.error_handling import MCPError
from ...utils.logging import get_module_logger
from ..base_mcp_client import BaseMCPClient

logger = get_module_logger(__name__)
config = get_config()


class AirbnbMCPClient(BaseMCPClient):
    """Client for the Airbnb MCP server."""

    def __init__(
        self,
        endpoint: str = "http://localhost:3000",
        timeout: float = 60.0,
        use_cache: bool = True,
        cache_ttl: int = 3600,  # 1 hour default
    ):
        """Initialize the Airbnb MCP client.

        Args:
            endpoint: MCP server endpoint URL
            timeout: Request timeout in seconds
            use_cache: Whether to use caching
            cache_ttl: Cache TTL in seconds
        """
        super().__init__(
            endpoint=endpoint,
            api_key=None,  # Airbnb MCP doesn't use API keys
            timeout=timeout,
            use_cache=use_cache,
            cache_ttl=cache_ttl,
        )
        logger.debug("Initialized Airbnb MCP client")

    async def search_accommodations(
        self,
        location: str,
        place_id: Optional[str] = None,
        checkin: Optional[Union[str, date]] = None,
        checkout: Optional[Union[str, date]] = None,
        adults: Optional[int] = None,
        children: Optional[int] = None,
        infants: Optional[int] = None,
        pets: Optional[int] = None,
        min_price: Optional[int] = None,
        max_price: Optional[int] = None,
        cursor: Optional[str] = None,
        ignore_robots_txt: bool = False,
        skip_cache: bool = False,
    ) -> Dict[str, Any]:
        """Search for Airbnb listings based on location and filters.

        Args:
            location: Location to search for
            place_id: Google Maps place ID
            checkin: Check-in date (YYYY-MM-DD)
            checkout: Check-out date (YYYY-MM-DD)
            adults: Number of adults
            children: Number of children
            infants: Number of infants
            pets: Number of pets
            min_price: Minimum price
            max_price: Maximum price
            cursor: Pagination cursor
            ignore_robots_txt: Whether to ignore robots.txt
            skip_cache: Whether to skip the cache

        Returns:
            Search results containing listings with details

        Raises:
            MCPError: If the search fails
        """
        # Convert date objects to strings if needed
        if isinstance(checkin, date):
            checkin = checkin.isoformat()
        if isinstance(checkout, date):
            checkout = checkout.isoformat()

        # Prepare parameters
        params = {
            "location": location,
        }

        # Add optional parameters if provided
        if place_id:
            params["placeId"] = place_id
        if checkin:
            params["checkin"] = checkin
        if checkout:
            params["checkout"] = checkout
        if adults is not None:
            params["adults"] = adults
        if children is not None:
            params["children"] = children
        if infants is not None:
            params["infants"] = infants
        if pets is not None:
            params["pets"] = pets
        if min_price is not None:
            params["minPrice"] = min_price
        if max_price is not None:
            params["maxPrice"] = max_price
        if cursor:
            params["cursor"] = cursor
        if ignore_robots_txt:
            params["ignoreRobotsText"] = ignore_robots_txt

        try:
            logger.info(
                "Searching Airbnb accommodations in %s with filters: %s",
                location,
                {k: v for k, v in params.items() if k != "location"},
            )

            # Call the airbnb_search tool
            result = await self.call_tool("airbnb_search", params, skip_cache)

            logger.info(
                "Found %s Airbnb listings in %s",
                len(result.get("listings", [])),
                location,
            )

            return result
        except Exception as e:
            logger.error("Airbnb accommodation search failed: %s", str(e))
            raise MCPError(
                message=f"Airbnb accommodation search failed: {str(e)}",
                server=self.endpoint,
                tool="airbnb_search",
                params=params,
            )

    async def get_listing_details(
        self,
        listing_id: str,
        checkin: Optional[Union[str, date]] = None,
        checkout: Optional[Union[str, date]] = None,
        adults: Optional[int] = None,
        children: Optional[int] = None,
        infants: Optional[int] = None,
        pets: Optional[int] = None,
        ignore_robots_txt: bool = False,
        skip_cache: bool = False,
    ) -> Dict[str, Any]:
        """Get detailed information about a specific Airbnb listing.

        Args:
            listing_id: Airbnb listing ID
            checkin: Check-in date (YYYY-MM-DD)
            checkout: Check-out date (YYYY-MM-DD)
            adults: Number of adults
            children: Number of children
            infants: Number of infants
            pets: Number of pets
            ignore_robots_txt: Whether to ignore robots.txt
            skip_cache: Whether to skip the cache

        Returns:
            Detailed listing information

        Raises:
            MCPError: If the request fails
        """
        # Convert date objects to strings if needed
        if isinstance(checkin, date):
            checkin = checkin.isoformat()
        if isinstance(checkout, date):
            checkout = checkout.isoformat()

        # Prepare parameters
        params = {
            "id": listing_id,
        }

        # Add optional parameters if provided
        if checkin:
            params["checkin"] = checkin
        if checkout:
            params["checkout"] = checkout
        if adults is not None:
            params["adults"] = adults
        if children is not None:
            params["children"] = children
        if infants is not None:
            params["infants"] = infants
        if pets is not None:
            params["pets"] = pets
        if ignore_robots_txt:
            params["ignoreRobotsText"] = ignore_robots_txt

        try:
            logger.info("Getting details for Airbnb listing %s", listing_id)

            # Call the airbnb_listing_details tool
            result = await self.call_tool("airbnb_listing_details", params, skip_cache)

            logger.info(
                "Successfully retrieved details for Airbnb listing %s", listing_id
            )

            return result
        except Exception as e:
            logger.error("Failed to get Airbnb listing details: %s", str(e))
            raise MCPError(
                message=f"Failed to get Airbnb listing details: {str(e)}",
                server=self.endpoint,
                tool="airbnb_listing_details",
                params=params,
            )
