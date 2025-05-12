"""
Pydantic models for Flight MCP client.

This module defines the parameter and response models for the Flight MCP Client,
providing proper validation and type safety.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class CabinClass(str, Enum):
    """Cabin class options for flights."""

    ECONOMY = "economy"
    PREMIUM_ECONOMY = "premium_economy"
    BUSINESS = "business"
    FIRST = "first"


class BaseParams(BaseModel):
    """Base model for all parameter models."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")


class BaseResponse(BaseModel):
    """Base model for all response models."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class FlightSearchParams(BaseParams):
    """Parameters for flight search queries."""

    origin: str = Field(..., description="Origin airport IATA code")
    destination: str = Field(..., description="Destination airport IATA code")
    departure_date: str = Field(..., description="Departure date (YYYY-MM-DD)")
    return_date: Optional[str] = Field(
        None, description="Return date for round trips (YYYY-MM-DD)"
    )
    adults: int = Field(1, ge=1, le=9, description="Number of adult passengers")
    children: int = Field(0, ge=0, le=9, description="Number of child passengers")
    infants: int = Field(0, ge=0, le=4, description="Number of infant passengers")
    cabin_class: CabinClass = Field(CabinClass.ECONOMY, description="Cabin class")
    max_stops: Optional[int] = Field(
        None, ge=0, le=3, description="Maximum number of stops"
    )
    max_price: Optional[float] = Field(None, gt=0, description="Maximum price in USD")
    preferred_airlines: Optional[List[str]] = Field(
        None, description="List of preferred airline codes"
    )

    @field_validator("departure_date", "return_date")
    @classmethod
    def validate_date_format(cls, v):
        """Validate that dates are in YYYY-MM-DD format."""
        if v:
            try:
                datetime.strptime(v, "%Y-%m-%d")
            except ValueError as e:
                raise ValueError("Date must be in YYYY-MM-DD format") from e
        return v

    @field_validator("origin", "destination")
    @classmethod
    def validate_airport_code(cls, v: str) -> str:
        """Validate and standardize airport codes."""
        if len(v) != 3:
            raise ValueError("Airport code must be 3 characters (IATA code)")
        return v.upper()

    @model_validator(mode="after")
    def validate_return_date_after_departure(self) -> "FlightSearchParams":
        """Validate that return date is after departure date if provided."""
        if (
            self.return_date
            and self.departure_date
            and self.return_date < self.departure_date
        ):
            raise ValueError("Return date must be after departure date")
        return self


class FlightSegment(BaseModel):
    """A segment of a flight (one leg of the journey)."""

    model_config = ConfigDict(extra="allow")

    origin: str = Field(..., description="Origin airport code")
    destination: str = Field(..., description="Destination airport code")
    departure_date: str = Field(..., description="Departure date (YYYY-MM-DD)")

    @field_validator("departure_date")
    @classmethod
    def validate_date_format(cls, v):
        """Validate that date is in YYYY-MM-DD format."""
        if v:
            try:
                datetime.strptime(v, "%Y-%m-%d")
            except ValueError as e:
                raise ValueError("Date must be in YYYY-MM-DD format") from e
        return v

    @field_validator("origin", "destination")
    @classmethod
    def validate_airport_code(cls, v: str) -> str:
        """Validate and standardize airport codes."""
        if len(v) != 3:
            raise ValueError("Airport code must be 3 characters (IATA code)")
        return v.upper()


class MultiCitySearchParams(BaseParams):
    """Parameters for multi-city flight search."""

    segments: List[FlightSegment] = Field(..., description="List of flight segments")
    adults: int = Field(1, ge=1, le=9, description="Number of adult passengers")
    children: int = Field(0, ge=0, le=9, description="Number of child passengers")
    infants: int = Field(0, ge=0, le=4, description="Number of infant passengers")
    cabin_class: CabinClass = Field(CabinClass.ECONOMY, description="Cabin class")

    @model_validator(mode="after")
    def validate_segments(self) -> "MultiCitySearchParams":
        """Validate that there are at least two segments."""
        if len(self.segments) < 2:
            raise ValueError("At least two segments are required for multi-city search")
        return self


class AirportSearchParams(BaseParams):
    """Parameters for airport search."""

    code: Optional[str] = Field(None, description="IATA airport code")
    search_term: Optional[str] = Field(
        None, description="Airport name or city to search for"
    )

    @model_validator(mode="after")
    def validate_params(self) -> "AirportSearchParams":
        """Validate that either code or search_term is provided."""
        if not self.code and not self.search_term:
            raise ValueError("Either code or search_term must be provided")

        if self.code and len(self.code) != 3:
            raise ValueError("Airport code must be 3 characters (IATA code)")

        return self


class OfferDetailsParams(BaseParams):
    """Parameters for retrieving offer details."""

    offer_id: str = Field(..., description="Flight offer ID")


class FlightPriceParams(BaseParams):
    """Parameters for retrieving flight price history."""

    origin: str = Field(..., description="Origin airport IATA code")
    destination: str = Field(..., description="Destination airport IATA code")
    departure_date: str = Field(..., description="Departure date (YYYY-MM-DD)")
    return_date: Optional[str] = Field(
        None, description="Return date for round trips (YYYY-MM-DD)"
    )

    @field_validator("departure_date", "return_date")
    @classmethod
    def validate_date_format(cls, v):
        """Validate that dates are in YYYY-MM-DD format."""
        if v:
            try:
                datetime.strptime(v, "%Y-%m-%d")
            except ValueError as e:
                raise ValueError("Date must be in YYYY-MM-DD format") from e
        return v

    @field_validator("origin", "destination")
    @classmethod
    def validate_airport_code(cls, v: str) -> str:
        """Validate and standardize airport codes."""
        if len(v) != 3:
            raise ValueError("Airport code must be 3 characters (IATA code)")
        return v.upper()


class PriceTrackingParams(BaseParams):
    """Parameters for tracking flight prices."""

    origin: str = Field(..., description="Origin airport IATA code")
    destination: str = Field(..., description="Destination airport IATA code")
    departure_date: str = Field(..., description="Departure date (YYYY-MM-DD)")
    return_date: Optional[str] = Field(
        None, description="Return date for round trips (YYYY-MM-DD)"
    )
    email: str = Field(..., description="Email to send notifications to")
    frequency: str = Field(
        "daily", description="Frequency of price checks (hourly, daily, weekly)"
    )
    threshold_percentage: Optional[float] = Field(
        None, gt=0, description="Price threshold for alerts"
    )

    @field_validator("departure_date", "return_date")
    @classmethod
    def validate_date_format(cls, v):
        """Validate that dates are in YYYY-MM-DD format."""
        if v:
            try:
                datetime.strptime(v, "%Y-%m-%d")
            except ValueError as e:
                raise ValueError("Date must be in YYYY-MM-DD format") from e
        return v

    @field_validator("origin", "destination")
    @classmethod
    def validate_airport_code(cls, v: str) -> str:
        """Validate and standardize airport codes."""
        if len(v) != 3:
            raise ValueError("Airport code must be 3 characters (IATA code)")
        return v.upper()

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Validate email format."""
        if not v or "@" not in v or "." not in v:
            raise ValueError("Invalid email format")
        return v

    @field_validator("frequency")
    @classmethod
    def validate_frequency(cls, v: str) -> str:
        """Validate frequency value."""
        valid_frequencies = ["hourly", "daily", "weekly"]
        if v not in valid_frequencies:
            raise ValueError(
                f"Frequency must be one of: {', '.join(valid_frequencies)}"
            )
        return v


