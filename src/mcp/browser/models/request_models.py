"""Request models for the Browser MCP server."""

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


class FlightStatusParams(BaseModel):
    """Parameters for checking flight status."""

    airline: str = Field(..., description="Airline code (e.g., 'AA', 'DL', 'UA')")
    flight_number: str = Field(
        ..., description="Flight number without airline code (e.g., '123')"
    )
    date: str = Field(..., description="Flight date in YYYY-MM-DD format")
    session_id: Optional[str] = Field(
        None, description="Optional session ID for browser context reuse"
    )


class CheckInParams(BaseModel):
    """Parameters for flight check-in."""

    airline: str = Field(..., description="Airline code (e.g., 'AA', 'DL', 'UA')")
    confirmation_code: str = Field(..., description="Booking confirmation code")
    last_name: str = Field(..., description="Passenger's last name")
    first_name: Optional[str] = Field(
        None, description="Passenger's first name (required for some airlines)"
    )
    flight_date: Optional[str] = Field(
        None, description="Flight date in YYYY-MM-DD format (if required by airline)"
    )
    session_id: Optional[str] = Field(
        None, description="Optional session ID for browser context reuse"
    )


class BookingVerificationParams(BaseModel):
    """Parameters for booking verification."""

    type: str = Field(..., description="Booking type: 'flight', 'hotel', or 'car'")
    provider: str = Field(
        ...,
        description="Provider code (e.g., 'AA' for American Airlines, 'hilton' for Hilton Hotels)",
    )
    confirmation_code: str = Field(..., description="Booking confirmation code")
    last_name: str = Field(..., description="Passenger/guest's last name")
    first_name: Optional[str] = Field(
        None, description="Passenger/guest's first name (if required)"
    )
    session_id: Optional[str] = Field(
        None, description="Optional session ID for browser context reuse"
    )


class PriceMonitorParams(BaseModel):
    """Parameters for price monitoring."""

    url: str = Field(..., description="URL of the webpage to monitor")
    selector: str = Field(..., description="CSS selector for the price element")
    check_frequency: str = Field(
        "daily",
        description="How often to check for price changes ('hourly', 'daily', 'weekly')",
    )
    notification_threshold: float = Field(
        5.0, description="Percentage change to trigger a notification"
    )
    session_id: Optional[str] = Field(
        None, description="Optional session ID for browser context reuse"
    )


class NavigateParams(BaseModel):
    """Parameters for browser navigation."""

    url: str = Field(..., description="URL to navigate to")
    wait_until: Optional[str] = Field(
        "load",
        description="When to consider navigation finished ('load', 'domcontentloaded', 'networkidle')",
    )
    timeout: Optional[int] = Field(
        None, description="Navigation timeout in milliseconds"
    )
    session_id: Optional[str] = Field(
        None, description="Optional session ID for browser context reuse"
    )


class ClickParams(BaseModel):
    """Parameters for clicking elements."""

    selector: str = Field(..., description="CSS selector for the element to click")
    timeout: Optional[int] = Field(None, description="Click timeout in milliseconds")
    session_id: Optional[str] = Field(
        None, description="Optional session ID for browser context reuse"
    )


class FillParams(BaseModel):
    """Parameters for filling form fields."""

    selector: str = Field(..., description="CSS selector for the input field")
    value: str = Field(..., description="Value to fill in the input field")
    timeout: Optional[int] = Field(None, description="Fill timeout in milliseconds")
    session_id: Optional[str] = Field(
        None, description="Optional session ID for browser context reuse"
    )


class SelectParams(BaseModel):
    """Parameters for selecting options in a dropdown."""

    selector: str = Field(..., description="CSS selector for the select element")
    value: Union[str, List[str]] = Field(..., description="Value or values to select")
    timeout: Optional[int] = Field(None, description="Select timeout in milliseconds")
    session_id: Optional[str] = Field(
        None, description="Optional session ID for browser context reuse"
    )


class ScreenshotParams(BaseModel):
    """Parameters for taking screenshots."""

    selector: Optional[str] = Field(
        None,
        description="CSS selector for the element to screenshot (full page if not provided)",
    )
    full_page: Optional[bool] = Field(
        False, description="Whether to take a screenshot of the full page"
    )
    session_id: Optional[str] = Field(
        None, description="Optional session ID for browser context reuse"
    )


class GetTextParams(BaseModel):
    """Parameters for getting text content."""

    selector: Optional[str] = Field(
        "body",
        description="CSS selector for the element to get text from (defaults to body)",
    )
    session_id: Optional[str] = Field(
        None, description="Optional session ID for browser context reuse"
    )


class WaitForSelectorParams(BaseModel):
    """Parameters for waiting for a selector to appear."""

    selector: str = Field(..., description="CSS selector to wait for")
    state: Optional[str] = Field(
        "visible",
        description="State to wait for ('attached', 'detached', 'visible', 'hidden')",
    )
    timeout: Optional[int] = Field(None, description="Wait timeout in milliseconds")
    session_id: Optional[str] = Field(
        None, description="Optional session ID for browser context reuse"
    )


class PressParams(BaseModel):
    """Parameters for pressing keys."""

    key: str = Field(
        ..., description="Key to press (e.g., 'Enter', 'Tab', 'ArrowDown')"
    )
    selector: Optional[str] = Field(
        None, description="CSS selector for element to focus before pressing key"
    )
    session_id: Optional[str] = Field(
        None, description="Optional session ID for browser context reuse"
    )


class EvaluateJSParams(BaseModel):
    """Parameters for executing JavaScript."""

    script: str = Field(..., description="JavaScript to execute")
    arg: Optional[Any] = Field(None, description="Argument to pass to the script")
    session_id: Optional[str] = Field(
        None, description="Optional session ID for browser context reuse"
    )


class GetConsoleLogsParams(BaseModel):
    """Parameters for retrieving console logs."""

    session_id: Optional[str] = Field(
        None, description="Optional session ID for browser context reuse"
    )


class CloseContextParams(BaseModel):
    """Parameters for closing a browser context."""

    session_id: str = Field(
        ..., description="Session ID of the browser context to close"
    )
