"""Typed models for Google Maps operations.

These Pydantic v2 models represent the subset of fields we use from
Google Maps Platform responses. They map closely to TripSage domain models
to minimize translation and duplication while keeping strong typing.
"""

from __future__ import annotations

from typing import Any, Final

from pydantic import Field

from tripsage_core.models.api._export_helpers import auto_all
from tripsage_core.models.base_core_model import TripSageModel
from tripsage_core.models.schemas_common.geographic import (
    Coordinates,
    Place,
    Route,
)


class PlaceSummary(TripSageModel):
    """Compact place representation for search results.

    Attributes:
        place: Normalized place (name, coordinates, address, place_id, type).
        rating: Average user rating (0.0-5.0).
        price_level: Price level (0-4) per Google semantics.
        user_ratings_total: Number of user ratings.
        types: Raw Google place types (for filters/telemetry).
        raw: Optional raw provider payload for trace/debug.
    """

    place: Place
    rating: float | None = Field(default=None, ge=0.0, le=5.0)
    price_level: int | None = Field(default=None, ge=0, le=4)
    user_ratings_total: int | None = Field(default=None, ge=0)
    types: list[str] | None = None
    raw: dict[str, Any] | None = None


class PlaceDetails(TripSageModel):
    """Detailed place information.

    Attributes:
        place: Normalized place with id/coords/address.
        rating: Average user rating (0.0-5.0).
        price_level: Price level (0-4).
        opening_hours: Provider-specific opening hours payload (kept opaque).
        phone_number: Formatted phone number if available.
        website: Public website URL.
        photos: Provider photo metadata (opaque list for caller to resolve).
        types: Raw Google place types.
        raw: Raw provider payload (debug/trace only).
    """

    place: Place
    rating: float | None = Field(default=None, ge=0.0, le=5.0)
    price_level: int | None = Field(default=None, ge=0, le=4)
    opening_hours: dict[str, Any] | None = None
    phone_number: str | None = None
    website: str | None = None
    photos: list[dict[str, Any]] | None = None
    types: list[str] | None = None
    raw: dict[str, Any] | None = None


class DirectionsLeg(TripSageModel):
    """Single leg in a directions route."""

    distance_meters: int | None = Field(default=None, ge=0)
    duration_seconds: int | None = Field(default=None, ge=0)
    start: Place | None = None
    end: Place | None = None


class DirectionsResult(TripSageModel):
    """Normalized directions result for a single route.

    Attributes:
        route: High-level route summary (origin, destination, distance/duration).
        legs: Route legs with metrics per segment.
        polyline: Encoded overview polyline.
        raw: Raw provider payload (debug/trace only).
    """

    route: Route
    legs: list[DirectionsLeg] = Field(default_factory=list)
    polyline: str | None = None
    raw: dict[str, Any] | None = None


class DistanceMatrixElement(TripSageModel):
    """Single origin→destination matrix element."""

    status: str
    distance_meters: int | None = Field(default=None, ge=0)
    duration_seconds: int | None = Field(default=None, ge=0)


class DistanceMatrixRow(TripSageModel):
    """Row in a distance matrix (for one origin)."""

    elements: list[DistanceMatrixElement]


class DistanceMatrix(TripSageModel):
    """Distance matrix across origins x destinations."""

    origin_addresses: list[str]
    destination_addresses: list[str]
    rows: list[DistanceMatrixRow]


class TimezoneInfo(TripSageModel):
    """Timezone info for a location."""

    time_zone_id: str
    raw_offset: int
    dst_offset: int


class ElevationPoint(TripSageModel):
    """Elevation data for a coordinate."""

    location: Coordinates
    elevation_meters: float


__all__: Final[list[str]] = auto_all(  # pyright: ignore[reportUnsupportedDunderAll]
    __name__, globals()
)
