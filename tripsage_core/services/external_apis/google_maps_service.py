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
from typing import Any, cast

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
from tripsage_core.services.external_apis.base_service import sanitize_response
from tripsage_core.utils.outbound import AsyncApiClient


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


class GoogleMapsService(AsyncApiClient):
    """Google Maps API service with typed results and async support."""

    def __init__(self, settings: Settings | None = None) -> None:
        """Initialize Google Maps service.

        Args:
            settings: Core application settings.
        """
        super().__init__()
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
            result_raw = await asyncio.to_thread(gm.geocode, address, **kwargs)  # type: ignore[reportAttributeAccessIssue]
            result_any = sanitize_response(result_raw)
            result = (
                cast(list[dict[str, Any]], result_any)
                if isinstance(result_any, list)
                else []
            )
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
            result_raw = await asyncio.to_thread(gm.reverse_geocode, latlng, **kwargs)  # type: ignore[reportAttributeAccessIssue]
            result_any = sanitize_response(result_raw)
            result = (
                cast(list[dict[str, Any]], result_any)
                if isinstance(result_any, list)
                else []
            )
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
            result_raw = await asyncio.to_thread(gm.places, **search_kwargs)  # type: ignore[reportAttributeAccessIssue]
            result_any = sanitize_response(result_raw)
            result = (
                cast(dict[str, Any], result_any) if isinstance(result_any, dict) else {}
            )
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
            result_raw = await asyncio.to_thread(gm.place, **details_kwargs)  # type: ignore[reportAttributeAccessIssue]
            result_any = sanitize_response(result_raw)
            result = (
                cast(dict[str, Any], result_any) if isinstance(result_any, dict) else {}
            )
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
            result_raw = await asyncio.to_thread(gm.directions, **directions_kwargs)  # type: ignore[reportAttributeAccessIssue]
            result_any = sanitize_response(result_raw)
            result = (
                cast(list[dict[str, Any]], result_any)
                if isinstance(result_any, list)
                else []
            )
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
            result_raw = await asyncio.to_thread(gm.distance_matrix, **matrix_kwargs)  # type: ignore[reportAttributeAccessIssue]
            result_any = sanitize_response(result_raw)
            result = (
                cast(dict[str, Any], result_any) if isinstance(result_any, dict) else {}
            )
            logger.debug(
                "Calculated distance matrix for %s origins to %s destinations",
                len(origins),
                len(destinations),
            )
            rows: list[DistanceMatrixRow] = []
            rows_raw_any = result.get("rows", [])
            rows_raw: list[Any] = (
                cast(list[Any], rows_raw_any) if isinstance(rows_raw_any, list) else []
            )
            for row_any in rows_raw:
                row_dict = (
                    cast(dict[str, Any], row_any) if isinstance(row_any, dict) else {}
                )
                elements_raw = row_dict.get("elements", [])
                elements: list[DistanceMatrixElement] = []
                elements_seq: list[Any] = (
                    cast(list[Any], elements_raw)
                    if isinstance(elements_raw, list)
                    else []
                )
                for el_any in elements_seq:
                    el = (
                        cast(dict[str, Any], el_any) if isinstance(el_any, dict) else {}
                    )
                    status = str(el.get("status", "UNKNOWN"))
                    dist_val = None
                    d_obj = el.get("distance", {})
                    if isinstance(d_obj, dict) and "value" in d_obj:
                        dv_any = cast(Any, d_obj["value"])
                        if isinstance(dv_any, (int, float)):
                            dist_val = int(dv_any)
                    dur_val = None
                    dd_obj = el.get("duration", {})
                    if isinstance(dd_obj, dict) and "value" in dd_obj:
                        tv_any = cast(Any, dd_obj["value"])
                        if isinstance(tv_any, (int, float)):
                            tv = tv_any
                            dur_val = int(tv)
                    elements.append(
                        DistanceMatrixElement(
                            status=status,
                            distance_meters=dist_val,
                            duration_seconds=dur_val,
                        )
                    )
                rows.append(DistanceMatrixRow(elements=elements))

            origin_addresses: list[str] = []
            origins_any = result.get("origin_addresses", [])
            if isinstance(origins_any, list):
                origins_list: list[Any] = cast(list[Any], origins_any)
                for s_any in origins_list:
                    if isinstance(s_any, str):
                        origin_addresses.extend([s_any])

            destination_addresses: list[str] = []
            dests_any = result.get("destination_addresses", [])
            if isinstance(dests_any, list):
                dests_list: list[Any] = cast(list[Any], dests_any)
                for s_any in dests_list:
                    if isinstance(s_any, str):
                        destination_addresses.extend([s_any])

            return DistanceMatrix(
                origin_addresses=origin_addresses,
                destination_addresses=destination_addresses,
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
        geometry = cast(dict[str, Any], item.get("geometry", {}))
        loc = cast(dict[str, Any] | None, geometry.get("location")) or {}
        coords = None
        if "lat" in loc and "lng" in loc:
            coords = Coordinates.model_validate(
                {
                    "latitude": float(loc["lat"]),
                    "longitude": float(loc["lng"]),
                    "altitude": None,
                }
            )

        components_any = item.get("address_components", [])
        address_components: dict[str, Any] = {}
        if isinstance(components_any, list):
            for c_any in cast(list[Any], components_any):
                c = cast(dict[str, Any], c_any) if isinstance(c_any, dict) else {}
                types = c.get("types", ["unknown"])
                key_obj = (
                    cast(Any, types[0])
                    if isinstance(types, list) and types
                    else "unknown"
                )
                key = key_obj if isinstance(key_obj, str) else "unknown"
                address_components[key] = c.get("long_name")
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
        geometry = cast(dict[str, Any], item.get("geometry", {}))
        loc = cast(dict[str, Any] | None, geometry.get("location")) or {}
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
        geometry = cast(dict[str, Any], item.get("geometry", {}))
        loc = cast(dict[str, Any] | None, geometry.get("location")) or {}
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
        legs_raw_any = route.get("legs", [])
        legs_raw: list[Any] = (
            cast(list[Any], legs_raw_any) if isinstance(legs_raw_any, list) else []
        )
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

        for leg_any in legs_raw:
            leg = cast(dict[str, Any], leg_any) if isinstance(leg_any, dict) else {}
            distance_val_num: int = 0
            d_obj = leg.get("distance", {})
            if isinstance(d_obj, dict) and "value" in d_obj:
                v_any = cast(Any, d_obj["value"])
                if isinstance(v_any, (int, float)):
                    distance_val_num = int(v_any)
            duration_val_num: int = 0
            dd_obj = leg.get("duration", {})
            if isinstance(dd_obj, dict) and "value" in dd_obj:
                v2_any = cast(Any, dd_obj["value"])
                if isinstance(v2_any, (int, float)):
                    duration_val_num = int(v2_any)
            total_distance_m += distance_val_num
            total_duration_s += duration_val_num

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
                    distance_meters=distance_val_num,
                    duration_seconds=duration_val_num,
                    start=start_place,
                    end=end_place,
                )
            )

        op_obj = route.get("overview_polyline", {})
        polyline: str | None = None
        if isinstance(op_obj, dict) and "points" in op_obj:
            p_any = cast(Any, op_obj["points"])
            polyline = p_any if isinstance(p_any, str) else None

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
