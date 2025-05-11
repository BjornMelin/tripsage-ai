"""
Booking verification handler for browser automation MCP.

This module contains functions for verifying bookings across different travel providers
using browser automation. It handles verification of flight, hotel, and rental car bookings.
"""

import asyncio
import logging
import re
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from playwright.async_api import Page
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.mcp.browser.config import Config
from src.mcp.browser.context.manager import get_playwright_manager
from src.mcp.browser.models.request_models import BookingVerificationParams
from src.mcp.browser.models.response_models import (
    BookingDetails,
    BookingStatus,
    BookingVerificationResponse,
)
from src.mcp.browser.utils.logging import get_logger, log_request
from src.mcp.browser.utils.validators import validate_booking_reference, validate_email

logger = get_logger(__name__)

# Mapping of providers to their verification URLs
PROVIDER_URLS = Config.BOOKING_VERIFICATION_URLS


async def verify_booking(params: BookingVerificationParams) -> Dict[str, Any]:
    """
    Verify a booking using browser automation.

    Args:
        params: Booking verification parameters

    Returns:
        Dictionary containing booking verification details
    """
    log_request(logger, "verify_booking", params.model_dump())

    # Validate input parameters
    try:
        validate_booking_reference(params.confirmation_code)
        if params.first_name and not params.first_name.strip():
            logger.warning("First name provided but empty")

        # Normalize provider name for dictionary lookup
        provider_key = params.provider.lower().replace(" ", "_")

        # Check if provider is supported for this booking type
        if params.type not in PROVIDER_URLS:
            return BookingVerificationResponse(
                success=False,
                message=f"Unsupported booking type: {params.type}",
                booking_type=params.type,
                provider=params.provider,
                booking_reference=params.confirmation_code,
            ).model_dump()

        if provider_key not in PROVIDER_URLS.get(params.type, {}):
            logger.warning(
                f"Provider '{provider_key}' not directly supported for '{params.type}'. Using generic handler."
            )

    except ValueError as e:
        return BookingVerificationResponse(
            success=False,
            message=str(e),
            booking_type=params.type,
            provider=params.provider,
            booking_reference=params.confirmation_code,
        ).model_dump()

    # Initialize PlaywrightManager and get browser context
    playwright_manager = get_playwright_manager()
    session_id = params.session_id or f"booking_verification_{params.confirmation_code}"

    try:
        context = await playwright_manager.get_context(session_id)
        page = await context.new_page()

        # Set appropriate verification handler based on booking type and provider
        verification_result = None

        if params.type == "flight":
            if provider_key == "aa":
                verification_result = await verify_american_airlines_booking(
                    page, params.confirmation_code, params.last_name
                )
            elif provider_key == "dl":
                verification_result = await verify_delta_booking(
                    page, params.confirmation_code, params.last_name
                )
            elif provider_key == "ua":
                verification_result = await verify_united_booking(
                    page, params.confirmation_code, params.last_name
                )
            elif provider_key == "wn":
                verification_result = await verify_southwest_booking(
                    page, params.confirmation_code, params.last_name, params.first_name
                )
            else:
                verification_result = await generic_flight_verification(
                    page,
                    PROVIDER_URLS.get(params.type, {}).get(provider_key, None),
                    params.confirmation_code,
                    params.last_name,
                    params.first_name,
                )

        elif params.type == "hotel":
            if provider_key == "marriott":
                verification_result = await verify_marriott_booking(
                    page, params.confirmation_code, params.last_name
                )
            elif provider_key == "hilton":
                verification_result = await verify_hilton_booking(
                    page, params.confirmation_code, params.last_name
                )
            elif provider_key == "hyatt":
                verification_result = await verify_hyatt_booking(
                    page, params.confirmation_code, params.last_name, params.first_name
                )
            else:
                verification_result = await generic_hotel_verification(
                    page,
                    PROVIDER_URLS.get(params.type, {}).get(provider_key, None),
                    params.confirmation_code,
                    params.last_name,
                    params.first_name,
                )

        elif params.type == "car":
            if provider_key == "hertz":
                verification_result = await verify_hertz_booking(
                    page, params.confirmation_code, params.last_name
                )
            elif provider_key == "enterprise":
                verification_result = await verify_enterprise_booking(
                    page, params.confirmation_code, params.last_name, params.first_name
                )
            elif provider_key == "avis":
                verification_result = await verify_avis_booking(
                    page, params.confirmation_code, params.last_name
                )
            else:
                verification_result = await generic_car_verification(
                    page,
                    PROVIDER_URLS.get(params.type, {}).get(provider_key, None),
                    params.confirmation_code,
                    params.last_name,
                    params.first_name,
                )

        else:
            return BookingVerificationResponse(
                success=False,
                message=f"Unsupported booking type: {params.type}",
                booking_type=params.type,
                provider=params.provider,
                booking_reference=params.confirmation_code,
            ).model_dump()

        if verification_result:
            success, booking_details, screenshot = verification_result

            return BookingVerificationResponse(
                success=success,
                message=(
                    "Booking verification successful"
                    if success
                    else "Booking not found or verification failed"
                ),
                booking_type=params.type,
                provider=params.provider,
                booking_reference=params.confirmation_code,
                booking_details=booking_details,
                screenshot=screenshot,
            ).model_dump()
        else:
            return BookingVerificationResponse(
                success=False,
                message="Failed to verify booking",
                booking_type=params.type,
                provider=params.provider,
                booking_reference=params.confirmation_code,
            ).model_dump()

    except Exception as e:
        logger.exception(f"Error verifying booking: {str(e)}")
        return BookingVerificationResponse(
            success=False,
            message=f"Error verifying booking: {str(e)}",
            booking_type=params.type,
            provider=params.provider,
            booking_reference=params.confirmation_code,
        ).model_dump()
    finally:
        # Close the page but keep the context for potential reuse
        try:
            if "page" in locals() and page:
                await page.close()
        except Exception as e:
            logger.error(f"Error closing page: {str(e)}")


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((TimeoutError, asyncio.TimeoutError)),
)
async def verify_american_airlines_booking(
    page: Page, confirmation_code: str, last_name: str
) -> Optional[Tuple[bool, Optional[BookingDetails], Optional[str]]]:
    """
    Verify a booking with American Airlines.

    Args:
        page: Playwright page instance
        confirmation_code: Booking confirmation code
        last_name: Last name on the booking

    Returns:
        Tuple of (success, booking_details, screenshot)
    """
    try:
        url = PROVIDER_URLS.get("flight", {}).get(
            "aa", "https://www.aa.com/reservation/view/find-your-reservation"
        )
        await page.goto(url, timeout=Config.NAVIGATION_TIMEOUT)

        # Fill in the booking reference and last name
        await page.fill("#recordLocator", confirmation_code)
        await page.fill("#lastName", last_name)

        # Submit the form
        await page.click('button[type="submit"]')

        # Wait for results page
        await page.wait_for_load_state("networkidle", timeout=Config.NAVIGATION_TIMEOUT)

        # Check if the booking exists (Verify success by checking for error messages)
        error_element = await page.query_selector(".message.error")

        if error_element:
            # Booking not found
            screenshot = await page.screenshot(type="jpeg", quality=50)
            screenshot_base64 = screenshot.decode("utf-8") if screenshot else None
            return False, None, screenshot_base64

        # Extract booking details from the page
        await page.wait_for_selector(".flight-info", timeout=Config.DEFAULT_TIMEOUT)

        # Take screenshot for verification
        screenshot = await page.screenshot(type="jpeg", quality=50)
        screenshot_base64 = screenshot.decode("utf-8") if screenshot else None

        # Extract flight details
        origin = await extract_text(page, ".flight-info .origin")
        destination = await extract_text(page, ".flight-info .destination")
        departure_date = await extract_text(page, ".flight-info .departure-date")
        flight_number = await extract_text(page, ".flight-number")

        # Create status based on cancellation indicators
        cancelled_element = await page.query_selector(".cancelled, .canceled")
        status = (
            BookingStatus.CANCELLED if cancelled_element else BookingStatus.CONFIRMED
        )

        booking_details = BookingDetails(
            passenger_name=last_name,
            origin=origin,
            destination=destination,
            departure_date=departure_date,
            return_date=None,  # May not be available on first page
            flight_number=flight_number,
            status=status,
            additional_info={},
        )

        return True, booking_details, screenshot_base64

    except Exception as e:
        logger.exception(f"Error verifying American Airlines booking: {str(e)}")
        try:
            screenshot = await page.screenshot(type="jpeg", quality=50)
            screenshot_base64 = screenshot.decode("utf-8") if screenshot else None
            return False, None, screenshot_base64
        except:
            return False, None, None


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((TimeoutError, asyncio.TimeoutError)),
)
async def verify_delta_booking(
    page: Page, confirmation_code: str, last_name: str
) -> Optional[Tuple[bool, Optional[BookingDetails], Optional[str]]]:
    """
    Verify a booking with Delta Airlines.

    Args:
        page: Playwright page instance
        confirmation_code: Booking confirmation code
        last_name: Last name on the booking

    Returns:
        Tuple of (success, booking_details, screenshot)
    """
    try:
        url = PROVIDER_URLS.get("flight", {}).get(
            "dl", "https://www.delta.com/mytrips/find"
        )
        await page.goto(url, timeout=Config.NAVIGATION_TIMEOUT)

        # Fill in the booking reference and last name
        await page.fill("#confirmationNumber", confirmation_code)
        await page.fill("#lastName", last_name)

        # Submit the form
        await page.click('button[type="submit"]')

        # Wait for results page
        await page.wait_for_load_state("networkidle", timeout=Config.NAVIGATION_TIMEOUT)

        # Check if the booking exists (Verify success by checking for error messages)
        error_element = await page.query_selector(".error-message")

        if error_element:
            # Booking not found
            screenshot = await page.screenshot(type="jpeg", quality=50)
            screenshot_base64 = screenshot.decode("utf-8") if screenshot else None
            return False, None, screenshot_base64

        # Extract booking details from the page
        await page.wait_for_selector(".flight-details", timeout=Config.DEFAULT_TIMEOUT)

        # Take screenshot for verification
        screenshot = await page.screenshot(type="jpeg", quality=50)
        screenshot_base64 = screenshot.decode("utf-8") if screenshot else None

        # Extract flight details
        origin = await extract_text(page, ".flight-details .origin-code")
        destination = await extract_text(page, ".flight-details .destination-code")
        departure_date = await extract_text(page, ".flight-details .departure-date")
        flight_number = await extract_text(page, ".flight-details .flight-number")

        # Create status based on cancellation indicators
        cancelled_element = await page.query_selector(".cancelled, .canceled")
        status = (
            BookingStatus.CANCELLED if cancelled_element else BookingStatus.CONFIRMED
        )

        booking_details = BookingDetails(
            passenger_name=last_name,
            origin=origin,
            destination=destination,
            departure_date=departure_date,
            return_date=None,  # May not be available on first page
            flight_number=flight_number,
            status=status,
            additional_info={},
        )

        return True, booking_details, screenshot_base64

    except Exception as e:
        logger.exception(f"Error verifying Delta booking: {str(e)}")
        try:
            screenshot = await page.screenshot(type="jpeg", quality=50)
            screenshot_base64 = screenshot.decode("utf-8") if screenshot else None
            return False, None, screenshot_base64
        except:
            return False, None, None


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((TimeoutError, asyncio.TimeoutError)),
)
async def verify_united_booking(
    page: Page, confirmation_code: str, last_name: str
) -> Optional[Tuple[bool, Optional[BookingDetails], Optional[str]]]:
    """
    Verify a booking with United Airlines.

    Args:
        page: Playwright page instance
        confirmation_code: Booking confirmation code
        last_name: Last name on the booking

    Returns:
        Tuple of (success, booking_details, screenshot)
    """
    try:
        url = PROVIDER_URLS.get("flight", {}).get(
            "ua", "https://www.united.com/en/us/manageres/mytrips"
        )
        await page.goto(url, timeout=Config.NAVIGATION_TIMEOUT)

        # Fill in the booking reference and last name
        await page.fill("#confirmationNumber", confirmation_code)
        await page.fill("#lastName", last_name)

        # Submit the form
        await page.click('button[type="submit"]')

        # Wait for results page
        await page.wait_for_load_state("networkidle", timeout=Config.NAVIGATION_TIMEOUT)

        # Check if the booking exists (Verify success by checking for error messages)
        error_element = await page.query_selector(".error-message, .error-text")

        if error_element:
            # Booking not found
            screenshot = await page.screenshot(type="jpeg", quality=50)
            screenshot_base64 = screenshot.decode("utf-8") if screenshot else None
            return False, None, screenshot_base64

        # Extract booking details from the page
        await page.wait_for_selector(
            ".itinerary-container", timeout=Config.DEFAULT_TIMEOUT
        )

        # Take screenshot for verification
        screenshot = await page.screenshot(type="jpeg", quality=50)
        screenshot_base64 = screenshot.decode("utf-8") if screenshot else None

        # Extract flight details
        origin = await extract_text(page, ".segment-airports .origin")
        destination = await extract_text(page, ".segment-airports .destination")
        departure_date = await extract_text(page, ".flight-date")
        flight_number = await extract_text(page, ".flight-number")

        # Create status based on cancellation indicators
        cancelled_element = await page.query_selector(
            ".cancellation-notice, .cancelled"
        )
        status = (
            BookingStatus.CANCELLED if cancelled_element else BookingStatus.CONFIRMED
        )

        booking_details = BookingDetails(
            passenger_name=last_name,
            origin=origin,
            destination=destination,
            departure_date=departure_date,
            return_date=None,  # May not be available on first page
            flight_number=flight_number,
            status=status,
            additional_info={},
        )

        return True, booking_details, screenshot_base64

    except Exception as e:
        logger.exception(f"Error verifying United Airlines booking: {str(e)}")
        try:
            screenshot = await page.screenshot(type="jpeg", quality=50)
            screenshot_base64 = screenshot.decode("utf-8") if screenshot else None
            return False, None, screenshot_base64
        except:
            return False, None, None


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((TimeoutError, asyncio.TimeoutError)),
)
async def verify_southwest_booking(
    page: Page, confirmation_code: str, last_name: str, first_name: Optional[str] = None
) -> Optional[Tuple[bool, Optional[BookingDetails], Optional[str]]]:
    """
    Verify a booking with Southwest Airlines.

    Args:
        page: Playwright page instance
        confirmation_code: Booking confirmation code
        last_name: Last name on the booking
        first_name: First name on the booking (optional for Southwest)

    Returns:
        Tuple of (success, booking_details, screenshot)
    """
    try:
        url = PROVIDER_URLS.get("flight", {}).get(
            "wn", "https://www.southwest.com/air/manage-reservation/index.html"
        )
        await page.goto(url, timeout=Config.NAVIGATION_TIMEOUT)

        # Fill in the booking reference and last name
        await page.fill("#confirmationNumber", confirmation_code)
        await page.fill("#passengerLastName", last_name)
        if first_name:
            await page.fill("#passengerFirstName", first_name)

        # Submit the form
        await page.click("#form-mixin--submit-button")

        # Wait for results page
        await page.wait_for_load_state("networkidle", timeout=Config.NAVIGATION_TIMEOUT)

        # Check if the booking exists (Verify success by checking for error messages)
        error_element = await page.query_selector(".error-message, .trip-error")

        if error_element:
            # Booking not found
            screenshot = await page.screenshot(type="jpeg", quality=50)
            screenshot_base64 = screenshot.decode("utf-8") if screenshot else None
            return False, None, screenshot_base64

        # Extract booking details from the page
        await page.wait_for_selector(".flight-details", timeout=Config.DEFAULT_TIMEOUT)

        # Take screenshot for verification
        screenshot = await page.screenshot(type="jpeg", quality=50)
        screenshot_base64 = screenshot.decode("utf-8") if screenshot else None

        # Extract flight details
        origin = await extract_text(page, ".airport-info .origin-code")
        destination = await extract_text(page, ".airport-info .destination-code")
        departure_date = await extract_text(page, ".flight-date")
        flight_number = await extract_text(page, ".flight-number")

        # Create status based on cancellation indicators
        cancelled_element = await page.query_selector(".cancellation, .cancelled")
        status = (
            BookingStatus.CANCELLED if cancelled_element else BookingStatus.CONFIRMED
        )

        # Full name
        full_name = f"{first_name} {last_name}" if first_name else last_name

        booking_details = BookingDetails(
            passenger_name=full_name,
            origin=origin,
            destination=destination,
            departure_date=departure_date,
            return_date=None,  # May not be available on first page
            flight_number=flight_number,
            status=status,
            additional_info={},
        )

        return True, booking_details, screenshot_base64

    except Exception as e:
        logger.exception(f"Error verifying Southwest Airlines booking: {str(e)}")
        try:
            screenshot = await page.screenshot(type="jpeg", quality=50)
            screenshot_base64 = screenshot.decode("utf-8") if screenshot else None
            return False, None, screenshot_base64
        except:
            return False, None, None


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((TimeoutError, asyncio.TimeoutError)),
)
async def verify_marriott_booking(
    page: Page, confirmation_code: str, last_name: str
) -> Optional[Tuple[bool, Optional[BookingDetails], Optional[str]]]:
    """
    Verify a hotel booking with Marriott.

    Args:
        page: Playwright page instance
        confirmation_code: Booking confirmation code
        last_name: Last name on the booking

    Returns:
        Tuple of (success, booking_details, screenshot)
    """
    try:
        url = PROVIDER_URLS.get("hotel", {}).get(
            "marriott", "https://www.marriott.com/reservation/lookup.mi"
        )
        await page.goto(url, timeout=Config.NAVIGATION_TIMEOUT)

        # Fill in the booking reference and last name
        await page.fill("#confirmationNumber", confirmation_code)
        await page.fill("#lastName", last_name)

        # Submit the form
        await page.click('button[type="submit"]')

        # Wait for results page
        await page.wait_for_load_state("networkidle", timeout=Config.NAVIGATION_TIMEOUT)

        # Check if the booking exists (Verify success by checking for error messages)
        error_element = await page.query_selector(".error-message, .validation-error")

        if error_element:
            # Booking not found
            screenshot = await page.screenshot(type="jpeg", quality=50)
            screenshot_base64 = screenshot.decode("utf-8") if screenshot else None
            return False, None, screenshot_base64

        # Extract booking details from the page
        await page.wait_for_selector(
            ".reservation-details", timeout=Config.DEFAULT_TIMEOUT
        )

        # Take screenshot for verification
        screenshot = await page.screenshot(type="jpeg", quality=50)
        screenshot_base64 = screenshot.decode("utf-8") if screenshot else None

        # Extract hotel details
        property_name = await extract_text(page, ".hotel-name")
        check_in_date = await extract_text(page, ".check-in-date")
        check_out_date = await extract_text(page, ".check-out-date")

        # Create status based on cancellation indicators
        cancelled_element = await page.query_selector(".cancelled, .canceled")
        status = (
            BookingStatus.CANCELLED if cancelled_element else BookingStatus.CONFIRMED
        )

        booking_details = BookingDetails(
            passenger_name=last_name,
            origin=None,
            destination=property_name,
            departure_date=check_in_date,
            return_date=check_out_date,
            flight_number=None,
            status=status,
            additional_info={"property_name": property_name},
        )

        return True, booking_details, screenshot_base64

    except Exception as e:
        logger.exception(f"Error verifying Marriott booking: {str(e)}")
        try:
            screenshot = await page.screenshot(type="jpeg", quality=50)
            screenshot_base64 = screenshot.decode("utf-8") if screenshot else None
            return False, None, screenshot_base64
        except:
            return False, None, None


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((TimeoutError, asyncio.TimeoutError)),
)
async def verify_hilton_booking(
    page: Page, confirmation_code: str, last_name: str
) -> Optional[Tuple[bool, Optional[BookingDetails], Optional[str]]]:
    """
    Verify a hotel booking with Hilton.

    Args:
        page: Playwright page instance
        confirmation_code: Booking confirmation code
        last_name: Last name on the booking

    Returns:
        Tuple of (success, booking_details, screenshot)
    """
    try:
        url = PROVIDER_URLS.get("hotel", {}).get(
            "hilton", "https://www.hilton.com/en/find-reservation/"
        )
        await page.goto(url, timeout=Config.NAVIGATION_TIMEOUT)

        # Fill in the booking reference and last name
        await page.fill("#confirmationNumber", confirmation_code)
        await page.fill("#lastName", last_name)

        # Submit the form
        await page.click('button[type="submit"]')

        # Wait for results page
        await page.wait_for_load_state("networkidle", timeout=Config.NAVIGATION_TIMEOUT)

        # Check if the booking exists (Verify success by checking for error messages)
        error_element = await page.query_selector(".error-message, .validation-error")

        if error_element:
            # Booking not found
            screenshot = await page.screenshot(type="jpeg", quality=50)
            screenshot_base64 = screenshot.decode("utf-8") if screenshot else None
            return False, None, screenshot_base64

        # Extract booking details from the page
        await page.wait_for_selector(
            ".reservation-details", timeout=Config.DEFAULT_TIMEOUT
        )

        # Take screenshot for verification
        screenshot = await page.screenshot(type="jpeg", quality=50)
        screenshot_base64 = screenshot.decode("utf-8") if screenshot else None

        # Extract hotel details
        property_name = await extract_text(page, ".hotel-name")
        check_in_date = await extract_text(page, ".check-in-date")
        check_out_date = await extract_text(page, ".check-out-date")

        # Create status based on cancellation indicators
        cancelled_element = await page.query_selector(".cancelled, .canceled")
        status = (
            BookingStatus.CANCELLED if cancelled_element else BookingStatus.CONFIRMED
        )

        booking_details = BookingDetails(
            passenger_name=last_name,
            origin=None,
            destination=property_name,
            departure_date=check_in_date,
            return_date=check_out_date,
            flight_number=None,
            status=status,
            additional_info={"property_name": property_name},
        )

        return True, booking_details, screenshot_base64

    except Exception as e:
        logger.exception(f"Error verifying Hilton booking: {str(e)}")
        try:
            screenshot = await page.screenshot(type="jpeg", quality=50)
            screenshot_base64 = screenshot.decode("utf-8") if screenshot else None
            return False, None, screenshot_base64
        except:
            return False, None, None


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((TimeoutError, asyncio.TimeoutError)),
)
async def verify_hyatt_booking(
    page: Page, confirmation_code: str, last_name: str, first_name: Optional[str] = None
) -> Optional[Tuple[bool, Optional[BookingDetails], Optional[str]]]:
    """
    Verify a hotel booking with Hyatt.

    Args:
        page: Playwright page instance
        confirmation_code: Booking confirmation code
        last_name: Last name on the booking
        first_name: First name on the booking (optional for Hyatt)

    Returns:
        Tuple of (success, booking_details, screenshot)
    """
    try:
        url = PROVIDER_URLS.get("hotel", {}).get(
            "hyatt", "https://www.hyatt.com/en-US/account/manage-reservation"
        )
        await page.goto(url, timeout=Config.NAVIGATION_TIMEOUT)

        # Fill in the booking reference and last name
        await page.fill("#confirmationNumber", confirmation_code)
        await page.fill("#lastName", last_name)
        if first_name:
            await page.fill("#firstName", first_name)

        # Submit the form
        await page.click('button[type="submit"]')

        # Wait for results page
        await page.wait_for_load_state("networkidle", timeout=Config.NAVIGATION_TIMEOUT)

        # Check if the booking exists (Verify success by checking for error messages)
        error_element = await page.query_selector(".error-message, .validation-error")

        if error_element:
            # Booking not found
            screenshot = await page.screenshot(type="jpeg", quality=50)
            screenshot_base64 = screenshot.decode("utf-8") if screenshot else None
            return False, None, screenshot_base64

        # Extract booking details from the page
        await page.wait_for_selector(
            ".reservation-details", timeout=Config.DEFAULT_TIMEOUT
        )

        # Take screenshot for verification
        screenshot = await page.screenshot(type="jpeg", quality=50)
        screenshot_base64 = screenshot.decode("utf-8") if screenshot else None

        # Extract hotel details
        property_name = await extract_text(page, ".hotel-name")
        check_in_date = await extract_text(page, ".check-in-date")
        check_out_date = await extract_text(page, ".check-out-date")

        # Create status based on cancellation indicators
        cancelled_element = await page.query_selector(".cancelled, .canceled")
        status = (
            BookingStatus.CANCELLED if cancelled_element else BookingStatus.CONFIRMED
        )

        # Full name
        full_name = f"{first_name} {last_name}" if first_name else last_name

        booking_details = BookingDetails(
            passenger_name=full_name,
            origin=None,
            destination=property_name,
            departure_date=check_in_date,
            return_date=check_out_date,
            flight_number=None,
            status=status,
            additional_info={"property_name": property_name},
        )

        return True, booking_details, screenshot_base64

    except Exception as e:
        logger.exception(f"Error verifying Hyatt booking: {str(e)}")
        try:
            screenshot = await page.screenshot(type="jpeg", quality=50)
            screenshot_base64 = screenshot.decode("utf-8") if screenshot else None
            return False, None, screenshot_base64
        except:
            return False, None, None


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((TimeoutError, asyncio.TimeoutError)),
)
async def verify_hertz_booking(
    page: Page, confirmation_code: str, last_name: str
) -> Optional[Tuple[bool, Optional[BookingDetails], Optional[str]]]:
    """
    Verify a car rental booking with Hertz.

    Args:
        page: Playwright page instance
        confirmation_code: Booking confirmation code
        last_name: Last name on the booking

    Returns:
        Tuple of (success, booking_details, screenshot)
    """
    try:
        url = PROVIDER_URLS.get("car", {}).get(
            "hertz",
            "https://www.hertz.com/rentacar/reservation/retrieveConfirmation.do",
        )
        await page.goto(url, timeout=Config.NAVIGATION_TIMEOUT)

        # Fill in the booking reference and last name
        await page.fill("#confirmationNumber", confirmation_code)
        await page.fill("#lastName", last_name)

        # Submit the form
        await page.click('button[type="submit"]')

        # Wait for results page
        await page.wait_for_load_state("networkidle", timeout=Config.NAVIGATION_TIMEOUT)

        # Check if the booking exists (Verify success by checking for error messages)
        error_element = await page.query_selector(".error-message, .validation-error")

        if error_element:
            # Booking not found
            screenshot = await page.screenshot(type="jpeg", quality=50)
            screenshot_base64 = screenshot.decode("utf-8") if screenshot else None
            return False, None, screenshot_base64

        # Extract booking details from the page
        await page.wait_for_selector(
            ".reservation-details", timeout=Config.DEFAULT_TIMEOUT
        )

        # Take screenshot for verification
        screenshot = await page.screenshot(type="jpeg", quality=50)
        screenshot_base64 = screenshot.decode("utf-8") if screenshot else None

        # Extract car rental details
        pickup_location = await extract_text(page, ".pickup-location")
        dropoff_location = await extract_text(page, ".dropoff-location")
        pickup_date = await extract_text(page, ".pickup-date")
        dropoff_date = await extract_text(page, ".dropoff-date")
        vehicle_type = await extract_text(page, ".vehicle-type")

        # Create status based on cancellation indicators
        cancelled_element = await page.query_selector(".cancelled, .canceled")
        status = (
            BookingStatus.CANCELLED if cancelled_element else BookingStatus.CONFIRMED
        )

        booking_details = BookingDetails(
            passenger_name=last_name,
            origin=pickup_location,
            destination=dropoff_location,
            departure_date=pickup_date,
            return_date=dropoff_date,
            flight_number=None,
            status=status,
            additional_info={"vehicle_type": vehicle_type},
        )

        return True, booking_details, screenshot_base64

    except Exception as e:
        logger.exception(f"Error verifying Hertz booking: {str(e)}")
        try:
            screenshot = await page.screenshot(type="jpeg", quality=50)
            screenshot_base64 = screenshot.decode("utf-8") if screenshot else None
            return False, None, screenshot_base64
        except:
            return False, None, None


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((TimeoutError, asyncio.TimeoutError)),
)
async def verify_enterprise_booking(
    page: Page, confirmation_code: str, last_name: str, first_name: Optional[str] = None
) -> Optional[Tuple[bool, Optional[BookingDetails], Optional[str]]]:
    """
    Verify a car rental booking with Enterprise.

    Args:
        page: Playwright page instance
        confirmation_code: Booking confirmation code
        last_name: Last name on the booking
        first_name: First name on the booking (optional for Enterprise)

    Returns:
        Tuple of (success, booking_details, screenshot)
    """
    try:
        url = PROVIDER_URLS.get("car", {}).get(
            "enterprise", "https://www.enterprise.com/en/reserve/manage.html"
        )
        await page.goto(url, timeout=Config.NAVIGATION_TIMEOUT)

        # Fill in the booking reference and last name
        await page.fill("#confirmationNumber", confirmation_code)
        await page.fill("#lastName", last_name)
        if first_name:
            await page.fill("#firstName", first_name)

        # Submit the form
        await page.click('button[type="submit"]')

        # Wait for results page
        await page.wait_for_load_state("networkidle", timeout=Config.NAVIGATION_TIMEOUT)

        # Check if the booking exists (Verify success by checking for error messages)
        error_element = await page.query_selector(".error-message, .reservation-error")

        if error_element:
            # Booking not found
            screenshot = await page.screenshot(type="jpeg", quality=50)
            screenshot_base64 = screenshot.decode("utf-8") if screenshot else None
            return False, None, screenshot_base64

        # Extract booking details from the page
        await page.wait_for_selector(
            ".reservation-details", timeout=Config.DEFAULT_TIMEOUT
        )

        # Take screenshot for verification
        screenshot = await page.screenshot(type="jpeg", quality=50)
        screenshot_base64 = screenshot.decode("utf-8") if screenshot else None

        # Extract car rental details
        pickup_location = await extract_text(page, ".pickup-location")
        dropoff_location = await extract_text(page, ".dropoff-location")
        pickup_date = await extract_text(page, ".pickup-date")
        dropoff_date = await extract_text(page, ".dropoff-date")
        vehicle_type = await extract_text(page, ".vehicle-type")

        # Create status based on cancellation indicators
        cancelled_element = await page.query_selector(".cancelled, .canceled")
        status = (
            BookingStatus.CANCELLED if cancelled_element else BookingStatus.CONFIRMED
        )

        # Full name
        full_name = f"{first_name} {last_name}" if first_name else last_name

        booking_details = BookingDetails(
            passenger_name=full_name,
            origin=pickup_location,
            destination=dropoff_location,
            departure_date=pickup_date,
            return_date=dropoff_date,
            flight_number=None,
            status=status,
            additional_info={"vehicle_type": vehicle_type},
        )

        return True, booking_details, screenshot_base64

    except Exception as e:
        logger.exception(f"Error verifying Enterprise booking: {str(e)}")
        try:
            screenshot = await page.screenshot(type="jpeg", quality=50)
            screenshot_base64 = screenshot.decode("utf-8") if screenshot else None
            return False, None, screenshot_base64
        except:
            return False, None, None


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((TimeoutError, asyncio.TimeoutError)),
)
async def verify_avis_booking(
    page: Page, confirmation_code: str, last_name: str
) -> Optional[Tuple[bool, Optional[BookingDetails], Optional[str]]]:
    """
    Verify a car rental booking with Avis.

    Args:
        page: Playwright page instance
        confirmation_code: Booking confirmation code
        last_name: Last name on the booking

    Returns:
        Tuple of (success, booking_details, screenshot)
    """
    try:
        url = PROVIDER_URLS.get("car", {}).get(
            "avis", "https://www.avis.com/en/reservation/view-modify-cancel"
        )
        await page.goto(url, timeout=Config.NAVIGATION_TIMEOUT)

        # Fill in the booking reference and last name
        await page.fill("#confirmationNumber", confirmation_code)
        await page.fill("#lastName", last_name)

        # Submit the form
        await page.click('button[type="submit"]')

        # Wait for results page
        await page.wait_for_load_state("networkidle", timeout=Config.NAVIGATION_TIMEOUT)

        # Check if the booking exists (Verify success by checking for error messages)
        error_element = await page.query_selector(".error-message, .error-notification")

        if error_element:
            # Booking not found
            screenshot = await page.screenshot(type="jpeg", quality=50)
            screenshot_base64 = screenshot.decode("utf-8") if screenshot else None
            return False, None, screenshot_base64

        # Extract booking details from the page
        await page.wait_for_selector(
            ".reservation-details", timeout=Config.DEFAULT_TIMEOUT
        )

        # Take screenshot for verification
        screenshot = await page.screenshot(type="jpeg", quality=50)
        screenshot_base64 = screenshot.decode("utf-8") if screenshot else None

        # Extract car rental details
        pickup_location = await extract_text(page, ".pickup-location")
        dropoff_location = await extract_text(page, ".dropoff-location")
        pickup_date = await extract_text(page, ".pickup-date")
        dropoff_date = await extract_text(page, ".dropoff-date")
        vehicle_type = await extract_text(page, ".vehicle-type")

        # Create status based on cancellation indicators
        cancelled_element = await page.query_selector(".cancelled, .canceled")
        status = (
            BookingStatus.CANCELLED if cancelled_element else BookingStatus.CONFIRMED
        )

        booking_details = BookingDetails(
            passenger_name=last_name,
            origin=pickup_location,
            destination=dropoff_location,
            departure_date=pickup_date,
            return_date=dropoff_date,
            flight_number=None,
            status=status,
            additional_info={"vehicle_type": vehicle_type},
        )

        return True, booking_details, screenshot_base64

    except Exception as e:
        logger.exception(f"Error verifying Avis booking: {str(e)}")
        try:
            screenshot = await page.screenshot(type="jpeg", quality=50)
            screenshot_base64 = screenshot.decode("utf-8") if screenshot else None
            return False, None, screenshot_base64
        except:
            return False, None, None


