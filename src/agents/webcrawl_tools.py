"""
Web crawling tools for TripSage agents.

This module provides function tools for web crawling, search, and content extraction
using external MCP servers (Crawl4AI and Firecrawl).
"""

from typing import Any, Dict

from agents import function_tool

# Import models from tools directory for backward compatibility
from src.agents.tools.webcrawl.models import (
    BlogCrawlParams,
    EventSearchParams,
    ExtractContentParams,
    PriceMonitorParams,
    SearchDestinationParams,
)
from src.mcp.webcrawl.client import get_client as get_webcrawl_client
from src.utils.error_handling import log_exception
from src.utils.logging import get_logger

logger = get_logger(__name__)

# Get unified client instance
webcrawl_client = get_webcrawl_client()


@function_tool
async def extract_page_content_tool(params: ExtractContentParams) -> Dict[str, Any]:
    """Extract content from a webpage.

    This tool extracts content from a webpage using the appropriate web crawling source
    (Crawl4AI or Firecrawl) based on the content type and URL pattern.

    Args:
        params: Parameters for content extraction

    Returns:
        The extracted content
    """
    try:
        logger.info(f"Extracting content from: {params.url}")

        # Call the unified WebCrawlMCPClient
        result = await webcrawl_client.extract_page_content(
            url=params.url,
            selectors=[params.specific_selector] if params.specific_selector else None,
            include_images=params.extract_images,
            format="markdown",
        )

        # Handle persistence if needed
        # Note: In a future task, this would integrate with a persistence manager

        return result

    except Exception as e:
        logger.error(f"Error extracting content from {params.url}: {str(e)}")
        log_exception(e)
        return {
            "success": False,
            "url": params.url,
            "error": str(e),
            "formatted": f"Failed to extract content from {params.url}: {str(e)}",
        }


@function_tool
async def search_destination_info_tool(
    params: SearchDestinationParams,
) -> Dict[str, Any]:
    """Search for information about a travel destination.

    This tool searches for information about a travel destination using the appropriate
    web crawling source (Crawl4AI or Firecrawl).

    Args:
        params: Parameters for destination search

    Returns:
        The search results
    """
    try:
        query = f"{params.query} {params.destination}"
        logger.info(f"Searching for destination information: {query}")

        # Call the unified WebCrawlMCPClient
        result = await webcrawl_client.search_destination_info(
            destination=params.destination,
            topics=[params.query] if params.query else None,
            max_results=5,
            traveler_profile=None,
        )

        # Add destination to result for tracking
        if isinstance(result, dict) and "destination" not in result:
            result["destination"] = params.destination

        # Handle persistence if needed
        # Note: In a future task, this would integrate with a persistence manager

        return result

    except Exception as e:
        logger.error(f"Error searching for destination information: {str(e)}")
        log_exception(e)
        return {
            "success": False,
            "query": f"{params.query} {params.destination}",
            "error": str(e),
            "formatted": f"Failed to search for destination information: {str(e)}",
        }


@function_tool
async def monitor_price_changes_tool(params: PriceMonitorParams) -> Dict[str, Any]:
    """Monitor price changes for a travel product.

    This tool monitors price changes for a travel product (flight, hotel, etc.)
    using Firecrawl.

    Args:
        params: Parameters for price monitoring

    Returns:
        The price monitoring result
    """
    try:
        logger.info(f"Monitoring price changes for {params.product_type}: {params.url}")

        # Extract price selector
        price_selector = (
            next(iter(params.target_selectors.values()))
            if params.target_selectors
            else ".price"
        )

        # Call the unified WebCrawlMCPClient
        result = await webcrawl_client.monitor_price_changes(
            url=params.url,
            price_selector=price_selector,
            frequency=params.frequency,
            notification_threshold=5.0,  # Default threshold
        )

        # Add product type for categorization
        if isinstance(result, dict) and "product_type" not in result:
            result["product_type"] = params.product_type

        # Handle persistence if needed
        # Note: In a future task, this would integrate with a persistence manager

        return result

    except Exception as e:
        logger.error(f"Error monitoring price changes: {str(e)}")
        log_exception(e)
        return {
            "success": False,
            "url": params.url,
            "error": str(e),
            "formatted": f"Failed to monitor price changes for {params.url}: {str(e)}",
        }