class Passenger(BaseModel):
    """Passenger information for flight booking."""

    model_config = ConfigDict(extra="allow")

    given_name: str = Field(..., description="First name")
    family_name: str = Field(..., description="Last name")
    gender: str = Field(..., description="Gender")
    born_on: str = Field(..., description="Date of birth (YYYY-MM-DD)")
    phone_number: str = Field(..., description="Phone number")
    email: str = Field(..., description="Email address")
    title: Optional[str] = Field(None, description="Title (Mr, Ms, etc.)")

    @field_validator("born_on")
    @classmethod
    def validate_date_format(cls, v):
        """Validate that date is in YYYY-MM-DD format."""
        if v:
            try:
                datetime.strptime(v, "%Y-%m-%d")
            except ValueError as e:
                raise ValueError("Date must be in YYYY-MM-DD format") from e
        return v

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Validate email format."""
        if not v or "@" not in v or "." not in v:
            raise ValueError("Invalid email format")
        return v


class PaymentDetails(BaseModel):
    """Payment information for flight booking."""

    model_config = ConfigDict(extra="allow")

    type: str = Field(..., description="Payment type")
    amount: float = Field(..., gt=0, description="Payment amount")
    currency: str = Field(..., description="Currency code")


class ContactDetails(BaseModel):
    """Contact information for flight booking."""

    model_config = ConfigDict(extra="allow")

    given_name: str = Field(..., description="First name")
    family_name: str = Field(..., description="Last name")
    email: str = Field(..., description="Email address")
    phone_number: str = Field(..., description="Phone number")

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Validate email format."""
        if not v or "@" not in v or "." not in v:
            raise ValueError("Invalid email format")
        return v


