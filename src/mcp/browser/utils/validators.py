"""Validation utilities for the Browser MCP server."""

import re
import urllib.parse
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Union

from src.mcp.browser.config import Config
from src.mcp.browser.utils.logging import get_logger

logger = get_logger(__name__)


def validate_url(url: str) -> bool:
    """Validate if a URL is properly formatted and allowed.

    Args:
        url: URL to validate

    Returns:
        True if URL is valid and allowed, False otherwise

    Raises:
        ValueError: If URL is invalid or disallowed
    """
    # Check if URL is properly formatted
    if not url or not isinstance(url, str):
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

    if not url_pattern.match(url):
        raise ValueError(f"Invalid URL format: {url}")

    # Parse URL
    parsed_url = urllib.parse.urlparse(url)

    # Check scheme
    if parsed_url.scheme not in ["http", "https"]:
        raise ValueError(f"URL must use http or https protocol: {url}")

    # Check for internal IP addresses
    if _is_internal_ip(parsed_url.netloc):
        raise ValueError(f"URLs to internal IP addresses are not allowed: {url}")

    # Check for localhost
    if "localhost" in parsed_url.netloc.lower() or "127.0.0.1" in parsed_url.netloc:
        raise ValueError(f"URLs to localhost are not allowed: {url}")

    return True


def validate_date(date_str: str) -> bool:
    """Validate if a date string is properly formatted.

    Args:
        date_str: Date string in YYYY-MM-DD format

    Returns:
        True if date is valid, False otherwise

    Raises:
        ValueError: If date is invalid
    """
    if not date_str or not isinstance(date_str, str):
        raise ValueError("Date is required and must be a string")

    # Check format
    date_pattern = re.compile(r"^\d{4}-\d{2}-\d{2}$")
    if not date_pattern.match(date_str):
        raise ValueError(f"Invalid date format: {date_str}. Expected YYYY-MM-DD")

    # Check if it's a valid date
    try:
        year, month, day = map(int, date_str.split("-"))
        datetime(year, month, day)
    except ValueError as e:
        raise ValueError(f"Invalid date: {date_str}. {str(e)}")

    return True


def validate_airline_code(airline_code: str) -> bool:
    """Validate if an airline code is properly formatted.

    Args:
        airline_code: Airline code (e.g., 'AA', 'DL')

    Returns:
        True if airline code is valid, False otherwise

    Raises:
        ValueError: If airline code is invalid
    """
    if not airline_code or not isinstance(airline_code, str):
        raise ValueError("Airline code is required and must be a string")

    # Basic airline code format validation (IATA codes are typically 2 characters)
    if not re.match(r"^[A-Z0-9]{2,3}$", airline_code):
        raise ValueError(
            f"Invalid airline code format: {airline_code}. Expected 2-3 uppercase letters/digits"
        )

    # Check if airline is supported
    if airline_code not in Config.AIRLINE_STATUS_URLS:
        # We'll allow unknown airlines but log a warning
        logger.warning(
            f"Unknown airline code: {airline_code}. Using generic status URL"
        )

    return True


def validate_flight_number(flight_number: str) -> bool:
    """Validate if a flight number is properly formatted.

    Args:
        flight_number: Flight number (without airline code)

    Returns:
        True if flight number is valid, False otherwise

    Raises:
        ValueError: If flight number is invalid
    """
    if not flight_number or not isinstance(flight_number, str):
        raise ValueError("Flight number is required and must be a string")

    # Basic flight number format validation
    if not re.match(r"^[0-9]{1,4}[A-Z]?$", flight_number):
        raise ValueError(
            f"Invalid flight number format: {flight_number}. Expected 1-4 digits, optionally followed by a letter"
        )

    return True


def validate_booking_type(booking_type: str) -> bool:
    """Validate if a booking type is supported.

    Args:
        booking_type: Booking type ('flight', 'hotel', or 'car')

    Returns:
        True if booking type is valid, False otherwise

    Raises:
        ValueError: If booking type is invalid
    """
    if not booking_type or not isinstance(booking_type, str):
        raise ValueError("Booking type is required and must be a string")

    valid_types = ["flight", "hotel", "car"]
    if booking_type not in valid_types:
        raise ValueError(
            f"Invalid booking type: {booking_type}. Must be one of: {', '.join(valid_types)}"
        )

    return True


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
    if not provider or not isinstance(provider, str):
        raise ValueError("Provider code is required and must be a string")

    # Check if provider is supported for the booking type
    supported_providers = Config.BOOKING_VERIFICATION_URLS.get(booking_type, {})
    if provider not in supported_providers:
        # We'll allow unknown providers but log a warning
        logger.warning(
            f"Unknown provider '{provider}' for booking type '{booking_type}'. Using generic verification URL"
        )

    return True