# Generic verification functions
async def generic_flight_verification(
    page: Page,
    url: str,
    confirmation_code: str,
    last_name: str,
    first_name: Optional[str] = None,
) -> Optional[Tuple[bool, Optional[BookingDetails], Optional[str]]]:
    """
    Generic flight booking verification for providers without specific implementations.

    Args:
        page: Playwright page instance
        url: URL to the booking verification page
        confirmation_code: Booking confirmation code
        last_name: Last name on the booking
        first_name: First name on the booking (optional)

    Returns:
        Tuple of (success, booking_details, screenshot)
    """
    try:
        if not url:
            logger.error("No URL provided for generic flight verification")
            return False, None, None

        await page.goto(url, timeout=Config.NAVIGATION_TIMEOUT)

        # Look for typical form fields
        reference_input = await find_form_field(
            page,
            [
                "confirmationNumber",
                "confirmation",
                "record",
                "recordLocator",
                "booking",
                "reference",
            ],
        )
        last_name_input = await find_form_field(
            page, ["lastName", "last-name", "surname", "passengerLastName"]
        )
        first_name_input = first_name and await find_form_field(
            page, ["firstName", "first-name", "givenName", "passengerFirstName"]
        )
        submit_button = await find_submit_button(page)

        if not reference_input or not last_name_input or not submit_button:
            logger.error("Could not locate all required form fields")
            screenshot = await page.screenshot(type="jpeg", quality=50)
            screenshot_base64 = screenshot.decode("utf-8") if screenshot else None
            return False, None, screenshot_base64

        # Fill the form
        await reference_input.fill(confirmation_code)
        await last_name_input.fill(last_name)
        if first_name and first_name_input:
            await first_name_input.fill(first_name)

        # Submit form
        await submit_button.click()
        await page.wait_for_load_state("networkidle", timeout=Config.NAVIGATION_TIMEOUT)

        # Take screenshot
        screenshot = await page.screenshot(type="jpeg", quality=50)
        screenshot_base64 = screenshot.decode("utf-8") if screenshot else None

        # Check for common error patterns
        error_element = await find_error_message(page, Config.COMMON_ERROR_PATTERNS)

        if error_element:
            return False, None, screenshot_base64

        # If no error found, attempt to extract basic booking information
        # This is highly generic and may not work for all providers
        flight_info = await extract_generic_flight_info(page)

        if flight_info:
            # Full name
            full_name = f"{first_name} {last_name}" if first_name else last_name

            booking_details = BookingDetails(
                passenger_name=full_name,
                origin=flight_info.get("origin"),
                destination=flight_info.get("destination"),
                departure_date=flight_info.get("departure_date"),
                return_date=flight_info.get("return_date"),
                flight_number=flight_info.get("flight_number"),
                status=flight_info.get("status", BookingStatus.CONFIRMED),
                additional_info={},
            )
            return True, booking_details, screenshot_base64
        else:
            # If we can't extract details but also don't find an error, assume success
            # but return minimal details
            full_name = f"{first_name} {last_name}" if first_name else last_name

            booking_details = BookingDetails(
                passenger_name=full_name,
                origin=None,
                destination=None,
                departure_date=None,
                return_date=None,
                flight_number=None,
                status=BookingStatus.CONFIRMED,  # Assume confirmed if no explicit error
                additional_info={},
            )
            return True, booking_details, screenshot_base64

    except Exception as e:
        logger.exception(f"Error in generic flight verification: {str(e)}")
        try:
            screenshot = await page.screenshot(type="jpeg", quality=50)
            screenshot_base64 = screenshot.decode("utf-8") if screenshot else None
            return False, None, screenshot_base64
        except:
            return False, None, None


