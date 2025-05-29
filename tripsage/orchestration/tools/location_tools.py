"""
Location tools for geographic operations using Google Maps.

This module provides LangGraph-compatible tools for location operations
including geocoding, place search, directions, and timezone data.
"""

import json
from typing import Any, List, Optional

from langchain_core.tools import BaseTool
from langchain_core.tools.base import ToolException
from pydantic import Field

from tripsage.services.location_service import (
    LocationServiceError,
    get_location_service,
)
from tripsage_core.utils.logging_utils import get_logger

logger = get_logger(__name__)


class LocationTool(BaseTool):
    """Base class for Google Maps location tools."""

    location_service: Any = Field(default_factory=get_location_service)

    def __init__(self, **kwargs):
        """Initialize the location tool."""
        super().__init__(location_service=get_location_service(), **kwargs)


class GeocodeTool(LocationTool):
    """Tool for geocoding addresses to coordinates."""

    name: str = "geocode_location"
    description: str = "Convert address to coordinates or get location details"

    async def _arun(self, address: str, **kwargs) -> str:
        """
        Execute geocoding asynchronously.

        Args:
            address: Address to geocode
            **kwargs: Additional parameters

        Returns:
            JSON string containing geocoding results
        """
        try:
            logger.info(f"Geocoding address: {address}")
            result = await self.location_service.geocode(address, **kwargs)
            logger.info(f"Geocoding successful for address: {address}")
            return json.dumps(result, ensure_ascii=False)

        except LocationServiceError as e:
            logger.error(f"Geocoding failed for address '{address}': {e}")
            raise ToolException(f"Geocoding failed: {e}") from e

    def _run(self, address: str, **kwargs) -> str:
        """
        Execute geocoding synchronously.

        Args:
            address: Address to geocode
            **kwargs: Additional parameters

        Returns:
            JSON string containing geocoding results
        """
        import asyncio

        try:
            return asyncio.run(self._arun(address, **kwargs))
        except Exception as e:
            raise ToolException(f"Geocoding failed: {e}") from e


class ReverseGeocodeTool(LocationTool):
    """Tool for reverse geocoding coordinates to addresses."""

    name: str = "reverse_geocode_location"
    description: str = "Convert coordinates to address"

    async def _arun(self, lat: float, lng: float, **kwargs) -> str:
        """
        Execute reverse geocoding asynchronously.

        Args:
            lat: Latitude coordinate
            lng: Longitude coordinate
            **kwargs: Additional parameters

        Returns:
            JSON string containing reverse geocoding results
        """
        try:
            logger.info(f"Reverse geocoding coordinates: ({lat}, {lng})")
            result = await self.location_service.reverse_geocode(lat, lng, **kwargs)
            logger.info(f"Reverse geocoding successful for coordinates: ({lat}, {lng})")
            return json.dumps(result, ensure_ascii=False)

        except LocationServiceError as e:
            logger.error(
                f"Reverse geocoding failed for coordinates ({lat}, {lng}): {e}"
            )
            raise ToolException(f"Reverse geocoding failed: {e}") from e

    def _run(self, lat: float, lng: float, **kwargs) -> str:
        """
        Execute reverse geocoding synchronously.

        Args:
            lat: Latitude coordinate
            lng: Longitude coordinate
            **kwargs: Additional parameters

        Returns:
            JSON string containing reverse geocoding results
        """
        import asyncio

        try:
            return asyncio.run(self._arun(lat, lng, **kwargs))
        except Exception as e:
            raise ToolException(f"Reverse geocoding failed: {e}") from e


class SearchPlacesTool(LocationTool):
    """Tool for searching places and points of interest."""

    name: str = "search_places"
    description: str = "Search for places and points of interest"

    async def _arun(
        self,
        query: str,
        location: Optional[str] = None,
        radius: Optional[int] = None,
        **kwargs,
    ) -> str:
        """
        Execute place search asynchronously.

        Args:
            query: Search query for places
            location: Optional location to search around (lat,lng format)
            radius: Optional search radius in meters
            **kwargs: Additional parameters

        Returns:
            JSON string containing place search results
        """
        try:
            logger.info(f"Searching places: {query}")

            # Convert location string to tuple if provided
            location_tuple = None
            if location:
                try:
                    lat_str, lng_str = location.split(",")
                    location_tuple = (float(lat_str.strip()), float(lng_str.strip()))
                except (ValueError, AttributeError):
                    logger.warning(f"Invalid location format: {location}, ignoring")

            result = await self.location_service.search_places(
                query, location_tuple, radius, **kwargs
            )
            logger.info(f"Place search successful for query: {query}")
            return json.dumps(result, ensure_ascii=False)

        except LocationServiceError as e:
            logger.error(f"Place search failed for query '{query}': {e}")
            raise ToolException(f"Place search failed: {e}") from e

    def _run(
        self,
        query: str,
        location: Optional[str] = None,
        radius: Optional[int] = None,
        **kwargs,
    ) -> str:
        """
        Execute place search synchronously.

        Args:
            query: Search query for places
            location: Optional location to search around (lat,lng format)
            radius: Optional search radius in meters
            **kwargs: Additional parameters

        Returns:
            JSON string containing place search results
        """
        import asyncio

        try:
            return asyncio.run(self._arun(query, location, radius, **kwargs))
        except Exception as e:
            raise ToolException(f"Place search failed: {e}") from e


