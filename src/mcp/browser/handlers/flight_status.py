"""Flight status handler for the Browser MCP server."""

import base64
import re
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.mcp.browser.config import Config
from src.mcp.browser.context.manager import get_playwright_manager
from src.mcp.browser.models.request_models import FlightStatusParams
from src.mcp.browser.models.response_models import FlightInfo, FlightStatusResponse
from src.mcp.browser.utils.logging import (
    get_logger,
    log_error,
    log_request,
    log_response,
)
from src.mcp.browser.utils.validators import (
    validate_airline_code,
    validate_date,
    validate_flight_number,
    validate_url,
)

logger = get_logger(__name__)


async def check_flight_status(params: FlightStatusParams) -> Dict[str, Any]:
    """Check flight status on airline website.

    Args:
        params: Flight status parameters

    Returns:
        Flight status information

    Raises:
        Exception: If the flight status check fails
    """
    # Log request
    log_request(logger, "check_flight_status", params.model_dump())

    try:
        # Validate parameters
        validate_airline_code(params.airline)
        validate_flight_number(params.flight_number)
        validate_date(params.date)

        # Generate session ID if not provided
        session_id = params.session_id or f"flight_status_{uuid.uuid4().hex[:8]}"

        # Get airline status URL
        airline_url = get_airline_status_url(params.airline)
        validate_url(airline_url)

        # Get playwright manager and context
        playwright_manager = get_playwright_manager()
        context = await playwright_manager.get_context(session_id)

        # Create a new page
        page = await context.new_page()

        try:
            # Navigate to airline status page
            await page.goto(
                airline_url, wait_until="networkidle", timeout=Config.NAVIGATION_TIMEOUT
            )

            # Wait for page to load
            await page.wait_for_load_state("networkidle")

            # Take screenshot of status page before filling - uncomment if needed
            # screenshot_before = await page.screenshot(full_page=False)

            # Fill in flight details based on airline
            flight_info = await fill_airline_status_form(
                page=page,
                airline=params.airline,
                flight_number=params.flight_number,
                date=params.date,
            )

            # Wait for results to load (with timeout)
            try:
                await page.wait_for_load_state("networkidle", timeout=30000)
            except Exception as e:
                logger.warning(f"Wait for load state timed out: {e}")

            # Take screenshot of results
            screenshot = await page.screenshot(full_page=False)

            # Get visible text content for parsing
            text_content = await page.evaluate("() => document.body.innerText")

            # Close the page
            await page.close()

            # Create response
            response = FlightStatusResponse(
                success=True,
                airline=params.airline,
                flight_number=params.flight_number,
                date=params.date,
                flight_info=flight_info,
                screenshot=(
                    base64.b64encode(screenshot).decode("utf-8") if screenshot else None
                ),
                raw_content=text_content[:1000] if text_content else None,
            )

            # Log response (without binary data)
            log_response(
                logger,
                "check_flight_status",
                {
                    "success": response.success,
                    "airline": response.airline,
                    "flight_number": response.flight_number,
                    "date": response.date,
                    "flight_info": (
                        response.flight_info.model_dump()
                        if response.flight_info
                        else None
                    ),
                    "has_screenshot": screenshot is not None,
                    "raw_content_length": len(text_content) if text_content else 0,
                },
            )

            return response.model_dump()

        except Exception as e:
            # Take error screenshot if possible
            error_screenshot = None
            try:
                error_screenshot = await page.screenshot(full_page=False)
            except Exception:
                pass

            # Close the page
            await page.close()

            # Log error
            log_error(logger, "check_flight_status", e, params.model_dump())

            # Create error response
            response = FlightStatusResponse(
                success=False,
                message=f"Failed to check flight status: {str(e)}",
                airline=params.airline,
                flight_number=params.flight_number,
                date=params.date,
                screenshot=(
                    base64.b64encode(error_screenshot).decode("utf-8")
                    if error_screenshot
                    else None
                ),
            )

            return response.model_dump()

    except Exception as e:
        # Log error
        log_error(logger, "check_flight_status", e, params.model_dump())

        # Create error response
        response = FlightStatusResponse(
            success=False,
            message=f"Failed to check flight status: {str(e)}",
            airline=params.airline,
            flight_number=params.flight_number,
            date=params.date,
        )

        return response.model_dump()


