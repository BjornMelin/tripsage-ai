"""Unified web crawling tools for TripSage agents.

Provides a unified interface for web crawling operations using either
Crawl4AI or Firecrawl MCP clients based on intelligent source selection,
with Playwright MCP as a fallback for JavaScript-heavy sites.
"""

from typing import Optional

from tripsage.tools.webcrawl.models import UnifiedCrawlResult
from tripsage.tools.webcrawl.result_normalizer import get_normalizer
from tripsage.tools.webcrawl.source_selector import get_source_selector
from tripsage.utils.error_handling import with_error_handling
from tripsage.utils.function_tools import function_tool
from tripsage.utils.logging import get_logger

logger = get_logger(__name__)


@function_tool
@with_error_handling
async def crawl_website_content(
    url: str,
    extract_structured_data: bool = False,
    content_type: Optional[str] = None,
    requires_javascript: bool = False,
    use_cache: bool = True,
    enable_playwright_fallback: bool = True,
) -> UnifiedCrawlResult:
    """Crawl a website using the most appropriate MCP client with Playwright fallback.

    This unified tool automatically selects between Crawl4AI and Firecrawl
    based on the URL domain, content type, and extraction requirements.
    If the primary crawler fails, it falls back to Playwright MCP for
    JavaScript-heavy content.

    Args:
        url: The URL to crawl
        extract_structured_data: Whether to extract structured data (JSON-LD, etc.)
        content_type: Type of content being extracted (e.g., "booking", "travel_blog")
        requires_javascript: Whether the page requires JavaScript execution
        use_cache: Whether to use cached results if available
        enable_playwright_fallback: Whether to use Playwright as fallback on failure

    Returns:
        UnifiedCrawlResult with normalized content from the appropriate crawler
    """
    # Get the source selector
    selector = get_source_selector()

    # Determine extraction complexity based on parameters
    extraction_complexity = "simple"
    if extract_structured_data and requires_javascript:
        extraction_complexity = "complex"
    elif extract_structured_data or requires_javascript:
        extraction_complexity = "moderate"

    # Get the appropriate client for this URL
    client = selector.get_client_for_url(
        url,
        content_type=content_type,
        prefer_structured_data=extract_structured_data,
        requires_javascript=requires_javascript,
        extraction_complexity=extraction_complexity,
    )

    # Get the normalizer
    normalizer = get_normalizer()

    # Helper function to check if a result needs fallback
    def needs_fallback(result: UnifiedCrawlResult) -> bool:
        """Check if a crawl result requires fallback to Playwright."""
        # Failed result
        if result.status == "error":
            return True

        # Empty or insufficient content
        if not result.has_content():
            return True

        # Check for common JS-required indicators
        error_patterns = [
            "JavaScript is required",
            "Enable JavaScript",
            "This site requires JavaScript",
            "Please enable JavaScript",
        ]

        if result.error_message:
            for pattern in error_patterns:
                if pattern.lower() in result.error_message.lower():
                    return True

        if result.main_content_text:
            for pattern in error_patterns:
                if pattern.lower() in result.main_content_text.lower():
                    return True

        # Check if content is suspiciously short (might indicate loading error)
        if result.main_content_text and len(result.main_content_text) < 100:
            return True

        return False

    primary_result = None
    try:
        # Determine which client we're using
        client_name = client.__class__.__name__
        logger.debug(f"Using {client_name} for {url}")

        if client_name == "FirecrawlMCPClient":
            # Use Firecrawl client
            from tripsage.clients.webcrawl.firecrawl_mcp_client import (
                FirecrawlScrapeParams,
            )

            params = FirecrawlScrapeParams(
                formats=["markdown", "html"]
                if extract_structured_data
                else ["markdown"],
                actions=[],
                mobile=requires_javascript,  # Mobile view can help with JS content
            )

            raw_result = await client.scrape_url(
                url, params=params, use_cache=use_cache
            )
            primary_result = await normalizer.normalize_firecrawl_output(
                raw_result, url
            )

        elif client_name == "PlaywrightMCPClient":
            # Use Playwright directly (selected by source selector)
            from tripsage.tools.browser.playwright_mcp_client import (
                PlaywrightNavigateOptions,
            )

            # Navigate to the URL
            navigate_options = PlaywrightNavigateOptions(
                browser_type="chromium",
                headless=True,
                width=1280,
                height=720,
                timeout=30000,
                wait_until="networkidle",
            )

            navigation_result = await client.navigate(url, navigate_options)

            # Get the page content
            visible_text = await client.get_visible_text()
            visible_html = await client.get_visible_html()

            # Close the browser
            await client.close()

            # Create the raw output for normalizer
            playwright_output = {
                "visible_text": visible_text,
                "visible_html": visible_html,
                "title": navigation_result.get("title"),
                "browser_type": navigate_options.browser_type,
                "status": "success",
            }

            # Normalize the Playwright output
            primary_result = await normalizer.normalize_playwright_mcp_output(
                playwright_output, url
            )

        else:
            # Use Crawl4AI client
            from tripsage.clients.webcrawl.crawl4ai_mcp_client import (
                Crawl4AICrawlParams,
            )

            params = Crawl4AICrawlParams(
                javascript_enabled=requires_javascript,
                extract_markdown=True,
                extract_html=extract_structured_data,
                extract_structured_data=extract_structured_data,
            )

            raw_result = await client.crawl_url(url, params=params, use_cache=use_cache)
            primary_result = await normalizer.normalize_crawl4ai_output(raw_result, url)

    except Exception as e:
        logger.error(f"Primary crawl failed for {url}: {str(e)}")
        primary_result = UnifiedCrawlResult(
            url=url,
            status="error",
            error_message=str(e),
            metadata={
                "source_crawler": client.__class__.__name__.replace(
                    "MCPClient", ""
                ).lower(),
                "error_type": type(e).__name__,
            },
        )

    # Check if we need fallback to Playwright
    if enable_playwright_fallback and needs_fallback(primary_result):
        logger.info(
            f"Primary crawler failed/insufficient, falling back to Playwright "
            f"MCP for {url}"
        )

        try:
            from tripsage.tools.browser.playwright_mcp_client import (
                PlaywrightMCPClient,
                PlaywrightNavigateOptions,
            )

            # Create Playwright client
            playwright_client = PlaywrightMCPClient()

            # Navigate to the URL
            navigate_options = PlaywrightNavigateOptions(
                browser_type="chromium",
                headless=True,
                width=1280,
                height=720,
                timeout=30000,  # 30 seconds
                wait_until="networkidle",
            )

            navigation_result = await playwright_client.navigate(url, navigate_options)

            # Get the page content
            visible_text = await playwright_client.get_visible_text()
            visible_html = await playwright_client.get_visible_html()

            # Close the browser
            await playwright_client.close()

            # Create the raw output for normalizer
            playwright_output = {
                "visible_text": visible_text,
                "visible_html": visible_html,
                "title": navigation_result.get("title"),
                "browser_type": navigate_options.browser_type,
                "status": "success",
            }

            # Normalize the Playwright output
            playwright_result = await normalizer.normalize_playwright_mcp_output(
                playwright_output, url
            )

            # Add metadata about fallback
            playwright_result.metadata["fallback_from"] = primary_result.source_crawler
            playwright_result.metadata["fallback_reason"] = (
                primary_result.error_message or "insufficient_content"
            )

            return playwright_result

        except Exception as e:
            logger.error(f"Playwright fallback also failed for {url}: {str(e)}")
            # Return the original primary result with fallback error info
            primary_result.metadata["fallback_attempted"] = True
            primary_result.metadata["fallback_error"] = str(e)
            return primary_result

    # Return the primary result if no fallback needed or disabled
    return primary_result


@function_tool
@with_error_handling
async def crawl_travel_blog(
    url: str, extract_insights: bool = True, use_cache: bool = True
) -> UnifiedCrawlResult:
    """Crawl a travel blog with optimized settings for blog content.

    This is a convenience function that uses content_type="travel_blog"
    to ensure optimal crawler selection for blog content.

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


@function_tool
@with_error_handling
async def crawl_booking_site(
    url: str, extract_prices: bool = True, use_cache: bool = True
) -> UnifiedCrawlResult:
    """Crawl a booking site with optimized settings for price/availability data.

    This is a convenience function that uses content_type="booking"
    to ensure optimal crawler selection for booking sites.

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


@function_tool
@with_error_handling
async def crawl_event_listing(
    url: str, extract_dates: bool = True, use_cache: bool = True
) -> UnifiedCrawlResult:
    """Crawl an event listing with optimized settings for event data.

    This is a convenience function that uses content_type="events"
    to ensure optimal crawler selection for event sites.

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