class PlaceDetailsTool(LocationTool):
    """Tool for getting detailed information about a place."""

    name: str = "get_place_details"
    description: str = "Get detailed information about a specific place using place ID"

    async def _arun(
        self, place_id: str, fields: Optional[List[str]] = None, **kwargs
    ) -> str:
        """
        Execute place details request asynchronously.

        Args:
            place_id: Google Maps place ID
            fields: Optional list of fields to include
            **kwargs: Additional parameters

        Returns:
            JSON string containing place details
        """
        try:
            logger.info(f"Getting place details for place_id: {place_id}")
            result = await self.location_service.get_place_details(
                place_id, fields, **kwargs
            )
            logger.info(f"Place details successful for place_id: {place_id}")
            return json.dumps(result, ensure_ascii=False)

        except LocationServiceError as e:
            logger.error(f"Place details failed for place_id '{place_id}': {e}")
            raise ToolException(f"Place details failed: {e}") from e

    def _run(self, place_id: str, fields: Optional[List[str]] = None, **kwargs) -> str:
        """
        Execute place details request synchronously.

        Args:
            place_id: Google Maps place ID
            fields: Optional list of fields to include
            **kwargs: Additional parameters

        Returns:
            JSON string containing place details
        """
        import asyncio

        try:
            return asyncio.run(self._arun(place_id, fields, **kwargs))
        except Exception as e:
            raise ToolException(f"Place details failed: {e}") from e


class DirectionsTool(LocationTool):
    """Tool for getting directions between locations."""

    name: str = "get_directions"
    description: str = "Get directions between two locations"

    async def _arun(
        self, origin: str, destination: str, mode: str = "driving", **kwargs
    ) -> str:
        """
        Execute directions request asynchronously.

        Args:
            origin: Origin address or coordinates
            destination: Destination address or coordinates
            mode: Travel mode (driving, walking, bicycling, transit)
            **kwargs: Additional parameters

        Returns:
            JSON string containing directions
        """
        try:
            logger.info(f"Getting directions from {origin} to {destination} ({mode})")
            result = await self.location_service.get_directions(
                origin, destination, mode, **kwargs
            )
            logger.info(f"Directions successful from {origin} to {destination}")
            return json.dumps(result, ensure_ascii=False)

        except LocationServiceError as e:
            logger.error(f"Directions failed from '{origin}' to '{destination}': {e}")
            raise ToolException(f"Directions failed: {e}") from e

    def _run(
        self, origin: str, destination: str, mode: str = "driving", **kwargs
    ) -> str:
        """
        Execute directions request synchronously.

        Args:
            origin: Origin address or coordinates
            destination: Destination address or coordinates
            mode: Travel mode (driving, walking, bicycling, transit)
            **kwargs: Additional parameters

        Returns:
            JSON string containing directions
        """
        import asyncio

        try:
            return asyncio.run(self._arun(origin, destination, mode, **kwargs))
        except Exception as e:
            raise ToolException(f"Directions failed: {e}") from e