async def generic_hotel_verification(
    page: Page,
    url: str,
    confirmation_code: str,
    last_name: str,
    first_name: Optional[str] = None,
) -> Optional[Tuple[bool, Optional[BookingDetails], Optional[str]]]:
    """
    Generic hotel booking verification for providers without specific implementations.

    Args:
        page: Playwright page instance
        url: URL to the booking verification page
        confirmation_code: Booking confirmation code
        last_name: Last name on the booking
        first_name: First name on the booking (optional)

    Returns:
        Tuple of (success, booking_details, screenshot)
    """
    try:
        if not url:
            logger.error("No URL provided for generic hotel verification")
            return False, None, None

        await page.goto(url, timeout=Config.NAVIGATION_TIMEOUT)

        # Look for typical form fields
        reference_input = await find_form_field(
            page,
            [
                "confirmationNumber",
                "confirmation",
                "booking",
                "reservation",
                "reference",
            ],
        )
        last_name_input = await find_form_field(
            page, ["lastName", "last-name", "surname", "guestLastName"]
        )
        first_name_input = first_name and await find_form_field(
            page, ["firstName", "first-name", "givenName", "guestFirstName"]
        )
        submit_button = await find_submit_button(page)

        if not reference_input or not last_name_input or not submit_button:
            logger.error("Could not locate all required form fields")
            screenshot = await page.screenshot(type="jpeg", quality=50)
            screenshot_base64 = screenshot.decode("utf-8") if screenshot else None
            return False, None, screenshot_base64

        # Fill the form
        await reference_input.fill(confirmation_code)
        await last_name_input.fill(last_name)
        if first_name and first_name_input:
            await first_name_input.fill(first_name)

        # Submit form
        await submit_button.click()
        await page.wait_for_load_state("networkidle", timeout=Config.NAVIGATION_TIMEOUT)

        # Take screenshot
        screenshot = await page.screenshot(type="jpeg", quality=50)
        screenshot_base64 = screenshot.decode("utf-8") if screenshot else None

        # Check for common error patterns
        error_element = await find_error_message(page, Config.COMMON_ERROR_PATTERNS)

        if error_element:
            return False, None, screenshot_base64

        # If no error found, attempt to extract basic booking information
        # Extract hotel details using common patterns
        hotel_info = await extract_generic_hotel_info(page)

        if hotel_info:
            # Full name
            full_name = f"{first_name} {last_name}" if first_name else last_name

            booking_details = BookingDetails(
                passenger_name=full_name,
                origin=None,
                destination=hotel_info.get("property_name"),
                departure_date=hotel_info.get("check_in_date"),
                return_date=hotel_info.get("check_out_date"),
                flight_number=None,
                status=hotel_info.get("status", BookingStatus.CONFIRMED),
                additional_info={"property_name": hotel_info.get("property_name")},
            )
            return True, booking_details, screenshot_base64
        else:
            # If we can't extract details but also don't find an error, assume success
            # but return minimal details
            full_name = f"{first_name} {last_name}" if first_name else last_name

            booking_details = BookingDetails(
                passenger_name=full_name,
                origin=None,
                destination=None,
                departure_date=None,
                return_date=None,
                flight_number=None,
                status=BookingStatus.CONFIRMED,  # Assume confirmed if no explicit error
                additional_info={},
            )
            return True, booking_details, screenshot_base64

    except Exception as e:
        logger.exception(f"Error in generic hotel verification: {str(e)}")
        try:
            screenshot = await page.screenshot(type="jpeg", quality=50)
            screenshot_base64 = screenshot.decode("utf-8") if screenshot else None
            return False, None, screenshot_base64
        except:
            return False, None, None


