"""
Browser tools for TripSage agents.

This module provides function tools for browser automation tasks
like checking flight status, verifying bookings, and monitoring prices.
It also includes Playwright MCP tools for general browser automation.
"""

from typing import Any, Dict, Literal, Optional

from agents import function_tool
from tripsage.mcp_abstraction.exceptions import TripSageMCPError
from tripsage.mcp_abstraction.manager import mcp_manager
from tripsage.tools.browser.playwright_mcp_client import (
    PlaywrightNavigateOptions,
    PlaywrightScreenshotOptions,
)
from tripsage.tools.browser.tools import (
    check_flight_status as browser_check_flight_status,
)
from tripsage.tools.browser.tools import monitor_price as browser_monitor_price
from tripsage.tools.browser.tools import verify_booking as browser_verify_booking
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


# Playwright MCP Tools


@function_tool
async def navigate_to_url(
    url: str,
    browser_type: Literal["chromium", "firefox", "webkit"] = "chromium",
    headless: bool = False,
    width: int = 1280,
    height: int = 720,
) -> Dict[str, Any]:
    """
    Navigate to a URL using the Playwright browser and retrieve
    the page title and content.

    Args:
        url: The URL to navigate to
        browser_type: Browser engine to use (chromium, firefox, or webkit)
        headless: Whether to run the browser in headless mode
        width: Browser viewport width in pixels
        height: Browser viewport height in pixels

    Returns:
        Dictionary containing page title and a summary of the content
    """
    logger.info(f"Navigating to {url} using Playwright MCP")

    try:
        # Initialize MCP
        await mcp_manager.initialize_mcp("playwright")

        options = PlaywrightNavigateOptions(
            browser_type=browser_type,
            headless=headless,
            width=width,
            height=height,
        )

        # Navigate to the URL
        nav_result = await mcp_manager.invoke(
            mcp_name="playwright",
            method_name="navigate",
            params={"url": url, "options": options},
        )

        # Get the visible text content
        text_content = await mcp_manager.invoke(
            mcp_name="playwright", method_name="get_visible_text", params={}
        )

        # Create a summary (just take first 500 chars for example)
        content_summary = (
            text_content[:500] + "..." if len(text_content) > 500 else text_content
        )

        return {
            "title": nav_result.get("title", "Unknown title"),
            "url": url,
            "content_summary": content_summary,
        }
    except TripSageMCPError as e:
        logger.error(f"Error navigating to {url}: {str(e)}")
        return {
            "error": str(e),
            "url": url,
        }


@function_tool
async def take_webpage_screenshot(
    url: str,
    name: str = "screenshot",
    full_page: bool = False,
    selector: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Navigate to a URL and take a screenshot of the page or a specific element.

    Args:
        url: The URL to navigate to
        name: Name for the screenshot
        full_page: Whether to capture the full page
        selector: CSS selector for a specific element (if provided)

    Returns:
        Dictionary containing screenshot data as base64 string
    """
    logger.info(f"Taking screenshot of {url} using Playwright MCP")

    try:
        # Initialize MCP
        await mcp_manager.initialize_mcp("playwright")

        # Navigate to the URL
        await mcp_manager.invoke(
            mcp_name="playwright", method_name="navigate", params={"url": url}
        )

        # Take the screenshot
        screenshot_options = PlaywrightScreenshotOptions(
            selector=selector,
            full_page=full_page,
            store_base64=True,
        )

        result = await mcp_manager.invoke(
            mcp_name="playwright",
            method_name="take_screenshot",
            params={"name": name, "options": screenshot_options},
        )

        return {
            "success": True,
            "screenshot_base64": result.get("base64", ""),
            "url": url,
            "name": name,
        }
    except TripSageMCPError as e:
        logger.error(f"Error taking screenshot of {url}: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "url": url,
            "name": name,
        }


@function_tool
async def extract_webpage_content(
    url: str,
    format: Literal["text", "html"] = "text",
) -> Dict[str, Any]:
    """
    Navigate to a URL and extract the visible content in text or HTML format.

    Args:
        url: The URL to navigate to
        format: Content format to extract ("text" or "html")

    Returns:
        Dictionary containing the extracted content
    """
    logger.info(f"Extracting {format} content from {url} using Playwright MCP")

    try:
        # Initialize MCP
        await mcp_manager.initialize_mcp("playwright")

        # Navigate to the URL
        await mcp_manager.invoke(
            mcp_name="playwright", method_name="navigate", params={"url": url}
        )

        # Extract the content
        if format == "text":
            content = await mcp_manager.invoke(
                mcp_name="playwright", method_name="get_visible_text", params={}
            )
        else:  # HTML
            content = await mcp_manager.invoke(
                mcp_name="playwright", method_name="get_visible_html", params={}
            )

        return {
            "success": True,
            "url": url,
            "format": format,
            "content": content,
        }
    except TripSageMCPError as e:
        logger.error(f"Error extracting content from {url}: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "url": url,
            "format": format,
        }


@function_tool
async def fill_web_form(
    url: str,
    form_fields: Dict[str, str],
    submit_selector: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Navigate to a URL, fill out a form, and optionally submit it.

    Args:
        url: The URL to navigate to
        form_fields: Dictionary mapping CSS selectors to values for form fields
        submit_selector: CSS selector for the submit button (if provided)

    Returns:
        Dictionary indicating success and the page URL after form submission
    """
    logger.info(f"Filling web form at {url} using Playwright MCP")

    try:
        # Initialize MCP
        await mcp_manager.initialize_mcp("playwright")

        # Navigate to the URL
        await mcp_manager.invoke(
            mcp_name="playwright", method_name="navigate", params={"url": url}
        )

        # Fill each form field
        for selector, value in form_fields.items():
            await mcp_manager.invoke(
                mcp_name="playwright",
                method_name="fill",
                params={"selector": selector, "value": value},
            )
            logger.debug(f"Filled field {selector} with value {value}")

        # Submit the form if a submit selector is provided
        if submit_selector:
            await mcp_manager.invoke(
                mcp_name="playwright",
                method_name="click",
                params={"selector": submit_selector},
            )
            logger.debug(f"Clicked submit button {submit_selector}")

        # Get the current URL (which might have changed after submission)
        result = await mcp_manager.invoke(
            mcp_name="playwright",
            method_name="execute_command",
            params={"command": "Playwright_navigate", "params": {"url": ""}},
        )
        current_url = result.get("url", url)

        return {
            "success": True,
            "url": current_url,
            "message": "Form filled successfully"
            + (" and submitted" if submit_selector else ""),
        }
    except TripSageMCPError as e:
        logger.error(f"Error filling form at {url}: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "url": url,
        }
