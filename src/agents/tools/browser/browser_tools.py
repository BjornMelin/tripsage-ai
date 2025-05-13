"""
Browser automation tools for TripSage agents.

This module provides function tools for browser automation using external MCPs:
- Playwright MCP for precise browser control
- Stagehand MCP for AI-driven browser interactions

These tools replace the custom Browser MCP that was previously used in TripSage.
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

import httpx
from openai import OpenAI
from openai.types.shared_params import FunctionDefinition
from pydantic import BaseModel, Field, field_validator

from src.cache.redis_cache import RedisCache
from src.utils.config import get_settings
from src.utils.error_handling import TripSageError

# Setup logging
logger = logging.getLogger(__name__)

# Initialize Redis cache for storing browser session results
redis_cache = RedisCache()

# Constants for MCP server types
MCP_TYPE_PLAYWRIGHT = "playwright"
MCP_TYPE_STAGEHAND = "stagehand"


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


class BrowserError(TripSageError):
    """Error raised when browser automation fails."""

    pass


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


class MCPClient:
    """Base client for MCP server communication."""

    def __init__(self, mcp_type: str):
        """Initialize MCP client.

        Args:
            mcp_type: Type of MCP server to use (playwright or stagehand)
        """
        self.settings = get_settings()
        self.mcp_type = mcp_type

        if mcp_type == MCP_TYPE_PLAYWRIGHT:
            self.config = self.settings.playwright_mcp
        elif mcp_type == MCP_TYPE_STAGEHAND:
            self.config = self.settings.stagehand_mcp
        else:
            raise ValueError(f"Unsupported MCP type: {mcp_type}")

        self.endpoint = self.config.endpoint
        self.api_key = (
            self.config.api_key.get_secret_value() if self.config.api_key else None
        )
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "Content-Type": "application/json",
                **({"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}),
            },
        )

    async def execute(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute MCP method with parameters.

        Args:
            method: MCP method name
            params: Method parameters

        Returns:
            Response data from MCP server

        Raises:
            BrowserError: If MCP server operation fails
        """
        try:
            logger.debug(f"Executing MCP method {method} with params: {params}")

            payload = {
                "method": method,
                "params": params,
                "id": str(uuid.uuid4()),
                "jsonrpc": "2.0",
            }

            response = await self.client.post(
                self.endpoint,
                json=payload,
            )

            response.raise_for_status()
            data = response.json()

            if "error" in data:
                raise BrowserError(
                    f"MCP server error: {data['error'].get('message', 'Unknown error')}"
                )

            if "result" not in data:
                raise BrowserError(
                    "Invalid MCP server response: missing 'result' field"
                )

            return data["result"]

        except httpx.HTTPError as e:
            error_msg = f"HTTP error communicating with MCP server: {str(e)}"
            raise BrowserError(error_msg) from e
        except json.JSONDecodeError as err:
            raise BrowserError("Failed to parse MCP server response as JSON") from err
        except Exception as e:
            raise BrowserError(f"MCP server operation failed: {str(e)}") from e

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()


class PlaywrightMCPClient(MCPClient):
    """Client for Playwright MCP server."""

    def __init__(self):
        """Initialize Playwright MCP client."""
        super().__init__(MCP_TYPE_PLAYWRIGHT)


class StagehandMCPClient(MCPClient):
    """Client for Stagehand MCP server."""

    def __init__(self):
        """Initialize Stagehand MCP client."""
        super().__init__(MCP_TYPE_STAGEHAND)


