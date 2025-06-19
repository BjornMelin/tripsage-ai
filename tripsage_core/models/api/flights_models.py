"""
Pydantic models for Duffel Flights API integration.

This module provides comprehensive data models for flight operations,
including search, booking, and management features.
"""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

# CabinClass enum moved to tripsage_core.models.schemas_common.enums
from tripsage_core.models.schemas_common.enums import CabinClass


class PassengerType(str, Enum):
    """Types of passengers."""

    ADULT = "adult"
    CHILD = "child"
    INFANT_WITHOUT_SEAT = "infant_without_seat"


class FareType(str, Enum):
    """Types of fares."""

    CONTRACT = "contract"
    PUBLISHED = "published"


class OrderState(str, Enum):
    """Order states."""

    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"


class PaymentType(str, Enum):
    """Payment types."""

    ARC_BSP_CASH = "arc_bsp_cash"
    BALANCE = "balance"
    CARD = "card"


class Currency(BaseModel):
    """Currency representation."""

    code: str = Field(..., pattern="^[A-Z]{3}$")
    name: str | None = None
    symbol: str | None = None


class Location(BaseModel):
    """Geographic location."""

    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)


class Airport(BaseModel):
    """Airport information model."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    type: str = "airport"
    iata_code: str = Field(..., pattern="^[A-Z]{3}$")
    iata_country_code: str = Field(..., pattern="^[A-Z]{2}$")
    iata_city_code: str | None = Field(None, pattern="^[A-Z]{3}$")
    icao_code: str | None = Field(None, pattern="^[A-Z]{4}$")
    name: str
    city_name: str | None = None
    city: dict[str, Any] | None = None
    latitude: float | None = Field(None, ge=-90, le=90)
    longitude: float | None = Field(None, ge=-180, le=180)
    time_zone: str | None = None


class Airline(BaseModel):
    """Airline information model."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    type: str = "airline"
    iata_code: str = Field(..., pattern="^[A-Z0-9]{2}$")
    icao_code: str | None = Field(None, pattern="^[A-Z]{3}$")
    name: str
    logo_url: HttpUrl | None = None
    logo_lockup_url: HttpUrl | None = None


class Aircraft(BaseModel):
    """Aircraft information model."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    type: str = "aircraft"
    iata_code: str
    icao_code: str | None = None
    name: str


class Place(BaseModel):
    """Place (airport or city) information."""

    id: str
    type: str
    iata_code: str
    iata_city_code: str | None = None
    name: str
    city_name: str | None = None
    city: dict[str, Any] | None = None
    airports: list[Airport] | None = None


class Duration(BaseModel):
    """Duration representation."""

    hours: int = Field(..., ge=0)
    minutes: int = Field(..., ge=0, lt=60)

    @property
    def total_minutes(self) -> int:
        """Get total duration in minutes."""
        return self.hours * 60 + self.minutes


class Distance(BaseModel):
    """Distance representation."""

    value: float = Field(..., ge=0)
    unit: str = "km"


class BaggageAllowance(BaseModel):
    """Baggage allowance information."""

    model_config = ConfigDict(populate_by_name=True)

    quantity: int = Field(..., ge=0)
    weight: float | None = Field(None, ge=0)
    weight_unit: str | None = Field(None, pattern="^(kg|lb)$")


class Segment(BaseModel):
    """Flight segment model."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    type: str = "segment"
    origin: Place
    destination: Place
    departure_datetime: datetime
    arrival_datetime: datetime
    duration: str | None = None
    distance: str | None = None

    operating_carrier: Airline
    operating_carrier_flight_number: str
    marketing_carrier: Airline
    marketing_carrier_flight_number: str

    aircraft: Aircraft | None = None
    passengers: list[dict[str, Any]] | None = None

    @property
    def flight_number(self) -> str:
        """Get the marketing flight number."""
        return (
            f"{self.marketing_carrier.iata_code}{self.marketing_carrier_flight_number}"
        )


