"""
Pydantic models for Duffel Flights API integration.

This module provides comprehensive data models for flight operations,
including search, booking, and management features.
"""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

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
    name: Optional[str] = None
    symbol: Optional[str] = None


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
    iata_city_code: Optional[str] = Field(None, pattern="^[A-Z]{3}$")
    icao_code: Optional[str] = Field(None, pattern="^[A-Z]{4}$")
    name: str
    city_name: Optional[str] = None
    city: Optional[Dict[str, Any]] = None
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    time_zone: Optional[str] = None


class Airline(BaseModel):
    """Airline information model."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    type: str = "airline"
    iata_code: str = Field(..., pattern="^[A-Z0-9]{2}$")
    icao_code: Optional[str] = Field(None, pattern="^[A-Z]{3}$")
    name: str
    logo_url: Optional[HttpUrl] = None
    logo_lockup_url: Optional[HttpUrl] = None


class Aircraft(BaseModel):
    """Aircraft information model."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    type: str = "aircraft"
    iata_code: str
    icao_code: Optional[str] = None
    name: str


class Place(BaseModel):
    """Place (airport or city) information."""

    id: str
    type: str
    iata_code: str
    iata_city_code: Optional[str] = None
    name: str
    city_name: Optional[str] = None
    city: Optional[Dict[str, Any]] = None
    airports: Optional[List[Airport]] = None


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
    weight: Optional[float] = Field(None, ge=0)
    weight_unit: Optional[str] = Field(None, pattern="^(kg|lb)$")


class Segment(BaseModel):
    """Flight segment model."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    type: str = "segment"
    origin: Place
    destination: Place
    departure_datetime: datetime
    arrival_datetime: datetime
    duration: Optional[str] = None
    distance: Optional[str] = None

    operating_carrier: Airline
    operating_carrier_flight_number: str
    marketing_carrier: Airline
    marketing_carrier_flight_number: str

    aircraft: Optional[Aircraft] = None
    passengers: Optional[List[Dict[str, Any]]] = None

    @property
    def flight_number(self) -> str:
        """Get the marketing flight number."""
        return (
            f"{self.marketing_carrier.iata_code}"
            f"{self.marketing_carrier_flight_number}"
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
    duration: Optional[str] = None
    segments: List[Segment]

    @property
    def stops(self) -> int:
        """Get number of stops."""
        return len(self.segments) - 1 if self.segments else 0


class OfferSliceSegment(BaseModel):
    """Segment within an offer slice."""

    model_config = ConfigDict(populate_by_name=True)

    segment: Segment
    cabin_class: CabinClass
    cabin_class_marketing_name: Optional[str] = None
    fare_basis_code: Optional[str] = None


class OfferSlice(BaseModel):
    """Slice within an offer."""

    model_config = ConfigDict(populate_by_name=True)

    slice: Slice
    segments: List[OfferSliceSegment]
    fare_brand_name: Optional[str] = None


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
    middle_name: Optional[str] = Field(None, max_length=100)
    title: Optional[str] = Field(None, pattern="^(mr|ms|mrs|miss|dr)$")
    gender: Optional[str] = Field(None, pattern="^(m|f)$")
    born_on: date
    phone_number: Optional[str] = None
    email: Optional[str] = None

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

    id: Optional[str] = None
    type: PassengerType
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    age: Optional[int] = Field(None, ge=0, le=150)
    born_on: Optional[date] = None


class FlightOffer(BaseModel):
    """Flight offer model."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    type: str = "offer"
    created_at: datetime
    expires_at: datetime
    live_mode: bool

    slices: List[OfferSlice]
    passengers: List[Passenger]

    total_amount: Decimal = Field(..., decimal_places=2)
    total_currency: str = Field(..., pattern="^[A-Z]{3}$")

    base_amount: Optional[Decimal] = Field(None, decimal_places=2)
    base_currency: Optional[str] = Field(None, pattern="^[A-Z]{3}$")

    tax_amount: Optional[Decimal] = Field(None, decimal_places=2)
    tax_currency: Optional[str] = Field(None, pattern="^[A-Z]{3}$")

    owner: Airline
    partial: bool = False
    private_fares: List[Dict[str, Any]] = Field(default_factory=list)

    conditions: Optional[Dict[str, Any]] = None
    available_services: Optional[List[Dict[str, Any]]] = None

    # TripSage extensions
    score: Optional[float] = Field(
        None, ge=0, le=1, description="TripSage quality score"
    )
    user_preferences_match: Optional[Dict[str, Any]] = None


