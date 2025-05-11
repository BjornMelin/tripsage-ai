"""
Google Maps MCP client for the TripSage travel planning system.

This module provides a client for the Google Maps MCP server, which allows searching
for places, calculating routes, and retrieving map information.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from ...cache.redis_cache import redis_cache
from ...utils.config import get_config
from ...utils.error_handling import MCPError, log_exception
from ...utils.logging import get_module_logger
from ..base_mcp_client import BaseMCPClient

logger = get_module_logger(__name__)
config = get_config()


class GoogleMapsMCPClient(BaseMCPClient):
    """Client for the Google Maps MCP server."""

    def __init__(
        self,
        endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: float = 60.0,
        use_cache: bool = True,
        cache_ttl: Optional[int] = None,
    ):
        """Initialize the Google Maps MCP client.

        Args:
            endpoint: MCP server endpoint URL (defaults to config value)
            api_key: API key for authentication (if required)
            timeout: Request timeout in seconds
            use_cache: Whether to use caching
            cache_ttl: Cache TTL in seconds (None means default TTL)
        """
        endpoint = endpoint or config.get(
            "mcp.googlemaps.endpoint", "http://localhost:3101"
        )
        api_key = api_key or config.get("mcp.googlemaps.api_key")

        super().__init__(
            endpoint=endpoint,
            api_key=api_key,
            timeout=timeout,
            use_cache=use_cache,
            cache_ttl=cache_ttl,
        )

        logger.debug("Initialized Google Maps MCP client for %s", endpoint)

    @redis_cache.cached("geocode", 86400)  # Cache for 24 hours
    async def geocode(
        self,
        address: str,
        skip_cache: bool = False,
    ) -> Dict[str, Any]:
        """Geocode an address to get coordinates.

        Args:
            address: Address to geocode
            skip_cache: Whether to skip the cache

        Returns:
            Geocoded result with coordinates and address components
        """
        params = {"address": address}

        try:
            # Call the geocode tool
            result = await self.call_tool("geocode", params, skip_cache=skip_cache)
            return result
        except Exception as e:
            logger.error("Error in geocoding: %s", str(e))
            log_exception(e)

            if isinstance(e, MCPError):
                raise

            raise MCPError(
                message=f"Geocoding failed: {str(e)}",
                server=self.endpoint,
                tool="geocode",
                params=params,
            )

    @redis_cache.cached("place_search", 3600)  # Cache for 1 hour
    async def place_search(
        self,
        query: str,
        location: Optional[str] = None,
        lat: Optional[float] = None,
        lng: Optional[float] = None,
        radius: Optional[int] = None,
        type: Optional[str] = None,
        skip_cache: bool = False,
    ) -> Dict[str, Any]:
        """Search for places based on a query.

        Args:
            query: Search query
            location: Location string (e.g., "New York, NY")
            lat: Latitude (alternative to location)
            lng: Longitude (alternative to location)
            radius: Search radius in meters
            type: Place type filter
            skip_cache: Whether to skip the cache

        Returns:
            Search results with places matching the query
        """
        # Build parameters
        params = {"query": query}

        # Add optional parameters if provided
        if location:
            params["location"] = location
        if lat is not None and lng is not None:
            params["lat"] = lat
            params["lng"] = lng
        if radius is not None:
            params["radius"] = radius
        if type is not None:
            params["type"] = type

        try:
            # Call the place_search tool
            result = await self.call_tool("place_search", params, skip_cache=skip_cache)
            return result
        except Exception as e:
            logger.error("Error in place search: %s", str(e))
            log_exception(e)

            if isinstance(e, MCPError):
                raise

            raise MCPError(
                message=f"Place search failed: {str(e)}",
                server=self.endpoint,
                tool="place_search",
                params=params,
            )

    @redis_cache.cached("place_details", 3600)  # Cache for 1 hour
    async def place_details(
        self,
        place_id: str,
        skip_cache: bool = False,
    ) -> Dict[str, Any]:
        """Get detailed information about a place.

        Args:
            place_id: Google Maps place ID
            skip_cache: Whether to skip the cache

        Returns:
            Detailed place information
        """
        params = {"place_id": place_id}

        try:
            # Call the place_details tool
            result = await self.call_tool(
                "place_details", params, skip_cache=skip_cache
            )
            return result
        except Exception as e:
            logger.error("Error getting place details: %s", str(e))
            log_exception(e)

            if isinstance(e, MCPError):
                raise

            raise MCPError(
                message=f"Place details failed: {str(e)}",
                server=self.endpoint,
                tool="place_details",
                params=params,
            )

    @redis_cache.cached("directions", 3600)  # Cache for 1 hour
    async def directions(
        self,
        origin: str,
        destination: str,
        mode: str = "driving",
        departure_time: Optional[Union[str, datetime]] = None,
        arrival_time: Optional[Union[str, datetime]] = None,
        waypoints: Optional[List[str]] = None,
        skip_cache: bool = False,
    ) -> Dict[str, Any]:
        """Get directions between locations.

        Args:
            origin: Origin location
            destination: Destination location
            mode: Transportation mode (driving, walking, bicycling, transit)
            departure_time: Departure time (ISO format or datetime)
            arrival_time: Arrival time (ISO format or datetime)
            waypoints: List of waypoints
            skip_cache: Whether to skip the cache

        Returns:
            Directions including routes, steps, and travel information
        """
        # Convert times to strings if needed
        if isinstance(departure_time, datetime):
            departure_time = departure_time.isoformat()
        if isinstance(arrival_time, datetime):
            arrival_time = arrival_time.isoformat()

        # Build parameters
        params = {
            "origin": origin,
            "destination": destination,
            "mode": mode,
        }

        # Add optional parameters if provided
        if departure_time:
            params["departure_time"] = departure_time
        if arrival_time:
            params["arrival_time"] = arrival_time
        if waypoints:
            params["waypoints"] = waypoints

        try:
            # Call the directions tool
            result = await self.call_tool("directions", params, skip_cache=skip_cache)
            return result
        except Exception as e:
            logger.error("Error getting directions: %s", str(e))
            log_exception(e)

            if isinstance(e, MCPError):
                raise

            raise MCPError(
                message=f"Directions failed: {str(e)}",
                server=self.endpoint,
                tool="directions",
                params=params,
            )

    @redis_cache.cached("distance_matrix", 3600)  # Cache for 1 hour
    async def distance_matrix(
        self,
        origins: List[str],
        destinations: List[str],
        mode: str = "driving",
        departure_time: Optional[Union[str, datetime]] = None,
        skip_cache: bool = False,
    ) -> Dict[str, Any]:
        """Get distance and duration information between multiple origins and destinations.

        Args:
            origins: List of origin locations
            destinations: List of destination locations
            mode: Transportation mode (driving, walking, bicycling, transit)
            departure_time: Departure time (ISO format or datetime)
            skip_cache: Whether to skip the cache

        Returns:
            Matrix of distances and durations
        """
        # Convert time to string if needed
        if isinstance(departure_time, datetime):
            departure_time = departure_time.isoformat()

        # Build parameters
        params = {
            "origins": origins,
            "destinations": destinations,
            "mode": mode,
        }

        # Add optional parameters if provided
        if departure_time:
            params["departure_time"] = departure_time

        try:
            # Call the distance_matrix tool
            result = await self.call_tool(
                "distance_matrix", params, skip_cache=skip_cache
            )
            return result
        except Exception as e:
            logger.error("Error getting distance matrix: %s", str(e))
            log_exception(e)

            if isinstance(e, MCPError):
                raise

            raise MCPError(
                message=f"Distance matrix failed: {str(e)}",
                server=self.endpoint,
                tool="distance_matrix",
                params=params,
            )


# Singleton instance getter
def get_client() -> GoogleMapsMCPClient:
    """Get or create a singleton instance of the Google Maps MCP client.

    Returns:
        GoogleMapsMCPClient instance
    """
    if not hasattr(get_client, "_instance"):
        get_client._instance = GoogleMapsMCPClient()
    return get_client._instance