async def generic_car_verification(
    page: Page,
    url: str,
    confirmation_code: str,
    last_name: str,
    first_name: Optional[str] = None,
) -> Optional[Tuple[bool, Optional[BookingDetails], Optional[str]]]:
    """
    Generic car rental booking verification for providers without specific implementations.

    Args:
        page: Playwright page instance
        url: URL to the booking verification page
        confirmation_code: Booking confirmation code
        last_name: Last name on the booking
        first_name: First name on the booking (optional)

    Returns:
        Tuple of (success, booking_details, screenshot)
    """
    try:
        if not url:
            logger.error("No URL provided for generic car verification")
            return False, None, None

        await page.goto(url, timeout=Config.NAVIGATION_TIMEOUT)

        # Look for typical form fields
        reference_input = await find_form_field(
            page,
            [
                "confirmationNumber",
                "confirmation",
                "booking",
                "reservation",
                "reference",
            ],
        )
        last_name_input = await find_form_field(
            page, ["lastName", "last-name", "surname", "driverLastName"]
        )
        first_name_input = first_name and await find_form_field(
            page, ["firstName", "first-name", "givenName", "driverFirstName"]
        )
        submit_button = await find_submit_button(page)

        if not reference_input or not last_name_input or not submit_button:
            logger.error("Could not locate all required form fields")
            screenshot = await page.screenshot(type="jpeg", quality=50)
            screenshot_base64 = screenshot.decode("utf-8") if screenshot else None
            return False, None, screenshot_base64

        # Fill the form
        await reference_input.fill(confirmation_code)
        await last_name_input.fill(last_name)
        if first_name and first_name_input:
            await first_name_input.fill(first_name)

        # Submit form
        await submit_button.click()
        await page.wait_for_load_state("networkidle", timeout=Config.NAVIGATION_TIMEOUT)

        # Take screenshot
        screenshot = await page.screenshot(type="jpeg", quality=50)
        screenshot_base64 = screenshot.decode("utf-8") if screenshot else None

        # Check for common error patterns
        error_element = await find_error_message(page, Config.COMMON_ERROR_PATTERNS)

        if error_element:
            return False, None, screenshot_base64

        # If no error found, attempt to extract basic booking information
        # Extract car rental details using common patterns
        car_info = await extract_generic_car_info(page)

        if car_info:
            # Full name
            full_name = f"{first_name} {last_name}" if first_name else last_name

            booking_details = BookingDetails(
                passenger_name=full_name,
                origin=car_info.get("pickup_location"),
                destination=car_info.get("dropoff_location"),
                departure_date=car_info.get("pickup_date"),
                return_date=car_info.get("dropoff_date"),
                flight_number=None,
                status=car_info.get("status", BookingStatus.CONFIRMED),
                additional_info={"vehicle_type": car_info.get("vehicle_type")},
            )
            return True, booking_details, screenshot_base64
        else:
            # If we can't extract details but also don't find an error, assume success
            # but return minimal details
            full_name = f"{first_name} {last_name}" if first_name else last_name

            booking_details = BookingDetails(
                passenger_name=full_name,
                origin=None,
                destination=None,
                departure_date=None,
                return_date=None,
                flight_number=None,
                status=BookingStatus.CONFIRMED,  # Assume confirmed if no explicit error
                additional_info={},
            )
            return True, booking_details, screenshot_base64

    except Exception as e:
        logger.exception(f"Error in generic car verification: {str(e)}")
        try:
            screenshot = await page.screenshot(type="jpeg", quality=50)
            screenshot_base64 = screenshot.decode("utf-8") if screenshot else None
            return False, None, screenshot_base64
        except:
            return False, None, None