def validate_booking_reference(booking_reference: str) -> bool:
    """Validate if a booking reference is properly formatted.

    Args:
        booking_reference: Booking reference/confirmation code

    Returns:
        True if booking reference is valid, False otherwise

    Raises:
        ValueError: If booking reference is invalid
    """
    if not booking_reference or not isinstance(booking_reference, str):
        raise ValueError("Booking reference is required and must be a string")

    # Basic booking reference format validation (alphanumeric, typically 5-8 characters)
    if not re.match(r"^[A-Z0-9]{4,10}$", booking_reference.upper()):
        raise ValueError(
            f"Invalid booking reference format: {booking_reference}. Expected 4-10 alphanumeric characters"
        )

    return True


def validate_email(email: str) -> bool:
    """Validate if an email address is properly formatted.

    Args:
        email: Email address

    Returns:
        True if email is valid, False otherwise

    Raises:
        ValueError: If email is invalid
    """
    if not email or not isinstance(email, str):
        raise ValueError("Email is required and must be a string")

    # Basic email format validation
    email_pattern = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
    if not email_pattern.match(email):
        raise ValueError(f"Invalid email format: {email}")

    return True


def validate_confirmation_code(confirmation_code: str) -> bool:
    """Validate if a confirmation code is properly formatted.

    Args:
        confirmation_code: Booking confirmation code

    Returns:
        True if confirmation code is valid, False otherwise

    Raises:
        ValueError: If confirmation code is invalid
    """
    if not confirmation_code or not isinstance(confirmation_code, str):
        raise ValueError("Confirmation code is required and must be a string")

    # Basic confirmation code format validation (alphanumeric, typically 5-8 characters)
    if not re.match(r"^[A-Z0-9]{4,10}$", confirmation_code.upper()):
        raise ValueError(
            f"Invalid confirmation code format: {confirmation_code}. Expected 4-10 alphanumeric characters"
        )

    return True


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
    if not selector or not isinstance(selector, str):
        raise ValueError("CSS selector is required and must be a string")

    # Check for common issues in selectors
    invalid_patterns = [
        r"<\s*[a-z]",  # HTML tags
        r"#\d",  # IDs that start with a digit
        r"@import",  # CSS import statements
        r"url\(",  # URL patterns
    ]

    for pattern in invalid_patterns:
        if re.search(pattern, selector):
            raise ValueError(f"Invalid CSS selector: {selector}")

    return True


def validate_check_frequency(frequency: str) -> bool:
    """Validate if a check frequency is valid.

    Args:
        frequency: Check frequency ('hourly', 'daily', or 'weekly')

    Returns:
        True if frequency is valid, False otherwise

    Raises:
        ValueError: If frequency is invalid
    """
    if not frequency or not isinstance(frequency, str):
        raise ValueError("Check frequency is required and must be a string")

    valid_frequencies = ["hourly", "daily", "weekly"]
    if frequency not in valid_frequencies:
        raise ValueError(
            f"Invalid check frequency: {frequency}. Must be one of: {', '.join(valid_frequencies)}"
        )

    return True


def validate_session_id(session_id: str) -> bool:
    """Validate if a session ID is properly formatted.

    Args:
        session_id: Session ID

    Returns:
        True if session ID is valid, False otherwise

    Raises:
        ValueError: If session ID is invalid
    """
    if not session_id or not isinstance(session_id, str):
        raise ValueError("Session ID is required and must be a string")

    # Basic session ID format validation (alphanumeric and dashes)
    if not re.match(r"^[A-Za-z0-9_-]{1,64}$", session_id):
        raise ValueError(
            f"Invalid session ID format: {session_id}. Expected alphanumeric characters, underscores, or dashes"
        )

    return True


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
