"""
Pydantic models for Google Maps MCP client.

This module defines the parameter and response models for the Google Maps MCP Client,
providing proper validation and type safety.
"""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class BaseParams(BaseModel):
    """Base model for all parameter models."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")


class BaseResponse(BaseModel):
    """Base model for all response models."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class TravelMode(str, Enum):
    """Travel mode for directions."""

    DRIVING = "driving"
    WALKING = "walking"
    BICYCLING = "bicycling"
    TRANSIT = "transit"


class PlaceType(str, Enum):
    """Place types for place search."""

    AIRPORT = "airport"
    AMUSEMENT_PARK = "amusement_park"
    AQUARIUM = "aquarium"
    ART_GALLERY = "art_gallery"
    ATM = "atm"
    BAKERY = "bakery"
    BANK = "bank"
    BAR = "bar"
    BEAUTY_SALON = "beauty_salon"
    BOOK_STORE = "book_store"
    BUS_STATION = "bus_station"
    CAFE = "cafe"
    CAMPGROUND = "campground"
    CAR_RENTAL = "car_rental"
    CASINO = "casino"
    LODGING = "lodging"
    MOVIE_THEATER = "movie_theater"
    MUSEUM = "museum"
    NIGHT_CLUB = "night_club"
    PARK = "park"
    PARKING = "parking"
    RESTAURANT = "restaurant"
    SHOPPING_MALL = "shopping_mall"
    SPA = "spa"
    STADIUM = "stadium"
    SUBWAY_STATION = "subway_station"
    SUPERMARKET = "supermarket"
    TOURIST_ATTRACTION = "tourist_attraction"
    TRAIN_STATION = "train_station"
    ZOO = "zoo"


class PlaceField(str, Enum):
    """Fields to include in place details response."""

    ADDRESS_COMPONENT = "address_component"
    BUSINESS_STATUS = "business_status"
    FORMATTED_ADDRESS = "formatted_address"
    GEOMETRY = "geometry"
    ICON = "icon"
    NAME = "name"
    PERMANENTLY_CLOSED = "permanently_closed"
    PHOTO = "photo"
    PLACE_ID = "place_id"
    PLUS_CODE = "plus_code"
    TYPE = "type"
    URL = "url"
    UTC_OFFSET = "utc_offset"
    VICINITY = "vicinity"
    WEBSITE = "website"
    PRICE_LEVEL = "price_level"
    RATING = "rating"
    REVIEW = "review"
    USER_RATINGS_TOTAL = "user_ratings_total"
    OPENING_HOURS = "opening_hours"


class RankBy(str, Enum):
    """Ranking for nearby search."""

    PROMINENCE = "prominence"
    DISTANCE = "distance"


class GeocodeParams(BaseParams):
    """Parameters for geocoding requests."""

    address: Optional[str] = Field(None, description="Address to geocode")
    place_id: Optional[str] = Field(None, description="Place ID to geocode")
    components: Optional[Dict[str, str]] = Field(None, description="Component filters")

    @model_validator(mode="after")
    def validate_params(self) -> "GeocodeParams":
        """Validate that either address or place_id is provided."""
        if not self.address and not self.place_id:
            raise ValueError("Either address or place_id must be provided")
        return self


class ReverseGeocodeParams(BaseParams):
    """Parameters for reverse geocoding requests."""

    lat: float = Field(..., description="Latitude coordinate")
    lng: float = Field(..., description="Longitude coordinate")
    result_type: Optional[str] = Field(None, description="Filter result types")
    location_type: Optional[str] = Field(None, description="Filter location types")


class PlaceSearchParams(BaseParams):
    """Parameters for place search requests."""

    query: Optional[str] = Field(None, description="Search query")
    location: Optional[str] = Field(None, description="Location around which to search")
    radius: Optional[int] = Field(
        None, ge=1, le=50000, description="Search radius in meters"
    )
    type: Optional[PlaceType] = Field(None, description="Type of place to search for")
    keyword: Optional[str] = Field(None, description="Keywords to match in places")
    language: Optional[str] = Field(None, description="Language code for results")
    min_price: Optional[int] = Field(
        None, ge=0, le=4, description="Minimum price level (0-4)"
    )
    max_price: Optional[int] = Field(
        None, ge=0, le=4, description="Maximum price level (0-4)"
    )
    open_now: Optional[bool] = Field(None, description="Whether place is open now")
    rank_by: Optional[RankBy] = Field(None, description="Ranking method")

    @model_validator(mode="after")
    def validate_params(self) -> "PlaceSearchParams":
        """Validate required parameter combinations."""
        if self.rank_by == RankBy.DISTANCE and not self.location:
            raise ValueError("Location is required when rank_by is 'distance'")

        if not self.query and not (self.location and (self.radius or self.rank_by)):
            raise ValueError("Either query or location with radius/rank_by is required")

        return self