# Helper functions for extracting information from pages


async def extract_text(page: Page, selector: str) -> Optional[str]:
    """Extract text from an element on the page."""
    try:
        element = await page.query_selector(selector)
        if element:
            return await element.text_content()
        return None
    except:
        return None


async def find_form_field(page: Page, field_identifiers: list[str]) -> Optional[Any]:
    """Find a form field based on common identifiers."""
    for identifier in field_identifiers:
        # Try by ID
        element = await page.query_selector(f"#{identifier}, [id*='{identifier}' i]")
        if element:
            return element

        # Try by name
        element = await page.query_selector(
            f"[name='{identifier}'], [name*='{identifier}' i]"
        )
        if element:
            return element

        # Try by placeholder
        element = await page.query_selector(f"[placeholder*='{identifier}' i]")
        if element:
            return element

        # Try by aria-label
        element = await page.query_selector(f"[aria-label*='{identifier}' i]")
        if element:
            return element

    return None


async def find_submit_button(page: Page) -> Optional[Any]:
    """Find a submit button on the page."""
    # Try various common patterns for submit buttons
    selectors = [
        "button[type='submit']",
        "input[type='submit']",
        "button:has-text('Submit')",
        "button:has-text('Search')",
        "button:has-text('Find')",
        "button:has-text('Verify')",
        "button:has-text('Check')",
        "button:has-text('Retrieve')",
        "button:has-text('View')",
        "button:has-text('Continue')",
        "button:has-text('Look up')",
        "button:has-text('Go')",
        ".submit-button",
        "#submit",
        "[aria-label*='submit' i]",
        "[aria-label*='search' i]",
    ]

    for selector in selectors:
        element = await page.query_selector(selector)
        if element and await element.is_visible():
            return element

    return None


