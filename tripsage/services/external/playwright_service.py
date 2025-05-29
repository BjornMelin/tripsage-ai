"""
Playwright Service for complex web scraping and browser automation.

This service provides direct Playwright SDK integration for scenarios requiring
JavaScript execution, complex interactions, or sophisticated browser automation.
"""

import asyncio
import time
from typing import Any, Dict, List, Optional, Union

from playwright.async_api import (
    Browser,
    BrowserContext,
    Playwright,
    async_playwright,
)
from pydantic import BaseModel, Field

from tripsage.utils.logging import get_logger

logger = get_logger(__name__)


class PlaywrightConfig(BaseModel):
    """Configuration for Playwright service."""

    headless: bool = Field(True, description="Run browser in headless mode")
    browser_type: str = Field(
        "chromium", description="Browser type: chromium, firefox, webkit"
    )
    viewport_width: int = Field(1920, description="Viewport width")
    viewport_height: int = Field(1080, description="Viewport height")
    timeout: int = Field(30000, description="Default timeout in milliseconds")
    user_agent: Optional[str] = Field(None, description="Custom user agent")
    proxy: Optional[str] = Field(None, description="Proxy URL")
    disable_javascript: bool = Field(False, description="Disable JavaScript execution")
    block_images: bool = Field(
        False, description="Block image loading for faster scraping"
    )
    block_css: bool = Field(False, description="Block CSS loading for faster scraping")


class ScrapingResult(BaseModel):
    """Result from web scraping operation."""

    url: str = Field(..., description="URL that was scraped")
    content: str = Field(..., description="Extracted content")
    html: Optional[str] = Field(None, description="Raw HTML content")
    title: Optional[str] = Field(None, description="Page title")
    links: List[str] = Field(default_factory=list, description="Extracted links")
    images: List[str] = Field(default_factory=list, description="Extracted image URLs")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )
    performance: Dict[str, Union[int, float]] = Field(
        default_factory=dict, description="Performance metrics"
    )
    success: bool = Field(True, description="Whether scraping was successful")
    error: Optional[str] = Field(None, description="Error message if failed")


