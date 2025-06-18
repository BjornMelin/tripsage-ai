"""
Unified flight schemas for TripSage.

This module contains consolidated Pydantic models for flight-related operations,
serving as the single source of truth for flight requests, responses, and data
structures. These models are used across API, service, and domain layers to
eliminate duplication.
"""

from datetime import date, datetime
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from .base_models import BaseResponse
from .common_validators import AirportCode
from .enums import CabinClass, PassengerType

# Removed TYPE_CHECKING imports to avoid circular import issues


class Airport(BaseModel):
    """Airport information model."""

    iata_code: AirportCode = Field(..., description="IATA airport code")
    name: str = Field(..., description="Airport name")
    city: str = Field(..., description="City name")
    country: str = Field(..., description="Country name")


class FlightPassenger(BaseModel):
    """Passenger information for flight bookings."""

    type: PassengerType = Field(..., description="Passenger type")
    age: Optional[int] = Field(None, ge=0, le=120, description="Passenger age")

    # Detailed passenger information (optional for bookings)
    given_name: Optional[str] = Field(None, description="First name")
    family_name: Optional[str] = Field(None, description="Last name")
    title: Optional[str] = Field(None, description="Title (Mr, Ms, etc.)")
    date_of_birth: Optional[datetime] = Field(None, description="Date of birth")
    email: Optional[str] = Field(None, description="Email address")
    phone: Optional[str] = Field(None, description="Phone number")

    @field_validator("age")
    @classmethod
    def validate_age_for_type(cls, v: Optional[int], info) -> Optional[int]:
        """Validate age is appropriate for passenger type."""
        if v is None:
            return v

        passenger_type = info.data.get("type")
        if passenger_type == PassengerType.CHILD and (v >= 18 or v < 2):
            raise ValueError("Child passengers must be between 2-17 years old")
        elif passenger_type == PassengerType.INFANT and v >= 2:
            raise ValueError("Infant passengers must be under 2 years old")
        elif passenger_type == PassengerType.ADULT and v < 18:
            raise ValueError("Adult passengers must be 18 or older")

        return v

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        """Validate email format."""
        if v and "@" not in v:
            raise ValueError("Invalid email format")
        return v


class FlightSearchRequest(BaseModel):
    """Unified flight search request model.

    This model combines the API and service layer requirements for flight searches.
    It supports both simple passenger counts and detailed passenger information.
    """

    origin: AirportCode = Field(..., description="Origin airport IATA code")
    destination: AirportCode = Field(..., description="Destination airport IATA code")
    departure_date: Union[date, datetime] = Field(..., description="Departure date")
    return_date: Optional[Union[date, datetime]] = Field(
        None, description="Return date for round trips"
    )

    # Passenger information - support both simple counts and detailed passengers
    adults: int = Field(1, ge=1, le=9, description="Number of adult passengers")
    children: int = Field(0, ge=0, le=9, description="Number of child passengers")
    infants: int = Field(0, ge=0, le=4, description="Number of infant passengers")
    passengers: Optional[List[FlightPassenger]] = Field(
        None, description="Detailed passenger information (optional)"
    )

    cabin_class: CabinClass = Field(CabinClass.ECONOMY, description="Cabin class")
    max_stops: Optional[int] = Field(
        None, ge=0, le=5, description="Maximum number of stops"
    )
    max_price: Optional[float] = Field(None, gt=0, description="Maximum price in USD")
    currency: str = Field(default="USD", description="Price currency")

    # Advanced options
    flexible_dates: bool = Field(
        default=False, description="Allow flexible date search"
    )
    preferred_airlines: Optional[List[str]] = Field(
        None, description="Preferred airline codes"
    )
    excluded_airlines: Optional[List[str]] = Field(
        None, description="Excluded airline codes"
    )

    # API-specific fields
    trip_id: Optional[UUID] = Field(None, description="Associated trip ID")

    @field_validator("return_date")
    @classmethod
    def validate_return_date(
        cls, v: Optional[Union[date, datetime]], info
    ) -> Optional[Union[date, datetime]]:
        """Validate that return date is after departure date if provided."""
        if v and info.data.get("departure_date"):
            departure = info.data["departure_date"]
            # Convert to date for comparison if needed
            dep_date = (
                departure.date() if isinstance(departure, datetime) else departure
            )
            ret_date = v.date() if isinstance(v, datetime) else v

            if ret_date <= dep_date:
                raise ValueError("Return date must be after departure date")
        return v

    @model_validator(mode="after")
    def validate_passenger_consistency(self) -> "FlightSearchRequest":
        """Validate that passenger counts are consistent with detailed passengers."""
        if self.passengers:
            # Count passengers by type
            adult_count = sum(
                1 for p in self.passengers if p.type == PassengerType.ADULT
            )
            child_count = sum(
                1 for p in self.passengers if p.type == PassengerType.CHILD
            )
            infant_count = sum(
                1 for p in self.passengers if p.type == PassengerType.INFANT
            )

            # Verify counts match
            if (
                adult_count != self.adults
                or child_count != self.children
                or infant_count != self.infants
            ):
                raise ValueError(
                    "Passenger counts must match detailed passenger information"
                )

        return self

    @property
    def total_passengers(self) -> int:
        """Get total number of passengers."""
        return self.adults + self.children + self.infants

    @property
    def is_round_trip(self) -> bool:
        """Check if this is a round trip search."""
        return self.return_date is not None


