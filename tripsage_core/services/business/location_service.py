"""Google Maps location service for TripSage.

This service provides comprehensive location operations using the typed
`GoogleMapsService`, including geocoding, place search, directions, distance
calculations, elevation, and timezone data.
"""

import logging
from typing import Any

from tripsage_core.models.api.maps_models import (
    DirectionsResult,
    DistanceMatrix,
    ElevationPoint,
    PlaceDetails,
    PlaceSummary,
    TimezoneInfo,
)
from tripsage_core.models.schemas_common.geographic import Place
from tripsage_core.services.external_apis.google_maps_service import (
    GoogleMapsService,
    GoogleMapsServiceError,
)
from tripsage_core.utils.decorator_utils import with_error_handling


logger = logging.getLogger(__name__)


class LocationServiceError(Exception):
    """Raised when location service operations fail."""


class LocationService:
    """Google Maps location service providing comprehensive geographic operations."""

    def __init__(self, google_maps_service: GoogleMapsService) -> None:
        """Initialize location service with injected Google Maps service."""
        self.google_maps_service: GoogleMapsService = google_maps_service
        logger.info("LocationService initialized successfully")

    @with_error_handling()
    async def geocode(self, address: str, **kwargs: Any) -> list[Place]:
        """Convert address to coordinates.

        Args:
            address: Address to geocode
            **kwargs: Additional parameters

        Returns:
            List of normalized places

        Raises:
            LocationServiceError: If geocoding fails
        """
        try:
            logger.debug("Geocoding address: %s", address)
            return await self.google_maps_service.geocode(address, **kwargs)
        except GoogleMapsServiceError as e:
            logger.exception("Geocoding failed for address '%s'", address)
            raise LocationServiceError(f"Geocoding failed: {e}") from e

    @with_error_handling()
    async def reverse_geocode(
        self, lat: float, lng: float, **kwargs: Any
    ) -> list[Place]:
        """Convert coordinates to address.

        Args:
            lat: Latitude coordinate
            lng: Longitude coordinate
            **kwargs: Additional parameters

        Returns:
            List of normalized places

        Raises:
            LocationServiceError: If reverse geocoding fails
        """
        try:
            logger.debug("Reverse geocoding coordinates: (%s, %s)", lat, lng)
            return await self.google_maps_service.reverse_geocode(lat, lng, **kwargs)
        except GoogleMapsServiceError as e:
            logger.exception(
                "Reverse geocoding failed for coordinates (%s, %s)", lat, lng
            )
            raise LocationServiceError(f"Reverse geocoding failed: {e}") from e

    @with_error_handling()
    async def search_places(
        self,
        query: str,
        location: tuple | None = None,
        radius: int | None = None,
        **kwargs: Any,
    ) -> list[PlaceSummary]:
        """Search for places.

        Args:
            query: Search query
            location: Optional center point for search (lat, lng tuple)
            radius: Optional search radius in meters
            **kwargs: Additional parameters

        Returns:
            List of place summaries

        Raises:
            LocationServiceError: If place search fails
        """
        try:
            logger.debug("Searching places: %s", query)
            return await self.google_maps_service.search_places(
                query, location, radius, **kwargs
            )
        except GoogleMapsServiceError as e:
            logger.exception("Place search failed for query '%s'", query)
            raise LocationServiceError(f"Place search failed: {e}") from e

    @with_error_handling()
    async def get_place_details(
        self, place_id: str, fields: list[str] | None = None, **kwargs: Any
    ) -> PlaceDetails:
        """Get detailed information about a specific place.

        Args:
            place_id: Google Maps place ID
            fields: Optional list of fields to include in response
            **kwargs: Additional parameters

        Returns:
            Detailed place information

        Raises:
            LocationServiceError: If place details request fails
        """
        try:
            logger.debug("Getting place details: %s", place_id)
            return await self.google_maps_service.get_place_details(
                place_id, fields, **kwargs
            )
        except GoogleMapsServiceError as e:
            logger.exception("Place details request failed for place_id '%s'", place_id)
            raise LocationServiceError(f"Place details request failed: {e}") from e

    @with_error_handling()
    async def get_directions(
        self, origin: str, destination: str, mode: str = "driving", **kwargs: Any
    ) -> list[DirectionsResult]:
        """Get directions between two locations.

        Args:
            origin: Origin address or coordinates
            destination: Destination address or coordinates
            mode: Travel mode (driving, walking, bicycling, transit)
            **kwargs: Additional parameters

        Returns:
            List of normalized directions routes

        Raises:
            LocationServiceError: If directions request fails
        """
        try:
            logger.debug("Getting directions: %s to %s", origin, destination)
            return await self.google_maps_service.get_directions(
                origin, destination, mode, **kwargs
            )
        except GoogleMapsServiceError as e:
            logger.exception(
                "Directions request failed from '%s' to '%s'", origin, destination
            )
            raise LocationServiceError(f"Directions request failed: {e}") from e

    @with_error_handling()
    async def distance_matrix(
        self,
        origins: list[str],
        destinations: list[str],
        mode: str = "driving",
        **kwargs: Any,
    ) -> DistanceMatrix:
        """Calculate distance and time for multiple origins/destinations.

        Args:
            origins: List of origin addresses or coordinates
            destinations: List of destination addresses or coordinates
            mode: Travel mode (driving, walking, bicycling, transit)
            **kwargs: Additional parameters

        Returns:
            Normalized distance matrix

        Raises:
            LocationServiceError: If distance matrix request fails
        """
        try:
            logger.debug("Calculating distance matrix")
            return await self.google_maps_service.distance_matrix(
                origins, destinations, mode, **kwargs
            )
        except GoogleMapsServiceError as e:
            logger.exception("Distance matrix request failed")
            raise LocationServiceError(f"Distance matrix request failed: {e}") from e

    @with_error_handling()
    async def get_elevation(
        self, locations: list[tuple[float, float]], **kwargs: Any
    ) -> list[ElevationPoint]:
        """Get elevation data for locations.

        Args:
            locations: List of (lat, lng) coordinate tuples
            **kwargs: Additional parameters

        Returns:
            List of elevation points

        Raises:
            LocationServiceError: If elevation request fails
        """
        try:
            logger.debug("Getting elevation data")
            return await self.google_maps_service.get_elevation(locations, **kwargs)
        except GoogleMapsServiceError as e:
            logger.exception("Elevation request failed")
            raise LocationServiceError(f"Elevation request failed: {e}") from e

    @with_error_handling()
    async def get_timezone(
        self, location: tuple[float, float], timestamp: int | None = None, **kwargs: Any
    ) -> TimezoneInfo:
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
            logger.debug("Getting timezone data for location: %s", location)
            return await self.google_maps_service.get_timezone(
                location, timestamp, **kwargs
            )
        except GoogleMapsServiceError as e:
            logger.exception("Timezone request failed for location %s", location)
            raise LocationServiceError(f"Timezone request failed: {e}") from e


# Note: Use dependency injection. Construct LocationService in composition
# roots (e.g., ServiceRegistry or app lifespan) and pass to callers.