class Slice(BaseModel):
    """Flight slice (one-way journey) model."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    type: str = "slice"
    origin: Place
    destination: Place
    departure_datetime: datetime
    arrival_datetime: datetime
    duration: str | None = None
    segments: list[Segment]

    @property
    def stops(self) -> int:
        """Get number of stops."""
        return len(self.segments) - 1 if self.segments else 0


class OfferSliceSegment(BaseModel):
    """Segment within an offer slice."""

    model_config = ConfigDict(populate_by_name=True)

    segment: Segment
    cabin_class: CabinClass
    cabin_class_marketing_name: str | None = None
    fare_basis_code: str | None = None


class OfferSlice(BaseModel):
    """Slice within an offer."""

    model_config = ConfigDict(populate_by_name=True)

    slice: Slice
    segments: list[OfferSliceSegment]
    fare_brand_name: str | None = None


class PriceBreakdown(BaseModel):
    """Price breakdown details."""

    model_config = ConfigDict(populate_by_name=True)

    amount: Decimal = Field(..., decimal_places=2)
    currency: str = Field(..., pattern="^[A-Z]{3}$")

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: Decimal) -> Decimal:
        """Ensure amount is positive."""
        if v < 0:
            raise ValueError("Amount must be non-negative")
        return v


class PassengerIdentity(BaseModel):
    """Passenger identity information."""

    model_config = ConfigDict(populate_by_name=True)

    given_name: str = Field(..., min_length=1, max_length=100)
    family_name: str = Field(..., min_length=1, max_length=100)
    middle_name: str | None = Field(None, max_length=100)
    title: str | None = Field(None, pattern="^(mr|ms|mrs|miss|dr)$")
    gender: str | None = Field(None, pattern="^(m|f)$")
    born_on: date
    phone_number: str | None = None
    email: str | None = None

    @field_validator("born_on")
    @classmethod
    def validate_birth_date(cls, v: date) -> date:
        """Validate birth date is not in the future."""
        if v > date.today():
            raise ValueError("Birth date cannot be in the future")
        return v


class Passenger(BaseModel):
    """Passenger information model."""

    model_config = ConfigDict(populate_by_name=True)

    id: str | None = None
    type: PassengerType
    given_name: str | None = None
    family_name: str | None = None
    age: int | None = Field(None, ge=0, le=150)
    born_on: date | None = None


class FlightOffer(BaseModel):
    """Flight offer model."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    type: str = "offer"
    created_at: datetime
    expires_at: datetime
    live_mode: bool

    slices: list[OfferSlice]
    passengers: list[Passenger]

    total_amount: Decimal = Field(..., decimal_places=2)
    total_currency: str = Field(..., pattern="^[A-Z]{3}$")

    base_amount: Decimal | None = Field(None, decimal_places=2)
    base_currency: str | None = Field(None, pattern="^[A-Z]{3}$")

    tax_amount: Decimal | None = Field(None, decimal_places=2)
    tax_currency: str | None = Field(None, pattern="^[A-Z]{3}$")

    owner: Airline
    partial: bool = False
    private_fares: list[dict[str, Any]] = Field(default_factory=list)

    conditions: dict[str, Any] | None = None
    available_services: list[dict[str, Any]] | None = None

    # TripSage extensions
    score: float | None = Field(None, ge=0, le=1, description="TripSage quality score")
    user_preferences_match: dict[str, Any] | None = None


class FlightOfferRequest(BaseModel):
    """Flight offer request model."""

    model_config = ConfigDict(populate_by_name=True)

    id: str | None = None
    type: str = "offer_request"
    created_at: datetime | None = None
    live_mode: bool = True

    slices: list[dict[str, Any]]
    passengers: list[Passenger]

    cabin_class: CabinClass | None = None
    max_connections: int | None = Field(None, ge=0)
    return_offers: bool = True

    # Filters
    only_airlines: list[str] | None = None
    exclude_airlines: list[str] | None = None


class OrderPassenger(BaseModel):
    """Passenger in an order."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    type: str = "order_passenger"
    given_name: str
    family_name: str
    title: str | None = None
    gender: str | None = None
    born_on: date
    phone_number: str | None = None
    email: str | None = None
    passenger_type: PassengerType = Field(..., alias="type")


class OrderSlice(BaseModel):
    """Slice in an order."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    type: str = "order_slice"
    origin: Place
    destination: Place
    departure_datetime: datetime
    arrival_datetime: datetime
    duration: str | None = None
    segments: list[dict[str, Any]]