def get_airline_status_url(airline: str) -> str:
    """Get URL for airline flight status page.

    Args:
        airline: Airline code

    Returns:
        URL for airline flight status page
    """
    return Config.AIRLINE_STATUS_URLS.get(
        airline, f"https://www.google.com/search?q={airline}+flight+status"
    )


async def fill_airline_status_form(
    page: Any, airline: str, flight_number: str, date: str
) -> Optional[FlightInfo]:
    """Fill airline flight status form based on airline.

    Args:
        page: Playwright page
        airline: Airline code
        flight_number: Flight number
        date: Flight date

    Returns:
        Flight information if available

    Raises:
        Exception: If form filling fails
    """
    # Convert date string to datetime
    flight_date = datetime.strptime(date, "%Y-%m-%d")

    if airline == "AA":  # American Airlines
        return await fill_american_airlines_form(page, flight_number, flight_date)
    elif airline == "DL":  # Delta Airlines
        return await fill_delta_airlines_form(page, flight_number, flight_date)
    elif airline == "UA":  # United Airlines
        return await fill_united_airlines_form(page, flight_number, flight_date)
    elif airline == "WN":  # Southwest Airlines
        return await fill_southwest_airlines_form(page, flight_number, flight_date)
    else:
        return await fill_generic_flight_status_form(
            page, airline, flight_number, flight_date
        )


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((TimeoutError, AssertionError)),
)
async def fill_american_airlines_form(
    page: Any, flight_number: str, flight_date: datetime
) -> Optional[FlightInfo]:
    """Fill American Airlines flight status form.

    Args:
        page: Playwright page
        flight_number: Flight number
        flight_date: Flight date

    Returns:
        Flight information if available

    Raises:
        Exception: If form filling fails
    """
    # Wait for the form to be visible
    await page.wait_for_selector(
        'form[name="flightStatusByFlightForm"]', state="visible"
    )

    # Fill in flight number
    await page.fill('input[name="flightNumber"]', flight_number)

    # Set date
    formatted_date = flight_date.strftime("%m/%d/%Y")
    await page.fill('input[type="date"], input.hasDatepicker', formatted_date)

    # Submit form
    await page.click('button[type="submit"], input[type="submit"]')

    # Wait for results
    await page.wait_for_selector(
        ".flight-status-details, .flight-status-container",
        state="visible",
        timeout=30000,
    )

    # Extract flight information from the page
    return await extract_aa_flight_info(page)