class BrowserService:
    """Service for browser automation using MCP servers."""

    def __init__(self):
        """Initialize browser service with MCP clients."""
        self.playwright_client = PlaywrightMCPClient()
        self.stagehand_client = StagehandMCPClient()
        self.settings = get_settings()
        self.redis_cache = RedisCache()

        # Default TTL for cached browser results (24 hours)
        self.cache_ttl = self.settings.redis.ttl_long

    async def close(self):
        """Close MCP clients."""
        await self.playwright_client.close()
        await self.stagehand_client.close()

    async def check_flight_status(
        self, params: FlightStatusParams
    ) -> FlightStatusResponse:
        """Check flight status.

        Args:
            params: Flight status parameters

        Returns:
            Flight status response

        Raises:
            BrowserError: If flight status check fails
        """
        cache_key = (
            f"flight_status:{params.airline}:{params.flight_number}:{params.date}"
        )
        cached_result = self.redis_cache.get(cache_key)

        if cached_result:
            try:
                return FlightStatusResponse.model_validate(json.loads(cached_result))
            except Exception as e:
                logger.warning(f"Failed to parse cached flight status: {str(e)}")

        try:
            # Use Playwright MCP for precise flight status checking
            mcp_params = {
                "airline": params.airline,
                "flightNumber": params.flight_number,
                "date": params.date,
            }

            if params.session_id:
                mcp_params["sessionId"] = params.session_id

            result = await self.playwright_client.execute(
                "checkFlightStatus", mcp_params
            )

            response = FlightStatusResponse(
                success=True,
                airline=params.airline,
                flight_number=params.flight_number,
                date=params.date,
                session_id=result.get("sessionId"),
                **{
                    k: v
                    for k, v in result.items()
                    if k in ["flight_info", "screenshot", "message"]
                },
            )

            # Cache the result
            self.redis_cache.set(cache_key, response.model_dump_json(), self.cache_ttl)

            return response

        except Exception as e:
            raise BrowserError(f"Flight status check failed: {str(e)}") from e

    async def verify_booking(
        self, params: BookingVerificationParams
    ) -> BookingVerificationResponse:
        """Verify booking details.

        Args:
            params: Booking verification parameters

        Returns:
            Booking verification response

        Raises:
            BrowserError: If booking verification fails
        """
        cache_key = (
            f"booking_verification:{params.type.value}:"
            f"{params.provider}:{params.confirmation_code}:{params.last_name}"
        )
        cached_result = self.redis_cache.get(cache_key)

        if cached_result:
            try:
                return BookingVerificationResponse.model_validate(
                    json.loads(cached_result)
                )
            except Exception as e:
                logger.warning(f"Failed to parse cached booking verification: {str(e)}")

        try:
            # Use Stagehand MCP for intelligent navigation and data extraction
            mcp_params = {
                "instruction": (
                    f"Verify {params.type.value} booking for {params.provider} with "
                    f"confirmation code {params.confirmation_code} and last name "
                    f"{params.last_name}"
                    + (f", first name {params.first_name}" if params.first_name else "")
                ),
                "variables": {
                    "bookingType": params.type.value,
                    "provider": params.provider,
                    "confirmationCode": params.confirmation_code,
                    "lastName": params.last_name,
                    "firstName": params.first_name or "",
                },
            }

            if params.session_id:
                mcp_params["sessionId"] = params.session_id

            # First navigate to the provider's website
            navigate_result = await self.stagehand_client.execute(
                "stagehand_navigate",
                {"url": self._get_provider_url(params.type.value, params.provider)},
            )

            # Then perform booking verification
            result = await self.stagehand_client.execute("stagehand_act", mcp_params)

            # Extract data from the page
            extract_params = {
                "instruction": (
                    "Extract all available booking details for this "
                    f"{params.type.value} booking. Include passenger/guest name, "
                    "dates, origin/destination, flight numbers, and status."
                ),
                "schema": {
                    "type": "object",
                    "properties": {
                        "passengerName": {"type": "string"},
                        "origin": {"type": "string"},
                        "destination": {"type": "string"},
                        "departureDate": {"type": "string"},
                        "returnDate": {"type": "string"},
                        "flightNumber": {"type": "string"},
                        "status": {
                            "type": "string",
                            "enum": [
                                "confirmed",
                                "cancelled",
                                "pending",
                                "modified",
                                "incomplete",
                                "unknown",
                            ],
                        },
                        "additionalInfo": {"type": "object"},
                    },
                    "required": ["passengerName", "status"],
                },
            }

            extract_result = await self.stagehand_client.execute(
                "stagehand_extract", extract_params
            )

            # Take a screenshot
            screenshot_result = await self.stagehand_client.execute(
                "browser_screenshot", {}
            )

            # Map extracted data to the response model
            extracted_data = extract_result.get("data", {})
            booking_details = BookingDetails(
                passenger_name=extracted_data.get("passengerName", "Unknown"),
                origin=extracted_data.get("origin"),
                destination=extracted_data.get("destination"),
                departure_date=extracted_data.get("departureDate"),
                return_date=extracted_data.get("returnDate"),
                flight_number=extracted_data.get("flightNumber"),
                status=BookingStatus(extracted_data.get("status", "unknown")),
                additional_info=extracted_data.get("additionalInfo", {}),
            )

            response = BookingVerificationResponse(
                success=True,
                booking_type=params.type.value,
                provider=params.provider,
                booking_reference=params.confirmation_code,
                booking_details=booking_details,
                screenshot=screenshot_result.get("screenshot"),
                session_id=result.get("sessionId") or navigate_result.get("sessionId"),
            )

            # Cache the result
            self.redis_cache.set(cache_key, response.model_dump_json(), self.cache_ttl)

            return response

        except Exception as e:
            raise BrowserError(f"Booking verification failed: {str(e)}") from e

    async def monitor_price(self, params: PriceMonitorParams) -> PriceMonitorResponse:
        """Monitor price on a webpage.

        Args:
            params: Price monitoring parameters

        Returns:
            Price monitoring response

        Raises:
            BrowserError: If price monitoring setup fails
        """
        try:
            # Generate a unique monitoring ID
            monitoring_id = str(uuid.uuid4())

            # Use Playwright MCP for precise element selection and extraction
            mcp_params = {
                "url": params.url,
                "selector": params.selector,
                "frequency": params.check_frequency,
                "threshold": params.notification_threshold,
            }

            if params.session_id:
                mcp_params["sessionId"] = params.session_id

            # Navigate to the URL
            navigate_result = await self.playwright_client.execute(
                "browser_navigate", {"url": params.url}
            )

            # Wait for the element to be visible
            await self.playwright_client.execute(
                "browser_wait_for_selector",
                {"selector": params.selector, "state": "visible"},
            )

            # Get the initial price text
            get_text_result = await self.playwright_client.execute(
                "browser_get_text", {"selector": params.selector}
            )

            # Take a screenshot
            screenshot_result = await self.playwright_client.execute(
                "browser_screenshot", {}
            )

            # Extract the price information
            price_text = get_text_result.get("text", "")
            try:
                # Try to extract numeric price and currency
                import re

                price_match = re.search(r"([₹$€£¥])?(\d+(?:[.,]\d+)?)", price_text)
                if price_match:
                    currency_symbol = price_match.group(1) or "$"
                    amount_str = price_match.group(2).replace(",", "")
                    amount = float(amount_str)

                    # Map currency symbols to ISO codes
                    currency_map = {
                        "$": "USD",
                        "€": "EUR",
                        "£": "GBP",
                        "¥": "JPY",
                        "₹": "INR",
                    }
                    currency = currency_map.get(currency_symbol, "USD")
                else:
                    amount = 0.0
                    currency = "USD"
            except Exception:
                # Default if parsing fails
                amount = 0.0
                currency = "USD"

            # Calculate next check time based on frequency
            from datetime import timedelta

            now = datetime.utcnow()

            if params.check_frequency == "hourly":
                next_check = now + timedelta(hours=1)
            elif params.check_frequency == "weekly":
                next_check = now + timedelta(days=7)
            else:  # daily (default)
                next_check = now + timedelta(days=1)

            price_info = PriceInfo(
                amount=amount,
                currency=currency,
                extracted_text=price_text,
                timestamp=now,
            )

            response = PriceMonitorResponse(
                success=True,
                url=params.url,
                initial_price=price_info,
                check_frequency=params.check_frequency,
                next_check=next_check.isoformat(),
                monitoring_id=monitoring_id,
                screenshot=screenshot_result.get("screenshot"),
                session_id=navigate_result.get("sessionId"),
            )

            # Store the monitoring session
            self.redis_cache.set(
                f"price_monitor:{monitoring_id}",
                response.model_dump_json(),
                self.cache_ttl,
            )

            return response

        except Exception as e:
            raise BrowserError(f"Price monitoring setup failed: {str(e)}") from e

    def _get_provider_url(self, booking_type: str, provider: str) -> str:
        """Get URL for a provider's booking verification page.

        Args:
            booking_type: Type of booking
            provider: Provider code

        Returns:
            URL for the provider's booking verification page
        """
        # Map of provider codes to verification URLs
        provider_urls = {
            "flight": {
                "aa": "https://www.aa.com/reservation/view/find-your-reservation",
                "dl": "https://www.delta.com/mytrips/",
                "ua": "https://www.united.com/en/us/manageres/mytrips",
                "wn": "https://www.southwest.com/air/manage-reservation",
                # Add more providers as needed
            },
            "hotel": {
                "hilton": "https://www.hilton.com/en/find-my-reservation/",
                "marriott": "https://www.marriott.com/en-us/find-reservation/lookup/find-my-reservation",
                "hyatt": "https://www.hyatt.com/en-US/my-account/find-my-reservation",
                # Add more providers as needed
            },
            "car": {
                "hertz": "https://www.hertz.com/rentacar/reservation/myreservation/index.jsp",
                "avis": "https://www.avis.com/en/reservation/view-modify-cancel",
                "enterprise": "https://www.enterprise.com/en/reservation/find.html",
                # Add more providers as needed
            },
        }

        # Default URLs for unknown providers
        default_urls = {
            "flight": "https://www.google.com/flights",
            "hotel": "https://www.google.com/travel/hotels",
            "car": "https://www.google.com/travel",
        }

        # Normalize provider code
        provider_key = provider.lower()

        # Get provider URL or default
        return provider_urls.get(booking_type, {}).get(
            provider_key, default_urls.get(booking_type, "https://www.google.com")
        )


# Instantiate the browser service
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
