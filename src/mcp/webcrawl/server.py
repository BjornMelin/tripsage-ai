"""WebCrawl MCP server implementation."""

from typing import Any, Dict

from src.mcp.base_mcp_server import BaseMCPServer
from src.mcp.webcrawl.config import Config
from src.mcp.webcrawl.handlers import (
    crawl_travel_blog,
    extract_page_content,
    get_latest_events,
    monitor_price_changes,
    search_destination_info,
)
from src.mcp.webcrawl.sources.source_selector import get_source_selector
from src.mcp.webcrawl.storage.cache import CacheService
from src.mcp.webcrawl.storage.memory import KnowledgeGraphStorage
from src.mcp.webcrawl.storage.supabase import SupabaseStorage
from src.mcp.webcrawl.utils.rate_limiter import AdaptiveRateLimiter
from src.mcp.webcrawl.utils.response_formatter import format_error, format_response
from src.utils.logging import get_logger

# Initialize logger
logger = get_logger(__name__)


class WebCrawlMCPServer(BaseMCPServer):
    """MCP server for web crawling functionality."""

    def __init__(self):
        """Initialize the WebCrawl MCP server."""
        super().__init__("webcrawl")

        # Initialize services
        self.cache = CacheService()
        self.supabase = SupabaseStorage()
        self.knowledge_graph = KnowledgeGraphStorage()
        self.rate_limiter = AdaptiveRateLimiter()
        self.source_selector = get_source_selector()

        # Register MCP tools
        self.register_tools()

        logger.info("WebCrawl MCP server initialized with intelligent source selection")

    def register_tools(self) -> None:
        """Register all MCP tools with the server."""
        # Extract page content tool
        self.register_tool(
            name="mcp__webcrawl__extract_page_content",
            handler=self._extract_page_content_handler,
            schema={
                "url": {
                    "type": "string",
                    "description": "URL of the webpage to extract content from",
                },
                "selectors": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Optional CSS selectors to target specific content "
                        "(e.g., 'div.main-content')"
                    ),
                },
                "include_images": {
                    "type": "boolean",
                    "default": False,
                    "description": (
                        "Whether to include image URLs in the extracted content"
                    ),
                },
                "format": {
                    "type": "string",
                    "enum": ["markdown", "text", "html"],
                    "default": "markdown",
                    "description": "Format of the extracted content",
                },
            },
            required=["url"],
            description=(
                "Extract specific content from a single webpage using "
                "optional CSS selectors."
            ),
        )

        # Search destination info tool
        self.register_tool(
            name="mcp__webcrawl__search_destination_info",
            handler=self._search_destination_info_handler,
            schema={
                "destination": {
                    "type": "string",
                    "description": "Destination name (e.g., 'Paris, France')",
                },
                "topics": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Specific topics to search for (e.g., "
                        "['attractions', 'local cuisine', 'transportation'])"
                    ),
                },
                "max_results": {
                    "type": "integer",
                    "default": 5,
                    "description": "Maximum number of results to return per topic",
                },
                "traveler_profile": {
                    "type": "string",
                    "description": (
                        "Traveler profile for personalized results (e.g., "
                        "'family_focused', 'budget_traveler', 'luxury_experience', "
                        "'safety_first', 'cultural_immersion', 'adventure_seeker')"
                    ),
                },
            },
            required=["destination"],
            description="Search for specific information about a travel destination.",
        )

        # Monitor price changes tool
        self.register_tool(
            name="mcp__webcrawl__monitor_price_changes",
            handler=self._monitor_price_changes_handler,
            schema={
                "url": {
                    "type": "string",
                    "description": "URL of the webpage to monitor",
                },
                "price_selector": {
                    "type": "string",
                    "description": "CSS selector for the price element",
                },
                "frequency": {
                    "type": "string",
                    "enum": ["hourly", "daily", "weekly"],
                    "default": "daily",
                    "description": "How often to check for price changes",
                },
                "notification_threshold": {
                    "type": "number",
                    "default": 5,
                    "description": "Percentage change to trigger a notification",
                },
            },
            required=["url", "price_selector"],
            description=(
                "Set up monitoring for price changes on a specific travel webpage."
            ),
        )

        # Get latest events tool
        self.register_tool(
            name="mcp__webcrawl__get_latest_events",
            handler=self._get_latest_events_handler,
            schema={
                "destination": {
                    "type": "string",
                    "description": "Destination name (e.g., 'Paris, France')",
                },
                "start_date": {
                    "type": "string",
                    "description": "Start date in YYYY-MM-DD format",
                },
                "end_date": {
                    "type": "string",
                    "description": "End date in YYYY-MM-DD format",
                },
                "categories": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Event categories (e.g., ['music', 'festivals', 'sports'])"
                    ),
                },
            },
            required=["destination", "start_date", "end_date"],
            description=(
                "Find upcoming events at a destination during a specific time period."
            ),
        )

        # Crawl travel blog tool
        self.register_tool(
            name="mcp__webcrawl__crawl_travel_blog",
            handler=self._crawl_travel_blog_handler,
            schema={
                "destination": {
                    "type": "string",
                    "description": "Destination name (e.g., 'Paris, France')",
                },
                "topics": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Specific topics to extract (e.g., "
                        "['hidden gems', 'local tips', 'safety'])"
                    ),
                },
                "max_blogs": {
                    "type": "integer",
                    "default": 3,
                    "description": "Maximum number of blogs to crawl",
                },
                "recent_only": {
                    "type": "boolean",
                    "default": True,
                    "description": "Whether to only include blogs from the past year",
                },
            },
            required=["destination"],
            description=(
                "Extract travel insights and recommendations from travel blogs."
            ),
        )

    async def _extract_page_content_handler(
        self, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle extract_page_content MCP tool.

        Args:
            params: Tool parameters

        Returns:
            Extracted content
        """
        try:
            # Extract parameters
            url = params.get("url")
            selectors = params.get("selectors")
            include_images = params.get("include_images", False)
            format_type = params.get("format", "markdown")

            # Generate cache key
            from src.mcp.webcrawl.utils.url_validator import get_cache_key

            cache_key = f"extract:{get_cache_key(url)}:{format_type}"

            # Check cache
            cached_result = await self.cache.get(cache_key)
            if cached_result:
                logger.info(f"Cache hit for URL: {url}")
                return format_response(cached_result)

            # Get domain for rate limiting
            from src.mcp.webcrawl.utils.url_validator import extract_domain

            domain = extract_domain(url)

            # Apply rate limiting
            await self.rate_limiter.acquire(domain)

            try:
                # Use intelligent source selection
                source_type = self.source_selector.select_source_for_url(url)
                logger.info(f"Selected {source_type} source for URL: {url}")

                # Extract content
                result = await extract_page_content(
                    url=url,
                    selectors=selectors,
                    include_images=include_images,
                    format=format_type,
                    source_type=source_type,  # Pass the selected source type
                )

                # Store in cache with appropriate TTL
                ttl = self.cache.get_cache_ttl_for_url(url)
                await self.cache.set(cache_key, result, ttl)

                # Store in Supabase
                await self.supabase.store_page_content(
                    url=url,
                    title=result.get("title", ""),
                    content=result.get("content", ""),
                    metadata=result.get("metadata"),
                )

                # Store in knowledge graph
                await self.knowledge_graph.store_page_content(
                    url=url,
                    title=result.get("title", ""),
                    content=result.get("content", ""),
                    metadata=result.get("metadata"),
                )

                # Report successful request for adaptive rate
                # limiting and source selection
                self.rate_limiter.report_success(domain)
                self.source_selector.report_success(source_type, True)

                return format_response(result)
            except Exception as e:
                # Report failed request for adaptive rate limiting and source selection
                self.rate_limiter.report_failure(domain)

                # If we know which source was selected, report failure
                if "source_type" in locals():
                    self.source_selector.report_success(source_type, False)

                logger.error(
                    f"Error in extract_page_content with source "
                    f"{locals().get('source_type', 'unknown')}: {str(e)}"
                )
                raise

        except Exception as e:
            logger.error(f"Error in extract_page_content handler: {str(e)}")
            return format_error(str(e))

    async def _search_destination_info_handler(
        self, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle search_destination_info MCP tool.

        Args:
            params: Tool parameters

        Returns:
            Destination information
        """
        try:
            # Extract parameters
            destination = params.get("destination")
            topics = params.get("topics")
            max_results = params.get("max_results", 5)
            traveler_profile = params.get("traveler_profile")

            # Generate cache key
            topics_str = ",".join(sorted(topics)) if topics else "default"
            profile_str = f":{traveler_profile}" if traveler_profile else ""
            cache_key = f"search:{destination}:{topics_str}:{max_results}{profile_str}"

            # Check cache
            cached_result = await self.cache.get(cache_key)
            if cached_result:
                logger.info(f"Cache hit for destination search: {destination}")
                return format_response(cached_result)

            # Use intelligent source selection
            source_type = self.source_selector.select_source_for_destination(
                destination, "search"
            )
            logger.info(
                f"Selected {source_type} source for destination search: {destination}"
            )

            # Search for destination information
            result = await search_destination_info(
                destination=destination,
                topics=topics,
                max_results=max_results,
                source_type=source_type,  # Pass the selected source type
                traveler_profile=traveler_profile,  # Pass traveler profile
            )

            # Check if results indicate a fallback to WebSearchTool
            if (
                "fallback_type" in result
                and result["fallback_type"] == "websearch_tool"
            ):
                # Return the results with guidance to the client w/o reporting failure
                logger.info(f"Returning WebSearchTool guidance for {destination}")
                return format_response(result)

            # Store in cache
            await self.cache.set(cache_key, result, Config.CACHE_TTL_DESTINATION_INFO)

            # Store in Supabase
            await self.supabase.store_destination_info(
                destination=destination,
                topics=result.get("topics", {}),
                sources=result.get("sources", []),
            )

            # Store in knowledge graph
            await self.knowledge_graph.store_destination_info(
                destination=destination,
                topics=result.get("topics", {}),
                sources=result.get("sources", []),
            )

            # Report success for source selection
            self.source_selector.report_success(source_type, True)

            return format_response(result)

        except Exception as e:
            # Report failure for source selection if available
            if "source_type" in locals():
                self.source_selector.report_success(source_type, False)

            logger.error(
                f"Error in search_destination_info handler with source "
                f"{locals().get('source_type', 'unknown')}: {str(e)}"
            )
            return format_error(str(e))

    async def _monitor_price_changes_handler(
        self, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle monitor_price_changes MCP tool.

        Args:
            params: Tool parameters

        Returns:
            Price monitoring configuration
        """
        try:
            # Extract parameters
            url = params.get("url")
            price_selector = params.get("price_selector")
            frequency = params.get("frequency", "daily")
            notification_threshold = params.get("notification_threshold", 5)

            # Get domain for rate limiting
            from src.mcp.webcrawl.utils.url_validator import extract_domain

            domain = extract_domain(url)

            # Apply rate limiting
            await self.rate_limiter.acquire(domain)

            try:
                # Set up price monitoring
                result = await monitor_price_changes(
                    url=url,
                    price_selector=price_selector,
                    frequency=frequency,
                    notification_threshold=notification_threshold,
                )

                # Store in Supabase
                await self.supabase.create_price_monitor(
                    url=url,
                    price_selector=price_selector,
                    monitoring_id=result.get("monitoring_id", ""),
                    frequency=frequency,
                    notification_threshold=notification_threshold,
                    initial_price=result.get("initial_price"),
                )

                # Store in knowledge graph
                await self.knowledge_graph.store_price_monitor(
                    url=url,
                    price_selector=price_selector,
                    monitoring_id=result.get("monitoring_id", ""),
                    frequency=frequency,
                    initial_price=result.get("initial_price"),
                )

                # Report successful request for adaptive rate limiting
                self.rate_limiter.report_success(domain)

                return format_response(result)
            except Exception:
                # Report failed request for adaptive rate limiting
                self.rate_limiter.report_failure(domain)
                raise

        except Exception as e:
            logger.error(f"Error in monitor_price_changes handler: {str(e)}")
            return format_error(str(e))

    async def _get_latest_events_handler(
        self, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle get_latest_events MCP tool.

        Args:
            params: Tool parameters

        Returns:
            Event listings
        """
        try:
            # Extract parameters
            destination = params.get("destination")
            start_date = params.get("start_date")
            end_date = params.get("end_date")
            categories = params.get("categories")

            # Generate cache key

            categories_str = ",".join(sorted(categories)) if categories else "all"
            cache_key = f"events:{destination}:{start_date}:{end_date}:{categories_str}"

            # Check cache
            cached_result = await self.cache.get(cache_key)
            if cached_result:
                logger.info(f"Cache hit for events: {destination}")
                return format_response(cached_result)

            # Use intelligent source selection
            source_type = self.source_selector.select_source_for_destination(
                destination, "events"
            )
            logger.info(f"Selected {source_type} source for events in {destination}")

            # Get events
            result = await get_latest_events(
                destination=destination,
                start_date=start_date,
                end_date=end_date,
                categories=categories,
                source_type=source_type,  # Pass the selected source type
            )

            # Store in cache
            await self.cache.set(cache_key, result, Config.CACHE_TTL_EVENTS)

            # Store in Supabase
            await self.supabase.store_events(
                destination=destination,
                date_range=result.get("date_range", {}),
                events=result.get("events", []),
                sources=result.get("sources", []),
            )

            # Store in knowledge graph
            await self.knowledge_graph.store_events(
                destination=destination,
                date_range=result.get("date_range", {}),
                events=result.get("events", []),
            )

            # Report success for source selection
            self.source_selector.report_success(source_type, True)

            return format_response(result)

        except Exception as e:
            # Report failure for source selection if available
            if "source_type" in locals():
                self.source_selector.report_success(source_type, False)

            logger.error(
                f"Error in get_latest_events handler with source "
                f"{locals().get('source_type', 'unknown')}: {str(e)}"
            )
            return format_error(str(e))

    async def _crawl_travel_blog_handler(
        self, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle crawl_travel_blog MCP tool.

        Args:
            params: Tool parameters

        Returns:
            Blog insights
        """
        try:
            # Extract parameters
            destination = params.get("destination")
            topics = params.get("topics")
            max_blogs = params.get("max_blogs", 3)
            recent_only = params.get("recent_only", True)

            # Generate cache key

            topics_str = ",".join(sorted(topics)) if topics else "default"
            cache_key = f"blog:{destination}:{topics_str}:{max_blogs}:{recent_only}"

            # Check cache
            cached_result = await self.cache.get(cache_key)
            if cached_result:
                logger.info(f"Cache hit for blog crawl: {destination}")
                return format_response(cached_result)

            # Crawl travel blogs
            result = await crawl_travel_blog(
                destination=destination,
                topics=topics,
                max_blogs=max_blogs,
                recent_only=recent_only,
            )

            # Store in cache
            await self.cache.set(cache_key, result, Config.CACHE_TTL_BLOG)

            # Store in Supabase
            await self.supabase.store_blog_insights(
                destination=destination,
                topics=result.get("topics", {}),
                sources=result.get("sources", []),
            )

            # Store in knowledge graph
            await self.knowledge_graph.store_blog_insights(
                destination=destination,
                topics=result.get("topics", {}),
                sources=result.get("sources", []),
            )

            return format_response(result)

        except Exception as e:
            logger.error(f"Error in crawl_travel_blog handler: {str(e)}")
            return format_error(str(e))


# Singleton instance for the WebCrawl MCP server
_webcrawl_server = None


def get_webcrawl_server() -> WebCrawlMCPServer:
    """Get or create the WebCrawl MCP server instance.

    Returns:
        WebCrawl MCP server instance
    """
    global _webcrawl_server

    if _webcrawl_server is None:
        _webcrawl_server = WebCrawlMCPServer()

    return _webcrawl_server