class PlaceDetailsParams(BaseParams):
    """Parameters for place details requests."""

    place_id: str = Field(..., description="Google Maps place ID")
    fields: Optional[List[PlaceField]] = Field(
        None, description="Fields to include in response"
    )
    language: Optional[str] = Field(None, description="Language code for results")


class DirectionsParams(BaseParams):
    """Parameters for directions requests."""

    origin: str = Field(..., description="Origin address or coordinates")
    destination: str = Field(..., description="Destination address or coordinates")
    mode: TravelMode = Field(TravelMode.DRIVING, description="Travel mode")
    waypoints: Optional[List[str]] = Field(
        None, description="Waypoints to include in route"
    )
    alternatives: Optional[bool] = Field(None, description="Request alternative routes")
    avoid: Optional[List[str]] = Field(
        None, description="Features to avoid (tolls, highways, ferries)"
    )
    units: Optional[str] = Field(None, description="Unit system (metric or imperial)")
    arrival_time: Optional[int] = Field(None, description="Desired arrival time")
    departure_time: Optional[int] = Field(None, description="Desired departure time")
    traffic_model: Optional[str] = Field(
        None, description="Traffic model for predictions"
    )
    transit_mode: Optional[List[str]] = Field(
        None, description="Preferred transit modes"
    )
    transit_routing_preference: Optional[str] = Field(
        None, description="Transit routing preferences"
    )


class DistanceMatrixParams(BaseParams):
    """Parameters for distance matrix requests."""

    origins: List[str] = Field(
        ..., min_length=1, description="Origin addresses or coordinates"
    )
    destinations: List[str] = Field(
        ..., min_length=1, description="Destination addresses or coordinates"
    )
    mode: TravelMode = Field(TravelMode.DRIVING, description="Travel mode")
    avoid: Optional[List[str]] = Field(
        None, description="Features to avoid (tolls, highways, ferries)"
    )
    units: Optional[str] = Field(None, description="Unit system (metric or imperial)")
    arrival_time: Optional[int] = Field(None, description="Desired arrival time")
    departure_time: Optional[int] = Field(None, description="Desired departure time")
    traffic_model: Optional[str] = Field(
        None, description="Traffic model for predictions"
    )
    transit_mode: Optional[List[str]] = Field(
        None, description="Preferred transit modes"
    )
    transit_routing_preference: Optional[str] = Field(
        None, description="Transit routing preferences"
    )


class TimeZoneParams(BaseParams):
    """Parameters for timezone requests."""

    location: str = Field(..., description="Location coordinates (lat,lng)")
    timestamp: Optional[int] = Field(
        None, description="Timestamp to use (defaults to current time)"
    )

    @field_validator("location")
    @classmethod
    def validate_location(cls, v: str) -> str:
        """Validate location format."""
        if not v or "," not in v:
            raise ValueError("Location must be in format 'lat,lng'")

        parts = v.split(",")
        if len(parts) != 2:
            raise ValueError("Location must contain exactly one comma")

        try:
            lat, lng = float(parts[0]), float(parts[1])
            if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
                raise ValueError(
                    "Invalid coordinates: latitude must be between -90 and 90, longitude between -180 and 180"
                )
        except ValueError:
            raise ValueError("Location coordinates must be valid numbers")

        return v


class ElevationParams(BaseParams):
    """Parameters for elevation requests."""

    locations: List[str] = Field(
        ..., min_length=1, description="Location coordinates (lat,lng)"
    )

    @field_validator("locations")
    @classmethod
    def validate_locations(cls, v: List[str]) -> List[str]:
        """Validate location format for each location."""
        for loc in v:
            if not loc or "," not in loc:
                raise ValueError(f"Location '{loc}' must be in format 'lat,lng'")

            parts = loc.split(",")
            if len(parts) != 2:
                raise ValueError(f"Location '{loc}' must contain exactly one comma")

            try:
                lat, lng = float(parts[0]), float(parts[1])
                if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
                    raise ValueError(
                        f"Invalid coordinates in '{loc}': latitude must be between -90 and 90, longitude between -180 and 180"
                    )
            except ValueError:
                raise ValueError(
                    f"Location coordinates in '{loc}' must be valid numbers"
                )

        return v


