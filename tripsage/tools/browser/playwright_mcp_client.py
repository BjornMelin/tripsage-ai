"""
Playwright MCP Client implementation for TripSage browser automation.

This module provides a client for interacting with an external Playwright MCP server.
It follows the MCP standard patterns from TripSage's configuration system.
"""

import json
import logging
import uuid
from contextlib import asynccontextmanager
from typing import Any, Dict, Literal, Optional

import httpx
from pydantic import BaseModel

from tripsage.config.mcp_settings import mcp_settings
from tripsage.utils.error_handling import with_error_handling

# Setup logging
logger = logging.getLogger(__name__)


class PlaywrightMCPError(Exception):
    """Error raised when Playwright MCP operations fail."""

    pass


class PlaywrightNavigateOptions(BaseModel):
    """Options for browser navigation."""

    browser_type: Literal["chromium", "firefox", "webkit"] = "chromium"
    width: int = 1280
    height: int = 720
    timeout: Optional[int] = None
    wait_until: Optional[str] = None
    headless: bool = False


class PlaywrightScreenshotOptions(BaseModel):
    """Options for taking screenshots."""

    selector: Optional[str] = None
    width: int = 800
    height: int = 600
    store_base64: bool = True
    full_page: bool = False
    save_png: bool = False
    downloads_dir: Optional[str] = None


class PlaywrightMCPClient:
    """Client for Playwright MCP server operations."""

    def __init__(self):
        """Initialize the Playwright MCP client using configuration
        from mcp_settings."""
        config = mcp_settings.playwright
        self.url = str(config.url)
        self.api_key = config.api_key.get_secret_value() if config.api_key else None
        self.timeout = config.timeout
        self.browser_type = config.browser_type
        self.headless = config.headless

        # Use config settings to determine headers
        headers = {
            "Content-Type": "application/json",
        }

        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        # Initialize async HTTP client
        self.client = httpx.AsyncClient(
            base_url=self.url,
            timeout=self.timeout,
            headers=headers,
            limits=httpx.Limits(
                max_connections=config.max_connections,
                max_keepalive_connections=config.max_connections // 2,
            ),
        )

        logger.info(f"Initialized Playwright MCP client for {self.url}")

    @asynccontextmanager
    async def session(self):
        """Provide a context manager for client session."""
        try:
            yield self
        finally:
            await self.close()

    @with_error_handling(error_class=PlaywrightMCPError)
    async def execute_raw_command(
        self, method_name: str, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a raw command against the Playwright MCP server.

        Args:
            method_name: The name of the Playwright MCP method to call
            params: Parameters to pass to the method

        Returns:
            The result from the Playwright MCP server

        Raises:
            PlaywrightMCPError: If the command execution fails
        """
        logger.debug(
            f"Executing Playwright MCP method: {method_name} with params: {params}"
        )

        payload = {
            "method": method_name,
            "params": params,
            "id": str(uuid.uuid4()),
            "jsonrpc": "2.0",
        }

        try:
            response = await self.client.post("", json=payload)
            response.raise_for_status()

            data = response.json()

            if "error" in data:
                error_message = data["error"].get("message", "Unknown error")
                error_code = data["error"].get("code", "unknown")
                raise PlaywrightMCPError(
                    f"Playwright MCP error {error_code}: {error_message}"
                )

            if "result" not in data:
                raise PlaywrightMCPError("Invalid response: missing 'result' field")

            return data["result"]

        except httpx.HTTPStatusError as e:
            raise PlaywrightMCPError(
                f"HTTP error: {e.response.status_code} - {e.response.text}"
            ) from e
        except httpx.RequestError as e:
            raise PlaywrightMCPError(f"Request error: {str(e)}") from e
        except json.JSONDecodeError as e:
            raise PlaywrightMCPError("Failed to parse response as JSON") from e

    @with_error_handling(error_class=PlaywrightMCPError)
    async def navigate(
        self, url: str, options: Optional[PlaywrightNavigateOptions] = None
    ) -> Dict[str, Any]:
        """Navigate to a URL using the Playwright browser.

        Args:
            url: The URL to navigate to
            options: Optional navigation options

        Returns:
            Result containing the page title and status
        """
        if options is None:
            options = PlaywrightNavigateOptions(
                browser_type=self.browser_type, headless=self.headless
            )

        params = {
            "url": url,
            "browserType": options.browser_type,
            "width": options.width,
            "height": options.height,
            "headless": options.headless,
        }

        if options.timeout is not None:
            params["timeout"] = options.timeout

        if options.wait_until is not None:
            params["waitUntil"] = options.wait_until

        return await self.execute_raw_command("Playwright_navigate", params)

    @with_error_handling(error_class=PlaywrightMCPError)
    async def take_screenshot(
        self, name: str, options: Optional[PlaywrightScreenshotOptions] = None
    ) -> Dict[str, Any]:
        """Take a screenshot of the current page.

        Args:
            name: Name for the screenshot
            options: Optional screenshot options

        Returns:
            Result containing the screenshot data or path
        """
        if options is None:
            options = PlaywrightScreenshotOptions()

        params = {
            "name": name,
            "width": options.width,
            "height": options.height,
            "storeBase64": options.store_base64,
            "fullPage": options.full_page,
            "savePng": options.save_png,
        }

        if options.selector is not None:
            params["selector"] = options.selector

        if options.downloads_dir is not None:
            params["downloadsDir"] = options.downloads_dir

        return await self.execute_raw_command("Playwright_screenshot", params)

    @with_error_handling(error_class=PlaywrightMCPError)
    async def click(self, selector: str) -> Dict[str, Any]:
        """Click an element on the page.

        Args:
            selector: CSS selector for the element to click

        Returns:
            Result indicating success
        """
        params = {"selector": selector}

        return await self.execute_raw_command("Playwright_click", params)

    @with_error_handling(error_class=PlaywrightMCPError)
    async def fill(self, selector: str, value: str) -> Dict[str, Any]:
        """Fill a form field with text.

        Args:
            selector: CSS selector for the input field
            value: The text to enter

        Returns:
            Result indicating success
        """
        params = {"selector": selector, "value": value}

        return await self.execute_raw_command("Playwright_fill", params)

    @with_error_handling(error_class=PlaywrightMCPError)
    async def get_visible_text(self) -> str:
        """Get the visible text content of the current page.

        Returns:
            The visible text content
        """
        result = await self.execute_raw_command("playwright_get_visible_text", {})
        return result.get("content", "")

    @with_error_handling(error_class=PlaywrightMCPError)
    async def get_visible_html(self) -> str:
        """Get the HTML content of the current page.

        Returns:
            The HTML content
        """
        result = await self.execute_raw_command("playwright_get_visible_html", {})
        return result.get("content", "")

    @with_error_handling(error_class=PlaywrightMCPError)
    async def close(self) -> None:
        """Close the browser session and release resources."""
        try:
            await self.execute_raw_command("Playwright_close", {})
        except Exception as e:
            logger.warning(f"Error during Playwright browser close: {str(e)}")

        await self.client.aclose()
