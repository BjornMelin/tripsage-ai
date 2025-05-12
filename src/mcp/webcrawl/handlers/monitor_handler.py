"""Handler for the monitor_price_changes MCP tool."""

from typing import Any, Dict

from src.mcp.webcrawl.config import Config
from src.mcp.webcrawl.sources.crawl4ai_source import Crawl4AISource
from src.mcp.webcrawl.sources.playwright_source import PlaywrightSource
from src.mcp.webcrawl.sources.source_interface import MonitorOptions
from src.utils.logging import get_logger

# Initialize logger
logger = get_logger(__name__)


async def monitor_price_changes(
    url: str,
    price_selector: str,
    frequency: str = "daily",
    notification_threshold: float = 5.0,
) -> Dict[str, Any]:
    """Set up monitoring for price changes on a specific travel webpage.

    Args:
        url: The full URL of the webpage to monitor
        price_selector: CSS selector for the price element
        frequency: How often to check for changes ("hourly", "daily", "weekly")
        notification_threshold: Percentage change to trigger a notification

    Returns:
        Dict containing monitoring configuration and initial price

    Raises:
        Exception: If the monitoring setup fails
    """
    logger.info(f"Setting up price monitoring for {url}")

    # Validate input
    if not url:
        raise ValueError("URL is required")

    if not price_selector:
        raise ValueError("Price selector is required")

    if frequency not in ["hourly", "daily", "weekly"]:
        raise ValueError(
            f"Invalid frequency: {frequency}. Must be one of: hourly, daily, weekly"
        )

    if notification_threshold <= 0:
        raise ValueError(
            f"Invalid notification threshold: {notification_threshold}. "
            f"Must be greater than 0"
        )

    # Prepare monitoring options
    options: MonitorOptions = {
        "frequency": frequency,
        "notification_threshold": notification_threshold,
    }

    # Select appropriate source based on URL characteristics
    source = _select_source(url)

    try:
        # Set up price monitoring using the selected source
        result = await source.monitor_price_changes(url, price_selector, options)

        # Save monitoring configuration to database here
        # This would typically involve storing the monitoring_id, URL, selector,
        # and other details

        # Format response to MCP standard
        return _format_monitor_response(result)
    except Exception as e:
        logger.error(f"Error setting up price monitoring for {url}: {str(e)}")
        raise


def _select_source(url: str) -> Any:
    """Select the appropriate source based on URL characteristics.

    Args:
        url: The URL to analyze

    Returns:
        The appropriate source
    """
    # Check if URL requires browser interaction
    requires_interaction = False

    # Sites that require authentication
    if any(auth_site in url for auth_site in Config.AUTH_SITES):
        requires_interaction = True

    # Interactive sites
    if any(interactive_site in url for interactive_site in Config.INTERACTIVE_SITES):
        requires_interaction = True

    # Choose source based on requirements
    if requires_interaction:
        logger.info(f"Using Playwright for interactive price monitoring on {url}")
        return PlaywrightSource()
    else:
        logger.info(f"Using Crawl4AI for price monitoring on {url}")
        return Crawl4AISource()


def _format_monitor_response(result: Dict[str, Any]) -> Dict[str, Any]:
    """Format monitoring result to standard MCP response format.

    Args:
        result: The monitoring result

    Returns:
        Formatted MCP response
    """
    # Format initial price
    initial_price = None
    if "initial_price" in result and result["initial_price"]:
        initial_price = {
            "amount": result["initial_price"].get("amount"),
            "currency": result["initial_price"].get("currency"),
            "timestamp": result["initial_price"].get("timestamp"),
        }

    return {
        "url": result.get("url", ""),
        "price_selector": result.get("price_selector", ""),
        "monitoring_id": result.get("monitoring_id", ""),
        "initial_price": initial_price,
        "status": result.get("status", "scheduled"),
        "frequency": result.get("frequency", "daily"),
        "notification_threshold": result.get("notification_threshold", 5.0),
        "next_check": result.get("next_check", ""),
    }
