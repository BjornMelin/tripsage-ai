"""Validation utilities for the Browser MCP server."""

import re
import urllib.parse
from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
    validate_call,
)

from src.mcp.browser.config import Config
from src.mcp.browser.utils.logging import get_logger

logger = get_logger(__name__)


class URLValidator(BaseModel):
    """Model for validating URLs."""

    url: str = Field(..., description="URL to validate")

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    @field_validator("url")
    @classmethod
    def validate_url_format(cls, v: str) -> str:
        """Validate if a URL is properly formatted."""
        if not v or not isinstance(v, str):
            raise ValueError("URL is required and must be a string")

        # Basic URL format validation
        url_pattern = re.compile(
            r"^(?:http|https)://"  # http:// or https://
            r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|"  # domain
            r"localhost|"  # localhost
            r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # or IPv4
            r"(?::\d+)?"  # optional port
            r"(?:/?|[/?]\S+)$",
            re.IGNORECASE,
        )

        if not url_pattern.match(v):
            raise ValueError(f"Invalid URL format: {v}")

        # Parse URL
        parsed_url = urllib.parse.urlparse(v)

        # Check scheme
        if parsed_url.scheme not in ["http", "https"]:
            raise ValueError(f"URL must use http or https protocol: {v}")

        # Check for internal IP addresses
        if _is_internal_ip(parsed_url.netloc):
            raise ValueError(f"URLs to internal IP addresses are not allowed: {v}")

        # Check for localhost
        if "localhost" in parsed_url.netloc.lower() or "127.0.0.1" in parsed_url.netloc:
            raise ValueError(f"URLs to localhost are not allowed: {v}")

        return v


class DateValidator(BaseModel):
    """Model for validating date strings."""

    date_str: str = Field(..., description="Date string in YYYY-MM-DD format")

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    @field_validator("date_str")
    @classmethod
    def validate_date_format(cls, v: str) -> str:
        """Validate if a date string is properly formatted."""
        if not v or not isinstance(v, str):
            raise ValueError("Date is required and must be a string")

        # Check format
        date_pattern = re.compile(r"^\d{4}-\d{2}-\d{2}$")
        if not date_pattern.match(v):
            raise ValueError(f"Invalid date format: {v}. Expected YYYY-MM-DD")

        # Check if it's a valid date
        try:
            year, month, day = map(int, v.split("-"))
            datetime(year, month, day)
        except ValueError as e:
            raise ValueError(f"Invalid date: {v}. {str(e)}")

        return v


class AirlineValidator(BaseModel):
    """Model for validating airline codes."""

    airline_code: str = Field(..., description="Airline code (e.g., 'AA', 'DL')")

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    @field_validator("airline_code")
    @classmethod
    def validate_airline_format(cls, v: str) -> str:
        """Validate if an airline code is properly formatted."""
        if not v or not isinstance(v, str):
            raise ValueError("Airline code is required and must be a string")

        # Basic airline code format validation (IATA codes are typically 2 characters)
        if not re.match(r"^[A-Z0-9]{2,3}$", v):
            raise ValueError(
                f"Invalid airline code format: {v}. Expected 2-3 uppercase letters/digits"
            )

        # Check if airline is supported
        if v not in Config.AIRLINE_STATUS_URLS:
            # We'll allow unknown airlines but log a warning
            logger.warning(f"Unknown airline code: {v}. Using generic status URL")

        return v


class FlightNumberValidator(BaseModel):
    """Model for validating flight numbers."""

    flight_number: str = Field(..., description="Flight number (without airline code)")

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    @field_validator("flight_number")
    @classmethod
    def validate_flight_number_format(cls, v: str) -> str:
        """Validate if a flight number is properly formatted."""
        if not v or not isinstance(v, str):
            raise ValueError("Flight number is required and must be a string")

        # Basic flight number format validation
        if not re.match(r"^[0-9]{1,4}[A-Z]?$", v):
            raise ValueError(
                f"Invalid flight number format: {v}. Expected 1-4 digits, optionally followed by a letter"
            )

        return v


class BookingTypeValidator(BaseModel):
    """Model for validating booking types."""

    booking_type: str = Field(
        ..., description="Booking type ('flight', 'hotel', or 'car')"
    )

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    @field_validator("booking_type")
    @classmethod
    def validate_booking_type_format(cls, v: str) -> str:
        """Validate if a booking type is supported."""
        if not v or not isinstance(v, str):
            raise ValueError("Booking type is required and must be a string")

        valid_types = ["flight", "hotel", "car"]
        if v not in valid_types:
            raise ValueError(
                f"Invalid booking type: {v}. Must be one of: {', '.join(valid_types)}"
            )

        return v