async def extract_aa_flight_info(page: Any) -> Optional[FlightInfo]:
    """Extract flight information from American Airlines results page.

    Args:
        page: Playwright page

    Returns:
        Flight information if available
    """
    # Check for errors first
    error_message = await page.query_selector(".error-message, .alert-error")
    if error_message:
        error_text = await error_message.text_content()
        if error_text and any(
            err in error_text.lower()
            for err in ["no results", "not found", "unable to find", "invalid"]
        ):
            return None

    # Try to extract flight information
    try:
        # Get basic flight info
        flight_number_elem = await page.query_selector(
            ".flight-number, [data-flight-number]"
        )
        flight_number_text = (
            await flight_number_elem.text_content() if flight_number_elem else ""
        )
        flight_number_match = re.search(r"AA\s*(\d+)", flight_number_text)
        flight_number = flight_number_match.group(1) if flight_number_match else ""

        # Get airport codes
        airport_elems = await page.query_selector_all(".airport-code, .station-code")
        airports = [await elem.text_content() for elem in airport_elems]
        departure_airport = airports[0] if len(airports) > 0 else ""
        arrival_airport = airports[1] if len(airports) > 1 else ""

        # Get status
        status_elem = await page.query_selector(".flight-status, .status-indicator")
        status = await status_elem.text_content() if status_elem else "Unknown"

        # Get scheduled times
        departure_time_elem = await page.query_selector(
            ".departure-time, [data-departure-time]"
        )
        arrival_time_elem = await page.query_selector(
            ".arrival-time, [data-arrival-time]"
        )

        departure_time_text = (
            await departure_time_elem.text_content() if departure_time_elem else ""
        )
        arrival_time_text = (
            await arrival_time_elem.text_content() if arrival_time_elem else ""
        )

        # Parse times - this is simplified and might need adjustment
        # based on actual format
        scheduled_departure = (
            datetime.now().replace(hour=12, minute=0)
            if not departure_time_text
            else datetime.now()
        )
        scheduled_arrival = (
            datetime.now().replace(hour=14, minute=0)
            if not arrival_time_text
            else datetime.now()
        )

        # Get terminal and gate information
        departure_terminal_elem = await page.query_selector(
            "[data-departure-terminal], .departure-terminal"
        )
        departure_gate_elem = await page.query_selector(
            "[data-departure-gate], .departure-gate"
        )
        arrival_terminal_elem = await page.query_selector(
            "[data-arrival-terminal], .arrival-terminal"
        )
        arrival_gate_elem = await page.query_selector(
            "[data-arrival-gate], .arrival-gate"
        )

        departure_terminal = (
            await departure_terminal_elem.text_content()
            if departure_terminal_elem
            else None
        )
        departure_gate = (
            await departure_gate_elem.text_content() if departure_gate_elem else None
        )
        arrival_terminal = (
            await arrival_terminal_elem.text_content()
            if arrival_terminal_elem
            else None
        )
        arrival_gate = (
            await arrival_gate_elem.text_content() if arrival_gate_elem else None
        )

        # Check for delays
        delay_elem = await page.query_selector(".delay-information, .delay-time")
        delay_text = await delay_elem.text_content() if delay_elem else ""
        delay_match = re.search(r"(\d+)", delay_text)
        delay_minutes = int(delay_match.group(1)) if delay_match else None

        # Create flight info
        return FlightInfo(
            airline="AA",
            flight_number=flight_number,
            departure_airport=departure_airport,
            arrival_airport=arrival_airport,
            scheduled_departure=scheduled_departure,
            scheduled_arrival=scheduled_arrival,
            status=status,
            delay_minutes=delay_minutes,
            terminal_departure=departure_terminal,
            gate_departure=departure_gate,
            terminal_arrival=arrival_terminal,
            gate_arrival=arrival_gate,
        )

    except Exception as e:
        logger.error(f"Error extracting AA flight info: {e}")
        return None


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((TimeoutError, AssertionError)),
)
async def fill_delta_airlines_form(
    page: Any, flight_number: str, flight_date: datetime
) -> Optional[FlightInfo]:
    """Fill Delta Airlines flight status form.

    Args:
        page: Playwright page
        flight_number: Flight number
        flight_date: Flight date

    Returns:
        Flight information if available

    Raises:
        Exception: If form filling fails
    """
    # Wait for the form to be visible
    await page.wait_for_selector(
        'form[name="flightStatusByFlight"], form#flightStatusSearchForm',
        state="visible",
    )

    # Check if there are tabs and select "Flight Number" tab if needed
    flight_number_tab = await page.query_selector(
        'a[href="#byFlightNumber"], button.flight-number-tab'
    )
    if flight_number_tab:
        await flight_number_tab.click()
        await page.wait_for_timeout(500)  # Small delay for tab switch

    # Fill in flight number
    await page.fill('input[name="flightNumber"], input#flightNumber', flight_number)

    # Select date
    date_input = await page.query_selector('input[name="flightDate"], input#flightDate')
    if date_input:
        formatted_date = flight_date.strftime("%m/%d/%Y")
        await date_input.fill(formatted_date)
    else:
        # If no direct date input, try date picker
        date_picker = await page.query_selector(".date-picker, .datepicker-input")
        if date_picker:
            await date_picker.click()
            await page.wait_for_timeout(500)

            # Format date for selector
            month_year = flight_date.strftime("%B %Y")
            day = str(flight_date.day)

            # Navigate to correct month
            while True:
                current_month = await page.text_content(
                    ".ui-datepicker-month, .month-year"
                )
                if month_year in current_month:
                    break
                next_month = await page.query_selector(
                    ".ui-datepicker-next, .next-month"
                )
                if not next_month:
                    break
                await next_month.click()
                await page.wait_for_timeout(300)

            # Select day
            day_selector = (
                f'.ui-datepicker-calendar td a:text-is("{day}"),'
                f' .calendar-day:text-is("{day}")'
            )
            day_elem = await page.query_selector(day_selector)
            if day_elem:
                await day_elem.click()

    # Submit form
    submit_button = await page.query_selector(
        'button[type="submit"], input[type="submit"], button.search-button'
    )
    if submit_button:
        await submit_button.click()
    else:
        # Try pressing Enter on the flight number field
        await page.press('input[name="flightNumber"], input#flightNumber', "Enter")

    # Wait for results
    await page.wait_for_selector(
        ".flight-status-results, .flight-details", state="visible", timeout=30000
    )

    # Extract flight information from the page
    return await extract_dl_flight_info(page)