async def find_error_message(page: Page, error_patterns: list[str]) -> Optional[Any]:
    """Find error messages on the page based on common patterns."""
    # Look for elements with error classes
    error_selectors = [
        ".error",
        ".error-message",
        ".alert-error",
        ".alert-danger",
        "[role='alert']",
        ".notification--error",
        ".validation-error",
        ".warning",
        ".failure-message",
    ]

    for selector in error_selectors:
        element = await page.query_selector(selector)
        if element and await element.is_visible():
            return element

    # Search page text for error patterns
    page_text = await page.text_content("body")
    if page_text:
        page_text_lower = page_text.lower()
        for pattern in error_patterns:
            if pattern.lower() in page_text_lower:
                return True

    return None


async def extract_generic_flight_info(page: Page) -> Dict[str, Any]:
    """
    Extract generic flight information from the page.

    This is a best-effort function that attempts to find common patterns
    for flight information across different airline websites.
    """
    result = {
        "origin": None,
        "destination": None,
        "departure_date": None,
        "return_date": None,
        "flight_number": None,
        "status": BookingStatus.CONFIRMED,  # Default to confirmed if we can find the booking
    }

    # Search for common airport code patterns (3 uppercase letters)
    airport_code_pattern = r"\b([A-Z]{3})\b"
    page_text = await page.text_content("body")

    if page_text:
        # Find all airport codes
        airport_codes = re.findall(airport_code_pattern, page_text)
        if len(airport_codes) >= 2:
            # Assume first is origin, second is destination
            # This is simplistic but works for basic cases
            result["origin"] = airport_codes[0]
            result["destination"] = airport_codes[1]

        # Look for flight numbers (common patterns like AA123, DL456)
        flight_number_pattern = r"\b([A-Z]{2})\s*(\d{1,4})\b"
        flight_matches = re.findall(flight_number_pattern, page_text)
        if flight_matches:
            airline_code, number = flight_matches[0]
            result["flight_number"] = f"{airline_code}{number}"

        # Look for dates
        date_patterns = [
            r"\b(\d{1,2})\s*(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s*(?:,\s*)?(\d{4})\b",
            r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s*(\d{1,2})(?:st|nd|rd|th)?\s*(?:,\s*)?(\d{4})\b",
            r"\b(\d{1,2})/(\d{1,2})/(\d{2,4})\b",
            r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b",
        ]

        found_dates = []
        for pattern in date_patterns:
            dates = re.findall(pattern, page_text)
            if dates:
                found_dates.extend(dates)

        if found_dates:
            # Just take the first date found as departure
            # This is simplistic but works for basic cases
            result["departure_date"] = str(found_dates[0])
            # If we found more than one date, assume second is return
            if len(found_dates) > 1:
                result["return_date"] = str(found_dates[1])

        # Check for cancellation indicators
        cancelled_indicators = ["cancelled", "canceled", "cancellation"]
        page_text_lower = page_text.lower()
        for indicator in cancelled_indicators:
            if indicator in page_text_lower:
                result["status"] = BookingStatus.CANCELLED
                break

    return result