class BookingParams(BaseParams):
    """Parameters for flight booking."""

    offer_id: str = Field(..., description="Flight offer ID")
    passengers: List[Passenger] = Field(
        ..., min_length=1, description="List of passengers"
    )
    payment_details: PaymentDetails = Field(..., description="Payment information")
    contact_details: ContactDetails = Field(..., description="Contact information")


class OrderDetailsParams(BaseParams):
    """Parameters for retrieving order details."""

    order_id: str = Field(..., description="Order ID")


class FlightOffer(BaseResponse):
    """Flight offer information."""

    id: str = Field(..., description="Offer ID")
    total_amount: float = Field(..., description="Total price")
    total_currency: str = Field(..., description="Currency code")
    base_amount: Optional[float] = Field(None, description="Base fare amount")
    tax_amount: Optional[float] = Field(None, description="Tax amount")
    slices: List[Dict[str, Any]] = Field(..., description="Flight slices (legs)")
    passenger_count: int = Field(..., description="Number of passengers")


class FlightSearchResponse(BaseResponse):
    """Response for flight search."""

    offers: List[FlightOffer] = Field([], description="List of flight offers")
    offer_count: int = Field(0, description="Number of offers found")
    currency: str = Field("USD", description="Currency code")
    search_id: Optional[str] = Field(None, description="Search ID for tracking")
    cheapest_price: Optional[float] = Field(None, description="Cheapest price found")
    error: Optional[str] = Field(None, description="Error message if search failed")


class Airport(BaseResponse):
    """Airport information."""

    iata_code: str = Field(..., description="IATA code")
    name: str = Field(..., description="Airport name")
    city: str = Field(..., description="City name")
    country: str = Field(..., description="Country name")
    latitude: Optional[float] = Field(None, description="Latitude coordinate")
    longitude: Optional[float] = Field(None, description="Longitude coordinate")
    timezone: Optional[str] = Field(None, description="Timezone")

    @field_validator("iata_code")
    @classmethod
    def validate_airport_code(cls, v: str) -> str:
        """Validate and standardize airport codes."""
        if len(v) != 3:
            raise ValueError("Airport code must be 3 characters (IATA code)")
        return v.upper()


class AirportSearchResponse(BaseResponse):
    """Response for airport search."""

    airports: List[Airport] = Field([], description="List of airports")
    count: int = Field(0, description="Number of airports found")
    error: Optional[str] = Field(None, description="Error message if search failed")


