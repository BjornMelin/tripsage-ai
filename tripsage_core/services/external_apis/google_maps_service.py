"""
Google Maps direct SDK service with TripSage Core integration.

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

from tripsage_core.config import Settings, get_settings
from tripsage_core.exceptions.exceptions import CoreExternalAPIError as CoreAPIError
from tripsage_core.exceptions.exceptions import CoreServiceError

logger = logging.getLogger(__name__)


class GoogleMapsServiceError(CoreAPIError):
    """Exception raised for Google Maps service errors."""

    def __init__(self, message: str, original_error: Optional[Exception] = None):
        super().__init__(
            message=message,
            code="GOOGLE_MAPS_API_ERROR",
            api_service="GoogleMapsService",
            details={"original_error": str(original_error) if original_error else None},
        )
        self.original_error = original_error


class GoogleMapsService:
    """Direct Google Maps API service with async support and connection pooling."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        """
        Initialize Google Maps service.

        Args:
            settings: Core application settings
        """
        self.settings = settings or get_settings()
        self._client: Optional[googlemaps.Client] = None
        self._connected = False

    @property
    def client(self) -> googlemaps.Client:
        """Get or create Google Maps client with connection pooling."""
        if not self._client:
            # Get API key from core settings
            google_maps_key = getattr(self.settings, "google_maps_api_key", None)
            if not google_maps_key:
                raise CoreServiceError(
                    message="Google Maps API key not configured in settings",
                    code="MISSING_API_KEY",
                    service="GoogleMapsService",
                )

            # Get timeout settings from core configuration
            timeout = getattr(self.settings, "google_maps_timeout", 10)
            retry_timeout = getattr(self.settings, "google_maps_retry_timeout", 60)
            queries_per_second = getattr(self.settings, "google_maps_queries_per_second", 10)

            self._client = googlemaps.Client(
                key=google_maps_key.get_secret_value(),
                timeout=timeout,
                retry_timeout=retry_timeout,
                queries_per_second=queries_per_second,
                retry_over_query_limit=True,
                channel=None,  # Use default channel
            )

            self._connected = True
            logger.info("Initialized Google Maps client with direct SDK")

        return self._client

    async def connect(self) -> None:
        """Initialize the Google Maps client."""
        # The client property handles initialization
        _ = self.client

    async def disconnect(self) -> None:
        """Clean up resources."""
        self._client = None
        self._connected = False
        logger.info("Google Maps service disconnected")

    async def ensure_connected(self) -> None:
        """Ensure service is connected."""
        if not self._connected:
            await self.connect()

    async def geocode(self, address: str, **kwargs) -> List[Dict[str, Any]]:
        """
        Convert address to coordinates.

        Args:
            address: Address to geocode
            **kwargs: Additional parameters for geocoding

        Returns:
            List of geocoding results

        Raises:
            GoogleMapsServiceError: If geocoding fails
        """
        await self.ensure_connected()

        try:
            result = await asyncio.to_thread(self.client.geocode, address, **kwargs)
            logger.debug(f"Geocoded address '{address}' with {len(result)} results")
            return result
        except (ApiError, HTTPError, Timeout, TransportError) as e:
            logger.error(f"Geocoding failed for address '{address}': {e}")
            raise GoogleMapsServiceError(f"Geocoding failed: {e}", e) from e

    async def reverse_geocode(self, lat: float, lng: float, **kwargs) -> List[Dict[str, Any]]:
        """
        Convert coordinates to address.

        Args:
            lat: Latitude coordinate
            lng: Longitude coordinate
            **kwargs: Additional parameters for reverse geocoding

        Returns:
            List of reverse geocoding results

        Raises:
            GoogleMapsServiceError: If reverse geocoding fails
        """
        await self.ensure_connected()

        try:
            latlng = (lat, lng)
            result = await asyncio.to_thread(self.client.reverse_geocode, latlng, **kwargs)
            logger.debug(f"Reverse geocoded coordinates ({lat}, {lng}) with {len(result)} results")
            return result
        except (ApiError, HTTPError, Timeout, TransportError) as e:
            logger.error(f"Reverse geocoding failed for coordinates ({lat}, {lng}): {e}")
            raise GoogleMapsServiceError(f"Reverse geocoding failed: {e}", e) from e

    async def search_places(
        self,
        query: str,
        location: Optional[tuple] = None,
        radius: Optional[int] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Search for places using text search.

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
        await self.ensure_connected()

        try:
            # Build search parameters
            search_kwargs = {"query": query}
            if location:
                search_kwargs["location"] = location
            if radius:
                search_kwargs["radius"] = radius
            search_kwargs.update(kwargs)

            result = await asyncio.to_thread(self.client.places, **search_kwargs)
            logger.debug(f"Place search for '{query}' returned {len(result.get('results', []))} results")
            return result
        except (ApiError, HTTPError, Timeout, TransportError) as e:
            logger.error(f"Place search failed for query '{query}': {e}")
            raise GoogleMapsServiceError(f"Place search failed: {e}", e) from e

    async def get_place_details(self, place_id: str, fields: Optional[List[str]] = None, **kwargs) -> Dict[str, Any]:
        """
        Get detailed information about a specific place.

        Args:
            place_id: Google Maps place ID
            fields: Optional list of fields to include in response
            **kwargs: Additional parameters for place details

        Returns:
            Place details

        Raises:
            GoogleMapsServiceError: If place details request fails
        """
        await self.ensure_connected()

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
            raise GoogleMapsServiceError(f"Place details request failed: {e}", e) from e

    async def get_directions(
        self, origin: str, destination: str, mode: str = "driving", **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Get directions between two locations.

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
        await self.ensure_connected()

        try:
            directions_kwargs = {
                "origin": origin,
                "destination": destination,
                "mode": mode,
            }
            directions_kwargs.update(kwargs)

            result = await asyncio.to_thread(self.client.directions, **directions_kwargs)
            logger.debug(f"Retrieved directions from '{origin}' to '{destination}' ({mode})")
            return result
        except (ApiError, HTTPError, Timeout, TransportError) as e:
            logger.error(f"Directions request failed from '{origin}' to '{destination}': {e}")
            raise GoogleMapsServiceError(f"Directions request failed: {e}", e) from e

    async def distance_matrix(
        self,
        origins: List[str],
        destinations: List[str],
        mode: str = "driving",
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Calculate distance and time for multiple origins/destinations.

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
        await self.ensure_connected()

        try:
            matrix_kwargs = {
                "origins": origins,
                "destinations": destinations,
                "mode": mode,
            }
            matrix_kwargs.update(kwargs)

            result = await asyncio.to_thread(self.client.distance_matrix, **matrix_kwargs)
            logger.debug(f"Calculated distance matrix for {len(origins)} origins to {len(destinations)} destinations")
            return result
        except (ApiError, HTTPError, Timeout, TransportError) as e:
            logger.error(f"Distance matrix request failed: {e}")
            raise GoogleMapsServiceError(f"Distance matrix request failed: {e}", e) from e

    async def get_elevation(self, locations: List[tuple], **kwargs) -> List[Dict[str, Any]]:
        """
        Get elevation data for locations.

        Args:
            locations: List of (lat, lng) coordinate tuples
            **kwargs: Additional parameters for elevation

        Returns:
            List of elevation results

        Raises:
            GoogleMapsServiceError: If elevation request fails
        """
        await self.ensure_connected()

        try:
            result = await asyncio.to_thread(self.client.elevation, locations, **kwargs)
            logger.debug(f"Retrieved elevation data for {len(locations)} locations")
            return result
        except (ApiError, HTTPError, Timeout, TransportError) as e:
            logger.error(f"Elevation request failed: {e}")
            raise GoogleMapsServiceError(f"Elevation request failed: {e}", e) from e

    async def get_timezone(self, location: tuple, timestamp: Optional[int] = None, **kwargs) -> Dict[str, Any]:
        """
        Get timezone information for a location.

        Args:
            location: (lat, lng) coordinate tuple
            timestamp: Optional timestamp (defaults to current time)
            **kwargs: Additional parameters for timezone

        Returns:
            Timezone information

        Raises:
            GoogleMapsServiceError: If timezone request fails
        """
        await self.ensure_connected()

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
            raise GoogleMapsServiceError(f"Timezone request failed: {e}", e) from e

    async def health_check(self) -> bool:
        """
        Check if the Google Maps API is accessible.

        Returns:
            True if API is accessible, False otherwise
        """
        try:
            await self.ensure_connected()
            # Simple test geocode
            await self.geocode("New York", limit=1)
            return True
        except Exception as e:
            logger.error(f"Google Maps API health check failed: {e}")
            return False

    async def close(self) -> None:
        """Close the service and clean up resources."""
        await self.disconnect()


# Global service instance
_google_maps_service: Optional[GoogleMapsService] = None


async def get_google_maps_service() -> GoogleMapsService:
    """
    Get the global Google Maps service instance.

    Returns:
        GoogleMapsService instance
    """
    global _google_maps_service

    if _google_maps_service is None:
        _google_maps_service = GoogleMapsService()
        await _google_maps_service.connect()

    return _google_maps_service


async def close_google_maps_service() -> None:
    """Close the global Google Maps service instance."""
    global _google_maps_service

    if _google_maps_service:
        await _google_maps_service.close()
        _google_maps_service = None
