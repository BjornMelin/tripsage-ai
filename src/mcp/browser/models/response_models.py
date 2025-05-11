"""Response models for the Browser MCP server."""

from datetime import datetime
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


class BookingStatus(str, Enum):
    """Booking status enum."""

    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    PENDING = "pending"
    MODIFIED = "modified"
    INCOMPLETE = "incomplete"
    UNKNOWN = "unknown"


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
    actual_departure: Optional[datetime] = Field(
        None, description="Actual departure time (if departed)"
    )
    actual_arrival: Optional[datetime] = Field(
        None, description="Actual arrival time (if arrived)"
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


class FlightStatusResponse(BaseModel):
    """Response model for flight status checks."""

    success: bool = Field(..., description="Whether the operation was successful")
    message: Optional[str] = Field(
        None, description="Message about the operation (especially for errors)"
    )
    airline: str = Field(..., description="Airline code")
    flight_number: str = Field(..., description="Flight number")
    date: str = Field(..., description="Flight date")
    flight_info: Optional[FlightInfo] = Field(
        None, description="Detailed flight information (if available)"
    )
    screenshot: Optional[str] = Field(None, description="Base64-encoded screenshot")
    raw_content: Optional[str] = Field(
        None, description="Raw text content from the page (truncated)"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Timestamp of the check"
    )


class CheckInResponse(BaseModel):
    """Response model for flight check-in."""

    success: bool = Field(..., description="Whether the operation was successful")
    message: Optional[str] = Field(
        None, description="Message about the operation (especially for errors)"
    )
    airline: str = Field(..., description="Airline code")
    confirmation_code: str = Field(..., description="Booking confirmation code")
    boarding_pass_available: Optional[bool] = Field(
        None, description="Whether a boarding pass is available"
    )
    passenger_name: Optional[str] = Field(
        None, description="Passenger name (if available)"
    )
    error: Optional[str] = Field(None, description="Error message (if any)")
    screenshot: Optional[str] = Field(None, description="Base64-encoded screenshot")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Timestamp of the check-in attempt"
    )


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


class BookingVerificationResponse(BaseModel):
    """Response model for booking verification."""

    success: bool = Field(..., description="Whether the operation was successful")
    message: Optional[str] = Field(
        None, description="Message about the operation (especially for errors)"
    )
    booking_type: str = Field(
        ..., description="Booking type: 'flight', 'hotel', or 'car'"
    )
    provider: str = Field(..., description="Provider code")
    booking_reference: str = Field(..., description="Booking confirmation code")
    booking_details: Optional[BookingDetails] = Field(
        None, description="Detailed booking information (if available)"
    )
    screenshot: Optional[str] = Field(None, description="Base64-encoded screenshot")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp of the verification attempt",
    )


class PriceInfo(BaseModel):
    """Price information model."""

    amount: float = Field(..., description="Price amount")
    currency: str = Field(..., description="Currency code")
    extracted_text: str = Field(..., description="Extracted price text")
    timestamp: datetime = Field(..., description="Timestamp of the price extraction")


class PriceMonitorResponse(BaseModel):
    """Response model for price monitoring."""

    success: bool = Field(..., description="Whether the operation was successful")
    message: Optional[str] = Field(
        None, description="Message about the operation (especially for errors)"
    )
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
    error: Optional[str] = Field(None, description="Error message (if any)")
    screenshot: Optional[str] = Field(None, description="Base64-encoded screenshot")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp of the monitoring attempt",
    )


class NavigateResponse(BaseModel):
    """Response model for browser navigation."""

    success: bool = Field(..., description="Whether the operation was successful")
    message: Optional[str] = Field(
        None, description="Message about the operation (especially for errors)"
    )
    url: str = Field(..., description="URL navigated to")
    title: Optional[str] = Field(None, description="Page title")
    session_id: str = Field(..., description="Session ID for the browser context")
    error: Optional[str] = Field(None, description="Error message (if any)")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Timestamp of the navigation"
    )


class ClickResponse(BaseModel):
    """Response model for clicking elements."""

    success: bool = Field(..., description="Whether the operation was successful")
    message: Optional[str] = Field(
        None, description="Message about the operation (especially for errors)"
    )
    selector: str = Field(..., description="CSS selector for the clicked element")
    session_id: str = Field(..., description="Session ID for the browser context")
    error: Optional[str] = Field(None, description="Error message (if any)")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Timestamp of the click"
    )


class FillResponse(BaseModel):
    """Response model for filling form fields."""

    success: bool = Field(..., description="Whether the operation was successful")
    message: Optional[str] = Field(
        None, description="Message about the operation (especially for errors)"
    )
    selector: str = Field(..., description="CSS selector for the filled element")
    value: str = Field(..., description="Value filled in the input field")
    session_id: str = Field(..., description="Session ID for the browser context")
    error: Optional[str] = Field(None, description="Error message (if any)")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Timestamp of the fill operation"
    )