class ProviderValidator(BaseModel):
    """Model for validating booking providers."""

    booking_type: str = Field(
        ..., description="Booking type ('flight', 'hotel', or 'car')"
    )
    provider: str = Field(..., description="Provider code")

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    @model_validator(mode="after")
    def validate_provider_for_booking_type(self) -> "ProviderValidator":
        """Validate if a provider for a booking type is supported."""
        booking_type = self.booking_type
        provider = self.provider

        if not provider or not isinstance(provider, str):
            raise ValueError("Provider code is required and must be a string")

        # Check if provider is supported for the booking type
        supported_providers = Config.BOOKING_VERIFICATION_URLS.get(booking_type, {})
        if provider not in supported_providers:
            # We'll allow unknown providers but log a warning
            logger.warning(
                f"Unknown provider '{provider}' for booking type '{booking_type}'. Using generic verification URL"
            )

        return self


class BookingReferenceValidator(BaseModel):
    """Model for validating booking references."""

    booking_reference: str = Field(
        ..., description="Booking reference/confirmation code"
    )

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    @field_validator("booking_reference")
    @classmethod
    def validate_booking_reference_format(cls, v: str) -> str:
        """Validate if a booking reference is properly formatted."""
        if not v or not isinstance(v, str):
            raise ValueError("Booking reference is required and must be a string")

        # Basic booking reference format validation (alphanumeric, typically 5-8 characters)
        if not re.match(r"^[A-Z0-9]{4,10}$", v.upper()):
            raise ValueError(
                f"Invalid booking reference format: {v}. Expected 4-10 alphanumeric characters"
            )

        return v


class EmailValidator(BaseModel):
    """Model for validating email addresses."""

    email: str = Field(..., description="Email address")

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v: str) -> str:
        """Validate if an email address is properly formatted."""
        if not v or not isinstance(v, str):
            raise ValueError("Email is required and must be a string")

        # Basic email format validation
        email_pattern = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
        if not email_pattern.match(v):
            raise ValueError(f"Invalid email format: {v}")

        return v


class CssSelectorValidator(BaseModel):
    """Model for validating CSS selectors."""

    selector: str = Field(..., description="CSS selector")

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    @field_validator("selector")
    @classmethod
    def validate_selector_format(cls, v: str) -> str:
        """Validate if a CSS selector is properly formatted."""
        if not v or not isinstance(v, str):
            raise ValueError("CSS selector is required and must be a string")

        # Check for common issues in selectors
        invalid_patterns = [
            r"<\s*[a-z]",  # HTML tags
            r"#\d",  # IDs that start with a digit
            r"@import",  # CSS import statements
            r"url\(",  # URL patterns
        ]

        for pattern in invalid_patterns:
            if re.search(pattern, v):
                raise ValueError(f"Invalid CSS selector: {v}")

        return v


class CheckFrequencyValidator(BaseModel):
    """Model for validating check frequencies."""

    frequency: str = Field(
        ..., description="Check frequency ('hourly', 'daily', or 'weekly')"
    )

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    @field_validator("frequency")
    @classmethod
    def validate_frequency_format(cls, v: str) -> str:
        """Validate if a check frequency is valid."""
        if not v or not isinstance(v, str):
            raise ValueError("Check frequency is required and must be a string")

        valid_frequencies = ["hourly", "daily", "weekly"]
        if v not in valid_frequencies:
            raise ValueError(
                f"Invalid check frequency: {v}. Must be one of: {', '.join(valid_frequencies)}"
            )

        return v


class SessionIdValidator(BaseModel):
    """Model for validating session IDs."""

    session_id: str = Field(..., description="Session ID")

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    @field_validator("session_id")
    @classmethod
    def validate_session_id_format(cls, v: str) -> str:
        """Validate if a session ID is properly formatted."""
        if not v or not isinstance(v, str):
            raise ValueError("Session ID is required and must be a string")

        # Basic session ID format validation (alphanumeric and dashes)
        if not re.match(r"^[A-Za-z0-9_-]{1,64}$", v):
            raise ValueError(
                f"Invalid session ID format: {v}. Expected alphanumeric characters, underscores, or dashes"
            )

        return v


# Function-based validators with @validate_call decorator for backward compatibility


@validate_call
def validate_url(url: str) -> bool:
    """Validate if a URL is properly formatted and allowed.

    Args:
        url: URL to validate

    Returns:
        True if URL is valid and allowed, False otherwise

    Raises:
        ValueError: If URL is invalid or disallowed
    """
    try:
        URLValidator(url=url)
        return True
    except ValidationError as e:
        raise ValueError(str(e)) from e


@validate_call
def validate_date(date_str: str) -> bool:
    """Validate if a date string is properly formatted.

    Args:
        date_str: Date string in YYYY-MM-DD format

    Returns:
        True if date is valid, False otherwise

    Raises:
        ValueError: If date is invalid
    """
    try:
        DateValidator(date_str=date_str)
        return True
    except ValidationError as e:
        raise ValueError(str(e)) from e


@validate_call
def validate_airline_code(airline_code: str) -> bool:
    """Validate if an airline code is properly formatted.

    Args:
        airline_code: Airline code (e.g., 'AA', 'DL')

    Returns:
        True if airline code is valid, False otherwise

    Raises:
        ValueError: If airline code is invalid
    """
    try:
        AirlineValidator(airline_code=airline_code)
        return True
    except ValidationError as e:
        raise ValueError(str(e)) from e


