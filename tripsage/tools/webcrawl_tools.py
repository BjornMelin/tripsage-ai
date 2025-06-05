"""Optimized web crawling tools with Crawl4AI primary + Playwright fallback.

This module implements the architecture from docs/REFACTOR/CRAWLING/:
- Primary: Direct Crawl4AI SDK (6-10x performance)
- Fallback: Native Playwright SDK (for complex JS sites)
- No MCP overhead for maximum performance
"""

from typing import Optional

from playwright.async_api import async_playwright

from tripsage.tools.webcrawl.models import UnifiedCrawlResult
from tripsage.tools.webcrawl.result_normalizer import ResultNormalizer
from tripsage.tools.webcrawl.source_selector import WebCrawlSourceSelector
from tripsage_core.config.webcrawl_feature_flags import get_performance_metrics
from tripsage_core.services.webcrawl_service import WebCrawlParams, get_webcrawl_service
from tripsage_core.utils.decorator_utils import with_error_handling
from tripsage_core.utils.logging_utils import get_logger

logger = get_logger(__name__)


@with_error_handling()
async def crawl_website_content(
    url: str,
    extract_structured_data: bool = False,
    content_type: Optional[str] = None,
    requires_javascript: bool = False,
    use_cache: bool = True,
    enable_playwright_fallback: bool = True,
) -> UnifiedCrawlResult:
    """Crawl a website using direct Crawl4AI SDK integration.

    This optimized implementation provides 2-3x performance improvement by
    bypassing MCP layers and using the Crawl4AI SDK directly.

    Args:
        url: The URL to crawl
        extract_structured_data: Whether to extract structured data (JSON-LD, etc.)
        content_type: Type of content being extracted (e.g., "booking", "travel_blog")
        requires_javascript: Whether the page requires JavaScript execution
        use_cache: Whether to use cached results if available
        enable_playwright_fallback: Whether to use Playwright as fallback on failure

    Returns:
        UnifiedCrawlResult with normalized content from direct SDK
    """
    logger.info(f"Starting direct Crawl4AI SDK crawl for {url}")

    # Get optimized configuration based on content type
    selector = WebCrawlSourceSelector()
    config = selector.get_optimized_config(
        content_type=content_type,
        requires_javascript=requires_javascript,
        extract_structured_data=extract_structured_data,
    )

    # Build parameters for the direct service
    crawl_params = WebCrawlParams(
        javascript_enabled=config["javascript_enabled"],
        extract_markdown=config["extract_markdown"],
        extract_html=config["extract_structured_data"],
        extract_structured_data=config["extract_structured_data"],
        use_cache=use_cache,
        screenshot=False,
        pdf=False,
    )

    try:
        # Use the direct service
        webcrawl_service = get_webcrawl_service()
        direct_result = await webcrawl_service.crawl_url(url, crawl_params)

        # Convert to UnifiedCrawlResult
        normalizer = ResultNormalizer()
        result = await normalizer.normalize_direct_crawl4ai_output(direct_result, url)

        # Record performance metrics
        metrics = get_performance_metrics()
        metrics.add_direct_sdk_result(
            direct_result.performance_metrics.get("duration_ms", 0),
            direct_result.success,
        )

        logger.info(
            f"Direct Crawl4AI completed for {url} - Success: {direct_result.success}"
        )
        return result

    except Exception as e:
        logger.error(f"Direct Crawl4AI failed for {url}: {str(e)}")

        # Try Playwright fallback if enabled
        if enable_playwright_fallback:
            logger.info(f"Attempting Playwright fallback for {url}")
            try:
                fallback_result = await _crawl_with_playwright_fallback(
                    url=url,
                    extract_structured_data=extract_structured_data,
                    requires_javascript=requires_javascript,
                )

                # Record fallback usage in metrics
                metrics = get_performance_metrics()
                metrics.add_playwright_fallback_result(True)

                logger.info(f"Playwright fallback succeeded for {url}")
                return fallback_result

            except Exception as fallback_error:
                logger.error(
                    f"Playwright fallback also failed for {url}: {str(fallback_error)}"
                )

                # Record fallback failure in metrics
                metrics = get_performance_metrics()
                metrics.add_playwright_fallback_result(False)

        # Return error result if all methods fail
        return UnifiedCrawlResult(
            url=url,
            status="error",
            error_message=f"All crawling methods failed. Crawl4AI: {str(e)}",
            metadata={
                "source_crawler": "failed_all",
                "crawl4ai_error": type(e).__name__,
            },
        )


@with_error_handling()
async def crawl_travel_blog(
    url: str, extract_insights: bool = True, use_cache: bool = True
) -> UnifiedCrawlResult:
    """Crawl a travel blog with optimized settings for blog content.

    This is a convenience function that uses content_type="travel_blog"
    to ensure optimal crawler configuration for blog content.

    Args:
        url: The URL of the travel blog
        extract_insights: Whether to extract structured travel insights
        use_cache: Whether to use cached results if available

    Returns:
        UnifiedCrawlResult with blog content and insights
    """
    return await crawl_website_content(
        url=url,
        extract_structured_data=extract_insights,
        content_type="travel_blog",
        requires_javascript=False,  # Most blogs don't need JS
        use_cache=use_cache,
    )


