"""
Browser automation schemas for the TripSage travel planning system.

This module provides data models for Browser tools, which access
browser automation capabilities through external MCPs (Playwright and Stagehand).
"""

import logging
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, field_validator

# Setup logging
logger = logging.getLogger(__name__)


class BookingType(str, Enum):
    """Booking type enum."""

    FLIGHT = "flight"
    HOTEL = "hotel"
    CAR = "car"


class BookingStatus(str, Enum):
    """Booking status enum."""

    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    PENDING = "pending"
    MODIFIED = "modified"
    INCOMPLETE = "incomplete"
    UNKNOWN = "unknown"


class BaseBrowserParams(BaseModel):
    """Base model for browser automation parameters."""

    session_id: Optional[str] = Field(
        None, description="Optional session ID for browser context reuse"
    )


class FlightStatusParams(BaseBrowserParams):
    """Parameters for checking flight status."""

    airline: str = Field(..., description="Airline code (e.g., 'AA', 'DL', 'UA')")
    flight_number: str = Field(
        ..., description="Flight number without airline code (e.g., '123')"
    )
    date: str = Field(..., description="Flight date in YYYY-MM-DD format")

    @field_validator("airline")
    @classmethod
    def validate_airline(cls, v: str) -> str:
        """Validate airline code."""
        if not v or len(v) > 3:
            raise ValueError("Airline code must be 1-3 characters")
        return v.upper()

    @field_validator("flight_number")
    @classmethod
    def validate_flight_number(cls, v: str) -> str:
        """Validate flight number."""
        if not v or not v.strip():
            raise ValueError("Flight number cannot be empty")
        return v


class BookingVerificationParams(BaseBrowserParams):
    """Parameters for booking verification."""

    type: BookingType = Field(
        ..., description="Booking type: 'flight', 'hotel', or 'car'"
    )
    provider: str = Field(
        ...,
        description="Provider code (e.g., 'AA' for American Airlines, "
        "'hilton' for Hilton Hotels)",
    )
    confirmation_code: str = Field(..., description="Booking confirmation code")
    last_name: str = Field(..., description="Passenger/guest's last name")
    first_name: Optional[str] = Field(
        None, description="Passenger/guest's first name (if required)"
    )


class PriceMonitorParams(BaseBrowserParams):
    """Parameters for price monitoring."""

    url: str = Field(..., description="URL of the webpage to monitor")
    selector: str = Field(..., description="CSS selector for the price element")
    check_frequency: str = Field(
        "daily",
        description="How often to check for price changes "
        "('hourly', 'daily', 'weekly')",
    )
    notification_threshold: float = Field(
        5.0, description="Percentage change to trigger a notification"
    )

    @field_validator("notification_threshold")
    @classmethod
    def validate_notification_threshold(cls, v: float) -> float:
        """Validate notification threshold."""
        if v <= 0:
            raise ValueError("Notification threshold must be greater than 0")
        return v


class FlightInfo(BaseModel):
    """Flight information model."""

    airline: str = Field(..., description="Airline code")
    flight_number: str = Field(..., description="Flight number")
    departure_airport: str = Field(..., description="Departure airport code")
    arrival_airport: str = Field(..., description="Arrival airport code")
    scheduled_departure: datetime = Field(..., description="Scheduled departure time")
    scheduled_arrival: datetime = Field(..., description="Scheduled arrival time")
    estimated_departure: Optional[datetime] = Field(
        None, description="Estimated departure time"
    )
    estimated_arrival: Optional[datetime] = Field(
        None, description="Estimated arrival time"
    )
    status: str = Field(
        ..., description="Flight status (e.g., 'On Time', 'Delayed', 'Cancelled')"
    )
    delay_minutes: Optional[int] = Field(
        None, description="Delay in minutes (if delayed)"
    )
    terminal_departure: Optional[str] = Field(None, description="Departure terminal")
    gate_departure: Optional[str] = Field(None, description="Departure gate")
    terminal_arrival: Optional[str] = Field(None, description="Arrival terminal")
    gate_arrival: Optional[str] = Field(None, description="Arrival gate")


class BookingDetails(BaseModel):
    """Booking details model for verification responses."""

    passenger_name: str = Field(..., description="Passenger/guest name")
    origin: Optional[str] = Field(
        None, description="Origin/pickup location (for flights/cars)"
    )
    destination: Optional[str] = Field(
        None, description="Destination/dropoff location (for flights/cars)"
    )
    departure_date: Optional[str] = Field(None, description="Departure/check-in date")
    return_date: Optional[str] = Field(None, description="Return/check-out date")
    flight_number: Optional[str] = Field(
        None, description="Flight number (for flights)"
    )
    status: BookingStatus = Field(BookingStatus.UNKNOWN, description="Booking status")
    additional_info: Dict[str, Any] = Field(
        default_factory=dict, description="Additional booking information"
    )


class PriceInfo(BaseModel):
    """Price information model."""

    amount: float = Field(..., description="Price amount")
    currency: str = Field(..., description="Currency code")
    extracted_text: str = Field(..., description="Extracted price text")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Timestamp of the price extraction"
    )

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: float) -> float:
        """Validate amount is positive."""
        if v < 0:
            raise ValueError("Price amount must be non-negative")
        return v


class BaseResponse(BaseModel):
    """Base response model for browser operations."""

    success: bool = Field(..., description="Whether the operation was successful")
    message: Optional[str] = Field(
        None, description="Message about the operation (especially for errors)"
    )
    error: Optional[str] = Field(None, description="Error message (if any)")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Timestamp of the operation"
    )
    session_id: Optional[str] = Field(
        None, description="Session ID for browser context"
    )


class FlightStatusResponse(BaseResponse):
    """Response model for flight status checks."""

    airline: str = Field(..., description="Airline code")
    flight_number: str = Field(..., description="Flight number")
    date: str = Field(..., description="Flight date")
    flight_info: Optional[FlightInfo] = Field(
        None, description="Detailed flight information (if available)"
    )
    screenshot: Optional[str] = Field(None, description="Base64-encoded screenshot")


class BookingVerificationResponse(BaseResponse):
    """Response model for booking verification."""

    booking_type: str = Field(
        ..., description="Booking type: 'flight', 'hotel', or 'car'"
    )
    provider: str = Field(..., description="Provider code")
    booking_reference: str = Field(..., description="Booking confirmation code")
    booking_details: Optional[BookingDetails] = Field(
        None, description="Detailed booking information (if available)"
    )
    screenshot: Optional[str] = Field(None, description="Base64-encoded screenshot")


class PriceMonitorResponse(BaseResponse):
    """Response model for price monitoring."""

    url: str = Field(..., description="URL being monitored")
    initial_price: Optional[PriceInfo] = Field(
        None, description="Initial price information"
    )
    check_frequency: str = Field(
        ..., description="How often to check for price changes"
    )
    next_check: str = Field(
        ..., description="When the next check will occur (ISO format)"
    )
    monitoring_id: str = Field(
        ..., description="Unique ID for this price monitoring session"
    )
    screenshot: Optional[str] = Field(None, description="Base64-encoded screenshot")
