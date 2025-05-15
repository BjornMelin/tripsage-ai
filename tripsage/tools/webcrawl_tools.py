"""Unified web crawling tools for TripSage agents.

Provides a unified interface for web crawling operations using either
Crawl4AI or Firecrawl MCP clients based on intelligent source selection.
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
) -> UnifiedCrawlResult:
    """Crawl a website using the most appropriate MCP client.

    This unified tool automatically selects between Crawl4AI and Firecrawl
    based on the URL domain, content type, and extraction requirements.

    Args:
        url: The URL to crawl
        extract_structured_data: Whether to extract structured data (JSON-LD, etc.)
        content_type: Type of content being extracted (e.g., "booking", "travel_blog")
        requires_javascript: Whether the page requires JavaScript execution
        use_cache: Whether to use cached results if available

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
            return await normalizer.normalize_firecrawl_output(raw_result, url)

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
            return await normalizer.normalize_crawl4ai_output(raw_result, url)

    except Exception as e:
        logger.error(f"Error crawling {url}: {str(e)}")
        return UnifiedCrawlResult(
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
