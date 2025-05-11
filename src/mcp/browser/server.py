"""Browser MCP server for TripSage."""

import asyncio
import logging
import uuid
from typing import Any, Callable, Dict, List, Optional, Union

from fastmcp import FastMCP

from src.mcp.browser.config import Config
from src.mcp.browser.context.manager import get_playwright_manager
from src.mcp.browser.handlers.booking_verification import verify_booking
from src.mcp.browser.handlers.flight_status import check_flight_status
from src.mcp.browser.handlers.price_monitor import monitor_price
from src.mcp.browser.models.request_models import (
    BookingVerificationParams,
    CheckInParams,
    ClickParams,
    CloseContextParams,
    EvaluateJSParams,
    FillParams,
    FlightStatusParams,
    GetConsoleLogsParams,
    GetTextParams,
    NavigateParams,
    PressParams,
    PriceMonitorParams,
    ScreenshotParams,
    SelectParams,
    WaitForSelectorParams,
)
from src.mcp.browser.utils.logging import (
    get_logger,
    log_error,
    log_request,
    log_response,
)

# Initialize logger
logger = get_logger(__name__)

# Create FastMCP app
app = FastMCP()


@app.on_startup
async def startup():
    """Initialize resources on startup."""
    logger.info("Starting Browser MCP server")

    # Initialize the playwright manager
    playwright_manager = get_playwright_manager()
    await playwright_manager.initialize()

    logger.info("Browser MCP server started")


@app.on_shutdown
async def shutdown():
    """Clean up resources on shutdown."""
    logger.info("Shutting down Browser MCP server")

    # Close all browser contexts and the browser
    playwright_manager = get_playwright_manager()
    await playwright_manager.close()

    logger.info("Browser MCP server shutdown complete")


@app.tool
async def mcp__browser__check_flight_status(
    params: FlightStatusParams,
) -> Dict[str, Any]:
    """Check flight status on airline website.

    Args:
        params: Flight status parameters

    Returns:
        Flight status information
    """
    return await check_flight_status(params)


@app.tool
async def mcp__browser__check_in_for_flight(params: CheckInParams) -> Dict[str, Any]:
    """Perform flight check-in.

    Args:
        params: Check-in parameters

    Returns:
        Check-in result
    """
    # Import handler function at runtime to avoid circular import
    from src.mcp.browser.handlers.flight_status import check_in_for_flight

    return await check_in_for_flight(params)


@app.tool
async def mcp__browser__verify_booking(
    params: BookingVerificationParams,
) -> Dict[str, Any]:
    """Verify a booking.

    Args:
        params: Booking verification parameters

    Returns:
        Verification result
    """
    return await verify_booking(params)


@app.tool
async def mcp__browser__monitor_price(params: PriceMonitorParams) -> Dict[str, Any]:
    """Monitor price for a travel item.

    Args:
        params: Price monitoring parameters

    Returns:
        Price monitoring result
    """
    return await monitor_price(params)


@app.tool
async def mcp__browser__browser_navigate(params: NavigateParams) -> Dict[str, Any]:
    """Navigate to a URL.

    Args:
        params: Navigation parameters

    Returns:
        Navigation result
    """
    log_request(logger, "browser_navigate", params.model_dump())

    try:
        # Generate session ID if not provided
        session_id = params.session_id or f"browser_{uuid.uuid4().hex[:8]}"

        # Get browser context
        playwright_manager = get_playwright_manager()
        context = await playwright_manager.get_context(session_id)

        # Create a new page
        page = await context.new_page()

        try:
            # Navigate to URL
            await page.goto(
                params.url,
                wait_until=params.wait_until,
                timeout=params.timeout or Config.NAVIGATION_TIMEOUT,
            )

            # Get page title
            title = await page.title()

            # Close the page to release resources
            await page.close()

            response = {
                "success": True,
                "url": params.url,
                "title": title,
                "session_id": session_id,
            }

            log_response(logger, "browser_navigate", response)
            return response

        except Exception as e:
            # Close the page to release resources
            try:
                await page.close()
            except:
                pass

            log_error(logger, "browser_navigate", e, params.model_dump())

            return {
                "success": False,
                "message": f"Navigation failed: {str(e)}",
                "url": params.url,
                "session_id": session_id,
                "error": str(e),
            }

    except Exception as e:
        log_error(logger, "browser_navigate", e, params.model_dump())

        return {
            "success": False,
            "message": f"Navigation failed: {str(e)}",
            "url": params.url,
            "error": str(e),
        }