class GeocodeResult(BaseModel):
    """Model for a geocoding result."""

    place_id: str = Field(..., description="Google Maps place ID")
    formatted_address: str = Field(..., description="Formatted address")
    geometry: Dict[str, Any] = Field(..., description="Location geometry")
    address_components: List[Dict[str, Any]] = Field(
        [], description="Address components"
    )
    types: List[str] = Field([], description="Place types")

    model_config = ConfigDict(extra="allow")


class GeocodeResponse(BaseResponse):
    """Response for geocoding requests."""

    results: List[GeocodeResult] = Field([], description="Geocoding results")
    status: str = Field(..., description="Request status")
    error_message: Optional[str] = Field(
        None, description="Error message if request failed"
    )


class PlaceResult(BaseModel):
    """Model for a place search result."""

    place_id: str = Field(..., description="Google Maps place ID")
    name: str = Field(..., description="Place name")
    formatted_address: Optional[str] = Field(None, description="Formatted address")
    geometry: Dict[str, Any] = Field(..., description="Location geometry")
    types: List[str] = Field([], description="Place types")
    business_status: Optional[str] = Field(None, description="Business status")
    icon: Optional[str] = Field(None, description="Icon URL")
    photos: Optional[List[Dict[str, Any]]] = Field(None, description="Place photos")
    price_level: Optional[int] = Field(None, description="Price level (0-4)")
    rating: Optional[float] = Field(None, description="User rating")
    user_ratings_total: Optional[int] = Field(
        None, description="Total number of ratings"
    )
    vicinity: Optional[str] = Field(None, description="Vicinity description")

    model_config = ConfigDict(extra="allow")


class PlaceSearchResponse(BaseResponse):
    """Response for place search requests."""

    results: List[PlaceResult] = Field([], description="Place search results")
    status: str = Field(..., description="Request status")
    next_page_token: Optional[str] = Field(
        None, description="Token for next page of results"
    )
    error_message: Optional[str] = Field(
        None, description="Error message if request failed"
    )


class PlaceDetailsResponse(BaseResponse):
    """Response for place details requests."""

    result: Optional[Dict[str, Any]] = Field(None, description="Place details")
    status: str = Field(..., description="Request status")
    error_message: Optional[str] = Field(
        None, description="Error message if request failed"
    )


class Route(BaseModel):
    """Model for a directions route."""

    summary: str = Field(..., description="Route summary")
    legs: List[Dict[str, Any]] = Field(..., description="Route legs")
    overview_polyline: Dict[str, str] = Field(
        ..., description="Encoded polyline for route"
    )
    warnings: List[str] = Field([], description="Warnings for this route")
    waypoint_order: List[int] = Field([], description="Order of waypoints")
    fare: Optional[Dict[str, Any]] = Field(None, description="Fare information")

    model_config = ConfigDict(extra="allow")


class DirectionsResponse(BaseResponse):
    """Response for directions requests."""

    routes: List[Route] = Field([], description="Available routes")
    status: str = Field(..., description="Request status")
    error_message: Optional[str] = Field(
        None, description="Error message if request failed"
    )
    geocoded_waypoints: Optional[List[Dict[str, Any]]] = Field(
        None, description="Geocoded waypoints"
    )


class DistanceMatrixResponse(BaseResponse):
    """Response for distance matrix requests."""

    origin_addresses: List[str] = Field([], description="Origin addresses")
    destination_addresses: List[str] = Field([], description="Destination addresses")
    rows: List[Dict[str, Any]] = Field([], description="Matrix rows")
    status: str = Field(..., description="Request status")
    error_message: Optional[str] = Field(
        None, description="Error message if request failed"
    )


class TimeZoneResponse(BaseResponse):
    """Response for timezone requests."""

    dstOffset: int = Field(..., description="Daylight saving time offset in seconds")
    rawOffset: int = Field(..., description="Raw time zone offset in seconds")
    timeZoneId: str = Field(..., description="Time zone ID")
    timeZoneName: str = Field(..., description="Time zone name")
    status: str = Field(..., description="Request status")
    error_message: Optional[str] = Field(
        None, description="Error message if request failed"
    )


class ElevationResponse(BaseResponse):
    """Response for elevation requests."""

    results: List[Dict[str, Any]] = Field([], description="Elevation results")
    status: str = Field(..., description="Request status")
    error_message: Optional[str] = Field(
        None, description="Error message if request failed"
    )
