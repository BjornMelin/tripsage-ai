"""WebCrawl Service using direct Crawl4AI SDK integration with TripSage Core.

This service provides high-performance web crawling capabilities using the
Crawl4AI SDK directly, with full TripSage Core integration for settings,
error handling, and logging.
"""

import asyncio
import time
from typing import Any

from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig
from pydantic import BaseModel, Field

from tripsage_core.config import Settings, get_settings
from tripsage_core.exceptions.exceptions import (
    CoreExternalAPIError as CoreAPIError,
    CoreServiceError,
)


class WebCrawlServiceError(CoreAPIError):
    """Exception raised for web crawl service errors."""

    def __init__(self, message: str, original_error: Exception | None = None):
        super().__init__(
            message=message,
            code="WEBCRAWL_SERVICE_ERROR",
            service="WebCrawlService",
            details={"original_error": str(original_error) if original_error else None},
        )
        self.original_error = original_error


class WebCrawlParams(BaseModel):
    """Parameters for web crawling operations."""

    javascript_enabled: bool = Field(
        default=True, description="Enable JavaScript execution"
    )
    extract_markdown: bool = Field(default=True, description="Extract markdown content")
    extract_html: bool = Field(default=False, description="Extract raw HTML content")
    extract_structured_data: bool = Field(
        default=False, description="Extract structured data"
    )
    use_cache: bool = Field(default=True, description="Use caching for results")
    wait_for: str | None = Field(
        default=None, description="CSS selector or time to wait for"
    )
    css_selector: str | None = Field(
        default=None, description="CSS selector for content extraction"
    )
    excluded_tags: list | None = Field(default=None, description="HTML tags to exclude")
    screenshot: bool = Field(default=False, description="Take screenshot")
    pdf: bool = Field(default=False, description="Generate PDF")
    timeout: int = Field(default=30, description="Request timeout in seconds")


class WebCrawlResult(BaseModel):
    """Result from web crawling operation."""

    success: bool
    url: str
    title: str | None = None
    markdown: str | None = None
    html: str | None = None
    structured_data: dict[str, Any] | None = None
    screenshot: bytes | None = None
    pdf: bytes | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    error_message: str | None = None
    status_code: int | None = None
    performance_metrics: dict[str, Any] = Field(default_factory=dict)