class FlightOfferRequest(BaseModel):
    """Flight offer request model."""

    model_config = ConfigDict(populate_by_name=True)

    id: Optional[str] = None
    type: str = "offer_request"
    created_at: Optional[datetime] = None
    live_mode: bool = True

    slices: List[Dict[str, Any]]
    passengers: List[Passenger]

    cabin_class: Optional[CabinClass] = None
    max_connections: Optional[int] = Field(None, ge=0)
    return_offers: bool = True

    # Filters
    only_airlines: Optional[List[str]] = None
    exclude_airlines: Optional[List[str]] = None


class OrderPassenger(BaseModel):
    """Passenger in an order."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    type: str = "order_passenger"
    given_name: str
    family_name: str
    title: Optional[str] = None
    gender: Optional[str] = None
    born_on: date
    phone_number: Optional[str] = None
    email: Optional[str] = None
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
    duration: Optional[str] = None
    segments: List[Dict[str, Any]]


class Payment(BaseModel):
    """Payment information."""

    model_config = ConfigDict(populate_by_name=True)

    type: PaymentType
    amount: Decimal = Field(..., decimal_places=2)
    currency: str = Field(..., pattern="^[A-Z]{3}$")
    created_at: Optional[datetime] = None


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
    synced_at: Optional[datetime] = None

    owner: Airline
    offer: Optional[FlightOffer] = None

    passengers: List[OrderPassenger]
    slices: List[OrderSlice]

    total_amount: Decimal = Field(..., decimal_places=2)
    total_currency: str = Field(..., pattern="^[A-Z]{3}$")

    base_amount: Optional[Decimal] = Field(None, decimal_places=2)
    base_currency: Optional[str] = Field(None, pattern="^[A-Z]{3}$")

    tax_amount: Optional[Decimal] = Field(None, decimal_places=2)
    tax_currency: Optional[str] = Field(None, pattern="^[A-Z]{3}$")

    payments: List[Payment] = Field(default_factory=list)
    services: List[Dict[str, Any]] = Field(default_factory=list)

    conditions: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


class OrderCreateRequest(BaseModel):
    """Request to create an order."""

    model_config = ConfigDict(populate_by_name=True)

    type: str = "instant"
    selected_offers: List[str]
    passengers: List[OrderPassenger]
    payments: List[Payment]
    services: Optional[List[Dict[str, Any]]] = None
    metadata: Optional[Dict[str, Any]] = None


class OrderCancellation(BaseModel):
    """Order cancellation model."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    type: str = "order_cancellation"
    order_id: str
    created_at: datetime
    live_mode: bool
    confirmed_at: Optional[datetime] = None
    refund_to: Optional[str] = None
    refund_amount: Optional[Decimal] = Field(None, decimal_places=2)
    refund_currency: Optional[str] = Field(None, pattern="^[A-Z]{3}$")


class SeatMap(BaseModel):
    """Seat map model."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    type: str = "seat_map"
    slice_id: str
    segment_id: str
    aircraft: Aircraft
    cabins: List[Dict[str, Any]]


class SearchParameters(BaseModel):
    """Flight search parameters."""

    model_config = ConfigDict(populate_by_name=True)

    origin: str = Field(..., pattern="^[A-Z]{3}$")
    destination: str = Field(..., pattern="^[A-Z]{3}$")
    departure_date: date
    return_date: Optional[date] = None

    adults: int = Field(1, ge=1, le=9)
    children: int = Field(0, ge=0, le=9)
    infants: int = Field(0, ge=0, le=9)

    cabin_class: CabinClass = CabinClass.ECONOMY
    max_connections: Optional[int] = Field(None, ge=0, le=3)

    # Price filters
    max_price: Optional[Decimal] = Field(None, ge=0)
    currency: str = Field("USD", pattern="^[A-Z]{3}$")

    # Airline preferences
    only_airlines: Optional[List[str]] = None
    exclude_airlines: Optional[List[str]] = None

    # Time preferences
    outbound_departure_time_from: Optional[str] = None
    outbound_departure_time_to: Optional[str] = None
    outbound_arrival_time_from: Optional[str] = None
    outbound_arrival_time_to: Optional[str] = None

    inbound_departure_time_from: Optional[str] = None
    inbound_departure_time_to: Optional[str] = None
    inbound_arrival_time_from: Optional[str] = None
    inbound_arrival_time_to: Optional[str] = None

    @field_validator("return_date")
    @classmethod
    def validate_return_date(cls, v: Optional[date], info) -> Optional[date]:
        """Ensure return date is after departure date."""
        if v and "departure_date" in info.data and v <= info.data["departure_date"]:
            raise ValueError("Return date must be after departure date")
        return v
