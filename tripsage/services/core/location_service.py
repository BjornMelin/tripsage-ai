"""
Google Maps location service for TripSage.

This service provides comprehensive location operations using the Google Maps
Python SDK,
including geocoding, place search, directions, distance calculations, and timezone data.
"""

import logging
from typing import Any, Dict, List, Optional

from tripsage.services.external.google_maps_service import (
    GoogleMapsServiceError,
    get_google_maps_service,
)
from tripsage.utils.decorators import with_error_handling

logger = logging.getLogger(__name__)


class LocationServiceError(Exception):
    """Raised when location service operations fail."""

    pass


class LocationService:
    """Google Maps location service providing comprehensive geographic operations."""

    def __init__(self) -> None:
        """Initialize location service with Google Maps integration."""
        self.google_maps_service = get_google_maps_service()
        logger.info("LocationService initialized successfully")

    @with_error_handling
    async def geocode(self, address: str, **kwargs) -> List[Dict[str, Any]]:
        """Convert address to coordinates.

        Args:
            address: Address to geocode
            **kwargs: Additional parameters

        Returns:
            List of geocoding results

        Raises:
            LocationServiceError: If geocoding fails
        """
        try:
            logger.debug(f"Geocoding address: {address}")
            return await self.google_maps_service.geocode(address, **kwargs)
        except GoogleMapsServiceError as e:
            logger.error(f"Geocoding failed for address '{address}': {e}")
            raise LocationServiceError(f"Geocoding failed: {e}") from e

    @with_error_handling
    async def reverse_geocode(
        self, lat: float, lng: float, **kwargs
    ) -> List[Dict[str, Any]]:
        """Convert coordinates to address.

        Args:
            lat: Latitude coordinate
            lng: Longitude coordinate
            **kwargs: Additional parameters

        Returns:
            List of reverse geocoding results

        Raises:
            LocationServiceError: If reverse geocoding fails
        """
        try:
            logger.debug(f"Reverse geocoding coordinates: ({lat}, {lng})")
            return await self.google_maps_service.reverse_geocode(lat, lng, **kwargs)
        except GoogleMapsServiceError as e:
            logger.error(
                f"Reverse geocoding failed for coordinates ({lat}, {lng}): {e}"
            )
            raise LocationServiceError(f"Reverse geocoding failed: {e}") from e

    @with_error_handling
    async def search_places(
        self,
        query: str,
        location: Optional[tuple] = None,
        radius: Optional[int] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Search for places.

        Args:
            query: Search query
            location: Optional center point for search (lat, lng tuple)
            radius: Optional search radius in meters
            **kwargs: Additional parameters

        Returns:
            Place search results

        Raises:
            LocationServiceError: If place search fails
        """
        try:
            logger.debug(f"Searching places: {query}")
            return await self.google_maps_service.search_places(
                query, location, radius, **kwargs
            )
        except GoogleMapsServiceError as e:
            logger.error(f"Place search failed for query '{query}': {e}")
            raise LocationServiceError(f"Place search failed: {e}") from e

    @with_error_handling
    async def get_place_details(
        self, place_id: str, fields: Optional[List[str]] = None, **kwargs
    ) -> Dict[str, Any]:
        """Get detailed information about a specific place.

        Args:
            place_id: Google Maps place ID
            fields: Optional list of fields to include in response
            **kwargs: Additional parameters

        Returns:
            Place details

        Raises:
            LocationServiceError: If place details request fails
        """
        try:
            logger.debug(f"Getting place details: {place_id}")
            return await self.google_maps_service.get_place_details(
                place_id, fields, **kwargs
            )
        except GoogleMapsServiceError as e:
            logger.error(f"Place details request failed for place_id '{place_id}': {e}")
            raise LocationServiceError(f"Place details request failed: {e}") from e

    @with_error_handling
    async def get_directions(
        self, origin: str, destination: str, mode: str = "driving", **kwargs
    ) -> List[Dict[str, Any]]:
        """Get directions between two locations.

        Args:
            origin: Origin address or coordinates
            destination: Destination address or coordinates
            mode: Travel mode (driving, walking, bicycling, transit)
            **kwargs: Additional parameters

        Returns:
            List of route directions

        Raises:
            LocationServiceError: If directions request fails
        """
        try:
            logger.debug(f"Getting directions: {origin} to {destination}")
            return await self.google_maps_service.get_directions(
                origin, destination, mode, **kwargs
            )
        except GoogleMapsServiceError as e:
            logger.error(
                f"Directions request failed from '{origin}' to '{destination}': {e}"
            )
            raise LocationServiceError(f"Directions request failed: {e}") from e

    @with_error_handling
    async def distance_matrix(
        self,
        origins: List[str],
        destinations: List[str],
        mode: str = "driving",
        **kwargs,
    ) -> Dict[str, Any]:
        """Calculate distance and time for multiple origins/destinations.

        Args:
            origins: List of origin addresses or coordinates
            destinations: List of destination addresses or coordinates
            mode: Travel mode (driving, walking, bicycling, transit)
            **kwargs: Additional parameters

        Returns:
            Distance matrix results

        Raises:
            LocationServiceError: If distance matrix request fails
        """
        try:
            logger.debug("Calculating distance matrix")
            return await self.google_maps_service.distance_matrix(
                origins, destinations, mode, **kwargs
            )
        except GoogleMapsServiceError as e:
            logger.error(f"Distance matrix request failed: {e}")
            raise LocationServiceError(f"Distance matrix request failed: {e}") from e

    @with_error_handling
    async def get_elevation(
        self, locations: List[tuple], **kwargs
    ) -> List[Dict[str, Any]]:
        """Get elevation data for locations.

        Args:
            locations: List of (lat, lng) coordinate tuples
            **kwargs: Additional parameters

        Returns:
            List of elevation results

        Raises:
            LocationServiceError: If elevation request fails
        """
        try:
            logger.debug("Getting elevation data")
            return await self.google_maps_service.get_elevation(locations, **kwargs)
        except GoogleMapsServiceError as e:
            logger.error(f"Elevation request failed: {e}")
            raise LocationServiceError(f"Elevation request failed: {e}") from e

    @with_error_handling
    async def get_timezone(
        self, location: tuple, timestamp: Optional[int] = None, **kwargs
    ) -> Dict[str, Any]:
        """Get timezone information for a location.

        Args:
            location: (lat, lng) coordinate tuple
            timestamp: Optional timestamp (defaults to current time)
            **kwargs: Additional parameters

        Returns:
            Timezone information

        Raises:
            LocationServiceError: If timezone request fails
        """
        try:
            logger.debug(f"Getting timezone data for location: {location}")
            return await self.google_maps_service.get_timezone(
                location, timestamp, **kwargs
            )
        except GoogleMapsServiceError as e:
            logger.error(f"Timezone request failed for location {location}: {e}")
            raise LocationServiceError(f"Timezone request failed: {e}") from e


# Singleton instance for global use
location_service = LocationService()


def get_location_service() -> LocationService:
    """Get the global location service instance.

    Returns:
        LocationService instance
    """
    return location_service