async def extract_generic_hotel_info(page: Page) -> Dict[str, Any]:
    """
    Extract generic hotel information from the page.

    This is a best-effort function that attempts to find common patterns
    for hotel information across different hotel websites.
    """
    result = {
        "property_name": None,
        "check_in_date": None,
        "check_out_date": None,
        "status": BookingStatus.CONFIRMED,  # Default to confirmed if we can find the booking
    }

    # Common selectors for property name
    property_selectors = [
        ".hotel-name",
        ".property-name",
        ".hotel-title",
        ".property-title",
        "h1",
        "h2",
        ".hotel",
        ".resort-name",
        ".accommodation-name",
    ]

    # Try to extract property name
    for selector in property_selectors:
        property_name = await extract_text(page, selector)
        if property_name and len(property_name.strip()) > 0:
            result["property_name"] = property_name.strip()
            break

    # Get page text for date extraction
    page_text = await page.text_content("body")

    if page_text:
        # Look for dates
        # Look for check-in/check-out date indicators
        check_in_indicators = ["check-in", "check in", "arrival", "arriving"]
        check_out_indicators = ["check-out", "check out", "departure", "departing"]

        # Look for dates (MM/DD/YYYY, YYYY-MM-DD, etc.)
        date_patterns = [
            r"\b(\d{1,2})\s*(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s*(?:,\s*)?(\d{4})\b",
            r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s*(\d{1,2})(?:st|nd|rd|th)?\s*(?:,\s*)?(\d{4})\b",
            r"\b(\d{1,2})/(\d{1,2})/(\d{2,4})\b",
            r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b",
        ]

        # Find all dates in the text
        all_dates = []
        for pattern in date_patterns:
            dates = re.findall(pattern, page_text)
            if dates:
                all_dates.extend([str(date) for date in dates])

        if len(all_dates) >= 2:
            # If we found at least two dates, try to match them to check-in/check-out
            result["check_in_date"] = all_dates[0]
            result["check_out_date"] = all_dates[1]

        # Check for cancellation indicators
        cancelled_indicators = ["cancelled", "canceled", "cancellation"]
        page_text_lower = page_text.lower()
        for indicator in cancelled_indicators:
            if indicator in page_text_lower:
                result["status"] = BookingStatus.CANCELLED
                break

    return result