@function_tool
async def get_latest_events_tool(params: EventSearchParams) -> Dict[str, Any]:
    """Get the latest events at a destination.

    This tool searches for events at a travel destination using Firecrawl.

    Args:
        params: Parameters for event search

    Returns:
        The events search result
    """
    try:
        logger.info(f"Getting events for destination: {params.destination}")

        # Call the unified WebCrawlMCPClient
        result = await webcrawl_client.get_latest_events(
            destination=params.destination,
            start_date=params.start_date or "",
            end_date=params.end_date or "",
            categories=[params.event_type] if params.event_type else None,
        )

        # Handle persistence if needed
        # Note: In a future task, this would integrate with a persistence manager

        return result

    except Exception as e:
        logger.error(f"Error getting events: {str(e)}")
        log_exception(e)
        return {
            "success": False,
            "destination": params.destination,
            "error": str(e),
            "formatted": f"Failed to get events for {params.destination}: {str(e)}",
        }


@function_tool
async def crawl_travel_blog_tool(params: BlogCrawlParams) -> Dict[str, Any]:
    """Crawl a travel blog and extract information.

    This tool crawls a travel blog and extracts information using the appropriate
    web crawling source (Crawl4AI or Firecrawl).

    Args:
        params: Parameters for blog crawling

    Returns:
        The blog crawl result
    """
    try:
        logger.info(f"Crawling travel blog: {params.url}")

        # Try to extract destination from URL or use a default
        destination = extract_destination_from_url(params.url)

        # Call the unified WebCrawlMCPClient
        result = await webcrawl_client.crawl_travel_blog(
            destination=destination,
            topics=[params.extract_type],
            max_blogs=params.max_pages,
            recent_only=True,
        )

        # Handle persistence if needed
        # Note: In a future task, this would integrate with a persistence manager

        return result

    except Exception as e:
        logger.error(f"Error crawling travel blog: {str(e)}")
        log_exception(e)
        return {
            "success": False,
            "url": params.url,
            "error": str(e),
            "formatted": f"Failed to crawl travel blog {params.url}: {str(e)}",
        }


@function_tool
async def search_web_tool(query: str, depth: str = "standard") -> Dict[str, Any]:
    """Search the web for information.

    This tool searches the web for information using the appropriate web crawling
    source (Crawl4AI or Firecrawl).

    Args:
        query: Search query
        depth: Search depth (standard or deep)

    Returns:
        The search results
    """
    try:
        logger.info(f"Searching web for: {query}")

        if depth == "deep":
            # Use deep research for comprehensive results
            result = await webcrawl_client.deep_research(
                query=query, max_depth=3, max_urls=10, time_limit=60
            )
        else:
            # Use regular search for standard results
            result = await webcrawl_client.search_destination_info(
                destination="", topics=[query], max_results=5
            )

        # Handle persistence if needed
        # Note: In a future task, this would integrate with a persistence manager

        return result

    except Exception as e:
        logger.error(f"Error searching web: {str(e)}")
        log_exception(e)
        return {
            "success": False,
            "query": query,
            "error": str(e),
            "formatted": f"Failed to search web for {query}: {str(e)}",
        }


def extract_destination_from_url(url: str) -> str:
    """Extract a destination name from a blog URL.

    Args:
        url: The URL to extract from

    Returns:
        The extracted destination or 'unknown' if not found
    """
    # Simple extraction based on URL patterns
    url_lower = url.lower()

    # List of common destinations to check for
    common_destinations = [
        "paris",
        "london",
        "tokyo",
        "new york",
        "rome",
        "sydney",
        "bali",
        "bangkok",
        "istanbul",
        "dubai",
        "singapore",
        "barcelona",
        "venice",
        "prague",
        "amsterdam",
        "athens",
        "hawaii",
        "kyoto",
        "cairo",
        "marrakech",
        "lisbon",
    ]

    # Check for destinations in URL
    for destination in common_destinations:
        if (
            destination.replace(" ", "-") in url_lower
            or destination.replace(" ", "") in url_lower
        ):
            return destination.title()

    # Default return
    return "unknown"