class MultiCityFlightSegment(BaseModel):
    """Model for a multi-city flight segment."""

    origin: AirportCode = Field(..., description="Origin airport IATA code")
    destination: AirportCode = Field(..., description="Destination airport IATA code")
    departure_date: Union[date, datetime] = Field(..., description="Departure date")


class MultiCityFlightSearchRequest(BaseModel):
    """Request model for multi-city flight search."""

    segments: List[MultiCityFlightSegment] = Field(
        description="List of flight segments",
        min_length=2,
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
        default=None, description="List of preferred airline codes"
    )
    trip_id: Optional[UUID] = Field(default=None, description="Associated trip ID")

    @model_validator(mode="after")
    def validate_segments(self) -> "MultiCityFlightSearchRequest":
        """Validate that there are at least two segments and dates are sequential."""
        if len(self.segments) < 2:
            raise ValueError("At least two segments are required for multi-city search")

        # Check that dates are sequential
        for i in range(len(self.segments) - 1):
            current_date = self.segments[i].departure_date
            next_date = self.segments[i + 1].departure_date

            # Convert to date for comparison if needed
            current = (
                current_date.date()
                if isinstance(current_date, datetime)
                else current_date
            )
            next_d = next_date.date() if isinstance(next_date, datetime) else next_date

            if next_d < current:
                raise ValueError(
                    f"Segment {i + 2} departure date must be on or after segment "
                    f"{i + 1} departure date"
                )

        return self


class AirportSearchRequest(BaseModel):
    """Request model for airport search."""

    query: str = Field(
        description="Search query (airport name, city, or IATA code)",
        min_length=1,
        max_length=100,
    )
    limit: int = Field(
        10, ge=1, le=50, description="Maximum number of results to return"
    )


class SavedFlightRequest(BaseModel):
    """Request model for saving a flight offer."""

    offer_id: str = Field(description="Flight offer ID")
    trip_id: UUID = Field(description="Trip ID to save the flight for")
    notes: Optional[str] = Field(
        default=None, description="Notes about this flight offer"
    )


# FlightOffer moved to domain layer - import from tripsage_core.models.domain.flight


class FlightSearchResponse(BaseResponse):
    """Response model for flight search results."""

    results: List[Any] = Field(description="Flight offers")  # FlightOffer from domain
    count: int = Field(description="Number of results")
    currency: str = Field(description="Currency code for prices", default="USD")
    search_id: str = Field(description="Search ID for reference")
    trip_id: Optional[UUID] = Field(default=None, description="Associated trip ID")
    min_price: Optional[float] = Field(default=None, description="Minimum price found")
    max_price: Optional[float] = Field(default=None, description="Maximum price found")
    search_request: Union[FlightSearchRequest, MultiCityFlightSearchRequest] = Field(
        description="Original search request"
    )


class AirportSearchResponse(BaseResponse):
    """Response model for airport search results."""

    results: List[Dict[str, Any]] = Field(description="Airport results")
    count: int = Field(description="Number of results")


class SavedFlightResponse(BaseModel):
    """Response model for a saved flight offer."""

    id: UUID = Field(description="Saved flight ID")
    user_id: str = Field(description="User ID")
    trip_id: UUID = Field(description="Trip ID")
    offer: Any = Field(description="Flight offer details")  # FlightOffer from domain
    saved_at: datetime = Field(description="Timestamp when flight was saved")
    notes: Optional[str] = Field(
        default=None, description="Notes about this flight offer"
    )


class UpcomingFlightResponse(BaseModel):
    """Response model for upcoming flights with real-time status."""

    id: str = Field(description="Flight ID")
    trip_id: Optional[str] = Field(default=None, description="Associated trip ID")
    trip_title: Optional[str] = Field(default=None, description="Trip title")
    airline: str = Field(description="Airline code")
    airline_name: str = Field(description="Airline name")
    flight_number: str = Field(description="Flight number")
    origin: AirportCode = Field(description="Origin airport code")
    destination: AirportCode = Field(description="Destination airport code")
    departure_time: datetime = Field(description="Departure time")
    arrival_time: datetime = Field(description="Arrival time")
    duration: int = Field(description="Flight duration in minutes")
    stops: int = Field(description="Number of stops")
    price: float = Field(description="Flight price")
    currency: str = Field(description="Currency code", default="USD")
    cabin_class: str = Field(description="Cabin class")
    seats_available: Optional[int] = Field(default=None, description="Available seats")
    status: str = Field(
        description="Flight status", default="upcoming"
    )  # upcoming, boarding, delayed, cancelled
    terminal: Optional[str] = Field(default=None, description="Terminal")
    gate: Optional[str] = Field(default=None, description="Gate")
    # Enhanced trip context fields
    is_shared_trip: Optional[bool] = Field(
        default=False, description="Whether the trip is shared"
    )
    collaborator_count: Optional[int] = Field(
        default=0, description="Number of trip collaborators"
    )