async def extract_generic_car_info(page: Page) -> Dict[str, Any]:
    """
    Extract generic car rental information from the page.

    This is a best-effort function that attempts to find common patterns
    for car rental information across different rental websites.
    """
    result = {
        "pickup_location": None,
        "dropoff_location": None,
        "pickup_date": None,
        "dropoff_date": None,
        "vehicle_type": None,
        "status": BookingStatus.CONFIRMED,  # Default to confirmed if we can find the booking
    }

    # Get page text for information extraction
    page_text = await page.text_content("body")

    if page_text:
        # Look for pickup/dropoff location indicators
        pickup_indicators = ["pick-up", "pick up", "pickup", "collect"]
        dropoff_indicators = ["drop-off", "drop off", "dropoff", "return"]

        # Look for vehicle type patterns
        vehicle_patterns = [
            r"(?:car|vehicle) type:?\s*([A-Za-z0-9\s\-]+)",
            r"(?:car|vehicle) class:?\s*([A-Za-z0-9\s\-]+)",
            r"(?:Reserved|Selected|Your)\s+(?:car|vehicle):?\s*([A-Za-z0-9\s\-]+)",
        ]

        # Try to extract vehicle type
        for pattern in vehicle_patterns:
            matches = re.findall(pattern, page_text, re.IGNORECASE)
            if matches:
                result["vehicle_type"] = matches[0].strip()
                break

        # Look for dates (MM/DD/YYYY, YYYY-MM-DD, etc.)
        date_patterns = [
            r"\b(\d{1,2})\s*(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s*(?:,\s*)?(\d{4})\b",
            r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s*(\d{1,2})(?:st|nd|rd|th)?\s*(?:,\s*)?(\d{4})\b",
            r"\b(\d{1,2})/(\d{1,2})/(\d{2,4})\b",
            r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b",
        ]

        # Find all dates in the text
        all_dates = []
        for pattern in date_patterns:
            dates = re.findall(pattern, page_text)
            if dates:
                all_dates.extend([str(date) for date in dates])

        if len(all_dates) >= 2:
            # If we found at least two dates, assume first is pickup and second is dropoff
            result["pickup_date"] = all_dates[0]
            result["dropoff_date"] = all_dates[1]

        # Look for location information
        # This is very simplistic but can catch some cases
        location_pattern = r"(?:Location|Address):\s*([A-Za-z0-9\s\-\.,]+)"
        location_matches = re.findall(location_pattern, page_text, re.IGNORECASE)
        if location_matches:
            if not result["pickup_location"]:
                result["pickup_location"] = location_matches[0].strip()
            if len(location_matches) > 1 and not result["dropoff_location"]:
                result["dropoff_location"] = location_matches[1].strip()
            elif not result["dropoff_location"]:
                # If only one location found, assume same for pickup and dropoff
                result["dropoff_location"] = result["pickup_location"]

        # Check for cancellation indicators
        cancelled_indicators = ["cancelled", "canceled", "cancellation"]
        page_text_lower = page_text.lower()
        for indicator in cancelled_indicators:
            if indicator in page_text_lower:
                result["status"] = BookingStatus.CANCELLED
                break

    return result
