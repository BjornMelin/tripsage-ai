"""Request models for the Browser MCP server."""

from enum import Enum
from typing import Any, List, Literal, Optional, Union

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from src.mcp.browser.utils.validators import (
    AirlineValidator,
    BookingReferenceValidator,
    CheckFrequencyValidator,
    CssSelectorValidator,
    DateValidator,
    FlightNumberValidator,
    ProviderValidator,
    SessionIdValidator,
    URLValidator,
)


class BookingType(str, Enum):
    """Booking type enum."""

    FLIGHT = "flight"
    HOTEL = "hotel"
    CAR = "car"


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

    model_config = ConfigDict(extra="forbid")

    @field_validator("airline")
    @classmethod
    def validate_airline(cls, v: str) -> str:
        """Validate airline code."""
        AirlineValidator(airline_code=v)
        return v

    @field_validator("flight_number")
    @classmethod
    def validate_flight_number(cls, v: str) -> str:
        """Validate flight number."""
        FlightNumberValidator(flight_number=v)
        return v

    @field_validator("date")
    @classmethod
    def validate_date(cls, v: str) -> str:
        """Validate date string."""
        DateValidator(date_str=v)
        return v

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, v: Optional[str]) -> Optional[str]:
        """Validate session ID if provided."""
        if v is not None:
            SessionIdValidator(session_id=v)
        return v


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

    model_config = ConfigDict(extra="forbid")

    @field_validator("airline")
    @classmethod
    def validate_airline(cls, v: str) -> str:
        """Validate airline code."""
        AirlineValidator(airline_code=v)
        return v

    @field_validator("confirmation_code")
    @classmethod
    def validate_confirmation_code(cls, v: str) -> str:
        """Validate confirmation code."""
        BookingReferenceValidator(booking_reference=v)
        return v

    @field_validator("flight_date")
    @classmethod
    def validate_flight_date(cls, v: Optional[str]) -> Optional[str]:
        """Validate flight date if provided."""
        if v is not None:
            DateValidator(date_str=v)
        return v

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, v: Optional[str]) -> Optional[str]:
        """Validate session ID if provided."""
        if v is not None:
            SessionIdValidator(session_id=v)
        return v


class BookingVerificationParams(BaseModel):
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
    session_id: Optional[str] = Field(
        None, description="Optional session ID for browser context reuse"
    )

    model_config = ConfigDict(extra="forbid")

    @field_validator("confirmation_code")
    @classmethod
    def validate_confirmation_code(cls, v: str) -> str:
        """Validate confirmation code."""
        BookingReferenceValidator(booking_reference=v)
        return v

    @model_validator(mode="after")
    def validate_provider_for_booking_type(self) -> "BookingVerificationParams":
        """Validate provider for booking type."""
        ProviderValidator(booking_type=self.type.value, provider=self.provider)
        return self

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, v: Optional[str]) -> Optional[str]:
        """Validate session ID if provided."""
        if v is not None:
            SessionIdValidator(session_id=v)
        return v


class PriceMonitorParams(BaseModel):
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
    session_id: Optional[str] = Field(
        None, description="Optional session ID for browser context reuse"
    )

    model_config = ConfigDict(extra="forbid")

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate URL."""
        URLValidator(url=v)
        return v

    @field_validator("selector")
    @classmethod
    def validate_selector(cls, v: str) -> str:
        """Validate CSS selector."""
        CssSelectorValidator(selector=v)
        return v

    @field_validator("check_frequency")
    @classmethod
    def validate_check_frequency(cls, v: str) -> str:
        """Validate check frequency."""
        CheckFrequencyValidator(frequency=v)
        return v

    @field_validator("notification_threshold")
    @classmethod
    def validate_notification_threshold(cls, v: float) -> float:
        """Validate notification threshold."""
        if v <= 0:
            raise ValueError("Notification threshold must be greater than 0")
        return v

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, v: Optional[str]) -> Optional[str]:
        """Validate session ID if provided."""
        if v is not None:
            SessionIdValidator(session_id=v)
        return v


class NavigateParams(BaseModel):
    """Parameters for browser navigation."""

    url: str = Field(..., description="URL to navigate to")
    wait_until: Optional[Literal["load", "domcontentloaded", "networkidle"]] = Field(
        "load",
        description="When to consider navigation finished "
        "('load', 'domcontentloaded', 'networkidle')",
    )
    timeout: Optional[int] = Field(
        None, description="Navigation timeout in milliseconds"
    )
    session_id: Optional[str] = Field(
        None, description="Optional session ID for browser context reuse"
    )

    model_config = ConfigDict(extra="forbid")

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate URL."""
        URLValidator(url=v)
        return v

    @field_validator("timeout")
    @classmethod
    def validate_timeout(cls, v: Optional[int]) -> Optional[int]:
        """Validate timeout."""
        if v is not None and v <= 0:
            raise ValueError("Timeout must be greater than 0")
        return v

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, v: Optional[str]) -> Optional[str]:
        """Validate session ID if provided."""
        if v is not None:
            SessionIdValidator(session_id=v)
        return v