@app.tool
async def mcp__browser__browser_click(params: ClickParams) -> Dict[str, Any]:
    """Click an element on the page.

    Args:
        params: Click parameters

    Returns:
        Click result
    """
    log_request(logger, "browser_click", params.model_dump())

    try:
        # Ensure session ID is provided
        if not params.session_id:
            raise ValueError("session_id is required for browser_click")

        # Get browser context
        playwright_manager = get_playwright_manager()
        context = await playwright_manager.get_context(params.session_id)

        # Get active page
        pages = await context.pages()
        if not pages:
            raise ValueError("No active pages in this session")

        page = pages[-1]  # Use the most recently created page

        try:
            # Click the element
            await page.click(
                params.selector, timeout=params.timeout or Config.DEFAULT_TIMEOUT
            )

            response = {
                "success": True,
                "selector": params.selector,
                "session_id": params.session_id,
            }

            log_response(logger, "browser_click", response)
            return response

        except Exception as e:
            log_error(logger, "browser_click", e, params.model_dump())

            return {
                "success": False,
                "message": f"Click failed: {str(e)}",
                "selector": params.selector,
                "session_id": params.session_id,
                "error": str(e),
            }

    except Exception as e:
        log_error(logger, "browser_click", e, params.model_dump())

        return {
            "success": False,
            "message": f"Click failed: {str(e)}",
            "selector": params.selector,
            "error": str(e),
        }


@app.tool
async def mcp__browser__browser_fill(params: FillParams) -> Dict[str, Any]:
    """Fill an input field.

    Args:
        params: Fill parameters

    Returns:
        Fill result
    """
    log_request(logger, "browser_fill", params.model_dump())

    try:
        # Ensure session ID is provided
        if not params.session_id:
            raise ValueError("session_id is required for browser_fill")

        # Get browser context
        playwright_manager = get_playwright_manager()
        context = await playwright_manager.get_context(params.session_id)

        # Get active page
        pages = await context.pages()
        if not pages:
            raise ValueError("No active pages in this session")

        page = pages[-1]  # Use the most recently created page

        try:
            # Fill the input field
            await page.fill(
                params.selector,
                params.value,
                timeout=params.timeout or Config.DEFAULT_TIMEOUT,
            )

            response = {
                "success": True,
                "selector": params.selector,
                "value": params.value,
                "session_id": params.session_id,
            }

            log_response(logger, "browser_fill", response)
            return response

        except Exception as e:
            log_error(logger, "browser_fill", e, params.model_dump())

            return {
                "success": False,
                "message": f"Fill failed: {str(e)}",
                "selector": params.selector,
                "value": params.value,
                "session_id": params.session_id,
                "error": str(e),
            }

    except Exception as e:
        log_error(logger, "browser_fill", e, params.model_dump())

        return {
            "success": False,
            "message": f"Fill failed: {str(e)}",
            "selector": params.selector,
            "value": params.value,
            "error": str(e),
        }


@app.tool
async def mcp__browser__browser_select(params: SelectParams) -> Dict[str, Any]:
    """Select an option in a dropdown.

    Args:
        params: Select parameters

    Returns:
        Select result
    """
    log_request(logger, "browser_select", params.model_dump())

    try:
        # Ensure session ID is provided
        if not params.session_id:
            raise ValueError("session_id is required for browser_select")

        # Get browser context
        playwright_manager = get_playwright_manager()
        context = await playwright_manager.get_context(params.session_id)

        # Get active page
        pages = await context.pages()
        if not pages:
            raise ValueError("No active pages in this session")

        page = pages[-1]  # Use the most recently created page

        try:
            # Convert value to list if it's a single string
            if isinstance(params.value, str):
                values = [params.value]
            else:
                values = params.value

            # Select the option(s)
            await page.select_option(
                params.selector,
                values,
                timeout=params.timeout or Config.DEFAULT_TIMEOUT,
            )

            response = {
                "success": True,
                "selector": params.selector,
                "value": params.value,
                "session_id": params.session_id,
            }

            log_response(logger, "browser_select", response)
            return response

        except Exception as e:
            log_error(logger, "browser_select", e, params.model_dump())

            return {
                "success": False,
                "message": f"Select failed: {str(e)}",
                "selector": params.selector,
                "value": params.value,
                "session_id": params.session_id,
                "error": str(e),
            }

    except Exception as e:
        log_error(logger, "browser_select", e, params.model_dump())

        return {
            "success": False,
            "message": f"Select failed: {str(e)}",
            "selector": params.selector,
            "value": params.value,
            "error": str(e),
        }