async def extract_dl_flight_info(page: Any) -> Optional[FlightInfo]:
    """Extract flight information from Delta Airlines results page.

    Args:
        page: Playwright page

    Returns:
        Flight information if available
    """
    # Implementation similar to AA extraction but adapted for Delta's page structure
    # This is a simplified placeholder - real implementation would need adaptation
    # to Delta's actual page structure
    return None


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((TimeoutError, AssertionError)),
)
async def fill_united_airlines_form(
    page: Any, flight_number: str, flight_date: datetime
) -> Optional[FlightInfo]:
    """Fill United Airlines flight status form.

    Args:
        page: Playwright page
        flight_number: Flight number
        flight_date: Flight date

    Returns:
        Flight information if available

    Raises:
        Exception: If form filling fails
    """
    # Wait for the form to be visible
    await page.wait_for_selector(
        'form[name="flightStatusSearchForm"], form#flightStatusForm', state="visible"
    )

    # Fill in flight number
    await page.fill('input[name="flightNumber"], input#flightNumber', flight_number)

    # Set date
    formatted_date = flight_date.strftime("%m/%d/%Y")
    await page.fill('input[name="flightDate"], input#flightDate', formatted_date)

    # Submit form
    await page.click(
        'button[type="submit"], input[type="submit"], button.search-button'
    )

    # Wait for results
    await page.wait_for_selector(
        ".flight-status-results, .flight-details-container",
        state="visible",
        timeout=30000,
    )

    # Extract flight information from the page
    return await extract_ua_flight_info(page)