class WebCrawlService:
    """Direct Crawl4AI SDK service for web crawling operations with Core integration.

    This service provides high-performance web crawling capabilities using
    the Crawl4AI SDK directly, with full TripSage Core integration.
    """

    def __init__(self, settings: Settings | None = None):
        """Initialize the WebCrawl service.

        Args:
            settings: Core application settings
        """
        self.settings = settings or get_settings()
        self._connected = False

        # Get crawler configuration from settings
        self._browser_type = getattr(self.settings, "webcrawl_browser_type", "chromium")
        self._headless = getattr(self.settings, "webcrawl_headless", True)
        self._viewport_width = getattr(self.settings, "webcrawl_viewport_width", 1280)
        self._viewport_height = getattr(self.settings, "webcrawl_viewport_height", 720)
        self._verbose = getattr(self.settings, "webcrawl_verbose", False)

        # Cache and performance settings
        self._default_cache_enabled = getattr(
            self.settings, "webcrawl_cache_enabled", True
        )
        self._default_timeout = getattr(self.settings, "webcrawl_timeout", 30)
        self._max_concurrent_crawls = getattr(
            self.settings, "webcrawl_max_concurrent", 3
        )

        # Rate limiting
        self._semaphore = asyncio.Semaphore(self._max_concurrent_crawls)

        self._browser_config = None

    async def connect(self) -> None:
        """Initialize the crawler configuration."""
        if self._connected:
            return

        try:
            self._browser_config = BrowserConfig(
                headless=self._headless,
                verbose=self._verbose,
                browser_type=self._browser_type,
                viewport_width=self._viewport_width,
                viewport_height=self._viewport_height,
            )
            self._connected = True

        except Exception as e:
            raise CoreServiceError(
                message=f"Failed to initialize WebCrawl service: {e!s}",
                code="CONNECTION_FAILED",
                service="WebCrawlService",
                details={"error": str(e)},
            ) from e

    async def disconnect(self) -> None:
        """Clean up resources."""
        self._browser_config = None
        self._connected = False

    async def ensure_connected(self) -> None:
        """Ensure service is connected."""
        if not self._connected:
            await self.connect()

    async def crawl_url(
        self, url: str, params: WebCrawlParams | None = None
    ) -> WebCrawlResult:
        """Crawl a single URL using direct Crawl4AI SDK.

        Args:
            url: The URL to crawl
            params: Crawling parameters

        Returns:
            WebCrawlResult with crawled content and metadata

        Raises:
            WebCrawlServiceError: When crawling fails
        """
        await self.ensure_connected()

        start_time = time.time()

        if params is None:
            params = WebCrawlParams()

        # Use semaphore to limit concurrent crawls
        async with self._semaphore:
            try:
                # Configure crawler run settings
                run_config = self._build_crawler_config(params)

                # Perform the crawl
                async with AsyncWebCrawler(config=self._browser_config) as crawler:
                    result = await crawler.arun(url=url, config=run_config)

                    # Calculate performance metrics
                    end_time = time.time()
                    duration_ms = (end_time - start_time) * 1000

                    # Convert to our result format
                    return self._convert_crawl_result(result, url, duration_ms)

            except Exception as e:
                end_time = time.time()
                duration_ms = (end_time - start_time) * 1000

                raise WebCrawlServiceError(
                    f"Web crawl failed for {url}: {e!s}", original_error=e
                ) from e

    async def crawl_multiple_urls(
        self, urls: list[str], params: WebCrawlParams | None = None
    ) -> list[WebCrawlResult]:
        """Crawl multiple URLs concurrently.

        Args:
            urls: List of URLs to crawl
            params: Crawling parameters (applied to all URLs)

        Returns:
            List of WebCrawlResult objects

        Raises:
            WebCrawlServiceError: When crawling setup fails
        """
        await self.ensure_connected()

        if not urls:
            return []

        if params is None:
            params = WebCrawlParams()

        try:
            # Create tasks for all URLs
            tasks = [self.crawl_url(url, params) for url in urls]

            # Execute all crawls concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Convert exceptions to failed results
            final_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    final_results.append(
                        WebCrawlResult(
                            success=False,
                            url=urls[i],
                            error_message=str(result),
                            performance_metrics={
                                "crawler_type": "crawl4ai_direct",
                                "error_type": type(result).__name__,
                            },
                        )
                    )
                else:
                    final_results.append(result)

            return final_results

        except Exception as e:
            raise WebCrawlServiceError(
                f"Failed to crawl multiple URLs: {e!s}", original_error=e
            ) from e

    def _build_crawler_config(self, params: WebCrawlParams) -> CrawlerRunConfig:
        """Build CrawlerRunConfig from WebCrawlParams.

        Args:
            params: Input parameters

        Returns:
            Configured CrawlerRunConfig
        """
        # Set cache mode - use setting default if not specified in params
        use_cache = (
            params.use_cache
            if params.use_cache is not None
            else self._default_cache_enabled
        )
        cache_mode = CacheMode.ENABLED if use_cache else CacheMode.BYPASS

        # Build configuration
        config = CrawlerRunConfig(
            cache_mode=cache_mode,
            screenshot=params.screenshot,
            pdf=params.pdf,
            word_count_threshold=10,  # Filter out very small content blocks
            verbose=self._verbose,
        )

        # Add JavaScript if needed
        if params.javascript_enabled:
            # Basic JavaScript for dynamic content loading - Wait for content
            config.js_code = [
                "window.scrollTo(0, document.body.scrollHeight);",
                "await new Promise(resolve => setTimeout(resolve, 1000));",
            ]

        # Add wait condition
        if params.wait_for:
            if params.wait_for.startswith(("css:", ".")):
                config.wait_for = params.wait_for
            else:
                # Assume it's a time value in seconds
                try:
                    wait_time = float(params.wait_for)
                    config.delay_before_return_html = wait_time
                except ValueError:
                    config.wait_for = params.wait_for

        # Add CSS selector for targeted extraction
        if params.css_selector:
            config.css_selector = params.css_selector

        # Exclude specific HTML tags
        if params.excluded_tags:
            config.excluded_tags = params.excluded_tags

        return config

    def _convert_crawl_result(
        self, crawl_result: Any, url: str, duration_ms: float
    ) -> WebCrawlResult:
        """Convert Crawl4AI result to WebCrawlResult format.

        Args:
            crawl_result: Result from Crawl4AI
            url: Original URL
            duration_ms: Crawl duration in milliseconds

        Returns:
            Converted WebCrawlResult
        """
        try:
            success = getattr(crawl_result, "success", False)

            if not success:
                error_msg = getattr(
                    crawl_result, "error_message", "Unknown crawl error"
                )
                return WebCrawlResult(
                    success=False,
                    url=url,
                    error_message=error_msg,
                    performance_metrics={
                        "duration_ms": duration_ms,
                        "crawler_type": "crawl4ai_direct",
                    },
                )

            # Extract content
            markdown = getattr(crawl_result, "markdown", "")
            html = getattr(crawl_result, "html", "")
            title = getattr(crawl_result, "metadata", {}).get("title", "")

            # Handle screenshot and PDF
            screenshot = getattr(crawl_result, "screenshot", None)
            pdf = getattr(crawl_result, "pdf", None)

            # Extract structured data if available
            structured_data = None
            if (
                hasattr(crawl_result, "extracted_content")
                and crawl_result.extracted_content
            ):
                try:
                    import json

                    structured_data = json.loads(crawl_result.extracted_content)
                except (json.JSONDecodeError, TypeError):
                    structured_data = {"raw_content": crawl_result.extracted_content}

            # Build metadata
            metadata = {
                "word_count": len(markdown.split()) if markdown else 0,
                "html_length": len(html) if html else 0,
                "status_code": getattr(crawl_result, "status_code", 200),
                "crawler_type": "crawl4ai_direct",
            }

            # Add any additional metadata from crawl result
            if hasattr(crawl_result, "metadata") and crawl_result.metadata:
                metadata.update(crawl_result.metadata)

            return WebCrawlResult(
                success=True,
                url=url,
                title=title,
                markdown=markdown,
                html=html if html else None,
                structured_data=structured_data,
                screenshot=screenshot,
                pdf=pdf,
                metadata=metadata,
                status_code=getattr(crawl_result, "status_code", 200),
                performance_metrics={
                    "duration_ms": duration_ms,
                    "crawler_type": "crawl4ai_direct",
                    "content_length": len(markdown) if markdown else 0,
                },
            )

        except Exception as e:
            return WebCrawlResult(
                success=False,
                url=url,
                error_message=f"Result conversion error: {e!s}",
                performance_metrics={
                    "duration_ms": duration_ms,
                    "crawler_type": "crawl4ai_direct",
                    "error_type": type(e).__name__,
                },
            )

    async def extract_travel_content(
        self, url: str, content_type: str = "general"
    ) -> WebCrawlResult:
        """Extract travel-specific content from a URL.

        Args:
            url: URL to crawl
            content_type: Type of travel content
                (hotels, flights, activities, restaurants)

        Returns:
            WebCrawlResult with travel-focused extraction
        """
        # Configure extraction based on content type
        params = WebCrawlParams(
            javascript_enabled=True,
            extract_markdown=True,
            extract_structured_data=True,
            use_cache=True,
        )

        # Add content-type specific selectors
        if content_type == "hotels":
            params.css_selector = ".hotel-details, .room-info, .amenities, .reviews"
            params.excluded_tags = ["script", "style", "nav", "footer", "aside"]
        elif content_type == "flights":
            params.css_selector = ".flight-details, .schedule, .price, .airline-info"
            params.excluded_tags = ["script", "style", "nav", "footer", "ads"]
        elif content_type == "activities":
            params.css_selector = ".activity-info, .description, .schedule, .booking"
            params.excluded_tags = ["script", "style", "nav", "footer"]
        elif content_type == "restaurants":
            params.css_selector = ".menu, .hours, .contact, .reviews, .photos"
            params.excluded_tags = ["script", "style", "nav", "footer"]

        return await self.crawl_url(url, params)

    async def health_check(self) -> bool:
        """Perform a health check to verify the service is working.

        Returns:
            True if the service is healthy, False otherwise
        """
        try:
            await self.ensure_connected()

            # Simple test crawl with a reliable endpoint
            result = await self.crawl_url(
                "https://httpbin.org/html",
                WebCrawlParams(use_cache=False, javascript_enabled=False, timeout=10),
            )
            return result.success
        except Exception:
            return False

    async def close(self) -> None:
        """Close the service and clean up resources.

        Since we use context managers for AsyncWebCrawler,
        there's no persistent cleanup needed.
        """
        await self.disconnect()

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()


# Global service instance
_webcrawl_service: WebCrawlService | None = None


async def get_webcrawl_service() -> WebCrawlService:
    """Get the global WebCrawl service instance.

    Returns:
        WebCrawlService instance
    """
    global _webcrawl_service

    if _webcrawl_service is None:
        _webcrawl_service = WebCrawlService()
        await _webcrawl_service.connect()

    return _webcrawl_service


async def close_webcrawl_service() -> None:
    """Close the global WebCrawl service instance."""
    global _webcrawl_service

    if _webcrawl_service:
        await _webcrawl_service.close()
        _webcrawl_service = None