@app.tool
async def mcp__browser__browser_screenshot(params: ScreenshotParams) -> Dict[str, Any]:
    """Take a screenshot of the page or an element.

    Args:
        params: Screenshot parameters

    Returns:
        Screenshot result
    """
    log_request(logger, "browser_screenshot", params.model_dump())

    try:
        # Ensure session ID is provided
        if not params.session_id:
            raise ValueError("session_id is required for browser_screenshot")

        # Get browser context
        playwright_manager = get_playwright_manager()
        context = await playwright_manager.get_context(params.session_id)

        # Get active page
        pages = await context.pages()
        if not pages:
            raise ValueError("No active pages in this session")

        page = pages[-1]  # Use the most recently created page

        try:
            # Take screenshot
            if params.selector:
                # Screenshot of a specific element
                element = await page.query_selector(params.selector)
                if not element:
                    raise ValueError(f"Element not found: {params.selector}")

                screenshot = await element.screenshot()
            else:
                # Screenshot of the entire page or viewport
                screenshot = await page.screenshot(full_page=params.full_page)

            # Encode screenshot as base64
            import base64

            screenshot_base64 = base64.b64encode(screenshot).decode("utf-8")

            response = {
                "success": True,
                "screenshot": screenshot_base64,
                "session_id": params.session_id,
            }

            # Only log metadata in the response, not the actual screenshot
            log_response(
                logger,
                "browser_screenshot",
                {
                    "success": True,
                    "has_screenshot": True,
                    "screenshot_size_bytes": len(screenshot),
                    "session_id": params.session_id,
                },
            )

            return response

        except Exception as e:
            log_error(logger, "browser_screenshot", e, params.model_dump())

            return {
                "success": False,
                "message": f"Screenshot failed: {str(e)}",
                "session_id": params.session_id,
                "error": str(e),
            }

    except Exception as e:
        log_error(logger, "browser_screenshot", e, params.model_dump())

        return {
            "success": False,
            "message": f"Screenshot failed: {str(e)}",
            "error": str(e),
        }


@app.tool
async def mcp__browser__browser_get_visible_text(
    params: GetTextParams,
) -> Dict[str, Any]:
    """Get visible text content from the page.

    Args:
        params: Get text parameters

    Returns:
        Text content
    """
    log_request(logger, "browser_get_visible_text", params.model_dump())

    try:
        # Ensure session ID is provided
        if not params.session_id:
            raise ValueError("session_id is required for browser_get_visible_text")

        # Get browser context
        playwright_manager = get_playwright_manager()
        context = await playwright_manager.get_context(params.session_id)

        # Get active page
        pages = await context.pages()
        if not pages:
            raise ValueError("No active pages in this session")

        page = pages[-1]  # Use the most recently created page

        try:
            # Get text content
            selector = params.selector or "body"
            element = await page.query_selector(selector)
            if not element:
                raise ValueError(f"Element not found: {selector}")

            text = await element.text_content()

            response = {
                "success": True,
                "text": text,
                "selector": selector,
                "session_id": params.session_id,
            }

            # Log truncated text to avoid excessive logging
            log_response(
                logger,
                "browser_get_visible_text",
                {
                    "success": True,
                    "text_length": len(text),
                    "text_preview": text[:100] + "..." if len(text) > 100 else text,
                    "selector": selector,
                    "session_id": params.session_id,
                },
            )

            return response

        except Exception as e:
            log_error(logger, "browser_get_visible_text", e, params.model_dump())

            return {
                "success": False,
                "message": f"Get text failed: {str(e)}",
                "selector": params.selector,
                "session_id": params.session_id,
                "error": str(e),
            }

    except Exception as e:
        log_error(logger, "browser_get_visible_text", e, params.model_dump())

        return {
            "success": False,
            "message": f"Get text failed: {str(e)}",
            "selector": params.selector,
            "error": str(e),
        }


