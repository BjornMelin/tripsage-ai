"""Pydantic models for accommodation-related tool interactions.

These models back both the MCP clients and LangGraph tools, providing a single
set of validated schemas that downstream modules can share without relying on
package-level re-exports.
"""

from datetime import date
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from tripsage_core.models.schemas_common.enums import AccommodationType
from tripsage_core.models.schemas_common.geographic import Coordinates


class AirbnbSearchParams(BaseModel):
    """Parameters for Airbnb accommodation search."""

    model_config = ConfigDict(extra="forbid")

    location: str = Field(..., description="Location to search in")
    place_id: str | None = Field(
        None, description="Google Maps place ID (if available)"
    )
    checkin: str | date | None = Field(None, description="Check-in date (YYYY-MM-DD)")
    checkout: str | date | None = Field(None, description="Check-out date (YYYY-MM-DD)")
    adults: int = Field(1, ge=1, le=16, description="Number of adults")
    children: int | None = Field(None, ge=0, description="Number of children")
    infants: int | None = Field(None, ge=0, description="Number of infants")
    pets: int | None = Field(None, ge=0, description="Number of pets")
    min_price: int | None = Field(None, ge=0, description="Minimum price per night")
    max_price: int | None = Field(None, ge=0, description="Maximum price per night")
    min_beds: int | None = Field(None, ge=1, description="Minimum number of beds")
    min_bedrooms: int | None = Field(
        None, ge=1, description="Minimum number of bedrooms"
    )
    min_bathrooms: int | None = Field(
        None, ge=1, description="Minimum number of bathrooms"
    )
    property_type: AccommodationType | None = Field(
        None, description="Type of property to filter by"
    )
    amenities: list[str] | None = Field(
        None, description="List of required amenities (e.g., ['pool', 'wifi'])"
    )
    room_type: str | None = Field(
        None, description="Room type (entire_home, private_room, shared_room)"
    )
    superhost: bool | None = Field(
        None, description="Filter for superhost listings only"
    )
    cursor: str | None = Field(None, description="Pagination cursor")
    ignore_robots_txt: bool = Field(False, description="Whether to ignore robots.txt")

    @field_validator("checkin", "checkout")
    @classmethod
    def validate_date_format(cls, v):
        """Validate that dates are in YYYY-MM-DD format."""
        if isinstance(v, date):
            return v.isoformat()
        if not v:
            return v
        try:
            date.fromisoformat(v)
            return v
        except ValueError as error:
            raise ValueError("Date must be in YYYY-MM-DD format") from error

    def to_airbnb_payload(self) -> dict[str, Any]:
        """Return parameters using Airbnb's expected field names."""
        data = self.model_dump(exclude_none=True)
        field_mapping = {
            "place_id": "placeId",
            "min_price": "minPrice",
            "max_price": "maxPrice",
            "min_beds": "minBeds",
            "min_bedrooms": "minBedrooms",
            "min_bathrooms": "minBathrooms",
            "property_type": "propertyType",
            "room_type": "roomType",
            "ignore_robots_txt": "ignoreRobotsText",
        }
        payload: dict[str, Any] = {}
        for key, value in data.items():
            wire_key = field_mapping.get(key, key)
            if isinstance(value, Enum):
                payload[wire_key] = value.value
            else:
                payload[wire_key] = value
        return payload


class AirbnbListingDetailsParams(BaseModel):
    """Parameters for retrieving Airbnb listing details."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., description="Airbnb listing ID")
    checkin: str | date | None = Field(None, description="Check-in date (YYYY-MM-DD)")
    checkout: str | date | None = Field(None, description="Check-out date (YYYY-MM-DD)")
    adults: int = Field(1, ge=1, le=16, description="Number of adults")
    children: int | None = Field(None, ge=0, description="Number of children")
    infants: int | None = Field(None, ge=0, description="Number of infants")
    pets: int | None = Field(None, ge=0, description="Number of pets")

    @field_validator("checkin", "checkout")
    @classmethod
    def validate_date_format(cls, v):
        """Validate that dates are in YYYY-MM-DD format."""
        if isinstance(v, date):
            return v.isoformat()
        if not v:
            return v
        try:
            date.fromisoformat(v)
            return v
        except ValueError as error:
            raise ValueError("Date must be in YYYY-MM-DD format") from error

    def to_airbnb_payload(self) -> dict[str, Any]:
        """Return parameters using Airbnb's expected field names."""
        data = self.model_dump(exclude_none=True)
        payload: dict[str, Any] = {}
        for key, value in data.items():
            if isinstance(value, Enum):
                payload[key] = value.value
            else:
                payload[key] = value
        return payload


