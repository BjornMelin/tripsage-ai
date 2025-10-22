"""Google Maps service using the official Python client with typed results.

This module provides a thin, typed wrapper around the official
`googlemaps` Python client. It standardizes responses into Pydantic
models used across TripSage and removes custom HTTP code paths.

Design goals:
- Rely on `googlemaps` features; no bespoke HTTP.
- Typed API: return Pydantic v2 models for safety and clarity.
- Async-friendly: run blocking client calls in a worker thread.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import googlemaps
from googlemaps.exceptions import (
    ApiError,
    HTTPError,
    Timeout,
    TransportError,
)

from tripsage_core.config import Settings, get_settings
from tripsage_core.exceptions.exceptions import (
    CoreExternalAPIError as CoreAPIError,
    CoreServiceError,
)
from tripsage_core.models.api.maps_models import (
    DirectionsLeg,
    DirectionsResult,
    DistanceMatrix,
    DistanceMatrixElement,
    DistanceMatrixRow,
    ElevationPoint,
    PlaceDetails,
    PlaceSummary,
    TimezoneInfo,
)
from tripsage_core.models.schemas_common.geographic import (
    Address,
    Coordinates,
    Place,
    Route,
)


logger = logging.getLogger(__name__)


class GoogleMapsServiceError(CoreAPIError):
    """Exception raised for Google Maps service errors."""

    def __init__(self, message: str, original_error: Exception | None = None):
        """Construct the error with an optional original exception."""
        super().__init__(
            message=message,
            code="GOOGLE_MAPS_API_ERROR",
            api_service="GoogleMapsService",
            details={"original_error": str(original_error) if original_error else None},
        )
        self.original_error = original_error


class GoogleMapsService:
    """Google Maps API service with typed results and async support."""

    def __init__(self, settings: Settings | None = None) -> None:
        """Initialize Google Maps service.

        Args:
            settings: Core application settings.
        """
        self.settings = settings or get_settings()
        self._client: googlemaps.Client | None = None
        self._connected = False

    @property
    def client(self) -> googlemaps.Client:
        """Get or create a configured Google Maps client.

        Returns:
            Configured `googlemaps.Client` instance.

        Raises:
            CoreServiceError: If the API key is not configured.
        """
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
            timeout = getattr(self.settings, "google_maps_timeout", 10.0)
            retry_timeout = getattr(self.settings, "google_maps_retry_timeout", 60)
            queries_per_second = getattr(
                self.settings, "google_maps_queries_per_second", 10
            )

            self._client = googlemaps.Client(
                key=google_maps_key.get_secret_value(),
                timeout=timeout,
                retry_timeout=retry_timeout,
                queries_per_second=queries_per_second,
                retry_over_query_limit=True,
                channel=None,  # Use default channel
            )

            self._connected = True
            logger.info("Initialized Google Maps client")

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

    async def geocode(self, address: str, **kwargs: Any) -> list[Place]:
        """Geocode an address to coordinates.

        Args:
            address: Address to geocode.
            **kwargs: Additional parameters forwarded to the SDK.

        Returns:
            A list of normalized places for matching results.

        Raises:
            GoogleMapsServiceError: If geocoding fails.
        """
        await self.ensure_connected()

        try:
            gm: Any = self.client
            result = await asyncio.to_thread(gm.geocode, address, **kwargs)  # type: ignore[reportAttributeAccessIssue]
            logger.debug("Geocoded address '%s' with %s results", address, len(result))
            mapper = self._map_geocode_result
            return [mapper(item) for item in result]
        except (ApiError, HTTPError, Timeout, TransportError) as e:
            logger.exception("Geocoding failed for address '%s'", address)
            raise GoogleMapsServiceError(f"Geocoding failed: {e}", e) from e

    async def reverse_geocode(
        self, lat: float, lng: float, **kwargs: Any
    ) -> list[Place]:
        """Reverse geocode coordinates to an address.

        Args:
            lat: Latitude.
            lng: Longitude.
            **kwargs: Additional parameters forwarded to the SDK.

        Returns:
            A list of normalized places for matching results.

        Raises:
            GoogleMapsServiceError: If reverse geocoding fails.
        """
        await self.ensure_connected()

        try:
            latlng = (lat, lng)
            gm: Any = self.client
            result = await asyncio.to_thread(gm.reverse_geocode, latlng, **kwargs)  # type: ignore[reportAttributeAccessIssue]
            logger.debug(
                "Reverse geocoded coordinates (%s, %s) with %s results",
                lat,
                lng,
                len(result),
            )
            mapper = self._map_geocode_result
            return [mapper(item) for item in result]
        except (ApiError, HTTPError, Timeout, TransportError) as e:
            logger.exception(
                "Reverse geocoding failed for coordinates (%s, %s)", lat, lng
            )
            raise GoogleMapsServiceError(f"Reverse geocoding failed: {e}", e) from e

    async def search_places(
        self,
        query: str,
        location: tuple[float, float] | None = None,
        radius: int | None = None,
        **kwargs: Any,
    ) -> list[PlaceSummary]:
        """Text-search for places.

        Args:
            query: Search query string.
            location: Optional center point for the search.
            radius: Optional search radius in meters.
            **kwargs: Additional parameters forwarded to the SDK.

        Returns:
            A list of summarized places.

        Raises:
            GoogleMapsServiceError: If place search fails.
        """
        await self.ensure_connected()

        try:
            # Build search parameters
            search_kwargs: dict[str, Any] = {"query": query}
            if location:
                search_kwargs["location"] = location
            if radius:
                search_kwargs["radius"] = radius
            search_kwargs.update(kwargs)

            gm: Any = self.client
            result = await asyncio.to_thread(gm.places, **search_kwargs)  # type: ignore[reportAttributeAccessIssue]
            items = result.get("results", [])
            logger.debug("Place search for '%s' returned %s results", query, len(items))
            mapper = self._map_place_summary
            return [mapper(item) for item in items]
        except (ApiError, HTTPError, Timeout, TransportError) as e:
            logger.exception("Place search failed for query '%s'", query)
            raise GoogleMapsServiceError(f"Place search failed: {e}", e) from e

    async def get_place_details(
        self, place_id: str, fields: list[str] | None = None, **kwargs: Any
    ) -> PlaceDetails:
        """Get detailed information about a specific place.

        Args:
            place_id: Google Maps place ID.
            fields: Optional list of fields to request.
            **kwargs: Additional parameters forwarded to the SDK.

        Returns:
            Normalized detailed place information.

        Raises:
            GoogleMapsServiceError: If the request fails.
        """
        await self.ensure_connected()

        try:
            details_kwargs: dict[str, Any] = {"place_id": place_id}
            if fields:
                details_kwargs["fields"] = fields
            details_kwargs.update(kwargs)

            gm: Any = self.client
            result = await asyncio.to_thread(gm.place, **details_kwargs)  # type: ignore[reportAttributeAccessIssue]
            logger.debug("Retrieved place details for place_id '%s'", place_id)
            data = result.get("result", {})
            det_mapper = self._map_place_details
            return det_mapper(data)
        except (ApiError, HTTPError, Timeout, TransportError) as e:
            logger.exception("Place details request failed for place_id '%s'", place_id)
            raise GoogleMapsServiceError(f"Place details request failed: {e}", e) from e

    async def get_directions(
        self, origin: str, destination: str, mode: str = "driving", **kwargs: Any
    ) -> list[DirectionsResult]:
        """Get directions between two locations.

        Args:
            origin: Origin address or coordinates.
            destination: Destination address or coordinates.
            mode: Travel mode (driving, walking, bicycling, transit).
            **kwargs: Additional parameters forwarded to the SDK.

        Returns:
            A list of normalized routes (usually 1-3).

        Raises:
            GoogleMapsServiceError: If directions request fails.
        """
        await self.ensure_connected()

        try:
            directions_kwargs: dict[str, Any] = {
                "origin": origin,
                "destination": destination,
                "mode": mode,
            }
            directions_kwargs.update(kwargs)

            gm: Any = self.client
            result = await asyncio.to_thread(gm.directions, **directions_kwargs)  # type: ignore[reportAttributeAccessIssue]
            logger.debug(
                "Retrieved directions from '%s' to '%s' (%s)", origin, destination, mode
            )
            route_mapper = self._map_directions_route
            return [route_mapper(route) for route in result]
        except (ApiError, HTTPError, Timeout, TransportError) as e:
            logger.exception(
                "Directions request failed from '%s' to '%s'", origin, destination
            )
            raise GoogleMapsServiceError(f"Directions request failed: {e}", e) from e

    async def distance_matrix(
        self,
        origins: list[str],
        destinations: list[str],
        mode: str = "driving",
        **kwargs: Any,
    ) -> DistanceMatrix:
        """Calculate distance/time for multiple origin/destination pairs.

        Args:
            origins: Origins as addresses or "lat,lng" strings.
            destinations: Destinations as addresses or "lat,lng" strings.
            mode: Travel mode (driving, walking, bicycling, transit).
            **kwargs: Additional parameters forwarded to the SDK.

        Returns:
            A normalized distance matrix.

        Raises:
            GoogleMapsServiceError: If the matrix request fails.
        """
        await self.ensure_connected()

        try:
            matrix_kwargs: dict[str, Any] = {
                "origins": origins,
                "destinations": destinations,
                "mode": mode,
            }
            matrix_kwargs.update(kwargs)

            gm: Any = self.client
            result = await asyncio.to_thread(gm.distance_matrix, **matrix_kwargs)  # type: ignore[reportAttributeAccessIssue]
            logger.debug(
                "Calculated distance matrix for %s origins to %s destinations",
                len(origins),
                len(destinations),
            )
            rows = [
                DistanceMatrixRow(
                    elements=[
                        DistanceMatrixElement(
                            status=el.get("status", "UNKNOWN"),
                            distance_meters=(
                                (el.get("distance", {}) or {}).get("value")
                            ),
                            duration_seconds=(
                                (el.get("duration", {}) or {}).get("value")
                            ),
                        )
                        for el in row.get("elements", [])
                    ]
                )
                for row in result.get("rows", [])
            ]
            return DistanceMatrix(
                origin_addresses=result.get("origin_addresses", []),
                destination_addresses=result.get("destination_addresses", []),
                rows=rows,
            )
        except (ApiError, HTTPError, Timeout, TransportError) as e:
            logger.exception("Distance matrix request failed")
            raise GoogleMapsServiceError(
                f"Distance matrix request failed: {e}", e
            ) from e

    async def get_elevation(
        self, locations: list[tuple[float, float]], **kwargs: Any
    ) -> list[ElevationPoint]:
        """Get elevation data for locations.

        Args:
            locations: List of (lat, lng) coordinate tuples.
            **kwargs: Additional parameters forwarded to the SDK.

        Returns:
            A list of normalized elevation points.

        Raises:
            GoogleMapsServiceError: If the elevation request fails.
        """
        await self.ensure_connected()

        try:
            gm: Any = self.client
            result = await asyncio.to_thread(gm.elevation, locations, **kwargs)  # type: ignore[reportAttributeAccessIssue]
            logger.debug("Retrieved elevation data for %s locations", len(locations))
            points: list[ElevationPoint] = []
            for item in result:
                loc = item.get("location", {})
                lat_val = loc.get("lat")
                lng_val = loc.get("lng")
                if lat_val is None or lng_val is None:
                    continue
                points.append(
                    ElevationPoint(
                        location=Coordinates.model_validate(
                            {
                                "latitude": float(lat_val),
                                "longitude": float(lng_val),
                                "altitude": None,
                            }
                        ),
                        elevation_meters=float(item.get("elevation", 0.0)),
                    )
                )
            return points
        except (ApiError, HTTPError, Timeout, TransportError) as e:
            logger.exception("Elevation request failed")
            raise GoogleMapsServiceError(f"Elevation request failed: {e}", e) from e

    async def get_timezone(
        self, location: tuple[float, float], timestamp: int | None = None, **kwargs: Any
    ) -> TimezoneInfo:
        """Get timezone information for a location.

        Args:
            location: (lat, lng) coordinate tuple.
            timestamp: Optional timestamp (defaults to current time).
            **kwargs: Additional parameters forwarded to the SDK.

        Returns:
            Normalized timezone information.

        Raises:
            GoogleMapsServiceError: If timezone request fails.
        """
        await self.ensure_connected()

        try:
            timezone_kwargs: dict[str, Any] = {"location": location}
            if timestamp:
                timezone_kwargs["timestamp"] = timestamp
            timezone_kwargs.update(kwargs)

            gm: Any = self.client
            result = await asyncio.to_thread(gm.timezone, **timezone_kwargs)  # type: ignore[reportAttributeAccessIssue]
            logger.debug("Retrieved timezone data for location %s", location)
            return TimezoneInfo(
                time_zone_id=result.get("timeZoneId", "UTC"),
                raw_offset=int(result.get("rawOffset", 0)),
                dst_offset=int(result.get("dstOffset", 0)),
            )
        except (ApiError, HTTPError, Timeout, TransportError) as e:
            logger.exception("Timezone request failed for location %s", location)
            raise GoogleMapsServiceError(f"Timezone request failed: {e}", e) from e

    async def health_check(self) -> bool:
        """Check if the Google Maps API is accessible.

        Returns:
            True if API is accessible, False otherwise.
        """
        try:
            await self.ensure_connected()
            # Simple test geocode
            results = await self.geocode("New York", limit=1)
            return bool(results)
        except Exception:
            logger.exception("Google Maps API health check failed")
            return False

    async def close(self) -> None:
        """Close the service and clean up resources."""
        await self.disconnect()

    # DI: Construct GoogleMapsService in composition root; no module singletons.

    # --- Internal mappers -------------------------------------------------

    def _map_geocode_result(self, item: dict[str, Any]) -> Place:
        """Map a geocoding result item to a `Place` model."""
        geometry = item.get("geometry", {})
        loc = geometry.get("location") or {}
        coords = None
        if "lat" in loc and "lng" in loc:
            coords = Coordinates.model_validate(
                {
                    "latitude": float(loc["lat"]),
                    "longitude": float(loc["lng"]),
                    "altitude": None,
                }
            )

        address_components = {
            c.get("types", ["unknown"])[0]: c.get("long_name")
            for c in item.get("address_components", [])
        }
        address = Address.model_validate(
            {
                "street": None,
                "city": address_components.get("locality")
                or address_components.get("postal_town"),
                "state": address_components.get("administrative_area_level_1"),
                "country": address_components.get("country"),
                "postal_code": address_components.get("postal_code"),
                "formatted": item.get("formatted_address"),
            }
        )

        return Place.model_validate(
            {
                "name": item.get("formatted_address", "Unknown"),
                "coordinates": coords,
                "address": address,
                "place_id": item.get("place_id"),
                "place_type": (item.get("types") or [None])[0],
            }
        )

    def _map_place_summary(self, item: dict[str, Any]) -> PlaceSummary:
        """Map a Places text search item to `PlaceSummary`."""
        geometry = item.get("geometry", {})
        loc = geometry.get("location") or {}
        coords = None
        if "lat" in loc and "lng" in loc:
            coords = Coordinates.model_validate(
                {
                    "latitude": float(loc["lat"]),
                    "longitude": float(loc["lng"]),
                    "altitude": None,
                }
            )

        address = Address.model_validate({"formatted": item.get("formatted_address")})
        place = Place.model_validate(
            {
                "name": item.get("name", "Unknown"),
                "coordinates": coords,
                "address": address,
                "place_id": item.get("place_id"),
                "place_type": (item.get("types") or [None])[0],
            }
        )
        rating_val = item.get("rating")
        return PlaceSummary(
            place=place,
            rating=(
                float(rating_val) if isinstance(rating_val, (int, float)) else None
            ),
            price_level=item.get("price_level"),
            user_ratings_total=item.get("user_ratings_total"),
            types=item.get("types"),
            raw=item,
        )

    def _map_place_details(self, item: dict[str, Any]) -> PlaceDetails:
        """Map a Place Details response to `PlaceDetails`."""
        geometry = item.get("geometry", {})
        loc = geometry.get("location") or {}
        coords = None
        if "lat" in loc and "lng" in loc:
            coords = Coordinates.model_validate(
                {
                    "latitude": float(loc["lat"]),
                    "longitude": float(loc["lng"]),
                    "altitude": None,
                }
            )

        address = Address.model_validate({"formatted": item.get("formatted_address")})
        place = Place.model_validate(
            {
                "name": item.get("name", "Unknown"),
                "coordinates": coords,
                "address": address,
                "place_id": item.get("place_id"),
                "place_type": (item.get("types") or [None])[0],
            }
        )

        rating_val = item.get("rating")
        return PlaceDetails(
            place=place,
            rating=(
                float(rating_val) if isinstance(rating_val, (int, float)) else None
            ),
            price_level=item.get("price_level"),
            opening_hours=item.get("opening_hours"),
            phone_number=item.get("formatted_phone_number"),
            website=item.get("website"),
            photos=item.get("photos"),
            types=item.get("types"),
            raw=item,
        )

    def _map_directions_route(self, route: dict[str, Any]) -> DirectionsResult:
        """Map a directions route to `DirectionsResult`."""
        legs_raw = route.get("legs", [])
        legs: list[DirectionsLeg] = []
        total_distance_m = 0
        total_duration_s = 0

        start_place: Place | None = None
        end_place: Place | None = None

        def _coords(obj: dict[str, Any] | None) -> Coordinates | None:
            if not obj:
                return None
            if "lat" in obj and "lng" in obj:
                return Coordinates.model_validate(
                    {
                        "latitude": float(obj["lat"]),
                        "longitude": float(obj["lng"]),
                        "altitude": None,
                    }
                )
            return None

        for leg in legs_raw:
            distance_val = (leg.get("distance", {}) or {}).get("value")
            duration_val = (leg.get("duration", {}) or {}).get("value")
            total_distance_m += int(distance_val or 0)
            total_duration_s += int(duration_val or 0)

            start_place = Place.model_validate(
                {
                    "name": leg.get("start_address", ""),
                    "coordinates": _coords(leg.get("start_location")),
                    "address": Address.model_validate(
                        {"formatted": leg.get("start_address")}
                    ),
                    "place_id": None,
                    "place_type": None,
                }
            )
            end_place = Place.model_validate(
                {
                    "name": leg.get("end_address", ""),
                    "coordinates": _coords(leg.get("end_location")),
                    "address": Address.model_validate(
                        {"formatted": leg.get("end_address")}
                    ),
                    "place_id": None,
                    "place_type": None,
                }
            )
            legs.append(
                DirectionsLeg(
                    distance_meters=int(distance_val or 0),
                    duration_seconds=int(duration_val or 0),
                    start=start_place,
                    end=end_place,
                )
            )

        polyline = (route.get("overview_polyline", {}) or {}).get("points")

        route_summary = Route(
            origin=start_place
            or Place.model_validate(
                {
                    "name": "",
                    "coordinates": None,
                    "address": None,
                    "place_id": None,
                    "place_type": None,
                }
            ),
            destination=end_place
            or Place.model_validate(
                {
                    "name": "",
                    "coordinates": None,
                    "address": None,
                    "place_id": None,
                    "place_type": None,
                }
            ),
            distance_km=(total_distance_m / 1000.0) if total_distance_m else None,
            duration_minutes=int(total_duration_s / 60) if total_duration_s else None,
            waypoints=None,
        )

        return DirectionsResult(
            route=route_summary, legs=legs, polyline=polyline, raw=route
        )