async def extract_ua_flight_info(page: Any) -> Optional[FlightInfo]:
    """Extract flight information from United Airlines results page.

    Args:
        page: Playwright page

    Returns:
        Flight information if available
    """
    # Implementation similar to AA extraction but adapted for United's page structure
    # This is a simplified placeholder - real implementation would need adaptation
    # to United's actual page structure
    return None


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((TimeoutError, AssertionError)),
)
async def fill_southwest_airlines_form(
    page: Any, flight_number: str, flight_date: datetime
) -> Optional[FlightInfo]:
    """Fill Southwest Airlines flight status form.

    Args:
        page: Playwright page
        flight_number: Flight number
        flight_date: Flight date

    Returns:
        Flight information if available

    Raises:
        Exception: If form filling fails
    """
    # Wait for the form to be visible
    await page.wait_for_selector(
        "form#flightStatusByFlightForm, form.flight-status-form", state="visible"
    )

    # Fill in flight number
    await page.fill('input[name="flightNumber"], input#flightNumber', flight_number)

    # Set date
    formatted_date = flight_date.strftime("%m/%d/%Y")
    date_input = await page.query_selector('input[name="date"], input#date')
    if date_input:
        await date_input.fill(formatted_date)
    else:
        # Try date picker
        date_picker = await page.query_selector(
            ".date-picker-button, button.calendar-button"
        )
        if date_picker:
            await date_picker.click()
            await page.wait_for_timeout(500)

            # Navigate to date and select
            # This is simplified and would need adaptation to
            # Southwest's actual date picker
            # ...

    # Submit form
    await page.click(
        'button[type="submit"], input[type="submit"], button.search-button'
    )

    # Wait for results
    await page.wait_for_selector(
        ".flight-status-details, .flight-info-container", state="visible", timeout=30000
    )

    # Extract flight information from the page
    return await extract_wn_flight_info(page)


async def extract_wn_flight_info(page: Any) -> Optional[FlightInfo]:
    """Extract flight information from Southwest Airlines results page.

    Args:
        page: Playwright page

    Returns:
        Flight information if available
    """
    # Implementation similar to AA extraction but adapted for Southwest's page structure
    # This is a simplified placeholder - real implementation would need
    # adaptation to Southwest's actual page structure
    return None


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((TimeoutError, AssertionError)),
)
async def fill_generic_flight_status_form(
    page: Any, airline: str, flight_number: str, flight_date: datetime
) -> Optional[FlightInfo]:
    """Fill generic flight status form.

    This is a fallback for airlines without specific implementations.

    Args:
        page: Playwright page
        airline: Airline code
        flight_number: Flight number
        flight_date: Flight date

    Returns:
        Flight information if available

    Raises:
        Exception: If form filling fails
    """
    # Wait for page to load
    await page.wait_for_load_state("networkidle")

    # Check if on Google Flight search
    if "google.com/search" in page.url:
        # Fill Google flight search
        search_box = await page.query_selector('input[name="q"]')
        if search_box:
            full_query = f"{airline} {flight_number} {flight_date.strftime('%B %d %Y')}"
            await search_box.fill(full_query)
            await page.press('input[name="q"]', "Enter")

            # Wait for search results
            await page.wait_for_selector(
                ".flight-info, .flight-status", state="visible", timeout=30000
            )

            # Extract flight information from Google search results
            return await extract_google_flight_info(page, airline, flight_number)

    # Generic form handling
    # Look for common flight status form patterns
    flight_input = await page.query_selector(
        'input[name="flight"], input[name="flightNumber"], input[placeholder*="flight"]'
    )
    if flight_input:
        await flight_input.fill(flight_number)

    # Look for airline field if there's a separate field for it
    airline_input = await page.query_selector(
        'input[name="airline"], select[name="airline"]'
    )
    if airline_input:
        # If it's a dropdown
        tag_name = await airline_input.evaluate("el => el.tagName.toLowerCase()")
        if tag_name == "select":
            await airline_input.select_option(value=airline, label=airline)
        else:
            await airline_input.fill(airline)

    # Look for date field
    formatted_date = flight_date.strftime("%Y-%m-%d")
    alt_formatted_date = flight_date.strftime("%m/%d/%Y")

    date_input = await page.query_selector(
        'input[type="date"], input[name="date"], input[name="flightDate"]'
    )
    if date_input:
        # Try both formats
        try:
            await date_input.fill(formatted_date)
        except Exception:
            try:
                await date_input.fill(alt_formatted_date)
            except Exception:
                logger.warning("Failed to fill date field with either format")

    # Look for search/submit button
    submit_button = await page.query_selector(
        (
            'button[type="submit"], input[type="submit"],'
            ' button:has-text("Search"), button:has-text("Find")'
        )
    )
    if submit_button:
        await submit_button.click()

    # Wait a bit for results
    await page.wait_for_timeout(5000)

    # Look for common flight status result patterns
    status_elem = await page.query_selector(
        ".flight-status, .status, [data-status], .statusLabel"
    )
    if status_elem:
        # Extract generic flight information based on common patterns
        return await extract_generic_flight_info(page, airline, flight_number)

    # If no results found, return None
    return None