@app.tool
async def mcp__browser__browser_wait_for_selector(
    params: WaitForSelectorParams,
) -> Dict[str, Any]:
    """Wait for a selector to appear or disappear.

    Args:
        params: Wait for selector parameters

    Returns:
        Wait result
    """
    log_request(logger, "browser_wait_for_selector", params.model_dump())

    try:
        # Ensure session ID is provided
        if not params.session_id:
            raise ValueError("session_id is required for browser_wait_for_selector")

        # Get browser context
        playwright_manager = get_playwright_manager()
        context = await playwright_manager.get_context(params.session_id)

        # Get active page
        pages = await context.pages()
        if not pages:
            raise ValueError("No active pages in this session")

        page = pages[-1]  # Use the most recently created page

        try:
            # Wait for selector
            await page.wait_for_selector(
                params.selector,
                state=params.state,
                timeout=params.timeout or Config.DEFAULT_TIMEOUT,
            )

            response = {
                "success": True,
                "selector": params.selector,
                "state": params.state,
                "session_id": params.session_id,
            }

            log_response(logger, "browser_wait_for_selector", response)
            return response

        except Exception as e:
            log_error(logger, "browser_wait_for_selector", e, params.model_dump())

            return {
                "success": False,
                "message": f"Wait for selector failed: {str(e)}",
                "selector": params.selector,
                "state": params.state,
                "session_id": params.session_id,
                "error": str(e),
            }

    except Exception as e:
        log_error(logger, "browser_wait_for_selector", e, params.model_dump())

        return {
            "success": False,
            "message": f"Wait for selector failed: {str(e)}",
            "selector": params.selector,
            "state": params.state,
            "error": str(e),
        }


@app.tool
async def mcp__browser__browser_press(params: PressParams) -> Dict[str, Any]:
    """Press a key.

    Args:
        params: Press parameters

    Returns:
        Press result
    """
    log_request(logger, "browser_press", params.model_dump())

    try:
        # Ensure session ID is provided
        if not params.session_id:
            raise ValueError("session_id is required for browser_press")

        # Get browser context
        playwright_manager = get_playwright_manager()
        context = await playwright_manager.get_context(params.session_id)

        # Get active page
        pages = await context.pages()
        if not pages:
            raise ValueError("No active pages in this session")

        page = pages[-1]  # Use the most recently created page

        try:
            # Focus element if selector is provided
            if params.selector:
                element = await page.query_selector(params.selector)
                if not element:
                    raise ValueError(f"Element not found: {params.selector}")

                await element.focus()

            # Press key
            await page.keyboard.press(params.key)

            response = {
                "success": True,
                "key": params.key,
                "selector": params.selector,
                "session_id": params.session_id,
            }

            log_response(logger, "browser_press", response)
            return response

        except Exception as e:
            log_error(logger, "browser_press", e, params.model_dump())

            return {
                "success": False,
                "message": f"Press failed: {str(e)}",
                "key": params.key,
                "selector": params.selector,
                "session_id": params.session_id,
                "error": str(e),
            }

    except Exception as e:
        log_error(logger, "browser_press", e, params.model_dump())

        return {
            "success": False,
            "message": f"Press failed: {str(e)}",
            "key": params.key,
            "selector": params.selector,
            "error": str(e),
        }


