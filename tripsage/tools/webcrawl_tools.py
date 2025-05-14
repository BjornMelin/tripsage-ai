"""
Web crawling tools for TripSage agents.

This module provides function tools for web crawling, search, and content extraction
using external MCP servers (Crawl4AI and Firecrawl).
"""

from typing import Any, Dict

from agents import function_tool
from tripsage.tools.schemas.webcrawl import (
    BlogCrawlParams,
    EventSearchParams,
    ExtractContentParams,
    PriceMonitorParams,
    SearchDestinationParams,
)
from tripsage.tools.webcrawl.crawl4ai_client import Crawl4AIClient
from tripsage.tools.webcrawl.firecrawl_client import FirecrawlClient
from tripsage.tools.webcrawl.persistence import WebcrawlPersistenceManager
from tripsage.tools.webcrawl.result_normalizer import ResultNormalizer
from tripsage.tools.webcrawl.source_selector import SourceSelector
from tripsage.utils.client_utils import validate_and_call_mcp_tool
from tripsage.utils.logging import get_logger

logger = get_logger(__name__)

# Initialize components
source_selector = SourceSelector()
result_normalizer = ResultNormalizer()
crawl4ai_client = Crawl4AIClient()
firecrawl_client = FirecrawlClient()
persistence_manager = WebcrawlPersistenceManager()


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

        # Determine the appropriate source
        source = source_selector.select_source(
            url=params.url,
            content_type=params.content_type,
            full_page=params.full_page,
        )
        logger.debug(f"Selected source for extraction: {source.name}")

        # Call the appropriate client
        if source == source_selector.SourceType.CRAWL4AI:
            response = await validate_and_call_mcp_tool(
                endpoint=crawl4ai_client.endpoint,
                tool_name="scrape",
                params={
                    "url": params.url,
                    "formats": ["markdown"],
                    "includeTags": None,
                    "excludeTags": None,
                    "onlyMainContent": not params.full_page,
                    "waitFor": 5000 if params.full_page else 2000,
                },
                response_model=crawl4ai_client.ScrapeResponse,
                timeout=60.0,
                server_name="Crawl4AI MCP",
            )
            result = crawl4ai_client.process_scrape_response(response)
        else:
            response = await validate_and_call_mcp_tool(
                endpoint=firecrawl_client.endpoint,
                tool_name="firecrawl_scrape",
                params={
                    "url": params.url,
                    "formats": ["markdown", "links"]
                    + (["screenshot"] if params.extract_images else []),
                    "onlyMainContent": not params.full_page,
                    "mobile": False,
                    "includeTags": None,
                    "excludeTags": None,
                    "waitFor": 5000 if params.full_page else 2000,
                },
                response_model=firecrawl_client.ScrapeResponse,
                timeout=60.0,
                server_name="Firecrawl MCP",
            )
            result = firecrawl_client.process_scrape_response(response)

        # Normalize the result
        normalized_result = result_normalizer.normalize_scrape_result(
            result, source.name
        )

        # Handle persistence if needed
        await persistence_manager.store_extraction_result(normalized_result, params.url)

        return normalized_result

    except Exception as e:
        logger.error(f"Error extracting content from {params.url}: {str(e)}")
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

        # Determine if we need deep or standard search
        if params.search_depth == "deep":
            # Use Firecrawl for deep research
            response = await validate_and_call_mcp_tool(
                endpoint=firecrawl_client.endpoint,
                tool_name="firecrawl_deep_research",
                params={
                    "query": query,
                    "maxDepth": 3,
                    "maxUrls": 10,
                    "timeLimit": 120,
                },
                response_model=firecrawl_client.DeepResearchResponse,
                timeout=180.0,  # Longer timeout for deep research
                server_name="Firecrawl MCP",
            )
            result = firecrawl_client.process_deep_research_response(response)
        else:
            # Use Crawl4AI for standard search
            response = await validate_and_call_mcp_tool(
                endpoint=crawl4ai_client.endpoint,
                tool_name="search",
                params={
                    "query": query,
                    "limit": 5,
                    "scrapeOptions": {
                        "formats": ["markdown"],
                        "onlyMainContent": True,
                    },
                },
                response_model=crawl4ai_client.SearchResponse,
                timeout=60.0,
                server_name="Crawl4AI MCP",
            )
            result = crawl4ai_client.process_search_response(response)

        # Normalize the result
        normalized_result = result_normalizer.normalize_search_result(
            result, "FIRECRAWL" if params.search_depth == "deep" else "CRAWL4AI"
        )

        # Add destination to result for tracking
        if (
            isinstance(normalized_result, dict)
            and "destination" not in normalized_result
        ):
            normalized_result["destination"] = params.destination

        # Handle persistence if needed
        await persistence_manager.store_destination_search_result(
            normalized_result, params.destination, params.query
        )

        return normalized_result

    except Exception as e:
        logger.error(f"Error searching for destination information: {str(e)}")
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
        _price_selector = (
            next(iter(params.target_selectors.values()))
            if params.target_selectors
            else ".price, .Price, [data-testid='price'], .current-price"
        )

        # Use Firecrawl for price monitoring (Crawl4AI doesn't support this)
        response = await validate_and_call_mcp_tool(
            endpoint=firecrawl_client.endpoint,
            tool_name="firecrawl_extract",
            params={
                "urls": [params.url],
                "schema": {
                    "type": "object",
                    "properties": {
                        "price": {"type": "number"},
                        "currency": {"type": "string"},
                        "name": {"type": "string"},
                        "availability": {"type": "string"},
                    },
                    "required": ["price"],
                },
                "prompt": (
                    f"Extract the current price for this {params.product_type} listing."
                ),
                "systemPrompt": (
                    "Extract pricing information accurately. Return currency as a "
                    "3-letter code (USD, EUR, etc.)"
                ),
            },
            response_model=firecrawl_client.ExtractResponse,
            timeout=60.0,
            server_name="Firecrawl MCP",
        )
        result = firecrawl_client.process_extract_response(response)

        # Normalize the result
        normalized_result = result_normalizer.normalize_price_result(
            result, "FIRECRAWL"
        )

        # Add product type for categorization
        if (
            isinstance(normalized_result, dict)
            and "product_type" not in normalized_result
        ):
            normalized_result["product_type"] = params.product_type

        # Add frequency information
        if (
            isinstance(normalized_result, dict)
            and "monitoring" not in normalized_result
        ):
            normalized_result["monitoring"] = {
                "frequency": params.frequency,
                "started_at": result_normalizer.get_current_timestamp(),
                "last_checked": result_normalizer.get_current_timestamp(),
            }

        # Handle persistence if needed
        await persistence_manager.store_price_monitoring_result(
            normalized_result, params.url, params.product_type
        )

        return normalized_result

    except Exception as e:
        logger.error(f"Error monitoring price changes: {str(e)}")
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

        # Construct query based on parameters
        query_parts = [params.destination, "events"]
        if params.event_type:
            query_parts.append(params.event_type)
        if params.start_date:
            query_parts.append(f"from {params.start_date}")
        if params.end_date:
            query_parts.append(f"to {params.end_date}")

        query = " ".join(query_parts)

        # Use Firecrawl for event search with structured extraction
        response = await validate_and_call_mcp_tool(
            endpoint=firecrawl_client.endpoint,
            tool_name="firecrawl_extract",
            params={
                "urls": [f"https://www.google.com/search?q={query.replace(' ', '+')}"],
                "schema": {
                    "type": "object",
                    "properties": {
                        "events": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "date": {"type": "string"},
                                    "location": {"type": "string"},
                                    "description": {"type": "string"},
                                    "url": {"type": "string"},
                                    "category": {"type": "string"},
                                },
                                "required": ["name", "date"],
                            },
                        },
                    },
                    "required": ["events"],
                },
                "prompt": f"Extract events in {params.destination}"
                + (f" of type {params.event_type}" if params.event_type else "")
                + (f" from {params.start_date}" if params.start_date else "")
                + (f" to {params.end_date}" if params.end_date else ""),
                "enableWebSearch": True,
            },
            response_model=firecrawl_client.ExtractResponse,
            timeout=90.0,
            server_name="Firecrawl MCP",
        )
        result = firecrawl_client.process_extract_response(response)

        # Normalize the result
        normalized_result = result_normalizer.normalize_events_result(
            result, "FIRECRAWL"
        )

        # Add destination and date range information
        if isinstance(normalized_result, dict):
            normalized_result["destination"] = params.destination
            if params.start_date:
                normalized_result["start_date"] = params.start_date
            if params.end_date:
                normalized_result["end_date"] = params.end_date

        # Handle persistence if needed
        await persistence_manager.store_events_result(
            normalized_result,
            params.destination,
            params.event_type,
            params.start_date,
            params.end_date,
        )

        return normalized_result

    except Exception as e:
        logger.error(f"Error getting events: {str(e)}")
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

        # Determine the appropriate source
        source = source_selector.select_source(
            url=params.url,
            extraction_complexity="complex",  # Blog extraction is usually complex
        )

        if source == source_selector.SourceType.CRAWL4AI:
            response = await validate_and_call_mcp_tool(
                endpoint=crawl4ai_client.endpoint,
                tool_name="scrape",
                params={
                    "url": params.url,
                    "formats": ["markdown"],
                    "onlyMainContent": True,
                },
                response_model=crawl4ai_client.ScrapeResponse,
                timeout=60.0,
                server_name="Crawl4AI MCP",
            )
            result = crawl4ai_client.process_blog_scrape(
                response, extract_type=params.extract_type
            )
        else:
            # Use Firecrawl with extraction
            response = await validate_and_call_mcp_tool(
                endpoint=firecrawl_client.endpoint,
                tool_name="firecrawl_extract",
                params={
                    "urls": [params.url],
                    "schema": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "author": {"type": "string"},
                            "date": {"type": "string"},
                            "destinations": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "highlights": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "itinerary": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "day": {"type": "string"},
                                        "activities": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                        },
                                        "location": {"type": "string"},
                                    },
                                },
                            },
                            "tips": {"type": "array", "items": {"type": "string"}},
                            "summary": {"type": "string"},
                        },
                        "required": ["title", "destinations"],
                    },
                    "prompt": (
                        f"Extract {params.extract_type} from this travel blog about "
                        f"{destination}."
                    ),
                },
                response_model=firecrawl_client.ExtractResponse,
                timeout=60.0,
                server_name="Firecrawl MCP",
            )
            result = firecrawl_client.process_extract_response(response)

        # Normalize the result
        normalized_result = result_normalizer.normalize_blog_result(
            result, source.name, extract_type=params.extract_type
        )

        # Add additional metadata
        if isinstance(normalized_result, dict):
            normalized_result["url"] = params.url
            normalized_result["destination"] = destination
            normalized_result["extract_type"] = params.extract_type

        # Handle persistence if needed
        await persistence_manager.store_blog_result(
            normalized_result, params.url, destination, params.extract_type
        )

        return normalized_result

    except Exception as e:
        logger.error(f"Error crawling travel blog: {str(e)}")
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
            # Use Firecrawl for deep research
            response = await validate_and_call_mcp_tool(
                endpoint=firecrawl_client.endpoint,
                tool_name="firecrawl_deep_research",
                params={
                    "query": query,
                    "maxDepth": 3,
                    "maxUrls": 10,
                    "timeLimit": 90,
                },
                response_model=firecrawl_client.DeepResearchResponse,
                timeout=120.0,  # Longer timeout for deep research
                server_name="Firecrawl MCP",
            )
            result = firecrawl_client.process_deep_research_response(response)
        else:
            # Use Crawl4AI for standard search
            response = await validate_and_call_mcp_tool(
                endpoint=crawl4ai_client.endpoint,
                tool_name="search",
                params={
                    "query": query,
                    "limit": 5,
                    "scrapeOptions": {
                        "formats": ["markdown"],
                        "onlyMainContent": True,
                    },
                },
                response_model=crawl4ai_client.SearchResponse,
                timeout=60.0,
                server_name="Crawl4AI MCP",
            )
            result = crawl4ai_client.process_search_response(response)

        # Normalize the result
        normalized_result = result_normalizer.normalize_search_result(
            result, "FIRECRAWL" if depth == "deep" else "CRAWL4AI"
        )

        # Add query information
        if isinstance(normalized_result, dict) and "query" not in normalized_result:
            normalized_result["query"] = query

        # Handle persistence if needed
        await persistence_manager.store_web_search_result(normalized_result, query)

        return normalized_result

    except Exception as e:
        logger.error(f"Error searching web: {str(e)}")
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
