"""Playwright Service for web scraping and browser automation.

This service provides direct Playwright SDK integration for scenarios requiring
JavaScript execution, complex interactions, or sophisticated browser automation.
"""

import asyncio
import logging
import time
from collections.abc import Mapping
from typing import Any, cast

from playwright.async_api import (
    Browser,
    BrowserContext,
    Playwright,
    Request,
    Route,
    async_playwright,
)
from pydantic import BaseModel, Field

from tripsage_core.config import Settings, get_settings
from tripsage_core.exceptions.exceptions import (
    CoreExternalAPIError as CoreAPIError,
    CoreServiceError,
)
from tripsage_core.services.external_apis.base_service import (
    AsyncServiceProvider,
)


logger = logging.getLogger(__name__)


class PlaywrightServiceError(CoreAPIError):
    """Exception raised for Playwright service errors."""

    def __init__(self, message: str, original_error: Exception | None = None):
        """Initialize the Playwright service error."""
        super().__init__(
            message=message,
            code="PLAYWRIGHT_SERVICE_ERROR",
            api_service="PlaywrightService",
            details={"original_error": str(original_error) if original_error else None},
        )
        self.original_error = original_error


class PlaywrightConfig(BaseModel):
    """Configuration for Playwright service."""

    headless: bool = Field(True, description="Run browser in headless mode")
    browser_type: str = Field(
        "chromium", description="Browser type: chromium, firefox, webkit"
    )
    viewport_width: int = Field(1920, description="Viewport width")
    viewport_height: int = Field(1080, description="Viewport height")
    timeout: int = Field(30000, description="Default timeout in milliseconds")
    user_agent: str | None = Field(None, description="Custom user agent")
    proxy: str | None = Field(None, description="Proxy URL")
    disable_javascript: bool = Field(False, description="Disable JavaScript execution")
    block_images: bool = Field(
        False, description="Block image loading for faster scraping"
    )
    block_css: bool = Field(False, description="Block CSS loading for faster scraping")
    max_concurrent_pages: int = Field(
        3, description="Maximum concurrent pages handled by the service"
    )


class ScrapingResult(BaseModel):
    """Result from web scraping operation."""

    url: str = Field(..., description="URL that was scraped")
    content: str = Field(..., description="Extracted content")
    html: str | None = Field(None, description="Raw HTML content")
    title: str | None = Field(None, description="Page title")
    links: list[str] = Field(default_factory=list, description="Extracted links")
    images: list[str] = Field(default_factory=list, description="Extracted image URLs")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )
    performance: dict[str, int | float] = Field(
        default_factory=dict, description="Performance metrics"
    )
    success: bool = Field(True, description="Whether scraping was successful")
    error: str | None = Field(None, description="Error message if failed")


