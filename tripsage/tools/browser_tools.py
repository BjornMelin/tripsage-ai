"""
Browser tools for TripSage agents.

This module provides function tools for browser automation tasks
like checking flight status, verifying bookings, and monitoring prices.
"""

from typing import Any, Dict, Literal, Optional

from openai_agents_sdk import function_tool

from tripsage.tools.browser.tools import (
    check_flight_status as browser_check_flight_status,
)
from tripsage.tools.browser.tools import (
    monitor_price as browser_monitor_price,
)
from tripsage.tools.browser.tools import (
    verify_booking as browser_verify_booking,
)
from tripsage.utils.logging import get_logger

logger = get_logger(__name__)


@function_tool
async def check_flight_status(
    airline: str, flight_number: str, date: str, session_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Check the current status of a flight.

    Args:
        airline: Airline code (e.g., 'AA', 'DL', 'UA')
        flight_number: Flight number without airline code (e.g., '123')
        date: Flight date in YYYY-MM-DD format
        session_id: Optional session ID for browser context reuse

    Returns:
        Flight status information including departure/arrival airports,
        scheduled/actual times, terminals, gates, and status
    """
    logger.info(f"Checking flight status for {airline} {flight_number} on {date}")
    return await browser_check_flight_status(
        airline=airline,
        flight_number=flight_number,
        date=date,
        session_id=session_id,
    )


@function_tool
async def verify_booking(
    booking_type: Literal["flight", "hotel", "car"],
    provider: str,
    confirmation_code: str,
    last_name: str,
    first_name: Optional[str] = None,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Verify booking details using provider websites.

    Args:
        booking_type: Type of booking ('flight', 'hotel', or 'car')
        provider: Provider code (e.g., 'AA' for American Airlines, 'hilton')
        confirmation_code: Booking confirmation/reference code
        last_name: Passenger/guest's last name
        first_name: Passenger/guest's first name (if required)
        session_id: Optional session ID for browser context reuse

    Returns:
        Booking verification details including passenger/guest name,
        dates, origin/destination (for flights/cars), and booking status
    """
    logger.info(
        f"Verifying {booking_type} booking for {provider} "
        f"with code {confirmation_code} and name {last_name}"
    )
    return await browser_verify_booking(
        booking_type=booking_type,
        provider=provider,
        confirmation_code=confirmation_code,
        last_name=last_name,
        first_name=first_name,
        session_id=session_id,
    )


@function_tool
async def monitor_price(
    url: str,
    selector: str,
    check_frequency: Literal["hourly", "daily", "weekly"] = "daily",
    notification_threshold: float = 5.0,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Set up monitoring for a price on a webpage.

    Args:
        url: URL of the webpage to monitor
        selector: CSS selector for the price element
        check_frequency: How often to check ('hourly', 'daily', 'weekly')
        notification_threshold: Percentage change to trigger a notification
        session_id: Optional session ID for browser context reuse

    Returns:
        Price monitoring setup details including initial price,
        frequency, next check time, and monitoring ID
    """
    logger.info(
        f"Setting up price monitoring for {url} with frequency {check_frequency}"
    )
    return await browser_monitor_price(
        url=url,
        selector=selector,
        check_frequency=check_frequency,
        notification_threshold=notification_threshold,
        session_id=session_id,
    )
