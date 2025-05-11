"""WebCrawl MCP client implementation."""

import logging
from typing import Any, Dict, List, Optional

from src.mcp.base_mcp_client import BaseMCPClient
from src.utils.logging import get_logger

# Initialize logger
logger = get_logger(__name__)


class WebCrawlMCPClient(BaseMCPClient):
    """Client for interacting with WebCrawl MCP Server.

    This client provides a high-level interface for agents to access
    web crawling functionality provided by the WebCrawl MCP Server.
    """

    def __init__(self):
        """Initialize the WebCrawl MCP client."""
        super().__init__("webcrawl")
        logger.info("WebCrawl MCP client initialized")

    async def extract_page_content(
        self,
        url: str,
        selectors: Optional[List[str]] = None,
        include_images: bool = False,
        format: str = "markdown",
    ) -> Dict[str, Any]:
        """Extract content from a webpage.

        Args:
            url: The URL of the webpage to extract content from
            selectors: Optional CSS selectors to target specific content
            include_images: Whether to include image URLs in the extracted content
            format: Format of the extracted content (markdown, text, html)

        Returns:
            The extracted content

        Raises:
            Exception: If the extraction fails
        """
        logger.info(f"Extracting content from {url}")

        try:
            # Prepare request parameters
            params = {
                "url": url,
                "selectors": selectors,
                "include_images": include_images,
                "format": format,
            }

            # Call MCP tool
            result = await self.call_tool("mcp__webcrawl__extract_page_content", params)

            # Check for errors
            if "error" in result:
                error = result["error"]
                error_message = error.get("message", "Unknown error")
                raise Exception(f"MCP error: {error_message}")

            # Return data
            return result.get("data", {})
        except Exception as e:
            logger.error(f"Error extracting content from {url}: {str(e)}")
            raise

    async def search_destination_info(
        self, destination: str, topics: Optional[List[str]] = None, max_results: int = 5
    ) -> Dict[str, Any]:
        """Search for specific information about a travel destination.

        Args:
            destination: Name of the destination (city, country, attraction)
            topics: Type of information to search for (e.g., "attractions", "local_customs")
            max_results: Maximum number of results to return per topic

        Returns:
            Dict containing extracted and structured information about the destination

        Raises:
            Exception: If the search fails
        """
        logger.info(f"Searching for information about {destination}")

        try:
            # Prepare request parameters
            params = {
                "destination": destination,
                "topics": topics,
                "max_results": max_results,
            }

            # Call MCP tool
            result = await self.call_tool(
                "mcp__webcrawl__search_destination_info", params
            )

            # Check for errors
            if "error" in result:
                error = result["error"]
                error_message = error.get("message", "Unknown error")
                raise Exception(f"MCP error: {error_message}")

            # Return data
            return result.get("data", {})
        except Exception as e:
            logger.error(
                f"Error searching destination info for {destination}: {str(e)}"
            )
            raise

    async def monitor_price_changes(
        self,
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

        try:
            # Prepare request parameters
            params = {
                "url": url,
                "price_selector": price_selector,
                "frequency": frequency,
                "notification_threshold": notification_threshold,
            }

            # Call MCP tool
            result = await self.call_tool(
                "mcp__webcrawl__monitor_price_changes", params
            )

            # Check for errors
            if "error" in result:
                error = result["error"]
                error_message = error.get("message", "Unknown error")
                raise Exception(f"MCP error: {error_message}")

            # Return data
            return result.get("data", {})
        except Exception as e:
            logger.error(f"Error setting up price monitoring for {url}: {str(e)}")
            raise

    async def get_latest_events(
        self,
        destination: str,
        start_date: str,
        end_date: str,
        categories: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Find upcoming events at a destination during a specific time period.

        Args:
            destination: Name of the destination
            start_date: Start date in ISO format (YYYY-MM-DD)
            end_date: End date in ISO format (YYYY-MM-DD)
            categories: Optional list of event categories to filter by

        Returns:
            Dict containing event listings with details

        Raises:
            Exception: If the event search fails
        """
        logger.info(
            f"Searching for events in {destination} from {start_date} to {end_date}"
        )

        try:
            # Prepare request parameters
            params = {
                "destination": destination,
                "start_date": start_date,
                "end_date": end_date,
                "categories": categories,
            }

            # Call MCP tool
            result = await self.call_tool("mcp__webcrawl__get_latest_events", params)

            # Check for errors
            if "error" in result:
                error = result["error"]
                error_message = error.get("message", "Unknown error")
                raise Exception(f"MCP error: {error_message}")

            # Return data
            return result.get("data", {})
        except Exception as e:
            logger.error(f"Error getting events for {destination}: {str(e)}")
            raise

    async def crawl_travel_blog(
        self,
        destination: str,
        topics: Optional[List[str]] = None,
        max_blogs: int = 3,
        recent_only: bool = True,
    ) -> Dict[str, Any]:
        """Extract travel insights and recommendations from travel blogs.

        Args:
            destination: Destination name (e.g., 'Paris, France')
            topics: Specific topics to extract (e.g., ['hidden gems', 'local tips'])
            max_blogs: Maximum number of blogs to crawl (default: 3)
            recent_only: Whether to only include blogs from the past year

        Returns:
            Dict containing extracted travel insights organized by topic

        Raises:
            Exception: If the blog crawling fails
        """
        logger.info(f"Crawling travel blogs for {destination}")

        try:
            # Prepare request parameters
            params = {
                "destination": destination,
                "topics": topics,
                "max_blogs": max_blogs,
                "recent_only": recent_only,
            }

            # Call MCP tool
            result = await self.call_tool("mcp__webcrawl__crawl_travel_blog", params)

            # Check for errors
            if "error" in result:
                error = result["error"]
                error_message = error.get("message", "Unknown error")
                raise Exception(f"MCP error: {error_message}")

            # Return data
            return result.get("data", {})
        except Exception as e:
            logger.error(f"Error crawling travel blogs for {destination}: {str(e)}")
            raise
