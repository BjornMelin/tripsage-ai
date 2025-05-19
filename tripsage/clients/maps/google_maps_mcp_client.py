"""
Google Maps MCP client for TripSage.

This module provides an asynchronous client for interacting with the
Google Maps MCP server, which offers geocoding, directions, place search,
and other Google Maps API services.
"""

import asyncio
from typing import Any, Dict, List, Optional, TypeVar

import httpx
from pydantic import BaseModel

from tripsage.config.app_settings import settings
from tripsage.tools.schemas.googlemaps import (
    DirectionsResponse,
    DistanceMatrixResponse,
    ElevationResponse,
    GeocodeResponse,
    PlaceDetailsResponse,
    PlaceSearchResponse,
    TimeZoneResponse,
)
from tripsage.utils.cache import ContentType, WebOperationsCache
from tripsage.utils.error_handling import MCPError, with_error_handling
from tripsage.utils.logging import get_logger

logger = get_logger(__name__)

# Type variable for return type
T = TypeVar("T", bound=BaseModel)


class GoogleMapsMCPClient:
    """Client for interacting with the Google Maps MCP server.

    This client provides methods for geocoding, reverse geocoding, place search,
    place details, directions, distance matrix, elevation, and timezone operations.
    """

    _instance = None
    _lock = asyncio.Lock()

    def __new__(cls, *args, **kwargs):
        """Implement singleton pattern to ensure only one client instance is created."""
        return cls._instance or super(GoogleMapsMCPClient, cls).__new__(cls)

    def __init__(
        self,
        endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        """Initialize the Google Maps MCP client.

        Args:
            endpoint: The MCP server endpoint URL
            api_key: The API key for the MCP server
        """
        # Only initialize once (singleton pattern)
        if self.__class__._instance is not None:
            return

        self.endpoint = endpoint or settings.googlemaps_mcp.endpoint
        self.api_key = api_key or settings.get_api_key_for_type("GoogleMapsMCPClient")
        self.client: Optional[httpx.AsyncClient] = None
        self.web_cache = WebOperationsCache(namespace="googlemaps_mcp")

        # Store the instance as a class variable
        self.__class__._instance = self

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()

    async def connect(self):
        """Connect to the MCP server."""
        if self.client is None:
            self.client = httpx.AsyncClient(
                base_url=self.endpoint,
                timeout=30.0,
                headers=(
                    {"Authorization": f"Bearer {self.api_key}"}
                    if self.api_key
                    else None
                ),
            )
            logger.info(f"Connected to Google Maps MCP server at {self.endpoint}")

    async def disconnect(self):
        """Disconnect from the MCP server."""
        if self.client is not None:
            await self.client.aclose()
            self.client = None
            logger.info("Disconnected from Google Maps MCP server")

    @classmethod
    async def get_instance(
        cls, endpoint: Optional[str] = None, api_key: Optional[str] = None
    ) -> "GoogleMapsMCPClient":
        """Get or create a singleton instance of the client.

        Args:
            endpoint: The MCP server endpoint URL
            api_key: The API key for the MCP server

        Returns:
            Singleton instance of the client
        """
        async with cls._lock:
            if cls._instance is None:
                cls._instance = cls(endpoint=endpoint, api_key=api_key)
                await cls._instance.connect()
            return cls._instance

    async def _call_mcp(
        self,
        tool_name: str,
        params: Dict[str, Any],
        response_model: type[T],
        content_type: ContentType = ContentType.SEMI_STATIC,
        skip_cache: bool = False,
    ) -> T:
        """Call an MCP endpoint and return the validated response.

        Args:
            tool_name: Name of the MCP tool to call
            params: Parameters to pass to the tool
            response_model: Pydantic model to validate and parse the response
            content_type: Content type for caching
            skip_cache: Whether to skip caching

        Returns:
            Validated response object

        Raises:
            MCPError: If the MCP call fails
        """
        if self.client is None:
            await self.connect()

        # Prepare cache key
        cache_key = self.web_cache.generate_cache_key(
            tool_name=f"googlemaps_{tool_name}",
            query=str(sorted(params.items())),
        )

        # Check cache if not skipping
        if not skip_cache:
            cached_result = await self.web_cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for Google Maps MCP {tool_name}")
                return response_model.model_validate(cached_result)

        # Make the request
        try:
            if self.client is None:
                raise MCPError(
                    message="Client is not connected",
                    server="Google Maps MCP",
                    tool=tool_name,
                    category="connection",
                )

            # Prepare request URL and parameters
            url = f"/{tool_name}"

            # Make the request
            logger.debug(f"Calling Google Maps MCP {tool_name} with params: {params}")
            response = await self.client.post(url, json=params)

            # Check for errors
            response.raise_for_status()
            data = response.json()

            # Check for error in response
            if data.get("status") not in ["OK", "ZERO_RESULTS"]:
                error_message = data.get("error_message", "Unknown error")
                raise MCPError(
                    message=f"Maps API error: {error_message}",
                    server="Google Maps MCP",
                    tool=tool_name,
                    params=params,
                    category="api_error",
                    status_code=data.get("status"),
                )

            # Parse and validate response
            result = response_model.model_validate(data)

            # Cache the result
            if not skip_cache:
                await self.web_cache.set(
                    cache_key, result.model_dump(), content_type=content_type
                )

            return result

        except httpx.HTTPStatusError as e:
            raise MCPError(
                message=f"HTTP error: {str(e)}",
                server="Google Maps MCP",
                tool=tool_name,
                params=params,
                category="http_error",
                status_code=e.response.status_code,
            ) from e
        except httpx.RequestError as e:
            raise MCPError(
                message=f"Request error: {str(e)}",
                server="Google Maps MCP",
                tool=tool_name,
                params=params,
                category="network_error",
            ) from e
        except Exception as e:
            raise MCPError(
                message=f"Unexpected error: {str(e)}",
                server="Google Maps MCP",
                tool=tool_name,
                params=params,
                category="unknown_error",
            ) from e

    @with_error_handling
    async def geocode(
        self,
        address: Optional[str] = None,
        place_id: Optional[str] = None,
        components: Optional[Dict[str, str]] = None,
    ) -> GeocodeResponse:
        """Convert an address to geographic coordinates.

        Args:
            address: The address to geocode
            place_id: Google Maps place ID to geocode
            components: Component filters (e.g., {"country": "US"})

        Returns:
            Geocoding results

        Raises:
            MCPError: If the geocoding fails
        """
        params = {
            k: v
            for k, v in {
                "address": address,
                "place_id": place_id,
                "components": components,
            }.items()
            if v is not None
        }

        return await self._call_mcp(
            tool_name="geocode",
            params=params,
            response_model=GeocodeResponse,
            content_type=ContentType.SEMI_STATIC,  # Geocoded addresses rarely change
        )

    @with_error_handling
    async def reverse_geocode(
        self,
        lat: float,
        lng: float,
        result_type: Optional[str] = None,
        location_type: Optional[str] = None,
    ) -> GeocodeResponse:
        """Convert geographic coordinates to an address.

        Args:
            lat: Latitude coordinate
            lng: Longitude coordinate
            result_type: Filter result types (e.g., "street_address")
            location_type: Filter location types (e.g., "ROOFTOP")

        Returns:
            Reverse geocoding results

        Raises:
            MCPError: If the reverse geocoding fails
        """
        params = {
            "lat": lat,
            "lng": lng,
            "result_type": result_type,
            "location_type": location_type,
        }

        return await self._call_mcp(
            tool_name="reverse_geocode",
            params={k: v for k, v in params.items() if v is not None},
            response_model=GeocodeResponse,
            # Reverse geocoded addresses rarely change
            content_type=ContentType.SEMI_STATIC,
        )

    @with_error_handling
    async def place_search(
        self,
        query: Optional[str] = None,
        location: Optional[str] = None,
        radius: Optional[int] = None,
        type: Optional[str] = None,
        keyword: Optional[str] = None,
        min_price: Optional[int] = None,
        max_price: Optional[int] = None,
        open_now: Optional[bool] = None,
        rank_by: Optional[str] = None,
    ) -> PlaceSearchResponse:
        """Search for places based on text query or location.

        Args:
            query: Text search query (e.g., "restaurants in Manhattan")
            location: Location to search around (lat,lng or address)
            radius: Search radius in meters (max 50000)
            type: Place type (e.g., "restaurant", "museum")
            keyword: Keyword to match in places
            min_price: Minimum price level (0-4)
            max_price: Maximum price level (0-4)
            open_now: Whether place is open now
            rank_by: Ranking method ("prominence" or "distance")

        Returns:
            Place search results

        Raises:
            MCPError: If the place search fails
        """
        params = {
            k: v
            for k, v in {
                "query": query,
                "location": location,
                "radius": radius,
                "type": type,
                "keyword": keyword,
                "min_price": min_price,
                "max_price": max_price,
                "open_now": open_now,
                "rank_by": rank_by,
            }.items()
            if v is not None
        }

        return await self._call_mcp(
            tool_name="place_search",
            params=params,
            response_model=PlaceSearchResponse,
            # Places can change daily (e.g., business status)
            content_type=ContentType.DAILY,
        )

    @with_error_handling
    async def place_details(
        self,
        place_id: str,
        fields: Optional[List[str]] = None,
    ) -> PlaceDetailsResponse:
        """Get detailed information about a place.

        Args:
            place_id: Google Maps place ID
            fields: Place fields to include in response

        Returns:
            Place details

        Raises:
            MCPError: If the place details request fails
        """
        params = {
            "place_id": place_id,
            "fields": fields,
        }

        return await self._call_mcp(
            tool_name="place_details",
            params={k: v for k, v in params.items() if v is not None},
            response_model=PlaceDetailsResponse,
            content_type=ContentType.DAILY,  # Place details can change daily
        )

    @with_error_handling
    async def directions(
        self,
        origin: str,
        destination: str,
        mode: str = "driving",
        waypoints: Optional[List[str]] = None,
        alternatives: Optional[bool] = None,
        avoid: Optional[List[str]] = None,
        units: Optional[str] = None,
        arrival_time: Optional[int] = None,
        departure_time: Optional[int] = None,
    ) -> DirectionsResponse:
        """Get directions between locations.

        Args:
            origin: Origin address or coordinates
            destination: Destination address or coordinates
            mode: Travel mode (driving, walking, bicycling, transit)
            waypoints: Waypoints to include in route
            alternatives: Whether to provide alternative routes
            avoid: Features to avoid (tolls, highways, ferries)
            units: Unit system (metric or imperial)
            arrival_time: Desired arrival time (unix timestamp)
            departure_time: Desired departure time (unix timestamp)

        Returns:
            Directions information

        Raises:
            MCPError: If the directions request fails
        """
        params = {
            k: v
            for k, v in {
                "origin": origin,
                "destination": destination,
                "mode": mode,
                "waypoints": waypoints,
                "alternatives": alternatives,
                "avoid": avoid,
                "units": units,
                "arrival_time": arrival_time,
                "departure_time": departure_time,
            }.items()
            if v is not None
        }

        # Directions can be traffic-dependent
        content_type = (
            ContentType.REALTIME
            if departure_time or arrival_time
            else ContentType.DAILY
        )

        return await self._call_mcp(
            tool_name="directions",
            params=params,
            response_model=DirectionsResponse,
            content_type=content_type,
        )

    @with_error_handling
    async def distance_matrix(
        self,
        origins: List[str],
        destinations: List[str],
        mode: str = "driving",
        avoid: Optional[List[str]] = None,
        units: Optional[str] = None,
        departure_time: Optional[int] = None,
    ) -> DistanceMatrixResponse:
        """
        Calculate distances and travel times between multiple
        origins and destinations.

        Args:
            origins: List of origin addresses or coordinates
            destinations: List of destination addresses or coordinates
            mode: Travel mode (driving, walking, bicycling, transit)
            avoid: Features to avoid (tolls, highways, ferries)
            units: Unit system (metric or imperial)
            departure_time: Desired departure time (unix timestamp)

        Returns:
            Distance matrix information

        Raises:
            MCPError: If the distance matrix request fails
        """
        params = {
            k: v
            for k, v in {
                "origins": origins,
                "destinations": destinations,
                "mode": mode,
                "avoid": avoid,
                "units": units,
                "departure_time": departure_time,
            }.items()
            if v is not None
        }

        # Travel times can be traffic-dependent
        content_type = ContentType.REALTIME if departure_time else ContentType.DAILY

        return await self._call_mcp(
            tool_name="distance_matrix",
            params=params,
            response_model=DistanceMatrixResponse,
            content_type=content_type,
        )

    @with_error_handling
    async def timezone(
        self,
        location: str,
        timestamp: Optional[int] = None,
    ) -> TimeZoneResponse:
        """Get time zone information for a location.

        Args:
            location: Location coordinates (lat,lng)
            timestamp: Timestamp to use (defaults to current time)

        Returns:
            Time zone information

        Raises:
            MCPError: If the timezone request fails
        """
        params = {"location": location}
        if timestamp is not None:
            params["timestamp"] = timestamp

        return await self._call_mcp(
            tool_name="timezone",
            params=params,
            response_model=TimeZoneResponse,
            content_type=ContentType.SEMI_STATIC,  # Timezone data rarely changes
        )

    @with_error_handling
    async def elevation(
        self,
        locations: List[str],
    ) -> ElevationResponse:
        """Get elevation data for locations.

        Args:
            locations: List of location coordinates (lat,lng)

        Returns:
            Elevation information

        Raises:
            MCPError: If the elevation request fails
        """
        params = {"locations": locations}

        return await self._call_mcp(
            tool_name="elevation",
            params=params,
            response_model=ElevationResponse,
            content_type=ContentType.STATIC,  # Elevation data doesn't change
        )
