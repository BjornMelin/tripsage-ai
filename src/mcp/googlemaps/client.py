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
        store_in_knowledge_graph: bool = False,
        memory_client=None,
    ) -> Dict[str, Any]:
        """Geocode an address to get coordinates.

        Args:
            address: Address to geocode
            skip_cache: Whether to skip the cache
            store_in_knowledge_graph: Whether to store the result in the knowledge graph
            memory_client: Optional memory client instance

        Returns:
            Geocoded result with coordinates and address components
        """
        params = {"address": address}

        try:
            # Call the maps_geocode tool from official Google Maps MCP server
            result = await self.call_tool("maps_geocode", params, skip_cache=skip_cache)

            # Store in knowledge graph if requested
            if store_in_knowledge_graph:
                await store_location_in_knowledge_graph(
                    location_name=address,
                    geocode_result=result,
                    memory_client=memory_client,
                )

            return result
        except Exception as e:
            logger.error("Error in geocoding: %s", str(e))
            log_exception(e)

            if isinstance(e, MCPError):
                raise

            raise MCPError(
                message=f"Geocoding failed: {str(e)}",
                server=self.endpoint,
                tool="maps_geocode",
                params=params,
            ) from e

    @redis_cache.cached("reverse_geocode", 86400)  # Cache for 24 hours
    async def reverse_geocode(
        self,
        lat: float,
        lng: float,
        skip_cache: bool = False,
    ) -> Dict[str, Any]:
        """Reverse geocode coordinates to get an address.

        Args:
            lat: Latitude
            lng: Longitude
            skip_cache: Whether to skip the cache

        Returns:
            Reverse geocoded result with address components
        """
        params = {"lat": lat, "lng": lng}

        try:
            # Call the maps_reverse_geocode tool
            result = await self.call_tool(
                "maps_reverse_geocode", params, skip_cache=skip_cache
            )
            return result
        except Exception as e:
            logger.error("Error in reverse geocoding: %s", str(e))
            log_exception(e)

            if isinstance(e, MCPError):
                raise

            raise MCPError(
                message=f"Reverse geocoding failed: {str(e)}",
                server=self.endpoint,
                tool="maps_reverse_geocode",
                params=params,
            ) from e

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
            # Call the maps_search_places tool
            result = await self.call_tool(
                "maps_search_places", params, skip_cache=skip_cache
            )
            return result
        except Exception as e:
            logger.error("Error in place search: %s", str(e))
            log_exception(e)

            if isinstance(e, MCPError):
                raise

            raise MCPError(
                message=f"Place search failed: {str(e)}",
                server=self.endpoint,
                tool="maps_search_places",
                params=params,
            ) from e

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
            # Call the maps_place_details tool
            result = await self.call_tool(
                "maps_place_details", params, skip_cache=skip_cache
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
                tool="maps_place_details",
                params=params,
            ) from e

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
            # Call the maps_directions tool
            result = await self.call_tool(
                "maps_directions", params, skip_cache=skip_cache
            )
            return result
        except Exception as e:
            logger.error("Error getting directions: %s", str(e))
            log_exception(e)

            if isinstance(e, MCPError):
                raise

            raise MCPError(
                message=f"Directions failed: {str(e)}",
                server=self.endpoint,
                tool="maps_directions",
                params=params,
            ) from e

    @redis_cache.cached("distance_matrix", 3600)  # Cache for 1 hour
    async def distance_matrix(
        self,
        origins: List[str],
        destinations: List[str],
        mode: str = "driving",
        departure_time: Optional[Union[str, datetime]] = None,
        skip_cache: bool = False,
    ) -> Dict[str, Any]:
        """Get distance and duration information between
        multiple origins and destinations.

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
            # Call the maps_distance_matrix tool
            result = await self.call_tool(
                "maps_distance_matrix", params, skip_cache=skip_cache
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
                tool="maps_distance_matrix",
                params=params,
            ) from e

    @redis_cache.cached("elevation", 86400)  # Cache for 24 hours
    async def elevation(
        self,
        locations: List[Dict[str, float]],
        skip_cache: bool = False,
    ) -> Dict[str, Any]:
        """Get elevation data for geographic coordinates.

        Args:
            locations: List of locations, each containing lat and lng keys
            skip_cache: Whether to skip the cache

        Returns:
            Elevation data for the specified locations
        """
        params = {"locations": locations}

        try:
            # Call the maps_elevation tool
            result = await self.call_tool(
                "maps_elevation", params, skip_cache=skip_cache
            )
            return result
        except Exception as e:
            logger.error("Error getting elevation data: %s", str(e))
            log_exception(e)

            if isinstance(e, MCPError):
                raise

            raise MCPError(
                message=f"Elevation data retrieval failed: {str(e)}",
                server=self.endpoint,
                tool="maps_elevation",
                params=params,
            ) from e


# Integration with Memory MCP (Knowledge Graph)
async def store_location_in_knowledge_graph(
    location_name: str,
    geocode_result: Dict[str, Any],
    memory_client=None,
) -> bool:
    """Store a geocoded location in the knowledge graph.

    This function creates or updates a Destination entity in the knowledge graph
    with information from the Google Maps MCP geocode result.

    Args:
        location_name: Name of the location (destination)
        geocode_result: Geocode result from Google Maps MCP
        memory_client: Optional memory client (if None, will try to get one)

    Returns:
        True if the location was successfully stored, False otherwise
    """
    try:
        # Try to get memory client if not provided
        if memory_client is None:
            try:
                from ..memory import get_client as get_memory_client

                memory_client = get_memory_client()
            except ImportError:
                logger.warning("Memory MCP client not available")
                return False

        # Extract relevant information from geocode result
        if (
            not geocode_result
            or "results" not in geocode_result
            or not geocode_result["results"]
        ):
            logger.warning("No geocode results to store in knowledge graph")
            return False

        result = geocode_result["results"][0]

        # Get formatted address and location coordinates
        formatted_address = result.get("formatted_address", "")
        location = result.get("geometry", {}).get("location", {})
        lat = location.get("lat")
        lng = location.get("lng")

        if not lat or not lng:
            logger.warning("No coordinates in geocode result")
            return False

        # Extract address components
        address_components = result.get("address_components", [])
        country = ""
        administrative_area = ""
        locality = ""

        for component in address_components:
            types = component.get("types", [])
            if "country" in types:
                country = component.get("long_name", "")
            elif "administrative_area_level_1" in types:
                administrative_area = component.get("long_name", "")
            elif "locality" in types:
                locality = component.get("long_name", "")

        # Create observations
        observations = [
            f"Formatted address: {formatted_address}",
            f"Coordinates: {lat}, {lng}",
        ]

        if country:
            observations.append(f"Country: {country}")
        if administrative_area:
            observations.append(f"Administrative area: {administrative_area}")
        if locality:
            observations.append(f"Locality: {locality}")

        # Check if destination entity exists
        destination_nodes = await memory_client.search_nodes(location_name)
        destination_exists = any(
            node["name"] == location_name and node["type"] == "Destination"
            for node in destination_nodes
        )

        if destination_exists:
            # Update existing entity with new observations
            await memory_client.add_observations(
                [
                    {
                        "entityName": location_name,
                        "contents": observations,
                    }
                ]
            )
            logger.info(
                "Updated existing destination entity in knowledge graph: %s",
                location_name,
            )
        else:
            # Create new destination entity
            await memory_client.create_entities(
                [
                    {
                        "name": location_name,
                        "entityType": "Destination",
                        "observations": observations,
                    }
                ]
            )
            logger.info(
                "Created new destination entity in knowledge graph: %s", location_name
            )

        # If country exists, create relationship between destination and country
        if country:
            # Check if country entity exists
            country_nodes = await memory_client.search_nodes(country)
            country_exists = any(
                node["name"] == country and node["type"] == "Country"
                for node in country_nodes
            )

            if not country_exists:
                # Create country entity
                await memory_client.create_entities(
                    [
                        {
                            "name": country,
                            "entityType": "Country",
                            "observations": [f"Country containing {location_name}"],
                        }
                    ]
                )
                logger.info(
                    "Created new country entity in knowledge graph: %s", country
                )

            # Create relationship between destination and country
            await memory_client.create_relations(
                [
                    {
                        "from": location_name,
                        "relationType": "is_located_in",
                        "to": country,
                    }
                ]
            )
            logger.info(
                "Created relationship: %s is_located_in %s", location_name, country
            )

        return True

    except Exception as e:
        logger.error("Error storing location in knowledge graph: %s", str(e))
        return False


# Singleton instance getter
def get_client() -> GoogleMapsMCPClient:
    """Get or create a singleton instance of the Google Maps MCP client.

    Returns:
        GoogleMapsMCPClient instance
    """
    if not hasattr(get_client, "_instance"):
        get_client._instance = GoogleMapsMCPClient()
    return get_client._instance