class OfferDetailsResponse(BaseResponse):
    """Response for offer details."""

    offer_id: str = Field(..., description="Offer ID")
    total_amount: float = Field(..., description="Total price")
    currency: str = Field(..., description="Currency code")
    slices: List[Dict[str, Any]] = Field(..., description="Flight slices (legs)")
    passengers: Dict[str, int] = Field(..., description="Passenger counts by type")
    fare_details: Optional[Dict[str, Any]] = Field(
        None, description="Fare details and rules"
    )
    error: Optional[str] = Field(None, description="Error message if retrieval failed")


class FlightPriceResponse(BaseResponse):
    """Response for flight price history."""

    origin: str = Field(..., description="Origin airport code")
    destination: str = Field(..., description="Destination airport code")
    departure_date: str = Field(..., description="Departure date")
    return_date: Optional[str] = Field(None, description="Return date")
    current_price: Optional[float] = Field(None, description="Current price")
    currency: str = Field("USD", description="Currency code")
    prices: List[float] = Field([], description="Historical prices")
    dates: List[str] = Field([], description="Dates for historical prices")
    trend: Optional[str] = Field(
        None, description="Price trend (rising, falling, stable)"
    )
    error: Optional[str] = Field(None, description="Error message if retrieval failed")

    @field_validator("origin", "destination")
    @classmethod
    def validate_airport_code(cls, v: str) -> str:
        """Validate and standardize airport codes."""
        if len(v) != 3:
            raise ValueError("Airport code must be 3 characters (IATA code)")
        return v.upper()


class PriceTrackingResponse(BaseResponse):
    """Response for price tracking."""

    tracking_id: str = Field(..., description="Tracking ID")
    origin: str = Field(..., description="Origin airport code")
    destination: str = Field(..., description="Destination airport code")
    departure_date: str = Field(..., description="Departure date")
    return_date: Optional[str] = Field(None, description="Return date")
    email: str = Field(..., description="Notification email")
    frequency: str = Field(..., description="Notification frequency")
    current_price: Optional[float] = Field(None, description="Current price")
    currency: str = Field("USD", description="Currency code")
    threshold_price: Optional[float] = Field(None, description="Alert threshold price")
    error: Optional[str] = Field(None, description="Error message if setup failed")

    @field_validator("origin", "destination")
    @classmethod
    def validate_airport_code(cls, v: str) -> str:
        """Validate and standardize airport codes."""
        if len(v) != 3:
            raise ValueError("Airport code must be 3 characters (IATA code)")
        return v.upper()


class BookingResponse(BaseResponse):
    """Response for flight booking."""

    order_id: Optional[str] = Field(None, description="Order ID")
    booking_reference: Optional[str] = Field(None, description="Booking reference/PNR")
    status: str = Field(..., description="Booking status")
    total_amount: Optional[float] = Field(None, description="Total amount paid")
    currency: Optional[str] = Field(None, description="Currency code")
    passengers: Optional[List[Dict[str, Any]]] = Field(
        None, description="Passenger details"
    )
    slices: Optional[List[Dict[str, Any]]] = Field(None, description="Flight details")
    error: Optional[str] = Field(None, description="Error message if booking failed")


class OrderDetailsResponse(BaseResponse):
    """Response for order details."""

    order_id: str = Field(..., description="Order ID")
    booking_reference: Optional[str] = Field(None, description="Booking reference/PNR")
    status: str = Field(..., description="Order status")
    total_amount: float = Field(..., description="Total amount paid")
    currency: str = Field(..., description="Currency code")
    passengers: List[Dict[str, Any]] = Field(..., description="Passenger details")
    slices: List[Dict[str, Any]] = Field(..., description="Flight details")
    created_at: str = Field(..., description="Creation timestamp")
    error: Optional[str] = Field(None, description="Error message if retrieval failed")
