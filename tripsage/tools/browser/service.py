"""
BrowserService for orchestrating browser automation tasks.
"""

import json
import logging
import re
import uuid
from datetime import datetime, timedelta

from tripsage.tools.browser.mcp_clients import (
    BrowserError,
    PlaywrightMCPClient,
    StagehandMCPClient,
)
from tripsage.tools.schemas.browser import (
    BookingDetails,
    BookingStatus,
    BookingVerificationParams,
    BookingVerificationResponse,
    FlightInfo,
    FlightStatusParams,
    FlightStatusResponse,
    PriceInfo,
    PriceMonitorParams,
    PriceMonitorResponse,
)
from tripsage.utils.cache import get_cache
from tripsage.utils.settings import settings

logger = logging.getLogger(__name__)


class BrowserService:
    """Service for browser automation using MCP servers."""

    def __init__(self):
        """Initialize browser service with MCP clients."""
        self.playwright_client = PlaywrightMCPClient()
        self.stagehand_client = StagehandMCPClient()
        self.cache = get_cache()

        # Default TTL for cached browser results (24 hours)
        self.cache_ttl = settings.cache.ttl_long

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
        cached_result = await self.cache.get(cache_key)

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

            # Map flight_info if it exists and is a dict
            if "flight_info" in result and isinstance(result["flight_info"], dict):
                response.flight_info = FlightInfo(**result["flight_info"])
            elif "flight_info" in result and result["flight_info"] is None:
                response.flight_info = (
                    None  # Explicitly set to None if API returns null
                )

            # Cache the result
            await self.cache.set(cache_key, response.model_dump_json(), self.cache_ttl)

            return response

        except Exception as e:
            logger.error(f"Flight status check error: {str(e)}", exc_info=True)
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
        cached_result = await self.cache.get(cache_key)

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
            current_session_id = navigate_result.get("sessionId")
            mcp_params["sessionId"] = current_session_id  # Use session from navigation

            # Then perform booking verification
            result = await self.stagehand_client.execute("stagehand_act", mcp_params)
            current_session_id = result.get(
                "sessionId", current_session_id
            )  # Update session id if returned

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
                "sessionId": current_session_id,
            }

            extract_result = await self.stagehand_client.execute(
                "stagehand_extract", extract_params
            )
            current_session_id = extract_result.get("sessionId", current_session_id)

            # Take a screenshot
            screenshot_result = await self.stagehand_client.execute(
                "browser_screenshot", {"sessionId": current_session_id}
            )
            current_session_id = screenshot_result.get("sessionId", current_session_id)

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
                session_id=current_session_id,
            )

            # Cache the result
            await self.cache.set(cache_key, response.model_dump_json(), self.cache_ttl)

            return response

        except Exception as e:
            logger.error(f"Booking verification error: {str(e)}", exc_info=True)
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
                "browser_navigate", {"url": params.url, "sessionId": params.session_id}
            )
            current_session_id = navigate_result.get("sessionId")

            # Wait for the element to be visible
            await self.playwright_client.execute(
                "browser_wait_for_selector",
                {
                    "selector": params.selector,
                    "state": "visible",
                    "sessionId": current_session_id,
                },
            )

            # Get the initial price text
            get_text_result = await self.playwright_client.execute(
                "browser_get_text",
                {"selector": params.selector, "sessionId": current_session_id},
            )

            # Take a screenshot
            screenshot_result = await self.playwright_client.execute(
                "browser_screenshot", {"sessionId": current_session_id}
            )

            # Extract the price information
            price_text = get_text_result.get("text", "")
            try:
                # Try to extract numeric price and currency
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
            now = datetime.now(datetime.UTC)

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
                session_id=current_session_id,
            )

            # Store the monitoring session
            await self.cache.set(
                f"price_monitor:{monitoring_id}",
                response.model_dump_json(),
                self.cache_ttl,
            )

            return response

        except Exception as e:
            logger.error(f"Price monitoring setup error: {str(e)}", exc_info=True)
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