@app.tool
async def mcp__browser__browser_evaluate(params: EvaluateJSParams) -> Dict[str, Any]:
    """Evaluate JavaScript in the browser.

    Args:
        params: Evaluate parameters

    Returns:
        Evaluation result
    """
    log_request(logger, "browser_evaluate", params.model_dump())

    try:
        # Ensure session ID is provided
        if not params.session_id:
            raise ValueError("session_id is required for browser_evaluate")

        # Get browser context
        playwright_manager = get_playwright_manager()
        context = await playwright_manager.get_context(params.session_id)

        # Get active page
        pages = await context.pages()
        if not pages:
            raise ValueError("No active pages in this session")

        page = pages[-1]  # Use the most recently created page

        try:
            # Evaluate JavaScript
            result = await page.evaluate(params.script, arg=params.arg)

            response = {
                "success": True,
                "result": result,
                "session_id": params.session_id,
            }

            log_response(logger, "browser_evaluate", response)
            return response

        except Exception as e:
            log_error(logger, "browser_evaluate", e, params.model_dump())

            return {
                "success": False,
                "message": f"Evaluate failed: {str(e)}",
                "session_id": params.session_id,
                "error": str(e),
            }

    except Exception as e:
        log_error(logger, "browser_evaluate", e, params.model_dump())

        return {
            "success": False,
            "message": f"Evaluate failed: {str(e)}",
            "error": str(e),
        }


@app.tool
async def mcp__browser__browser_get_console_logs(
    params: GetConsoleLogsParams,
) -> Dict[str, Any]:
    """Get console logs from the browser.

    Args:
        params: Get console logs parameters

    Returns:
        Console logs
    """
    log_request(logger, "browser_get_console_logs", params.model_dump())

    try:
        # Ensure session ID is provided
        if not params.session_id:
            raise ValueError("session_id is required for browser_get_console_logs")

        # Get browser context
        playwright_manager = get_playwright_manager()
        context = await playwright_manager.get_context(params.session_id)

        # Get active page
        pages = await context.pages()
        if not pages:
            raise ValueError("No active pages in this session")

        page = pages[-1]  # Use the most recently created page

        try:
            # Execute JavaScript to retrieve console logs
            # Note: This is a simplified approach as Playwright doesn't directly expose console logs API
            logs = await page.evaluate(
                """() => {
                return window.__console_logs || [];
            }"""
            )

            # Format logs
            formatted_logs = []
            for log in logs:
                formatted_logs.append(
                    {
                        "type": log.get("type", "log"),
                        "text": log.get("text", ""),
                        "location": log.get("location", ""),
                        "timestamp": log.get("timestamp", ""),
                    }
                )

            response = {
                "success": True,
                "logs": formatted_logs,
                "session_id": params.session_id,
            }

            log_response(
                logger,
                "browser_get_console_logs",
                {
                    "success": True,
                    "log_count": len(formatted_logs),
                    "session_id": params.session_id,
                },
            )

            return response

        except Exception as e:
            log_error(logger, "browser_get_console_logs", e, params.model_dump())

            return {
                "success": False,
                "message": f"Get console logs failed: {str(e)}",
                "session_id": params.session_id,
                "error": str(e),
            }

    except Exception as e:
        log_error(logger, "browser_get_console_logs", e, params.model_dump())

        return {
            "success": False,
            "message": f"Get console logs failed: {str(e)}",
            "error": str(e),
        }


@app.tool
async def mcp__browser__browser_close_context(
    params: CloseContextParams,
) -> Dict[str, Any]:
    """Close a browser context.

    Args:
        params: Close context parameters

    Returns:
        Close result
    """
    log_request(logger, "browser_close_context", params.model_dump())

    try:
        # Get playwright manager
        playwright_manager = get_playwright_manager()

        # Close the context
        await playwright_manager.close_context(params.session_id)

        response = {"success": True, "session_id": params.session_id}

        log_response(logger, "browser_close_context", response)
        return response

    except Exception as e:
        log_error(logger, "browser_close_context", e, params.model_dump())

        return {
            "success": False,
            "message": f"Close context failed: {str(e)}",
            "session_id": params.session_id,
            "error": str(e),
        }


@app.health
async def health_check() -> Dict[str, Any]:
    """Health check endpoint.

    Returns:
        Health check result
    """
    try:
        # Check if the playwright manager is available
        playwright_manager = get_playwright_manager()

        # Check if the browser is initialized
        browser_initialized = playwright_manager.browser is not None

        return {
            "status": "healthy",
            "browser_initialized": browser_initialized,
            "active_contexts": len(playwright_manager.contexts),
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


if __name__ == "__main__":
    # Run the FastMCP app
    app.run(host=Config.SERVER_HOST, port=Config.SERVER_PORT)