class ClickParams(BaseModel):
    """Parameters for clicking elements."""

    selector: str = Field(..., description="CSS selector for the element to click")
    timeout: Optional[int] = Field(None, description="Click timeout in milliseconds")
    session_id: Optional[str] = Field(
        None, description="Optional session ID for browser context reuse"
    )

    model_config = ConfigDict(extra="forbid")

    @field_validator("selector")
    @classmethod
    def validate_selector(cls, v: str) -> str:
        """Validate CSS selector."""
        CssSelectorValidator(selector=v)
        return v

    @field_validator("timeout")
    @classmethod
    def validate_timeout(cls, v: Optional[int]) -> Optional[int]:
        """Validate timeout."""
        if v is not None and v <= 0:
            raise ValueError("Timeout must be greater than 0")
        return v

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, v: Optional[str]) -> Optional[str]:
        """Validate session ID if provided."""
        if v is not None:
            SessionIdValidator(session_id=v)
        return v


class FillParams(BaseModel):
    """Parameters for filling form fields."""

    selector: str = Field(..., description="CSS selector for the input field")
    value: str = Field(..., description="Value to fill in the input field")
    timeout: Optional[int] = Field(None, description="Fill timeout in milliseconds")
    session_id: Optional[str] = Field(
        None, description="Optional session ID for browser context reuse"
    )

    model_config = ConfigDict(extra="forbid")

    @field_validator("selector")
    @classmethod
    def validate_selector(cls, v: str) -> str:
        """Validate CSS selector."""
        CssSelectorValidator(selector=v)
        return v

    @field_validator("timeout")
    @classmethod
    def validate_timeout(cls, v: Optional[int]) -> Optional[int]:
        """Validate timeout."""
        if v is not None and v <= 0:
            raise ValueError("Timeout must be greater than 0")
        return v

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, v: Optional[str]) -> Optional[str]:
        """Validate session ID if provided."""
        if v is not None:
            SessionIdValidator(session_id=v)
        return v


class SelectParams(BaseModel):
    """Parameters for selecting options in a dropdown."""

    selector: str = Field(..., description="CSS selector for the select element")
    value: Union[str, List[str]] = Field(..., description="Value or values to select")
    timeout: Optional[int] = Field(None, description="Select timeout in milliseconds")
    session_id: Optional[str] = Field(
        None, description="Optional session ID for browser context reuse"
    )

    model_config = ConfigDict(extra="forbid")

    @field_validator("selector")
    @classmethod
    def validate_selector(cls, v: str) -> str:
        """Validate CSS selector."""
        CssSelectorValidator(selector=v)
        return v

    @field_validator("timeout")
    @classmethod
    def validate_timeout(cls, v: Optional[int]) -> Optional[int]:
        """Validate timeout."""
        if v is not None and v <= 0:
            raise ValueError("Timeout must be greater than 0")
        return v

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, v: Optional[str]) -> Optional[str]:
        """Validate session ID if provided."""
        if v is not None:
            SessionIdValidator(session_id=v)
        return v


