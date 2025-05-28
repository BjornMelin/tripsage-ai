"""
Google Maps direct SDK service.

This module provides a service class for direct Google Maps API integration,
replacing MCP wrapper with native SDK calls for improved performance.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

import googlemaps
from googlemaps.exceptions import (
    ApiError,
    HTTPError,
    Timeout,
    TransportError,
)

from tripsage.config.app_settings import get_settings
from tripsage.utils.decorators import with_error_handling

logger = logging.getLogger(__name__)


class GoogleMapsService:
    """Direct Google Maps API service with async support and connection pooling."""

    def __init__(self) -> None:
        """Initialize Google Maps service."""
        self.settings = get_settings()
        self._client: Optional[googlemaps.Client] = None

    @property
    def client(self) -> googlemaps.Client:
        """Get or create Google Maps client with connection pooling."""
        if not self._client:
            if not self.settings.google_maps_api_key:
                raise ValueError(
                    "Google Maps API key is required for direct integration"
                )

            self._client = googlemaps.Client(
                key=self.settings.google_maps_api_key.get_secret_value(),
                timeout=self.settings.google_maps_timeout,
                retry_timeout=self.settings.google_maps_retry_timeout,
                queries_per_second=self.settings.google_maps_queries_per_second,
                retry_over_query_limit=True,
                channel=None,  # Use default channel
            )
            logger.info("Initialized Google Maps client with direct SDK")

        return self._client

    @with_error_handling
    async def geocode(self, address: str, **kwargs) -> List[Dict[str, Any]]:
        """Convert address to coordinates.

        Args:
            address: Address to geocode
            **kwargs: Additional parameters for geocoding

        Returns:
            List of geocoding results

        Raises:
            GoogleMapsServiceError: If geocoding fails
        """
        try:
            result = await asyncio.to_thread(self.client.geocode, address, **kwargs)
            logger.debug(f"Geocoded address '{address}' with {len(result)} results")
            return result
        except (ApiError, HTTPError, Timeout, TransportError) as e:
            logger.error(f"Geocoding failed for address '{address}': {e}")
            raise GoogleMapsServiceError(f"Geocoding failed: {e}") from e

    @with_error_handling
    async def reverse_geocode(
        self, lat: float, lng: float, **kwargs
    ) -> List[Dict[str, Any]]:
        """Convert coordinates to address.

        Args:
            lat: Latitude coordinate
            lng: Longitude coordinate
            **kwargs: Additional parameters for reverse geocoding

        Returns:
            List of reverse geocoding results

        Raises:
            GoogleMapsServiceError: If reverse geocoding fails
        """
        try:
            latlng = (lat, lng)
            result = await asyncio.to_thread(
                self.client.reverse_geocode, latlng, **kwargs
            )
            logger.debug(
                f"Reverse geocoded coordinates ({lat}, {lng}) with "
                f"{len(result)} results"
            )
            return result
        except (ApiError, HTTPError, Timeout, TransportError) as e:
            logger.error(
                f"Reverse geocoding failed for coordinates ({lat}, {lng}): {e}"
            )
            raise GoogleMapsServiceError(f"Reverse geocoding failed: {e}") from e

    @with_error_handling
    async def search_places(
        self,
        query: str,
        location: Optional[tuple] = None,
        radius: Optional[int] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Search for places using text search.

        Args:
            query: Search query
            location: Optional center point for search (lat, lng tuple)
            radius: Optional search radius in meters
            **kwargs: Additional parameters for place search

        Returns:
            Place search results

        Raises:
            GoogleMapsServiceError: If place search fails
        """
        try:
            # Build search parameters
            search_kwargs = {"query": query}
            if location:
                search_kwargs["location"] = location
            if radius:
                search_kwargs["radius"] = radius
            search_kwargs.update(kwargs)

            result = await asyncio.to_thread(self.client.places, **search_kwargs)
            logger.debug(
                f"Place search for '{query}' returned "
                f"{len(result.get('results', []))} results"
            )
            return result
        except (ApiError, HTTPError, Timeout, TransportError) as e:
            logger.error(f"Place search failed for query '{query}': {e}")
            raise GoogleMapsServiceError(f"Place search failed: {e}") from e

    @with_error_handling
    async def get_place_details(
        self, place_id: str, fields: Optional[List[str]] = None, **kwargs
    ) -> Dict[str, Any]:
        """Get detailed information about a specific place.

        Args:
            place_id: Google Maps place ID
            fields: Optional list of fields to include in response
            **kwargs: Additional parameters for place details

        Returns:
            Place details

        Raises:
            GoogleMapsServiceError: If place details request fails
        """
        try:
            details_kwargs = {"place_id": place_id}
            if fields:
                details_kwargs["fields"] = fields
            details_kwargs.update(kwargs)

            result = await asyncio.to_thread(self.client.place, **details_kwargs)
            logger.debug(f"Retrieved place details for place_id '{place_id}'")
            return result
        except (ApiError, HTTPError, Timeout, TransportError) as e:
            logger.error(f"Place details request failed for place_id '{place_id}': {e}")
            raise GoogleMapsServiceError(f"Place details request failed: {e}") from e

    @with_error_handling
    async def get_directions(
        self, origin: str, destination: str, mode: str = "driving", **kwargs
    ) -> List[Dict[str, Any]]:
        """Get directions between two locations.

        Args:
            origin: Origin address or coordinates
            destination: Destination address or coordinates
            mode: Travel mode (driving, walking, bicycling, transit)
            **kwargs: Additional parameters for directions

        Returns:
            List of route directions

        Raises:
            GoogleMapsServiceError: If directions request fails
        """
        try:
            directions_kwargs = {
                "origin": origin,
                "destination": destination,
                "mode": mode,
            }
            directions_kwargs.update(kwargs)

            result = await asyncio.to_thread(
                self.client.directions, **directions_kwargs
            )
            logger.debug(
                f"Retrieved directions from '{origin}' to '{destination}' ({mode})"
            )
            return result
        except (ApiError, HTTPError, Timeout, TransportError) as e:
            logger.error(
                f"Directions request failed from '{origin}' to '{destination}': {e}"
            )
            raise GoogleMapsServiceError(f"Directions request failed: {e}") from e

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
            **kwargs: Additional parameters for distance matrix

        Returns:
            Distance matrix results

        Raises:
            GoogleMapsServiceError: If distance matrix request fails
        """
        try:
            matrix_kwargs = {
                "origins": origins,
                "destinations": destinations,
                "mode": mode,
            }
            matrix_kwargs.update(kwargs)

            result = await asyncio.to_thread(
                self.client.distance_matrix, **matrix_kwargs
            )
            logger.debug(
                f"Calculated distance matrix for {len(origins)} origins to "
                f"{len(destinations)} destinations"
            )
            return result
        except (ApiError, HTTPError, Timeout, TransportError) as e:
            logger.error(f"Distance matrix request failed: {e}")
            raise GoogleMapsServiceError(f"Distance matrix request failed: {e}") from e

    @with_error_handling
    async def get_elevation(
        self, locations: List[tuple], **kwargs
    ) -> List[Dict[str, Any]]:
        """Get elevation data for locations.

        Args:
            locations: List of (lat, lng) coordinate tuples
            **kwargs: Additional parameters for elevation

        Returns:
            List of elevation results

        Raises:
            GoogleMapsServiceError: If elevation request fails
        """
        try:
            result = await asyncio.to_thread(self.client.elevation, locations, **kwargs)
            logger.debug(f"Retrieved elevation data for {len(locations)} locations")
            return result
        except (ApiError, HTTPError, Timeout, TransportError) as e:
            logger.error(f"Elevation request failed: {e}")
            raise GoogleMapsServiceError(f"Elevation request failed: {e}") from e

    @with_error_handling
    async def get_timezone(
        self, location: tuple, timestamp: Optional[int] = None, **kwargs
    ) -> Dict[str, Any]:
        """Get timezone information for a location.

        Args:
            location: (lat, lng) coordinate tuple
            timestamp: Optional timestamp (defaults to current time)
            **kwargs: Additional parameters for timezone

        Returns:
            Timezone information

        Raises:
            GoogleMapsServiceError: If timezone request fails
        """
        try:
            timezone_kwargs = {"location": location}
            if timestamp:
                timezone_kwargs["timestamp"] = timestamp
            timezone_kwargs.update(kwargs)

            result = await asyncio.to_thread(self.client.timezone, **timezone_kwargs)
            logger.debug(f"Retrieved timezone data for location {location}")
            return result
        except (ApiError, HTTPError, Timeout, TransportError) as e:
            logger.error(f"Timezone request failed for location {location}: {e}")
            raise GoogleMapsServiceError(f"Timezone request failed: {e}") from e


class GoogleMapsServiceError(Exception):
    """Exception raised for Google Maps service errors."""

    pass


# Singleton instance for global use
google_maps_service = GoogleMapsService()


def get_google_maps_service() -> GoogleMapsService:
    """Get the global Google Maps service instance.

    Returns:
        GoogleMapsService instance
    """
    return google_maps_service