class AirbnbListing(BaseModel):
    """Details of an Airbnb listing."""

    id: str = Field(..., description="Airbnb listing ID")
    name: str = Field(..., description="Listing title")
    url: str = Field(..., description="URL to the listing")
    image: str | None = Field(None, description="Primary image URL")
    superhost: bool = Field(False, description="Whether host is a superhost")
    price_string: str = Field(..., description="Formatted price string")
    price_total: float = Field(..., description="Total price for the stay")
    price_per_night: float | None = Field(None, description="Price per night")
    currency: str = Field("USD", description="Currency code")
    rating: float | None = Field(None, description="Overall rating")
    reviews_count: int | None = Field(None, description="Number of reviews")
    location_info: str = Field(..., description="Location description")
    property_type: str = Field(..., description="Type of property")
    beds: int | None = Field(None, description="Number of beds")
    bedrooms: int | None = Field(None, description="Number of bedrooms")
    bathrooms: int | None = Field(None, description="Number of bathrooms")
    max_guests: int | None = Field(None, description="Maximum number of guests")
    amenities: list[str] | None = Field(None, description="List of amenities")

    model_config = ConfigDict(extra="allow")


class AirbnbHost(BaseModel):
    """Airbnb host details."""

    name: str = Field(..., description="Host name")
    image: str | None = Field(None, description="Host profile image URL")
    superhost: bool = Field(False, description="Whether the host is a superhost")
    response_rate: float | None = Field(None, description="Host response rate")
    response_time: str | None = Field(None, description="Host response time")
    joined_date: str | None = Field(None, description="When the host joined Airbnb")
    languages: list[str] | None = Field(None, description="Languages spoken by host")

    model_config = ConfigDict(extra="allow")


class AirbnbSearchResult(BaseModel):
    """Result of an Airbnb search."""

    location: str = Field(..., description="Search location")
    count: int = Field(0, description="Number of listings found")
    listings: list[AirbnbListing] = Field([], description="List of listings")
    next_cursor: str | None = Field(None, description="Pagination cursor for next page")
    search_params: dict[str, Any] = Field({}, description="Original search parameters")
    error: str | None = Field(None, description="Error message if search failed")

    model_config = ConfigDict(extra="allow")


class AirbnbListingDetails(BaseModel):
    """Detailed information about an Airbnb listing."""

    id: str = Field(..., description="Airbnb listing ID")
    url: str = Field(..., description="URL to the listing")
    name: str = Field(..., description="Listing title")
    description: str = Field(..., description="Full listing description")
    host: AirbnbHost = Field(..., description="Host details")
    property_type: str = Field(..., description="Type of property")
    location: str = Field(..., description="Location description")
    coordinates: Coordinates | None = Field(
        None, description="Geographical coordinates"
    )
    amenities: list[str] = Field([], description="List of amenities")
    bedrooms: int | None = Field(None, description="Number of bedrooms")
    beds: int | None = Field(None, description="Number of beds")
    bathrooms: int | None = Field(None, description="Number of bathrooms")
    max_guests: int | None = Field(None, description="Maximum number of guests")
    rating: float | None = Field(None, description="Overall rating")
    reviews_count: int | None = Field(None, description="Number of reviews")
    reviews_summary: list[dict[str, Any]] | None = Field(
        None, description="Summary of reviews by category"
    )
    price_per_night: float | None = Field(None, description="Price per night")
    price_total: float | None = Field(None, description="Total price for the stay")
    currency: str = Field("USD", description="Currency code")
    images: list[str] = Field([], description="List of image URLs")
    check_in_time: str | None = Field(None, description="Check-in time window")
    check_out_time: str | None = Field(None, description="Check-out time")
    house_rules: list[str] | None = Field(None, description="House rules")
    cancellation_policy: str | None = Field(None, description="Cancellation policy")

    model_config = ConfigDict(extra="allow")


class AccommodationSearchParams(BaseModel):
    """Parameters for generic accommodation search."""

    model_config = ConfigDict(extra="forbid")

    location: str = Field(..., description="Location to search in")
    source: str = Field(
        "airbnb", description="Source to search (airbnb, booking, etc.)"
    )
    check_in: str | date | None = Field(None, description="Check-in date (YYYY-MM-DD)")
    check_out: str | date | None = Field(
        None, description="Check-out date (YYYY-MM-DD)"
    )
    adults: int = Field(1, ge=1, le=16, description="Number of adults")
    children: int | None = Field(None, ge=0, description="Number of children")
    min_price: int | None = Field(None, ge=0, description="Minimum price per night")
    max_price: int | None = Field(None, ge=0, description="Maximum price per night")
    property_type: AccommodationType | None = Field(
        None, description="Type of property to filter by"
    )
    min_rating: float | None = Field(
        None, ge=0, le=5, description="Minimum rating (0-5)"
    )
    amenities: list[str] | None = Field(
        None, description="List of required amenities (e.g., ['pool', 'wifi'])"
    )

    @field_validator("check_in", "check_out")
    @classmethod
    def validate_date_format(cls, v):
        """Validate that dates are in YYYY-MM-DD format."""
        if isinstance(v, date):
            return v.isoformat()
        if not v:
            return v
        try:
            date.fromisoformat(v)
            return v
        except ValueError as error:
            raise ValueError("Date must be in YYYY-MM-DD format") from error

    def to_filters(self) -> dict[str, Any]:
        """Return normalized filters for downstream services."""
        data = self.model_dump(exclude_none=True)
        normalized: dict[str, Any] = {}
        for key, value in data.items():
            if isinstance(value, Enum):
                normalized[key] = value.value
            else:
                normalized[key] = value
        return normalized