class ScreenshotParams(BaseModel):
    """Parameters for taking screenshots."""

    selector: Optional[str] = Field(
        None,
        description="CSS selector for the element to screenshot "
        "(full page if not provided)",
    )
    full_page: Optional[bool] = Field(
        False, description="Whether to take a screenshot of the full page"
    )
    session_id: Optional[str] = Field(
        None, description="Optional session ID for browser context reuse"
    )

    model_config = ConfigDict(extra="forbid")

    @field_validator("selector")
    @classmethod
    def validate_selector(cls, v: Optional[str]) -> Optional[str]:
        """Validate CSS selector if provided."""
        if v is not None:
            CssSelectorValidator(selector=v)
        return v

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, v: Optional[str]) -> Optional[str]:
        """Validate session ID if provided."""
        if v is not None:
            SessionIdValidator(session_id=v)
        return v


class GetTextParams(BaseModel):
    """Parameters for getting text content."""

    selector: Optional[str] = Field(
        "body",
        description="CSS selector for the element to get text from (defaults to body)",
    )
    session_id: Optional[str] = Field(
        None, description="Optional session ID for browser context reuse"
    )

    model_config = ConfigDict(extra="forbid")

    @field_validator("selector")
    @classmethod
    def validate_selector(cls, v: Optional[str]) -> Optional[str]:
        """Validate CSS selector if provided."""
        if v is not None:
            CssSelectorValidator(selector=v)
        return v

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, v: Optional[str]) -> Optional[str]:
        """Validate session ID if provided."""
        if v is not None:
            SessionIdValidator(session_id=v)
        return v


class WaitForSelectorParams(BaseModel):
    """Parameters for waiting for a selector to appear."""

    selector: str = Field(..., description="CSS selector to wait for")
    state: Optional[Literal["attached", "detached", "visible", "hidden"]] = Field(
        "visible",
        description="State to wait for ('attached', 'detached', 'visible', 'hidden')",
    )
    timeout: Optional[int] = Field(None, description="Wait timeout in milliseconds")
    session_id: Optional[str] = Field(
        None, description="Optional session ID for browser context reuse"
    )

    model_config = ConfigDict(extra="forbid")

    @field_validator("selector")
    @classmethod
    def validate_selector(cls, v: str) -> str:
        """Validate CSS selector."""
        CssSelectorValidator(selector=v)
        return v

    @field_validator("timeout")
    @classmethod
    def validate_timeout(cls, v: Optional[int]) -> Optional[int]:
        """Validate timeout."""
        if v is not None and v <= 0:
            raise ValueError("Timeout must be greater than 0")
        return v

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, v: Optional[str]) -> Optional[str]:
        """Validate session ID if provided."""
        if v is not None:
            SessionIdValidator(session_id=v)
        return v


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

    model_config = ConfigDict(extra="forbid")

    @field_validator("selector")
    @classmethod
    def validate_selector(cls, v: Optional[str]) -> Optional[str]:
        """Validate CSS selector if provided."""
        if v is not None:
            CssSelectorValidator(selector=v)
        return v

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, v: Optional[str]) -> Optional[str]:
        """Validate session ID if provided."""
        if v is not None:
            SessionIdValidator(session_id=v)
        return v


class EvaluateJSParams(BaseModel):
    """Parameters for executing JavaScript."""

    script: str = Field(..., description="JavaScript to execute")
    arg: Optional[Any] = Field(None, description="Argument to pass to the script")
    session_id: Optional[str] = Field(
        None, description="Optional session ID for browser context reuse"
    )

    model_config = ConfigDict(extra="forbid")

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, v: Optional[str]) -> Optional[str]:
        """Validate session ID if provided."""
        if v is not None:
            SessionIdValidator(session_id=v)
        return v


class GetConsoleLogsParams(BaseModel):
    """Parameters for retrieving console logs."""

    session_id: Optional[str] = Field(
        None, description="Optional session ID for browser context reuse"
    )

    model_config = ConfigDict(extra="forbid")

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, v: Optional[str]) -> Optional[str]:
        """Validate session ID if provided."""
        if v is not None:
            SessionIdValidator(session_id=v)
        return v


class CloseContextParams(BaseModel):
    """Parameters for closing a browser context."""

    session_id: str = Field(
        ..., description="Session ID of the browser context to close"
    )

    model_config = ConfigDict(extra="forbid")

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, v: str) -> str:
        """Validate session ID."""
        SessionIdValidator(session_id=v)
        return v