class PlaywrightService:
    """Direct Playwright SDK service for complex web scraping with Core integration."""

    def __init__(
        self,
        config: PlaywrightConfig | None = None,
        settings: Settings | None = None,
    ):
        """Initialize Playwright service.

        Args:
            config: Playwright configuration options
            settings: Core application settings
        """
        self.settings = settings or get_settings()

        # Build config from settings if not provided
        if config is None:
            config = self._build_config_from_settings()

        self.config = config
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._connected = False

        concurrency_limit = getattr(
            self.settings,
            "playwright_max_concurrent_pages",
            self.config.max_concurrent_pages,
        )
        self.config.max_concurrent_pages = concurrency_limit
        self._page_semaphore = asyncio.Semaphore(concurrency_limit)

    def _build_config_from_settings(self) -> PlaywrightConfig:
        """Build PlaywrightConfig from Core settings."""
        return PlaywrightConfig(
            headless=getattr(self.settings, "playwright_headless", True),
            browser_type=getattr(self.settings, "playwright_browser_type", "chromium"),
            viewport_width=getattr(self.settings, "playwright_viewport_width", 1920),
            viewport_height=getattr(self.settings, "playwright_viewport_height", 1080),
            timeout=getattr(self.settings, "playwright_timeout", 30000),
            user_agent=getattr(self.settings, "playwright_user_agent", None),
            proxy=getattr(self.settings, "playwright_proxy", None),
            disable_javascript=getattr(
                self.settings, "playwright_disable_javascript", False
            ),
            block_images=getattr(self.settings, "playwright_block_images", False),
            block_css=getattr(self.settings, "playwright_block_css", False),
            max_concurrent_pages=getattr(
                self.settings, "playwright_max_concurrent_pages", 3
            ),
        )

    async def connect(self) -> None:
        """Initialize Playwright and browser."""
        if self._connected:
            return

        try:
            start_time = time.time()

            # Start Playwright
            self._playwright = await async_playwright().start()

            # Launch browser
            browser_launcher = getattr(self._playwright, self.config.browser_type)
            launch_options: dict[str, Any] = {
                "headless": self.config.headless,
                "args": [],
            }

            # Add performance optimizations
            args_value = launch_options.get("args", [])
            if self.config.block_images or self.config.block_css:
                if isinstance(args_value, list):
                    args_list: list[str] = list(args_value)  # type: ignore[arg-type]
                    args_list.extend(
                        [
                            "--disable-web-security",
                            "--disable-features=VizDisplayCompositor",
                        ]
                    )
                    launch_options["args"] = args_list
                else:
                    # Convert boolean to list if needed
                    launch_options["args"] = [
                        "--disable-web-security",
                        "--disable-features=VizDisplayCompositor",
                    ]

            if self.config.proxy:
                launch_options["proxy"] = {"server": self.config.proxy}

            self._browser = await browser_launcher.launch(**launch_options)

            # Create browser context
            context_options: dict[str, Any] = {
                "viewport": {
                    "width": self.config.viewport_width,
                    "height": self.config.viewport_height,
                }
            }

            if self.config.user_agent:
                context_options["user_agent"] = self.config.user_agent

            browser = self._browser
            if browser is None:
                raise PlaywrightServiceError(
                    "Browser initialization failed before context creation."
                )

            self._context = await browser.new_context(**context_options)

            # Set up request interception for blocking resources
            if self.config.block_images or self.config.block_css:
                await self._context.route("**/*", self._handle_route)

            self._connected = True

            _connection_time = time.time() - start_time

        except Exception as e:
            await self.disconnect()
            raise CoreServiceError(
                message=f"Failed to connect Playwright service: {e!s}",
                code="CONNECTION_FAILED",
                service="PlaywrightService",
                details={"error": str(e)},
            ) from e

    def _require_context(self) -> BrowserContext:
        """Ensure a browser context is available."""
        if self._context is None:
            raise PlaywrightServiceError(
                "Playwright browser context is not initialized. Call connect() first."
            )
        return self._context

    async def _handle_route(self, route: Route, request: Request):
        """Handle resource blocking."""
        resource_type = request.resource_type

        # Block images if configured
        if self.config.block_images and resource_type in ["image", "imageset"]:
            await route.abort()
            return

        # Block CSS if configured
        if self.config.block_css and resource_type == "stylesheet":
            await route.abort()
            return

        # Continue with other requests
        await route.continue_()

    async def disconnect(self) -> None:
        """Clean up Playwright resources."""
        try:
            if self._context:
                await self._context.close()
                self._context = None

            if self._browser:
                await self._browser.close()
                self._browser = None

            if self._playwright:
                await self._playwright.stop()
                self._playwright = None

            self._connected = False

        except Exception as e:
            raise CoreServiceError(
                message=f"Error disconnecting Playwright service: {e!s}",
                code="DISCONNECT_FAILED",
                service="PlaywrightService",
                details={"error": str(e)},
            ) from e

    async def ensure_connected(self) -> None:
        """Ensure service is connected."""
        if not self._connected:
            await self.connect()

    async def scrape_url(
        self,
        url: str,
        *,
        wait_for_selector: str | None = None,
        wait_for_function: str | None = None,
        custom_timeout: int | None = None,
        extract_links: bool = True,
        extract_images: bool = True,
        include_html: bool = False,
        **kwargs: Any,
    ) -> ScrapingResult:
        """Scrape a single URL with advanced options.

        Args:
            url: URL to scrape
            wait_for_selector: CSS selector to wait for before extracting content
            wait_for_function: JavaScript function to wait for before extracting
            custom_timeout: Custom timeout for this operation
            extract_links: Extract all links from the page
            extract_images: Extract all image URLs from the page
            include_html: Include raw HTML in response
            **kwargs: Additional keyword arguments

        Returns:
            ScrapingResult with extracted content and metadata

        Raises:
            PlaywrightServiceError: When scraping fails
        """
        await self.ensure_connected()

        start_time = time.time()
        timeout = custom_timeout or self.config.timeout

        async with self._page_semaphore:
            page = None
            try:
                # Create new page
                context = self._require_context()
                page = await context.new_page()

                # Set timeout
                page.set_default_timeout(timeout)

                # Disable JavaScript if configured
                if self.config.disable_javascript:
                    await page.set_extra_http_headers(
                        {
                            "Accept": (
                                "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
                            )
                        }
                    )
                    await page.add_init_script(
                        "Object.defineProperty(navigator, 'webdriver', "
                        "{get: () => undefined})"
                    )

                # Navigate to URL
                nav_start = time.time()
                response = await page.goto(url, wait_until="domcontentloaded")
                nav_time = time.time() - nav_start

                if not response or not response.ok:
                    error_msg = (
                        f"Failed to load page: "
                        f"{response.status if response else 'No response'}"
                    )
                    return ScrapingResult(
                        url=url,
                        content="",
                        html=None,
                        title=None,
                        success=False,
                        error=error_msg,
                        performance={"total_time": time.time() - start_time},
                    )

                # Wait for specific conditions if requested
                if wait_for_selector:
                    try:
                        await page.wait_for_selector(wait_for_selector, timeout=timeout)
                    except CoreServiceError as wait_error:
                        logger.debug(
                            "Playwright wait_for_selector '%s' failed on %s: %s",
                            wait_for_selector,
                            url,
                            wait_error,
                        )

                if wait_for_function:
                    try:
                        await page.wait_for_function(wait_for_function, timeout=timeout)
                    except CoreServiceError as wait_error:
                        logger.debug(
                            "Playwright wait_for_function failed on %s: %s",
                            url,
                            wait_error,
                        )

                # Extract content
                # Get text content (similar to Crawl4AI's cleaned text)
                content = await page.evaluate(
                    """
                    () => {
                        // Remove script and style elements
                        const scripts = document.querySelectorAll(
                            'script, style, noscript'
                        );
                        scripts.forEach(el => el.remove());

                        // Get text content and clean it up
                        const text = document.body
                            ? document.body.innerText
                            : document.documentElement.innerText;

                        // Clean up whitespace
                        return text.replace(/\\s+/g, ' ').trim();
                    }
                """
                )

                # Get title
                title = await page.title()

                links = await self._extract_links(page) if extract_links else []

                images = await self._extract_images(page) if extract_images else []

                html = await self._get_page_content(page) if include_html else None

                # Calculate timing
                end_time = time.time()
                total_time = end_time - start_time
                extract_time = max(0.1, total_time - 1.0)  # Approximate extraction time

                performance = self._build_performance_metrics(
                    content=content,
                    links=links,
                    images=images,
                    navigation_time=nav_time,
                    extraction_time=extract_time,
                    total_time=total_time,
                )

                metadata = self._build_response_metadata(response)

                return ScrapingResult(
                    url=url,
                    content=content,
                    html=html,
                    title=title,
                    links=links,
                    images=images,
                    metadata=metadata,
                    performance=performance,
                    error=None,
                    success=True,
                )

            except Exception as e:
                total_time = time.time() - start_time
                raise PlaywrightServiceError(
                    f"Error scraping {url}: {e!s}", original_error=e
                ) from e
            finally:
                if page:
                    await page.close()

    async def _extract_links(self, page: Any) -> list[str]:
        """Extract HTTP links from the current page."""
        links_any = await page.evaluate(
            """
            () => {
                const linkElements = document.querySelectorAll('a[href]');
                return Array.from(linkElements)
                    .map(a => a.href)
                    .filter(href => href.startsWith('http'));
            }
        """
        )
        return [str(link) for link in links_any if isinstance(link, str)]

    async def _extract_images(self, page: Any) -> list[str]:
        """Extract HTTP image sources from the current page."""
        images_any = await page.evaluate(
            """
            () => {
                const imgElements = document.querySelectorAll('img[src]');
                return Array.from(imgElements)
                    .map(img => img.src)
                    .filter(src => src.startsWith('http'));
            }
        """
        )
        return [str(img) for img in images_any if isinstance(img, str)]

    async def _get_page_content(self, page: Any) -> str:
        """Retrieve the full HTML content for the current page."""
        return await page.content()

    def _build_performance_metrics(
        self,
        *,
        content: str,
        links: list[str],
        images: list[str],
        navigation_time: float,
        extraction_time: float,
        total_time: float,
    ) -> dict[str, Any]:
        """Construct the performance metrics payload."""
        return {
            "navigation_time": navigation_time,
            "extraction_time": extraction_time,
            "total_time": total_time,
            "content_length": len(content),
            "links_count": len(links),
            "images_count": len(images),
        }

    @staticmethod
    def _build_response_metadata(response: Any) -> dict[str, Any]:
        """Extract response metadata for the scraping result."""
        headers_any = getattr(response, "headers", None)
        content_type: str | None = None
        if isinstance(headers_any, Mapping) or hasattr(headers_any, "get"):
            headers_mapping = cast(Mapping[str, Any], headers_any)
            content_type = cast(str | None, headers_mapping.get("content-type"))
        return {
            "status_code": getattr(response, "status", None),
            "content_type": content_type,
        }

    async def scrape_multiple_urls(
        self, urls: list[str], max_concurrent: int | None = None, **scrape_options: Any
    ) -> list[ScrapingResult]:
        """Scrape multiple URLs concurrently.

        Args:
            urls: List of URLs to scrape
            max_concurrent: Maximum number of concurrent scraping operations
            **scrape_options: Options to pass to scrape_url

        Returns:
            List of ScrapingResult objects
        """
        await self.ensure_connected()

        if not urls:
            return []

        # Use settings default if not specified
        target_concurrency = (
            max_concurrent
            if max_concurrent is not None
            else self.config.max_concurrent_pages
        )

        # Create semaphore to limit concurrency
        semaphore = asyncio.Semaphore(target_concurrency)

        async def scrape_with_semaphore(url: str) -> ScrapingResult:
            async with semaphore:
                try:
                    return await self.scrape_url(url, **scrape_options)
                except CoreServiceError as e:
                    return ScrapingResult(
                        url=url,
                        content="",
                        html=None,
                        title=None,
                        success=False,
                        error=str(e),
                        performance={},
                    )

        # Execute scraping tasks
        tasks = [scrape_with_semaphore(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Convert exceptions to failed results
        processed_results: list[ScrapingResult] = []
        for i, result in enumerate(results):
            if isinstance(result, BaseException):
                processed_results.append(
                    ScrapingResult(
                        url=urls[i],
                        content="",
                        html=None,
                        title=None,
                        success=False,
                        error=str(result),
                        performance={},
                    )
                )
            elif isinstance(result, ScrapingResult):  # pyright: ignore[reportUnnecessaryIsInstance]
                processed_results.append(result)
            else:
                # Handle unexpected result types
                processed_results.append(
                    ScrapingResult(
                        url=urls[i],
                        content="",
                        html=None,
                        title=None,
                        success=False,
                        error=f"Unexpected result type: {type(result)}",
                        performance={},
                    )
                )

        return processed_results

    async def execute_custom_script(
        self, url: str, script: str, wait_before_script: float = 1.0
    ) -> dict[str, Any]:
        """Execute custom JavaScript on a page.

        Args:
            url: URL to navigate to
            script: JavaScript code to execute
            wait_before_script: Time to wait before executing script

        Returns:
            Result from script execution

        Raises:
            PlaywrightServiceError: When script execution fails
        """
        await self.ensure_connected()

        async with self._page_semaphore:
            page = None
            try:
                context = self._require_context()
                page = await context.new_page()
                await page.goto(url, wait_until="domcontentloaded")

                if wait_before_script > 0:
                    await asyncio.sleep(wait_before_script)

                result = await page.evaluate(script)
                return {"success": True, "result": result}

            except Exception as e:
                raise PlaywrightServiceError(
                    f"Error executing script on {url}: {e!s}", original_error=e
                ) from e
            finally:
                if page:
                    await page.close()

    async def take_screenshot(
        self, url: str, output_path: str | None = None, full_page: bool = True
    ) -> bytes | None:
        """Take screenshot of a webpage.

        Args:
            url: URL to take screenshot of
            output_path: Path to save screenshot (optional)
            full_page: Take full page screenshot vs viewport only

        Returns:
            Screenshot as bytes if output_path not provided

        Raises:
            PlaywrightServiceError: When screenshot fails
        """
        await self.ensure_connected()

        async with self._page_semaphore:
            page = None
            try:
                context = self._require_context()
                page = await context.new_page()
                await page.goto(url, wait_until="domcontentloaded")

                screenshot_options: dict[str, Any] = {"full_page": full_page}
                if output_path:
                    screenshot_options["path"] = output_path

                screenshot = await page.screenshot(**screenshot_options)
                return screenshot if output_path else None

            except Exception as e:
                raise PlaywrightServiceError(
                    f"Error taking screenshot of {url}: {e!s}", original_error=e
                ) from e
            finally:
                if page:
                    await page.close()

    async def scrape_travel_content(
        self, url: str, content_type: str = "general", wait_time: float = 2.0
    ) -> ScrapingResult:
        """Scrape travel-specific content with specialized extraction.

        Args:
            url: URL to scrape
            content_type: Type of travel content
                (hotels, flights, activities, restaurants)
            wait_time: Time to wait for dynamic content

        Returns:
            ScrapingResult with travel-focused extraction
        """
        # Configure extraction based on content type
        options: dict[str, Any] = {
            "extract_links": True,
            "extract_images": True,
            "include_html": False,
        }

        # Add content-type specific selectors
        if content_type == "hotels":
            options["wait_for_selector"] = ".hotel-details, .room-info, .amenities"
        elif content_type == "flights":
            options["wait_for_selector"] = ".flight-details, .schedule, .price"
        elif content_type == "activities":
            options["wait_for_selector"] = ".activity-info, .description, .booking"
        elif content_type == "restaurants":
            options["wait_for_selector"] = ".menu, .hours, .contact, .reviews"

        # Add wait function for dynamic content
        options["wait_for_function"] = (
            f"() => new Promise(resolve => setTimeout(resolve, {wait_time * 1000}))"
        )

        return await self.scrape_url(url, **options)

    async def health_check(self) -> bool:
        """Perform a health check to verify the service is working.

        Returns:
            True if the service is healthy, False otherwise
        """
        try:
            await self.ensure_connected()

            # Simple test scrape
            result = await self.scrape_url(
                "https://httpbin.org/html",
                extract_links=False,
                extract_images=False,
                custom_timeout=10000,
            )
            return result.success
        except CoreServiceError:
            return False


_playwright_service_provider = AsyncServiceProvider(
    factory=PlaywrightService,
    initializer=lambda service: service.connect(),  # type: ignore[arg-type]
    finalizer=lambda service: service.close(),  # type: ignore[arg-type]
)


async def get_playwright_service() -> PlaywrightService:
    """Return the shared Playwright service instance."""
    return await _playwright_service_provider.get()


async def close_playwright_service() -> None:
    """Dispose of the shared Playwright service instance."""
    await _playwright_service_provider.close()


# Convenience functions
async def create_playwright_service(
    config: PlaywrightConfig | None = None,
    settings: Settings | None = None,
) -> PlaywrightService:
    """Create and initialize a Playwright service."""
    service = PlaywrightService(config, settings)
    await service.connect()
    return service


async def scrape_with_playwright(
    url: str,
    config: PlaywrightConfig | None = None,
    settings: Settings | None = None,
    **scrape_options: Any,
) -> ScrapingResult:
    """Quick function to scrape a URL with Playwright."""
    service = await create_playwright_service(config, settings)
    try:
        return await service.scrape_url(url, **scrape_options)
    finally:
        await service.disconnect()


__all__ = [
    "PlaywrightConfig",
    "PlaywrightService",
    "PlaywrightServiceError",
    "ScrapingResult",
    "close_playwright_service",
    "create_playwright_service",
    "get_playwright_service",
    "scrape_with_playwright",
]
