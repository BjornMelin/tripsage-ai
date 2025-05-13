"""
Function tools for browser automation, suitable for OpenAI Agents SDK.
"""

import asyncio
import logging
from typing import Any, Dict, List, Literal, Optional

from openai import OpenAI
from openai.types.shared_params import FunctionDefinition

from .service import BrowserService
from .types import (
    BookingVerificationParams,
    FlightStatusParams,
    PriceMonitorParams,
)

logger = logging.getLogger(__name__)

# Instantiate the browser service for use by the tools
browser_service = BrowserService()


# Function tools for OpenAI Agents SDK


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
    params = FlightStatusParams(
        airline=airline, flight_number=flight_number, date=date, session_id=session_id
    )

    response = await browser_service.check_flight_status(params)

    if not response.success:
        return {
            "success": False,
            "error": response.error or "Flight status check failed",
        }

    result = {
        "success": True,
        "airline": response.airline,
        "flight_number": response.flight_number,
        "date": response.date,
        "session_id": response.session_id,
    }

    if response.flight_info:
        result["flight_info"] = response.flight_info.model_dump()

    return result


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
    params = BookingVerificationParams(
        type=booking_type,
        provider=provider,
        confirmation_code=confirmation_code,
        last_name=last_name,
        first_name=first_name,
        session_id=session_id,
    )

    response = await browser_service.verify_booking(params)

    if not response.success:
        return {
            "success": False,
            "error": response.error or "Booking verification failed",
        }

    result = {
        "success": True,
        "booking_type": response.booking_type,
        "provider": response.provider,
        "booking_reference": response.booking_reference,
        "session_id": response.session_id,
    }

    if response.booking_details:
        result["booking_details"] = response.booking_details.model_dump()

    return result


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
    params = PriceMonitorParams(
        url=url,
        selector=selector,
        check_frequency=check_frequency,
        notification_threshold=notification_threshold,
        session_id=session_id,
    )

    response = await browser_service.monitor_price(params)

    if not response.success:
        return {
            "success": False,
            "error": response.error or "Price monitoring setup failed",
        }

    result = {
        "success": True,
        "url": response.url,
        "check_frequency": response.check_frequency,
        "next_check": response.next_check,
        "monitoring_id": response.monitoring_id,
        "session_id": response.session_id,
    }

    if response.initial_price:
        result["initial_price"] = response.initial_price.model_dump()

    return result


# Create function definitions for OpenAI Agents SDK
def get_browser_tool_definitions() -> List[FunctionDefinition]:
    """
    Get function definitions for browser tools.

    Returns:
        List of FunctionDefinition objects for OpenAI Agents SDK
    """
    client = OpenAI()

    return [
        client.function_to_json(check_flight_status),
        client.function_to_json(verify_booking),
        client.function_to_json(monitor_price),
    ]


# Synchronous wrappers for function tools


def check_flight_status_sync(
    airline: str, flight_number: str, date: str, session_id: Optional[str] = None
) -> Dict[str, Any]:
    """Synchronous wrapper for check_flight_status."""
    return asyncio.run(
        check_flight_status(
            airline=airline,
            flight_number=flight_number,
            date=date,
            session_id=session_id,
        )
    )


def verify_booking_sync(
    booking_type: Literal["flight", "hotel", "car"],
    provider: str,
    confirmation_code: str,
    last_name: str,
    first_name: Optional[str] = None,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Synchronous wrapper for verify_booking."""
    return asyncio.run(
        verify_booking(
            booking_type=booking_type,
            provider=provider,
            confirmation_code=confirmation_code,
            last_name=last_name,
            first_name=first_name,
            session_id=session_id,
        )
    )


def monitor_price_sync(
    url: str,
    selector: str,
    check_frequency: Literal["hourly", "daily", "weekly"] = "daily",
    notification_threshold: float = 5.0,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Synchronous wrapper for monitor_price."""
    return asyncio.run(
        monitor_price(
            url=url,
            selector=selector,
            check_frequency=check_frequency,
            notification_threshold=notification_threshold,
            session_id=session_id,
        )
    )
