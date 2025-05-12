"""Handler for the get_latest_events MCP tool."""

import datetime
from typing import Any, Dict, List, Optional

from src.mcp.webcrawl.config import Config
from src.mcp.webcrawl.sources.crawl4ai_source import Crawl4AISource
from src.mcp.webcrawl.sources.playwright_source import PlaywrightSource
from src.mcp.webcrawl.utils.result_normalizer import get_result_normalizer
from src.utils.logging import get_logger

# Initialize logger
logger = get_logger(__name__)

# Get the result normalizer
_normalizer = get_result_normalizer()


async def get_latest_events(
    destination: str,
    start_date: str,
    end_date: str,
    categories: Optional[List[str]] = None,
    source_type: str = "crawl4ai",
) -> Dict[str, Any]:
    """Find upcoming events at a destination during a specific time period.

    Args:
        destination: Name of the destination
        start_date: Start date in ISO format (YYYY-MM-DD)
        end_date: End date in ISO format (YYYY-MM-DD)
        categories: Optional list of event categories to filter by
        source_type: Type of source to use ("crawl4ai" or "playwright")

    Returns:
        Dict containing event listings with details

    Raises:
        Exception: If the event search fails
    """
    logger.info(
        f"Searching for events in {destination} from {start_date} to {end_date} using "
        f"{source_type}"
    )

    # Validate input
    if not destination:
        raise ValueError("Destination is required")

    if not start_date or not end_date:
        raise ValueError("Start date and end date are required")

    # Validate dates
    try:
        start = datetime.datetime.fromisoformat(start_date)
        end = datetime.datetime.fromisoformat(end_date)

        if start > end:
            raise ValueError("Start date must be before end date")

        # Don't allow searches more than 1 year in the future
        now = datetime.datetime.now()
        one_year_from_now = now + datetime.timedelta(days=365)

        if end > one_year_from_now:
            raise ValueError("End date cannot be more than 1 year in the future")
    except ValueError as e:
        raise ValueError(f"Invalid date format: {str(e)}") from e

    # Validate source_type
    if source_type not in ["crawl4ai", "playwright"]:
        logger.warning(f"Invalid source_type: {source_type}, defaulting to crawl4ai")
        source_type = "crawl4ai"

    try:
        # Initialize the selected source
        if source_type == "crawl4ai":
            source = Crawl4AISource()
            logger.info(f"Using Crawl4AI source for events in {destination}")
        else:  # playwright
            source = PlaywrightSource()
            logger.info(f"Using Playwright source for events in {destination}")

        # Get events using the selected source
        result = await source.get_latest_events(
            destination=destination,
            start_date=start_date,
            end_date=end_date,
            categories=categories,
        )

        # Store events in database or knowledge graph here
        # This would typically involve persisting the event data

        # Normalize and format response to MCP standard
        normalized_result = _normalizer.normalize_events_results(
            results=result, source_type=source_type
        )
        return _format_events_response(normalized_result)
    except Exception as e:
        logger.error(f"{source_type} events search failed for {destination}: {str(e)}")

        # Try fallback to the other source
        fallback_type = "playwright" if source_type == "crawl4ai" else "crawl4ai"
        try:
            logger.info(f"Trying {fallback_type} fallback for events in {destination}")

            if fallback_type == "crawl4ai":
                fallback_source = Crawl4AISource()
            else:
                fallback_source = PlaywrightSource()

            result = await fallback_source.get_latest_events(
                destination=destination,
                start_date=start_date,
                end_date=end_date,
                categories=categories,
            )

            # Normalize and format response from fallback
            normalized_result = _normalizer.normalize_events_results(
                results=result, source_type=fallback_type
            )
            return _format_events_response(normalized_result)
        except Exception as fallback_e:
            logger.error(
                f"Fallback {fallback_type} events search failed for {destination}: "
                f"{str(fallback_e)}"
            )
            raise Exception(
                f"All events search attempts failed for {destination}"
            ) from fallback_e


def _select_source(destination: str) -> Any:
    """Select the appropriate source based on destination characteristics.

    Args:
        destination: The destination to analyze

    Returns:
        The appropriate source
    """
    # Check if it's a city that typically needs browser automation for events
    is_dynamic_event_city = any(
        city.lower() in destination.lower() for city in Config.DYNAMIC_EVENT_CITIES
    )

    if is_dynamic_event_city:
        logger.info(f"Using Playwright for event search in {destination}")
        return PlaywrightSource()
    else:
        logger.info(f"Using Crawl4AI for event search in {destination}")
        return Crawl4AISource()


def _format_events_response(result: Dict[str, Any]) -> Dict[str, Any]:
    """Format events result to standard MCP response format.

    Args:
        result: The events result

    Returns:
        Formatted MCP response
    """
    # Process events to ensure consistent format
    events = []

    for event in result.get("events", []):
        # Normalize event data
        formatted_event = {
            "name": event.get("name", ""),
            "description": event.get("description", ""),
            "category": event.get("category", ""),
            "date": event.get("date", ""),
            "time": event.get("time", ""),
            "venue": event.get("venue", ""),
            "address": event.get("address", ""),
            "url": event.get("url", ""),
            "price_range": event.get("price_range", ""),
            "image_url": event.get("image_url", ""),
            "source": event.get("source", ""),
        }

        events.append(formatted_event)

    # Categorize events
    categories = {}
    for event in events:
        category = event.get("category", "").lower()
        if category:
            if category not in categories:
                categories[category] = 0
            categories[category] += 1

    return {
        "destination": result.get("destination", ""),
        "date_range": result.get("date_range", {"start_date": "", "end_date": ""}),
        "events": events,
        "event_count": len(events),
        "categories": categories,
        "sources": result.get("sources", []),
    }