class Payment(BaseModel):
    """Payment information."""

    model_config = ConfigDict(populate_by_name=True)

    type: PaymentType
    amount: Decimal = Field(..., decimal_places=2)
    currency: str = Field(..., pattern="^[A-Z]{3}$")
    created_at: datetime | None = None


class PaymentRequest(BaseModel):
    """Payment request for creating orders."""

    model_config = ConfigDict(populate_by_name=True)

    type: PaymentType = PaymentType.CARD
    amount: Decimal = Field(..., decimal_places=2)
    currency: str = Field(..., pattern="^[A-Z]{3}$")


class Order(BaseModel):
    """Flight order model."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    type: str = "order"
    created_at: datetime
    live_mode: bool

    booking_reference: str
    synced_at: datetime | None = None

    owner: Airline
    offer: FlightOffer | None = None

    passengers: list[OrderPassenger]
    slices: list[OrderSlice]

    total_amount: Decimal = Field(..., decimal_places=2)
    total_currency: str = Field(..., pattern="^[A-Z]{3}$")

    base_amount: Decimal | None = Field(None, decimal_places=2)
    base_currency: str | None = Field(None, pattern="^[A-Z]{3}$")

    tax_amount: Decimal | None = Field(None, decimal_places=2)
    tax_currency: str | None = Field(None, pattern="^[A-Z]{3}$")

    payments: list[Payment] = Field(default_factory=list)
    services: list[dict[str, Any]] = Field(default_factory=list)

    conditions: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None


class OrderCreateRequest(BaseModel):
    """Request to create an order."""

    model_config = ConfigDict(populate_by_name=True)

    type: str = "instant"
    selected_offers: list[str]
    passengers: list[OrderPassenger]
    payments: list[Payment]
    services: list[dict[str, Any]] | None = None
    metadata: dict[str, Any] | None = None


class OrderCancellation(BaseModel):
    """Order cancellation model."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    type: str = "order_cancellation"
    order_id: str
    created_at: datetime
    live_mode: bool
    confirmed_at: datetime | None = None
    refund_to: str | None = None
    refund_amount: Decimal | None = Field(None, decimal_places=2)
    refund_currency: str | None = Field(None, pattern="^[A-Z]{3}$")


class SeatMap(BaseModel):
    """Seat map model."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    type: str = "seat_map"
    slice_id: str
    segment_id: str
    aircraft: Aircraft
    cabins: list[dict[str, Any]]


class SearchParameters(BaseModel):
    """Flight search parameters."""

    model_config = ConfigDict(populate_by_name=True)

    origin: str = Field(..., pattern="^[A-Z]{3}$")
    destination: str = Field(..., pattern="^[A-Z]{3}$")
    departure_date: date
    return_date: date | None = None

    adults: int = Field(1, ge=1, le=9)
    children: int = Field(0, ge=0, le=9)
    infants: int = Field(0, ge=0, le=9)

    cabin_class: CabinClass = CabinClass.ECONOMY
    max_connections: int | None = Field(None, ge=0, le=3)

    # Price filters
    max_price: Decimal | None = Field(None, ge=0)
    currency: str = Field("USD", pattern="^[A-Z]{3}$")

    # Airline preferences
    only_airlines: list[str] | None = None
    exclude_airlines: list[str] | None = None

    # Time preferences
    outbound_departure_time_from: str | None = None
    outbound_departure_time_to: str | None = None
    outbound_arrival_time_from: str | None = None
    outbound_arrival_time_to: str | None = None

    inbound_departure_time_from: str | None = None
    inbound_departure_time_to: str | None = None
    inbound_arrival_time_from: str | None = None
    inbound_arrival_time_to: str | None = None

    @field_validator("return_date")
    @classmethod
    def validate_return_date(cls, v: date | None, info) -> date | None:
        """Ensure return date is after departure date."""
        if v and "departure_date" in info.data and v <= info.data["departure_date"]:
            raise ValueError("Return date must be after departure date")
        return v
