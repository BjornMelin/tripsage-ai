"""WebCrawl MCP client implementation.

This module provides a client for interacting with the WebCrawl MCP Server,
with proper Pydantic v2 validation for parameters and responses.
"""

from typing import Any, Dict, Generic, List, Optional, TypeVar, cast

from pydantic import ValidationError

from src.mcp.base_mcp_client import BaseMCPClient
from src.mcp.webcrawl.models import (
    BaseParams,
    BaseResponse,
    DeepResearchParams,
    DeepResearchResponse,
    ScrapeParams,
    ScrapeResponse,
    SearchParams,
    SearchResponse,
)
from src.utils.logging import get_logger

# Initialize logger
logger = get_logger(__name__)

# Type vars for generic parameter and response types
P = TypeVar("P", bound=BaseParams)
R = TypeVar("R", bound=BaseResponse)


class MCPError(Exception):
    """Exception raised for MCP client errors."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """Initialize MCPError with a message and optional details."""
        self.message = message
        self.details = details or {}
        super().__init__(message)


class WebCrawlMCPClient(BaseMCPClient, Generic[P, R]):
    """Client for interacting with WebCrawl MCP Server.

    This client provides a high-level interface for agents to access
    web crawling functionality provided by the WebCrawl MCP Server,
    with proper Pydantic v2 validation for parameters and responses.
    """

    def __init__(self):
        """Initialize the WebCrawl MCP client."""
        super().__init__("webcrawl")
        logger.info("WebCrawl MCP client initialized")

    async def _call_validate_tool(
        self,
        tool_name: str,
        params: P,
        response_model: type[R],
        skip_cache: bool = False,
        cache_key: Optional[str] = None,
        cache_ttl: Optional[int] = None,
    ) -> R:
        """Call a tool and validate both parameters and response.

        Args:
            tool_name: Name of the MCP tool to call
            params: Pydantic model with validated parameters
            response_model: Pydantic model class for response validation
            skip_cache: Whether to skip cache for this call
            cache_key: Optional custom cache key
            cache_ttl: Optional custom cache TTL in seconds

        Returns:
            Validated response object

        Raises:
            MCPError: If parameter validation or the call fails
        """
        try:
            # Convert parameters to dict using model_dump() for Pydantic v2
            params_dict = (
                params.model_dump(exclude_none=True)
                if hasattr(params, "model_dump")
                else params
            )

            # Call the tool
            response = await self.call_tool(
                tool_name,
                params_dict,
                skip_cache=skip_cache,
                cache_key=cache_key,
                cache_ttl=cache_ttl,
            )

            # Check for errors in response
            if response and isinstance(response, dict) and "error" in response:
                error = response["error"]
                error_message = error.get("message", "Unknown error")

                # If there's WebSearchTool guidance included, don't raise an exception
                # but pass through the guidance for the agent to use
                if "data" in response and "websearch_tool_guidance" in response.get(
                    "data", {}
                ):
                    logger.info(
                        "WebCrawl extraction failed but structured guidance provided"
                    )
                    # Still try to validate the response
                    try:
                        return response_model.model_validate(response)
                    except ValidationError:
                        # Return the raw response if validation fails
                        return cast(R, response)

                raise MCPError(f"MCP error: {error_message}", details=response)

            try:
                # Validate response using model_validate for Pydantic v2
                validated_response = response_model.model_validate(response)
                return validated_response
            except ValidationError as e:
                logger.warning(f"Response validation failed for {tool_name}: {str(e)}")
                # Return the raw response if validation fails
                # This is to ensure backward compatibility
                return cast(R, response)
        except ValidationError as e:
            logger.error(f"Parameter validation failed for {tool_name}: {str(e)}")
            raise MCPError(
                f"Invalid parameters for {tool_name}: {str(e)}",
                details={"validation_error": str(e)},
            ) from e
        except Exception as e:
            logger.error(f"Error calling {tool_name}: {str(e)}")
            raise MCPError(f"Error calling {tool_name}: {str(e)}") from e

    async def extract_page_content(
        self,
        url: str,
        selectors: Optional[List[str]] = None,
        include_images: bool = False,
        format: str = "markdown",
    ) -> ScrapeResponse:
        """Extract content from a webpage.

        Args:
            url: The URL of the webpage to extract content from
            selectors: Optional CSS selectors to target specific content
            include_images: Whether to include image URLs in the extracted content
            format: Format of the extracted content (markdown, text, html)

        Returns:
            The extracted content in the requested format

        Raises:
            MCPError: If the extraction fails
        """
        logger.info(f"Extracting content from {url}")

        try:
            # Create and validate parameters model
            params = ScrapeParams(
                url=url,
                formats=[format],
                includeTags=selectors,
                removeBase64Images=not include_images,
            )

            # Call with validation
            response = await self._call_validate_tool(
                "mcp__webcrawl__firecrawl_scrape", params, ScrapeResponse
            )

            return response
        except ValidationError as e:
            logger.error(f"Validation error in extract_page_content: {str(e)}")
            raise MCPError(f"Invalid parameters: {str(e)}") from e
        except Exception as e:
            logger.error(f"Error extracting content from {url}: {str(e)}")
            raise

    async def search_destination_info(
        self,
        destination: str,
        topics: Optional[List[str]] = None,
        max_results: int = 5,
        traveler_profile: Optional[str] = None,
    ) -> SearchResponse:
        """Search for specific information about a travel destination.

        Args:
            destination: Name of the destination (city, country, attraction)
            topics: Type of information to search for (e.g.,
                   "attractions", "local_customs")
            max_results: Maximum number of results to return per topic
            traveler_profile: Optional traveler profile for personalized results

        Returns:
            Dict containing extracted and structured information about the destination

        Raises:
            MCPError: If the search fails
        """
        logger.info(f"Searching for information about {destination}")

        try:
            # Construct the search query based on parameters
            query = destination
            if topics:
                query += " " + " ".join(topics)
            if traveler_profile:
                query += f" for {traveler_profile}"

            # Create and validate parameters model
            params = SearchParams(query=query, limit=max_results)

            # Call with validation
            response = await self._call_validate_tool(
                "mcp__webcrawl__firecrawl_search", params, SearchResponse
            )

            return response
        except ValidationError as e:
            logger.error(f"Validation error in search_destination_info: {str(e)}")
            raise MCPError(f"Invalid parameters: {str(e)}") from e
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
            MCPError: If the monitoring setup fails
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
                raise MCPError(f"MCP error: {error_message}")

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
            MCPError: If the event search fails
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
                raise MCPError(f"MCP error: {error_message}")

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
            MCPError: If the blog crawling fails
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
                raise MCPError(f"MCP error: {error_message}")

            # Return data
            return result.get("data", {})
        except Exception as e:
            logger.error(f"Error crawling travel blogs for {destination}: {str(e)}")
            raise

    async def deep_research(
        self,
        query: str,
        max_depth: int = 3,
        max_urls: int = 20,
        time_limit: int = 120,
    ) -> DeepResearchResponse:
        """Conduct deep research on a travel-related query using
        web crawling and AI analysis.

        Args:
            query: The research query
            max_depth: Maximum depth of research iterations (1-10)
            max_urls: Maximum number of URLs to analyze (1-1000)
            time_limit: Time limit in seconds (30-300)

        Returns:
            Research results with summary, sources, and insights

        Raises:
            MCPError: If the research fails
        """
        logger.info(f"Conducting deep research on: {query}")

        try:
            # Create and validate parameters model
            params = DeepResearchParams(
                query=query,
                maxDepth=max_depth,
                maxUrls=max_urls,
                timeLimit=time_limit,
            )

            # Call with validation
            response = await self._call_validate_tool(
                "mcp__webcrawl__firecrawl_deep_research", params, DeepResearchResponse
            )

            return response
        except ValidationError as e:
            logger.error(f"Validation error in deep_research: {str(e)}")
            raise MCPError(f"Invalid parameters: {str(e)}") from e
        except Exception as e:
            logger.error(f"Error conducting research for query '{query}': {str(e)}")
            raise
