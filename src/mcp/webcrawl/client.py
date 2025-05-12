"""
WebCrawl MCP client for the TripSage travel planning system.

This client provides access to web crawling capabilities through external MCPs
(Crawl4AI and Firecrawl) rather than implementing a custom server.
"""

from typing import Any, Dict, List, Optional, Type, TypeVar

from pydantic import BaseModel, ValidationError

from src.mcp.base_mcp_client import BaseMCPClient
from src.mcp.webcrawl.models import (
    DeepResearchParams,
    DeepResearchResponse,
    ScrapeOptions,
    ScrapeParams,
    ScrapeResponse,
    SearchParams,
    SearchResponse,
)
from src.utils.config import AppSettings
from src.utils.error_handling import MCPError
from src.utils.logging import get_logger

logger = get_logger(__name__)

# Create a generic type variable for Pydantic models
T = TypeVar("T", bound=BaseModel)


class WebCrawlMCPClient(BaseMCPClient):
    """
    Client for web crawling capabilities leveraging external MCPs.

    This client implements the TripSage web crawling interface, but delegates
    the actual crawling to external MCPs (Crawl4AI and Firecrawl) rather than
    using a custom server implementation.
    """

    def __init__(self):
        """Initialize the WebCrawl MCP client."""
        self.settings = AppSettings()

        # Initialize BaseMCPClient with default settings
        super().__init__(
            endpoint=self.settings.webcrawl_mcp.firecrawl_api_url,
            api_key=(
                self.settings.webcrawl_mcp.firecrawl_api_key.get_secret_value()
                if self.settings.webcrawl_mcp.firecrawl_api_key
                else None
            ),
        )

        # Crawl4AI configuration
        self.crawl4ai_api_key = (
            self.settings.webcrawl_mcp.crawl4ai_api_key.get_secret_value()
            if self.settings.webcrawl_mcp.crawl4ai_api_key
            else None
        )
        self.crawl4ai_api_url = self.settings.webcrawl_mcp.crawl4ai_api_url

        # Firecrawl configuration
        self.firecrawl_api_key = (
            self.settings.webcrawl_mcp.firecrawl_api_key.get_secret_value()
            if self.settings.webcrawl_mcp.firecrawl_api_key
            else None
        )
        self.firecrawl_api_url = self.settings.webcrawl_mcp.firecrawl_api_url

        # Default source selection (firecrawl preferred for most travel content)
        self.default_source = "firecrawl"

        logger.info("Initialized WebCrawl MCP client using external MCPs")

    async def _call_validate_tool(
        self,
        tool_name: str,
        params: BaseModel,
        response_model: Type[T],
        skip_cache: bool = False,
        cache_key: Optional[str] = None,
        cache_ttl: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Call an MCP tool with validation of parameters and response.

        Args:
            tool_name: Name of the tool to call
            params: Parameters for the tool as a Pydantic model
            response_model: Expected response model type
            skip_cache: Whether to skip cache lookup
            cache_key: Optional cache key to use
            cache_ttl: Optional cache TTL in seconds

        Returns:
            Response data as a dictionary

        Raises:
            MCPError: If the call fails or validation fails
        """
        try:
            params_dict = params.model_dump()
            response = await self.call_tool(
                tool_name,
                params_dict,
                skip_cache=skip_cache,
                cache_key=cache_key,
                cache_ttl=cache_ttl,
            )

            # Validate response with the expected model
            # Just check if it would validate, but return the original dict
            response_model.model_validate(response)
            return response

        except ValidationError as e:
            logger.error(f"Validation error in {tool_name}: {str(e)}")
            raise MCPError(f"Invalid parameters for {tool_name}: {str(e)}") from e
        except Exception as e:
            logger.error(f"Error in {tool_name}: {str(e)}")
            raise MCPError(f"MCP error: {str(e)}") from e

    async def extract_page_content(
        self,
        url: str,
        selectors: Optional[List[str]] = None,
        include_images: bool = False,
        format: str = "markdown",
    ) -> Dict[str, Any]:
        """
        Extract content from a webpage.

        Args:
            url: URL to extract content from
            selectors: CSS selectors to target specific content
            include_images: Whether to include images
            format: Output format (markdown, html)

        Returns:
            Extracted content

        Raises:
            MCPError: If extraction fails
        """
        logger.info(f"Extracting content from {url}")

        # Prepare parameters
        formats = [format]
        if include_images:
            formats.append("screenshot")

        params = {
            "url": url,
            "formats": formats,
            "removeBase64Images": not include_images,
        }

        if selectors:
            params["includeTags"] = selectors

        try:
            return await self._call_validate_tool(
                "mcp__webcrawl__firecrawl_scrape",
                ScrapeParams(
                    url=url,
                    options=ScrapeOptions(
                        css_selector=",".join(selectors) if selectors else None,
                        include_screenshots=include_images,
                        full_page=False,
                    ),
                ),
                ScrapeResponse,
            )
        except Exception as e:
            raise MCPError(f"Failed to extract page content: {str(e)}") from e

    async def search_destination_info(
        self,
        destination: str,
        topics: Optional[List[str]] = None,
        max_results: int = 5,
        traveler_profile: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Search for information about a travel destination.

        Args:
            destination: The destination to search for
            topics: Specific topics to research
            max_results: Maximum number of results to return
            traveler_profile: Traveler profile to tailor results

        Returns:
            Search results related to the destination

        Raises:
            MCPError: If search fails
        """
        logger.info(f"Searching for information about {destination}")

        # Construct search query
        topics_str = " ".join(topics) if topics else ""
        profile_str = f" for {traveler_profile}" if traveler_profile else ""
        query = f"{destination} {topics_str}{profile_str}".strip()

        # Set up search parameters
        params = SearchParams(query=query, limit=max_results)

        try:
            return await self._call_validate_tool(
                "mcp__webcrawl__firecrawl_search", params, SearchResponse
            )
        except Exception as e:
            raise MCPError(f"Failed to search destination info: {str(e)}") from e

    async def deep_research(
        self, query: str, max_depth: int = 3, max_urls: int = 10, time_limit: int = 60
    ) -> Dict[str, Any]:
        """
        Conduct deep research on a travel-related topic.

        Args:
            query: Research query
            max_depth: Maximum research depth
            max_urls: Maximum URLs to analyze
            time_limit: Time limit in seconds

        Returns:
            Detailed research results

        Raises:
            MCPError: If research fails
        """
        logger.info(f"Conducting deep research on: {query}")

        _params = {
            "query": query,
            "maxDepth": max_depth,
            "maxUrls": max_urls,
            "timeLimit": time_limit,
        }

        try:
            return await self._call_validate_tool(
                "mcp__webcrawl__firecrawl_deep_research",
                DeepResearchParams(
                    query=query,
                    max_depth=max_depth,
                    max_urls=max_urls,
                    time_limit=time_limit,
                ),
                DeepResearchResponse,
            )
        except Exception as e:
            raise MCPError(f"Failed to conduct deep research: {str(e)}") from e

    async def monitor_price_changes(
        self,
        url: str,
        price_selector: str,
        frequency: str = "daily",
        notification_threshold: float = 5.0,
    ) -> Dict[str, Any]:
        """
        Set up monitoring for price changes on a URL.

        Args:
            url: URL to monitor
            price_selector: CSS selector for the price element
            frequency: Monitoring frequency (hourly, daily, weekly)
            notification_threshold: Percentage change threshold for notifications

        Returns:
            Monitoring configuration details

        Raises:
            MCPError: If monitoring setup fails
        """
        logger.info(f"Setting up price monitoring for {url}")

        params = {
            "url": url,
            "price_selector": price_selector,
            "frequency": frequency,
            "notification_threshold": notification_threshold,
        }

        try:
            return await self._call_validate_tool(
                "mcp__webcrawl__monitor_price_changes",
                BaseModel.model_validate(params),
                BaseModel,
            )
        except Exception as e:
            raise MCPError(f"Failed to set up price monitoring: {str(e)}") from e

    async def get_latest_events(
        self,
        destination: str,
        start_date: str,
        end_date: str,
        categories: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Get latest events at a destination.

        Args:
            destination: Location to get events for
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            categories: Event categories to include

        Returns:
            List of events at the destination

        Raises:
            MCPError: If event retrieval fails
        """
        logger.info(f"Getting events in {destination} from {start_date} to {end_date}")

        params = {
            "destination": destination,
            "start_date": start_date,
            "end_date": end_date,
            "categories": categories or [],
        }

        try:
            return await self._call_validate_tool(
                "mcp__webcrawl__get_latest_events",
                BaseModel.model_validate(params),
                BaseModel,
            )
        except Exception as e:
            raise MCPError(f"Failed to get latest events: {str(e)}") from e

    async def crawl_travel_blog(
        self,
        destination: str,
        topics: List[str],
        max_blogs: int = 3,
        recent_only: bool = True,
    ) -> Dict[str, Any]:
        """
        Crawl travel blogs for insights about a destination.

        Args:
            destination: Destination to research
            topics: Specific topics to look for
            max_blogs: Maximum number of blogs to analyze
            recent_only: Whether to only include recent blogs

        Returns:
            Travel insights extracted from blogs

        Raises:
            MCPError: If blog crawling fails
        """
        logger.info(f"Crawling travel blogs about {destination}")

        params = {
            "destination": destination,
            "topics": topics,
            "max_blogs": max_blogs,
            "recent_only": recent_only,
        }

        try:
            return await self._call_validate_tool(
                "mcp__webcrawl__crawl_travel_blog",
                BaseModel.model_validate(params),
                BaseModel,
            )
        except Exception as e:
            raise MCPError(f"Failed to crawl travel blogs: {str(e)}") from e

    def _select_source(self, url: str, options: ScrapeOptions) -> str:
        """
        Select the appropriate source for web crawling.

        Args:
            url: The URL to crawl
            options: Scrape options

        Returns:
            The selected source ("crawl4ai" or "firecrawl")
        """
        # Simple domain-based selection rules
        crawl4ai_domains = {
            "tripadvisor.com",
            "wikitravel.org",
            "wikipedia.org",
            "lonelyplanet.com",
            "travel.state.gov",
            "flyertalk.com",
        }

        firecrawl_domains = {
            "airbnb.com",
            "booking.com",
            "expedia.com",
            "hotels.com",
            "kayak.com",
            "trip.com",
            "eventbrite.com",
            "timeout.com",
        }

        # Extract domain from URL
        domain = self._extract_domain(url)

        # Check domain-specific optimization
        if domain:
            if domain in crawl4ai_domains:
                return "crawl4ai"
            elif domain in firecrawl_domains:
                return "firecrawl"

        # Consider content requirements
        if options.js_enabled or options.full_page:
            return "firecrawl"  # Firecrawl handles JS better

        # Default source
        return self.default_source

    def _extract_domain(self, url: str) -> Optional[str]:
        """
        Extract the domain from a URL.

        Args:
            url: The URL to extract from

        Returns:
            The domain or None if not found
        """
        parts = url.split("/")
        if len(parts) >= 3:
            domain = parts[2].split(":")[0]  # Remove port if present
            domain = domain.removeprefix("www.")  # Remove www prefix
            return domain
        return None


# Create singleton instance
webcrawl_client = WebCrawlMCPClient()


def get_client() -> WebCrawlMCPClient:
    """Get a configured WebCrawl MCP client.

    Returns:
        A configured WebCrawl MCP client
    """
    return webcrawl_client