async def extract_google_flight_info(
    page: Any, airline: str, flight_number: str
) -> Optional[FlightInfo]:
    """Extract flight information from Google search results.

    Args:
        page: Playwright page
        airline: Airline code
        flight_number: Flight number

    Returns:
        Flight information if available
    """
    # Check for flight status box
    flight_status_box = await page.query_selector(
        ".flight-status-box, .bUOXSd, .kp-blk"
    )
    if not flight_status_box:
        return None

    # Get all text from the box for parsing
    text_content = await flight_status_box.text_content()

    # Extract information using regex patterns
    # This is simplified and would need adaptation to Google's actual result format
    airports = re.findall(r"\b([A-Z]{3})\b", text_content)
    departure_airport = airports[0] if len(airports) > 0 else ""
    arrival_airport = airports[1] if len(airports) > 1 else ""

    status_pattern = re.compile(
        r"(On time|Delayed|Cancelled|Arrived|Departed|In flight)", re.IGNORECASE
    )
    status_match = status_pattern.search(text_content)
    status = status_match.group(1) if status_match else "Unknown"

    # Extract times - this is simplified
    time_pattern = re.compile(r"(\d{1,2}:\d{2} [AP]M)", re.IGNORECASE)  # noqa: F841
    # Uncomment if needed: times = time_pattern.findall(text_content)

    scheduled_departure = datetime.now().replace(hour=12, minute=0)
    scheduled_arrival = datetime.now().replace(hour=14, minute=0)

    # Create flight info
    return FlightInfo(
        airline=airline,
        flight_number=flight_number,
        departure_airport=departure_airport,
        arrival_airport=arrival_airport,
        scheduled_departure=scheduled_departure,
        scheduled_arrival=scheduled_arrival,
        status=status,
        # The remaining fields are optional
    )


async def extract_generic_flight_info(
    page: Any, airline: str, flight_number: str
) -> Optional[FlightInfo]:
    """Extract flight information from a generic flight status page.

    Args:
        page: Playwright page
        airline: Airline code
        flight_number: Flight number

    Returns:
        Flight information if available
    """
    # Get all text content for parsing
    text_content = await page.evaluate("() => document.body.innerText")

    # Extract information using regex patterns
    # This is a simplified approach and would need adaptation based on actual pages
    airports = re.findall(r"\b([A-Z]{3})\b", text_content)
    departure_airport = airports[0] if len(airports) > 0 else ""
    arrival_airport = airports[1] if len(airports) > 1 else ""

    status_pattern = re.compile(
        r"(?:Status|Flight Status)[\s:]+([A-Za-z\s]+)", re.IGNORECASE
    )
    status_match = status_pattern.search(text_content)
    status = status_match.group(1).strip() if status_match else "Unknown"

    # Extract times - this is simplified
    scheduled_departure = datetime.now().replace(hour=12, minute=0)
    scheduled_arrival = datetime.now().replace(hour=14, minute=0)

    # Check for delays
    delay_pattern = re.compile(r"(?:Delayed|Delay)[\s:]+(\d+)", re.IGNORECASE)
    delay_match = delay_pattern.search(text_content)
    delay_minutes = int(delay_match.group(1)) if delay_match else None

    # Create flight info
    return FlightInfo(
        airline=airline,
        flight_number=flight_number,
        departure_airport=departure_airport,
        arrival_airport=arrival_airport,
        scheduled_departure=scheduled_departure,
        scheduled_arrival=scheduled_arrival,
        status=status,
        delay_minutes=delay_minutes,
        # The remaining fields are optional
    )