@validate_call
def validate_flight_number(flight_number: str) -> bool:
    """Validate if a flight number is properly formatted.

    Args:
        flight_number: Flight number (without airline code)

    Returns:
        True if flight number is valid, False otherwise

    Raises:
        ValueError: If flight number is invalid
    """
    try:
        FlightNumberValidator(flight_number=flight_number)
        return True
    except ValidationError as e:
        raise ValueError(str(e)) from e


@validate_call
def validate_booking_type(booking_type: str) -> bool:
    """Validate if a booking type is supported.

    Args:
        booking_type: Booking type ('flight', 'hotel', or 'car')

    Returns:
        True if booking type is valid, False otherwise

    Raises:
        ValueError: If booking type is invalid
    """
    try:
        BookingTypeValidator(booking_type=booking_type)
        return True
    except ValidationError as e:
        raise ValueError(str(e)) from e


@validate_call
def validate_provider(booking_type: str, provider: str) -> bool:
    """Validate if a provider for a booking type is supported.

    Args:
        booking_type: Booking type ('flight', 'hotel', or 'car')
        provider: Provider code

    Returns:
        True if provider is valid for the booking type, False otherwise

    Raises:
        ValueError: If provider is invalid for the booking type
    """
    try:
        ProviderValidator(booking_type=booking_type, provider=provider)
        return True
    except ValidationError as e:
        raise ValueError(str(e)) from e


@validate_call
def validate_booking_reference(booking_reference: str) -> bool:
    """Validate if a booking reference is properly formatted.

    Args:
        booking_reference: Booking reference/confirmation code

    Returns:
        True if booking reference is valid, False otherwise

    Raises:
        ValueError: If booking reference is invalid
    """
    try:
        BookingReferenceValidator(booking_reference=booking_reference)
        return True
    except ValidationError as e:
        raise ValueError(str(e)) from e


@validate_call
def validate_email(email: str) -> bool:
    """Validate if an email address is properly formatted.

    Args:
        email: Email address

    Returns:
        True if email is valid, False otherwise

    Raises:
        ValueError: If email is invalid
    """
    try:
        EmailValidator(email=email)
        return True
    except ValidationError as e:
        raise ValueError(str(e)) from e


@validate_call
def validate_confirmation_code(confirmation_code: str) -> bool:
    """Validate if a confirmation code is properly formatted.

    Args:
        confirmation_code: Booking confirmation code

    Returns:
        True if confirmation code is valid, False otherwise

    Raises:
        ValueError: If confirmation code is invalid
    """
    # Alias for validate_booking_reference
    return validate_booking_reference(booking_reference=confirmation_code)


@validate_call
def validate_css_selector(selector: str) -> bool:
    """Validate if a CSS selector is properly formatted.

    Note: This is a basic validation and might not catch all invalid selectors.

    Args:
        selector: CSS selector

    Returns:
        True if selector is valid, False otherwise

    Raises:
        ValueError: If selector is invalid
    """
    try:
        CssSelectorValidator(selector=selector)
        return True
    except ValidationError as e:
        raise ValueError(str(e)) from e


@validate_call
def validate_check_frequency(frequency: str) -> bool:
    """Validate if a check frequency is valid.

    Args:
        frequency: Check frequency ('hourly', 'daily', or 'weekly')

    Returns:
        True if frequency is valid, False otherwise

    Raises:
        ValueError: If frequency is invalid
    """
    try:
        CheckFrequencyValidator(frequency=frequency)
        return True
    except ValidationError as e:
        raise ValueError(str(e)) from e


@validate_call
def validate_session_id(session_id: str) -> bool:
    """Validate if a session ID is properly formatted.

    Args:
        session_id: Session ID

    Returns:
        True if session ID is valid, False otherwise

    Raises:
        ValueError: If session ID is invalid
    """
    try:
        SessionIdValidator(session_id=session_id)
        return True
    except ValidationError as e:
        raise ValueError(str(e)) from e


def _is_internal_ip(netloc: str) -> bool:
    """Check if a netloc string represents an internal IP address.

    Args:
        netloc: Netloc from URL (e.g., '192.168.1.1:8080')

    Returns:
        True if netloc is an internal IP address, False otherwise
    """
    # Extract hostname without port
    hostname = netloc.split(":")[0]

    # Check if it's an IP address
    ip_pattern = re.compile(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$")
    if not ip_pattern.match(hostname):
        return False

    # Parse the IP address
    octets = hostname.split(".")
    if len(octets) != 4:
        return False

    # Check for internal IPs
    if octets[0] == "10":  # 10.0.0.0/8
        return True
    if octets[0] == "172" and 16 <= int(octets[1]) <= 31:  # 172.16.0.0/12
        return True
    if octets[0] == "192" and octets[1] == "168":  # 192.168.0.0/16
        return True

    return False