@with_error_handling()
async def crawl_booking_site(
    url: str, extract_prices: bool = True, use_cache: bool = True
) -> UnifiedCrawlResult:
    """Crawl a booking site with optimized settings for price/availability data.

    This is a convenience function that uses content_type="booking"
    to ensure optimal crawler configuration for booking sites.

    Args:
        url: The URL of the booking site (Airbnb, Booking.com, etc.)
        extract_prices: Whether to extract price and availability data
        use_cache: Whether to use cached results if available

    Returns:
        UnifiedCrawlResult with booking data
    """
    return await crawl_website_content(
        url=url,
        extract_structured_data=extract_prices,
        content_type="booking",
        requires_javascript=True,  # Booking sites usually need JS
        use_cache=use_cache,
    )


@with_error_handling()
async def crawl_event_listing(
    url: str, extract_dates: bool = True, use_cache: bool = True
) -> UnifiedCrawlResult:
    """Crawl an event listing with optimized settings for event data.

    This is a convenience function that uses content_type="events"
    to ensure optimal crawler configuration for event sites.

    Args:
        url: The URL of the event listing
        extract_dates: Whether to extract event dates and details
        use_cache: Whether to use cached results if available

    Returns:
        UnifiedCrawlResult with event data
    """
    return await crawl_website_content(
        url=url,
        extract_structured_data=extract_dates,
        content_type="events",
        requires_javascript=True,  # Event sites often need JS
        use_cache=use_cache,
    )


async def _crawl_with_playwright_fallback(
    url: str,
    extract_structured_data: bool = False,
    requires_javascript: bool = True,
) -> UnifiedCrawlResult:
    """Native Playwright SDK fallback for complex sites.

    This implementation follows the architecture from docs/REFACTOR/CRAWLING/
    using direct Playwright SDK for maximum performance and capability.

    Args:
        url: The URL to crawl
        extract_structured_data: Whether to extract structured data
        requires_javascript: Whether the page requires JavaScript execution

    Returns:
        UnifiedCrawlResult with content from Playwright
    """
    logger.info(f"Starting Playwright fallback crawl for {url}")

    async with async_playwright() as p:
        # Launch browser with optimized settings
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-extensions",
            ],
        )

        try:
            # Create context with travel-optimized settings
            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="TripSage/2.0 (Travel Planning Bot; +https://tripsage.ai)",
                extra_http_headers={
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept-Encoding": "gzip, deflate, br",
                    "Accept": (
                        "text/html,application/xhtml+xml,application/xml;q=0.9,"
                        "image/webp,*/*;q=0.8"
                    ),
                },
                ignore_https_errors=True,
            )

            page = await context.new_page()

            # Navigate to the page with timeout
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)

            # Wait for JavaScript if required
            if requires_javascript:
                await page.wait_for_timeout(2000)  # Wait for JS to settle
                await page.wait_for_load_state("networkidle", timeout=10000)

            # Extract content
            title = await page.title()

            # Get main content text
            main_content_text = await page.inner_text("body")

            # Get HTML if structured data is requested
            html_content = None
            structured_data = {}

            if extract_structured_data:
                html_content = await page.content()

                # Extract JSON-LD structured data
                json_ld_scripts = await page.query_selector_all(
                    'script[type="application/ld+json"]'
                )
                json_ld_data = []

                for script in json_ld_scripts:
                    try:
                        script_content = await script.inner_text()
                        import json

                        json_ld_data.append(json.loads(script_content))
                    except Exception:
                        continue  # Skip invalid JSON-LD

                if json_ld_data:
                    structured_data["json_ld"] = json_ld_data

                # Extract meta tags
                meta_tags = await page.query_selector_all("meta")
                meta_data = {}

                for meta in meta_tags:
                    name = await meta.get_attribute("name") or await meta.get_attribute(
                        "property"
                    )
                    content = await meta.get_attribute("content")
                    if name and content:
                        meta_data[name] = content

                if meta_data:
                    structured_data["meta"] = meta_data

            # Create markdown-like formatting for main content
            main_content_markdown = f"# {title}\n\n{main_content_text}"

            # Build result
            result = UnifiedCrawlResult(
                url=url,
                title=title,
                main_content_markdown=main_content_markdown,
                main_content_text=main_content_text,
                html_content=html_content,
                structured_data=structured_data,
                status="success",
                metadata={
                    "source_crawler": "playwright_fallback",
                    "javascript_enabled": requires_javascript,
                    "extract_structured_data": extract_structured_data,
                    "viewport": "1920x1080",
                    "browser": "chromium",
                },
            )

            logger.info(f"Playwright fallback completed successfully for {url}")
            return result

        finally:
            await browser.close()