class SelectResponse(BaseModel):
    """Response model for selecting options in a dropdown."""

    success: bool = Field(..., description="Whether the operation was successful")
    message: Optional[str] = Field(
        None, description="Message about the operation (especially for errors)"
    )
    selector: str = Field(..., description="CSS selector for the select element")
    value: Union[str, List[str]] = Field(..., description="Value or values selected")
    session_id: str = Field(..., description="Session ID for the browser context")
    error: Optional[str] = Field(None, description="Error message (if any)")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Timestamp of the select operation"
    )


class ScreenshotResponse(BaseModel):
    """Response model for taking screenshots."""

    success: bool = Field(..., description="Whether the operation was successful")
    message: Optional[str] = Field(
        None, description="Message about the operation (especially for errors)"
    )
    screenshot: Optional[str] = Field(None, description="Base64-encoded screenshot")
    session_id: str = Field(..., description="Session ID for the browser context")
    error: Optional[str] = Field(None, description="Error message (if any)")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Timestamp of the screenshot"
    )


class GetTextResponse(BaseModel):
    """Response model for getting text content."""

    success: bool = Field(..., description="Whether the operation was successful")
    message: Optional[str] = Field(
        None, description="Message about the operation (especially for errors)"
    )
    text: Optional[str] = Field(None, description="Text content of the element")
    selector: str = Field(..., description="CSS selector for the element")
    session_id: str = Field(..., description="Session ID for the browser context")
    error: Optional[str] = Field(None, description="Error message (if any)")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Timestamp of the text extraction"
    )


class WaitForSelectorResponse(BaseModel):
    """Response model for waiting for a selector to appear."""

    success: bool = Field(..., description="Whether the operation was successful")
    message: Optional[str] = Field(
        None, description="Message about the operation (especially for errors)"
    )
    selector: str = Field(..., description="CSS selector that was waited for")
    state: str = Field(..., description="State that was waited for")
    session_id: str = Field(..., description="Session ID for the browser context")
    error: Optional[str] = Field(None, description="Error message (if any)")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Timestamp of the wait operation"
    )


class PressResponse(BaseModel):
    """Response model for pressing keys."""

    success: bool = Field(..., description="Whether the operation was successful")
    message: Optional[str] = Field(
        None, description="Message about the operation (especially for errors)"
    )
    key: str = Field(..., description="Key that was pressed")
    selector: Optional[str] = Field(
        None, description="CSS selector for element that was focused"
    )
    session_id: str = Field(..., description="Session ID for the browser context")
    error: Optional[str] = Field(None, description="Error message (if any)")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Timestamp of the key press"
    )


class EvaluateJSResponse(BaseModel):
    """Response model for executing JavaScript."""

    success: bool = Field(..., description="Whether the operation was successful")
    message: Optional[str] = Field(
        None, description="Message about the operation (especially for errors)"
    )
    result: Optional[Any] = Field(
        None, description="Result of the JavaScript execution"
    )
    session_id: str = Field(..., description="Session ID for the browser context")
    error: Optional[str] = Field(None, description="Error message (if any)")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp of the JavaScript execution",
    )


class ConsoleLogEntry(BaseModel):
    """Console log entry model."""

    type: str = Field(..., description="Log type (e.g., 'log', 'error', 'warning')")
    text: str = Field(..., description="Log text")
    location: Optional[str] = Field(None, description="Code location of the log")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Timestamp of the log entry"
    )


class GetConsoleLogsResponse(BaseModel):
    """Response model for retrieving console logs."""

    success: bool = Field(..., description="Whether the operation was successful")
    message: Optional[str] = Field(
        None, description="Message about the operation (especially for errors)"
    )
    logs: List[ConsoleLogEntry] = Field(
        default_factory=list, description="Console log entries"
    )
    session_id: str = Field(..., description="Session ID for the browser context")
    error: Optional[str] = Field(None, description="Error message (if any)")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Timestamp of the log retrieval"
    )


class CloseContextResponse(BaseModel):
    """Response model for closing a browser context."""

    success: bool = Field(..., description="Whether the operation was successful")
    message: Optional[str] = Field(
        None, description="Message about the operation (especially for errors)"
    )
    session_id: str = Field(..., description="Session ID of the closed browser context")
    error: Optional[str] = Field(None, description="Error message (if any)")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Timestamp of the context closure"
    )


class BaseResponse(BaseModel):
    """Base response model for Browser MCP operations."""

    success: bool = Field(..., description="Whether the operation was successful")
    message: Optional[str] = Field(
        None, description="Message about the operation (especially for errors)"
    )
    error: Optional[str] = Field(None, description="Error message (if any)")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Timestamp of the operation"
    )