class PlaywrightService:
    """Direct Playwright SDK service for complex web scraping."""

    def __init__(self, config: Optional[PlaywrightConfig] = None):
        """
        Initialize Playwright service.

        Args:
            config: Playwright configuration options
        """
        self.config = config or PlaywrightConfig()
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._connected = False

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
            launch_options = {"headless": self.config.headless, "args": []}

            # Add performance optimizations
            if self.config.block_images or self.config.block_css:
                launch_options["args"].extend(
                    [
                        "--disable-web-security",
                        "--disable-features=VizDisplayCompositor",
                    ]
                )

            if self.config.proxy:
                launch_options["proxy"] = {"server": self.config.proxy}

            self._browser = await browser_launcher.launch(**launch_options)

            # Create browser context
            context_options = {
                "viewport": {
                    "width": self.config.viewport_width,
                    "height": self.config.viewport_height,
                }
            }

            if self.config.user_agent:
                context_options["user_agent"] = self.config.user_agent

            self._context = await self._browser.new_context(**context_options)

            # Set up request interception for blocking resources
            if self.config.block_images or self.config.block_css:
                await self._context.route("**/*", self._handle_route)

            self._connected = True

            connection_time = time.time() - start_time
            logger.info(f"Playwright service connected in {connection_time:.2f}s")

        except Exception as e:
            logger.error(f"Failed to connect Playwright service: {e}")
            await self.disconnect()
            raise

    async def _handle_route(self, route, request):
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
            logger.info("Playwright service disconnected")

        except Exception as e:
            logger.error(f"Error disconnecting Playwright service: {e}")

    async def scrape_url(
        self,
        url: str,
        wait_for_selector: Optional[str] = None,
        wait_for_function: Optional[str] = None,
        custom_timeout: Optional[int] = None,
        extract_links: bool = True,
        extract_images: bool = True,
        include_html: bool = False,
    ) -> ScrapingResult:
        """
        Scrape a single URL with advanced options.

        Args:
            url: URL to scrape
            wait_for_selector: CSS selector to wait for before extracting content
            wait_for_function: JavaScript function to wait for before extracting
            custom_timeout: Custom timeout for this operation
            extract_links: Extract all links from the page
            extract_images: Extract all image URLs from the page
            include_html: Include raw HTML in response

        Returns:
            ScrapingResult with extracted content and metadata
        """
        if not self._connected:
            await self.connect()

        start_time = time.time()
        timeout = custom_timeout or self.config.timeout

        page = None
        try:
            # Create new page
            page = await self._context.new_page()

            # Set timeout
            page.set_default_timeout(timeout)

            # Disable JavaScript if configured
            if self.config.disable_javascript:
                await page.set_extra_http_headers(
                    {
                        "Accept": (
                            "text/html,application/xhtml+xml,"
                            "application/xml;q=0.9,*/*;q=0.8"
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
                    success=False,
                    error=error_msg,
                    performance={"total_time": time.time() - start_time},
                )

            # Wait for specific conditions if requested
            if wait_for_selector:
                try:
                    await page.wait_for_selector(wait_for_selector, timeout=timeout)
                except Exception as e:
                    logger.warning(
                        f"Wait for selector '{wait_for_selector}' failed: {e}"
                    )

            if wait_for_function:
                try:
                    await page.wait_for_function(wait_for_function, timeout=timeout)
                except Exception as e:
                    logger.warning(f"Wait for function failed: {e}")

            # Extract content
            extract_start = time.time()

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

            # Extract links if requested
            links = []
            if extract_links:
                links = await page.evaluate(
                    """
                    () => {
                        const linkElements = document.querySelectorAll('a[href]');
                        return Array.from(linkElements)
                            .map(a => a.href)
                            .filter(href => href.startsWith('http'));
                    }
                """
                )

            # Extract images if requested
            images = []
            if extract_images:
                images = await page.evaluate(
                    """
                    () => {
                        const imgElements = document.querySelectorAll('img[src]');
                        return Array.from(imgElements)
                            .map(img => img.src)
                            .filter(src => src.startsWith('http'));
                    }
                """
                )

            # Get HTML if requested
            html = None
            if include_html:
                html = await page.content()

            extract_time = time.time() - extract_start
            total_time = time.time() - start_time

            # Performance metrics
            performance = {
                "navigation_time": nav_time,
                "extraction_time": extract_time,
                "total_time": total_time,
                "content_length": len(content),
                "links_count": len(links),
                "images_count": len(images),
            }

            return ScrapingResult(
                url=url,
                content=content,
                html=html,
                title=title,
                links=links,
                images=images,
                metadata={
                    "status_code": response.status,
                    "content_type": response.headers.get("content-type"),
                },
                performance=performance,
                success=True,
            )

        except Exception as e:
            total_time = time.time() - start_time
            logger.error(f"Error scraping {url}: {e}")
            return ScrapingResult(
                url=url,
                content="",
                success=False,
                error=str(e),
                performance={"total_time": total_time},
            )
        finally:
            if page:
                await page.close()

    async def scrape_multiple_urls(
        self, urls: List[str], max_concurrent: int = 3, **scrape_options
    ) -> List[ScrapingResult]:
        """
        Scrape multiple URLs concurrently.

        Args:
            urls: List of URLs to scrape
            max_concurrent: Maximum number of concurrent scraping operations
            **scrape_options: Options to pass to scrape_url

        Returns:
            List of ScrapingResult objects
        """
        if not self._connected:
            await self.connect()

        # Create semaphore to limit concurrency
        semaphore = asyncio.Semaphore(max_concurrent)

        async def scrape_with_semaphore(url: str) -> ScrapingResult:
            async with semaphore:
                return await self.scrape_url(url, **scrape_options)

        # Execute scraping tasks
        tasks = [scrape_with_semaphore(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Convert exceptions to failed results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(
                    ScrapingResult(
                        url=urls[i],
                        content="",
                        success=False,
                        error=str(result),
                        performance={},
                    )
                )
            else:
                processed_results.append(result)

        return processed_results

    async def execute_custom_script(
        self, url: str, script: str, wait_before_script: float = 1.0
    ) -> Dict[str, Any]:
        """
        Execute custom JavaScript on a page.

        Args:
            url: URL to navigate to
            script: JavaScript code to execute
            wait_before_script: Time to wait before executing script

        Returns:
            Result from script execution
        """
        if not self._connected:
            await self.connect()

        page = None
        try:
            page = await self._context.new_page()
            await page.goto(url, wait_until="domcontentloaded")

            if wait_before_script > 0:
                await asyncio.sleep(wait_before_script)

            result = await page.evaluate(script)
            return {"success": True, "result": result}

        except Exception as e:
            logger.error(f"Error executing script on {url}: {e}")
            return {"success": False, "error": str(e)}
        finally:
            if page:
                await page.close()

    async def take_screenshot(
        self, url: str, output_path: Optional[str] = None, full_page: bool = True
    ) -> Optional[bytes]:
        """
        Take screenshot of a webpage.

        Args:
            url: URL to take screenshot of
            output_path: Path to save screenshot (optional)
            full_page: Take full page screenshot vs viewport only

        Returns:
            Screenshot as bytes if output_path not provided
        """
        if not self._connected:
            await self.connect()

        page = None
        try:
            page = await self._context.new_page()
            await page.goto(url, wait_until="domcontentloaded")

            screenshot_options = {"full_page": full_page}
            if output_path:
                screenshot_options["path"] = output_path

            screenshot = await page.screenshot(**screenshot_options)
            return screenshot if not output_path else None

        except Exception as e:
            logger.error(f"Error taking screenshot of {url}: {e}")
            return None
        finally:
            if page:
                await page.close()

    def __del__(self):
        """Cleanup on deletion."""
        if self._connected:
            try:
                asyncio.create_task(self.disconnect())
            except Exception:
                pass  # Ignore cleanup errors


# Convenience functions
async def create_playwright_service(
    config: Optional[PlaywrightConfig] = None,
) -> PlaywrightService:
    """Create and initialize a Playwright service."""
    service = PlaywrightService(config)
    await service.connect()
    return service


async def scrape_with_playwright(
    url: str, config: Optional[PlaywrightConfig] = None, **scrape_options
) -> ScrapingResult:
    """Quick function to scrape a URL with Playwright."""
    service = await create_playwright_service(config)
    try:
        return await service.scrape_url(url, **scrape_options)
    finally:
        await service.disconnect()


__all__ = [
    "PlaywrightService",
    "PlaywrightConfig",
    "ScrapingResult",
    "create_playwright_service",
    "scrape_with_playwright",
]