class DistanceMatrixTool(LocationTool):
    """Tool for calculating distances and travel times between multiple locations."""

    name: str = "distance_matrix"
    description: str = (
        "Calculate distances and travel times between multiple origins and destinations"
    )

    async def _arun(
        self,
        origins: List[str],
        destinations: List[str],
        mode: str = "driving",
        **kwargs,
    ) -> str:
        """
        Execute distance matrix request asynchronously.

        Args:
            origins: List of origin addresses or coordinates
            destinations: List of destination addresses or coordinates
            mode: Travel mode (driving, walking, bicycling, transit)
            **kwargs: Additional parameters

        Returns:
            JSON string containing distance matrix
        """
        try:
            logger.info(
                f"Calculating distance matrix for {len(origins)} origins "
                f"to {len(destinations)} destinations"
            )
            result = await self.location_service.distance_matrix(
                origins, destinations, mode, **kwargs
            )
            logger.info("Distance matrix calculation successful")
            return json.dumps(result, ensure_ascii=False)

        except LocationServiceError as e:
            logger.error(f"Distance matrix failed: {e}")
            raise ToolException(f"Distance matrix failed: {e}") from e

    def _run(
        self,
        origins: List[str],
        destinations: List[str],
        mode: str = "driving",
        **kwargs,
    ) -> str:
        """
        Execute distance matrix request synchronously.

        Args:
            origins: List of origin addresses or coordinates
            destinations: List of destination addresses or coordinates
            mode: Travel mode (driving, walking, bicycling, transit)
            **kwargs: Additional parameters

        Returns:
            JSON string containing distance matrix
        """
        import asyncio

        try:
            return asyncio.run(self._arun(origins, destinations, mode, **kwargs))
        except Exception as e:
            raise ToolException(f"Distance matrix failed: {e}") from e


class ElevationTool(LocationTool):
    """Tool for getting elevation data for locations."""

    name: str = "get_elevation"
    description: str = "Get elevation data for one or more locations"

    async def _arun(self, locations: List[str], **kwargs) -> str:
        """
        Execute elevation request asynchronously.

        Args:
            locations: List of locations as "lat,lng" strings
            **kwargs: Additional parameters

        Returns:
            JSON string containing elevation data
        """
        try:
            logger.info(f"Getting elevation data for {len(locations)} locations")

            # Convert string locations to tuples
            location_tuples = []
            for loc in locations:
                try:
                    lat_str, lng_str = loc.split(",")
                    location_tuples.append(
                        (float(lat_str.strip()), float(lng_str.strip()))
                    )
                except (ValueError, AttributeError):
                    logger.warning(f"Invalid location format: {loc}, skipping")

            if not location_tuples:
                raise ValueError("No valid locations provided")

            result = await self.location_service.get_elevation(
                location_tuples, **kwargs
            )
            logger.info(
                f"Elevation data successful for {len(location_tuples)} locations"
            )
            return json.dumps(result, ensure_ascii=False)

        except (LocationServiceError, ValueError) as e:
            logger.error(f"Elevation request failed: {e}")
            raise ToolException(f"Elevation request failed: {e}") from e

    def _run(self, locations: List[str], **kwargs) -> str:
        """
        Execute elevation request synchronously.

        Args:
            locations: List of locations as "lat,lng" strings
            **kwargs: Additional parameters

        Returns:
            JSON string containing elevation data
        """
        import asyncio

        try:
            return asyncio.run(self._arun(locations, **kwargs))
        except Exception as e:
            raise ToolException(f"Elevation request failed: {e}") from e


class TimezoneTool(LocationTool):
    """Tool for getting timezone information for a location."""

    name: str = "get_timezone"
    description: str = "Get timezone information for a location"

    async def _arun(
        self, location: str, timestamp: Optional[int] = None, **kwargs
    ) -> str:
        """
        Execute timezone request asynchronously.

        Args:
            location: Location as "lat,lng" string
            timestamp: Optional timestamp (defaults to current time)
            **kwargs: Additional parameters

        Returns:
            JSON string containing timezone information
        """
        try:
            logger.info(f"Getting timezone for location: {location}")

            # Convert string location to tuple
            try:
                lat_str, lng_str = location.split(",")
                location_tuple = (float(lat_str.strip()), float(lng_str.strip()))
            except (ValueError, AttributeError) as e:
                raise ValueError(f"Invalid location format: {location}") from e

            result = await self.location_service.get_timezone(
                location_tuple, timestamp, **kwargs
            )
            logger.info(f"Timezone data successful for location: {location}")
            return json.dumps(result, ensure_ascii=False)

        except (LocationServiceError, ValueError) as e:
            logger.error(f"Timezone request failed for location '{location}': {e}")
            raise ToolException(f"Timezone request failed: {e}") from e

    def _run(self, location: str, timestamp: Optional[int] = None, **kwargs) -> str:
        """
        Execute timezone request synchronously.

        Args:
            location: Location as "lat,lng" string
            timestamp: Optional timestamp (defaults to current time)
            **kwargs: Additional parameters

        Returns:
            JSON string containing timezone information
        """
        import asyncio

        try:
            return asyncio.run(self._arun(location, timestamp, **kwargs))
        except Exception as e:
            raise ToolException(f"Timezone request failed: {e}") from e
