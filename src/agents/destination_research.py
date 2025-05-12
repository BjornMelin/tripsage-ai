"""
Destination research capabilities for TripSage.

This module provides comprehensive functionality for researching travel destinations
using web crawling, knowledge graph storage, and caching for optimal performance.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from src.cache.redis_cache import redis_cache
from src.utils.config import get_config
from src.utils.logging import get_module_logger

logger = get_module_logger(__name__)
config = get_config()


class ResearchTopicResult(BaseModel):
    """Result for a specific research topic."""

    title: str = Field(..., description="Title of the content")
    content: str = Field(..., description="Main content extract")
    source: str = Field(..., description="Source of the information")
    url: str = Field(..., description="URL of the source")
    confidence: float = Field(
        0.8, description="Confidence score for relevance", ge=0.0, le=1.0
    )


class DestinationInfo(BaseModel):
    """Structured destination information from research."""

    destination: str = Field(..., description="Name of the destination")
    topics: Dict[str, List[ResearchTopicResult]] = Field(
        ..., description="Research results by topic"
    )
    sources: List[str] = Field(default_factory=list, description="All sources used")


class DestinationEvent(BaseModel):
    """Event happening at a destination."""

    name: str = Field(..., description="Name of the event")
    description: str = Field(..., description="Event description")
    category: str = Field(..., description="Event category")
    date: str = Field(..., description="Event date")
    time: Optional[str] = Field(None, description="Event time")
    venue: Optional[str] = Field(None, description="Event venue")
    address: Optional[str] = Field(None, description="Event address")
    url: Optional[str] = Field(None, description="Event URL")
    price_range: Optional[str] = Field(None, description="Price range")
    image_url: Optional[str] = Field(None, description="Event image URL")
    source: str = Field(..., description="Source of the information")


class EventList(BaseModel):
    """List of events at a destination."""

    destination: str = Field(..., description="Destination name")
    date_range: Dict[str, str] = Field(..., description="Date range for events")
    events: List[DestinationEvent] = Field(..., description="List of events")
    sources: List[str] = Field(default_factory=list, description="All sources used")


class BlogTopic(BaseModel):
    """Blog topic information from research."""

    title: str = Field(..., description="Topic title")
    summary: str = Field(..., description="Topic summary")
    key_points: List[str] = Field(..., description="Key points from the blog")
    sentiment: str = Field(
        ..., description="Overall sentiment (positive, neutral, negative)"
    )
    source_index: int = Field(..., description="Index in the sources list")


class BlogSource(BaseModel):
    """Blog source information."""

    url: str = Field(..., description="Blog URL")
    title: str = Field(..., description="Blog title")
    author: Optional[str] = Field(None, description="Blog author")
    publish_date: Optional[str] = Field(None, description="Publication date")
    reputation_score: Optional[float] = Field(
        None, description="Source reputation score"
    )


class BlogInsights(BaseModel):
    """Insights from travel blogs about a destination."""

    destination: str = Field(..., description="Destination name")
    topics: Dict[str, List[BlogTopic]] = Field(..., description="Topics from blogs")
    sources: List[BlogSource] = Field(..., description="Blog sources")
    extraction_date: str = Field(..., description="Date of extraction")


class TripSageDestinationResearch:
    """Destination research capabilities for TripSage."""

    def __init__(self, webcrawl_client=None):
        """Initialize the destination research component.

        Args:
            webcrawl_client: Optional WebCrawl MCP client for web crawling
        """
        self.query_templates = {
            "general": "travel guide {destination} best things to do",
            "attractions": "top attractions in {destination} must-see sights",
            "safety": "{destination} travel safety information for tourists",
            "transportation": "how to get around {destination} public transportation",
            "best_time": "best time to visit {destination} weather seasons",
            "budget": "{destination} travel cost budget accommodation food",
            "food": "best restaurants in {destination} local cuisine food specialties",
            "culture": "{destination} local customs culture etiquette tips",
            "day_trips": "best day trips from {destination} nearby attractions",
            "family": "things to do in {destination} with children family-friendly",
        }
        self.webcrawl_client = webcrawl_client
        logger.info("TripSage Destination Research component initialized")

    async def search_destination_info(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Search for comprehensive information about a travel destination.

        Uses WebSearchTool and specialized web crawling to gather and analyze
        detailed information about a destination.

        Args:
            params: Parameters including destination name and info types to search for:
                destination: Name of the destination (city, country, attraction)
                topics: List of topics to research (e.g., "attractions", "safety",
                    "transportation", "best_time")
                max_results: Maximum number of results per topic (default: 5)

        Returns:
            Dictionary containing structured information about the destination
        """
        try:
            # Extract parameters
            destination = params.get("destination")
            topics = params.get("topics", ["general"])
            max_results = params.get("max_results", 5)

            if not destination:
                return {"error": "Destination parameter is required"}

            # Build queries for each topic
            search_results = {}

            for topic in topics:
                query = self._build_destination_query(destination, topic)

                # Check cache first
                cache_key = f"destination:{destination}:topic:{topic}"
                cached_result = await redis_cache.get(cache_key)

                if cached_result:
                    search_results[topic] = cached_result
                    search_results[topic]["cache"] = "hit"
                    continue

                # Use WebCrawl MCP for specialized extraction
                try:
                    # Use instance webcrawl_client if available, otherwise
                    # try to get a new client
                    if self.webcrawl_client:
                        webcrawl_client = self.webcrawl_client
                    else:
                        from src.mcp.webcrawl import get_client as get_webcrawl_client

                        webcrawl_client = get_webcrawl_client()

                    # Use WebCrawl's specialized destination search
                    crawl_result = await webcrawl_client.search_destination_info(
                        destination=destination, topics=[topic], max_results=max_results
                    )

                    if crawl_result and not crawl_result.get("error"):
                        # Cache the result with TTL based on content type
                        ttl = self._determine_cache_ttl(topic)
                        await redis_cache.set(cache_key, crawl_result, ttl=ttl)

                        crawl_result["cache"] = "miss"
                        search_results[topic] = crawl_result
                        continue

                except Exception as e:
                    logger.warning(
                        "WebCrawl extraction failed for %s/%s: %s",
                        destination,
                        topic,
                        str(e),
                    )

                # Fallback: Check if WebCrawl provided structured guidance
                if (
                    "websearch_tool_guidance" in crawl_result
                    and topic in crawl_result["websearch_tool_guidance"]
                ):
                    # Extract the structured guidance for more effective
                    # WebSearchTool use
                    guidance = crawl_result["websearch_tool_guidance"][topic]
                    search_results[topic] = {
                        "query": query,
                        "cache": "miss",
                        "source": "web_search",
                        "guidance": guidance,
                        "note": (
                            "Data will be provided by WebSearchTool using "
                            "structured guidance patterns to improve search "
                            "quality and consistency"
                        ),
                    }
                else:
                    # Simple fallback without structured guidance
                    search_results[topic] = {
                        "query": query,
                        "cache": "miss",
                        "source": "web_search",
                        "note": (
                            "Data will be provided by WebSearchTool and "
                            "processed by the agent"
                        ),
                    }

            # Store in knowledge graph when available
            try:
                from src.mcp.memory import get_client as get_memory_client

                memory_client = get_memory_client()

                # Check if destination entity exists
                destination_nodes = await memory_client.search_nodes(destination)
                destination_exists = any(
                    node["name"] == destination and node["type"] == "Destination"
                    for node in destination_nodes
                )

                # Create destination entity if it doesn't exist
                if not destination_exists:
                    await memory_client.create_entities(
                        [
                            {
                                "name": destination,
                                "entityType": "Destination",
                                "observations": [
                                    f"Destination name: {destination}",
                                    "Created from destination research",
                                ],
                            }
                        ]
                    )

                # Add observations for each topic with valid data
                for topic, result in search_results.items():
                    if result.get("topics") and result.get("topics").get(topic):
                        topic_data = result["topics"][topic]
                        if topic_data and len(topic_data) > 0:
                            observations = []
                            for item in topic_data[:3]:  # Store top 3 insights
                                if item.get("title") and item.get("content"):
                                    observations.append(
                                        f"{topic.capitalize()}: {item['title']} - "
                                        f"{item['content'][:150]}..."
                                    )

                            if observations:
                                await memory_client.add_observations(
                                    [
                                        {
                                            "entityName": destination,
                                            "contents": observations,
                                        }
                                    ]
                                )
            except Exception as e:
                logger.warning("Failed to update knowledge graph: %s", str(e))

            return {
                "destination": destination,
                "topics": topics,
                "search_results": search_results,
            }

        except Exception as e:
            logger.error("Error searching destination info: %s", str(e))
            return {"error": f"Destination search error: {str(e)}"}

    async def get_destination_events(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get information about events happening at a destination.

        Args:
            params: Parameters for the event search:
                destination: Destination name (e.g., "Paris, France")
                start_date: Start date in YYYY-MM-DD format
                end_date: End date in YYYY-MM-DD format
                categories: List of event categories (optional)

        Returns:
            Dictionary containing event information for the destination
        """
        try:
            # Extract parameters
            destination = params.get("destination")
            start_date = params.get("start_date")
            end_date = params.get("end_date")
            categories = params.get("categories", [])

            if not destination:
                return {"error": "Destination parameter is required"}
            if not start_date or not end_date:
                return {"error": "Both start_date and end_date are required"}

            # Check cache first
            cache_key = (
                f"events:{destination}:{start_date}:{end_date}:{','.join(categories)}"
            )
            cached_result = await redis_cache.get(cache_key)

            if cached_result:
                return {**cached_result, "cache": "hit"}

            # Use WebCrawl MCP to fetch events
            try:
                # Use instance webcrawl_client if available, otherwise
                # try to get a new client
                if self.webcrawl_client:
                    webcrawl_client = self.webcrawl_client
                else:
                    from src.mcp.webcrawl import get_client as get_webcrawl_client

                    webcrawl_client = get_webcrawl_client()

                # Get events information
                events_result = await webcrawl_client.get_latest_events(
                    destination=destination,
                    start_date=start_date,
                    end_date=end_date,
                    categories=categories,
                )

                if events_result and not events_result.get("error"):
                    # Cache the result for 24 hours (events change frequently)
                    await redis_cache.set(
                        cache_key,
                        events_result,
                        ttl=86400,  # 24 hours
                    )

                    return {**events_result, "cache": "miss"}

            except Exception as e:
                logger.warning(
                    "WebCrawl events search failed for %s: %s", destination, str(e)
                )

            # Fallback: Return a structured error
            return {
                "error": "Could not retrieve event information",
                "destination": destination,
                "date_range": {"start_date": start_date, "end_date": end_date},
                "note": "Events data requires WebCrawl MCP integration",
            }

        except Exception as e:
            logger.error("Error getting destination events: %s", str(e))
            return {"error": f"Events search error: {str(e)}"}

    async def crawl_travel_blog(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Extract insights from travel blogs about a destination.

        Args:
            params: Parameters for blog crawling:
                destination: Destination name (e.g., "Paris, France")
                topics: List of topics to extract (e.g., "hidden gems")
                max_blogs: Maximum number of blogs to crawl (default: 3)
                recent_only: Whether to include only recent blogs (default: True)

        Returns:
            Dictionary containing blog insights about the destination
        """
        try:
            # Extract parameters
            destination = params.get("destination")
            topics = params.get("topics", [])
            max_blogs = params.get("max_blogs", 3)
            recent_only = params.get("recent_only", True)

            if not destination:
                return {"error": "Destination parameter is required"}

            # Check cache first
            cache_key = (
                f"blogs:{destination}:{','.join(topics)}:{max_blogs}:{recent_only}"
            )
            cached_result = await redis_cache.get(cache_key)

            if cached_result:
                return {**cached_result, "cache": "hit"}

            # Use WebCrawl MCP to crawl blogs
            try:
                # Use instance webcrawl_client if available, otherwise
                # try to get a new client
                if self.webcrawl_client:
                    webcrawl_client = self.webcrawl_client
                else:
                    from src.mcp.webcrawl import get_client as get_webcrawl_client

                    webcrawl_client = get_webcrawl_client()

                # Get blog insights
                blog_result = await webcrawl_client.crawl_travel_blog(
                    destination=destination,
                    topics=topics,
                    max_blogs=max_blogs,
                    recent_only=recent_only,
                )

                if blog_result and not blog_result.get("error"):
                    # Cache the result for 1 week (blog content doesn't change often)
                    await redis_cache.set(cache_key, blog_result, ttl=604800)  # 1 week

                    # Store insights in knowledge graph
                    try:
                        from src.mcp.memory import get_client as get_memory_client

                        memory_client = get_memory_client()

                        # Add observations from blog insights
                        if blog_result.get("topics"):
                            observations = []
                            for topic, insights in blog_result["topics"].items():
                                for insight in insights[:2]:  # Top 2 insights per topic
                                    if insight.get("key_points"):
                                        for point in insight["key_points"][
                                            :3
                                        ]:  # Top 3 points
                                            observations.append(
                                                f"Blog insight ({topic}): {point}"
                                            )

                            if observations:
                                await memory_client.add_observations(
                                    [
                                        {
                                            "entityName": destination,
                                            "contents": observations,
                                        }
                                    ]
                                )
                    except Exception as e:
                        logger.warning("Failed to update knowledge graph: %s", str(e))

                    return {**blog_result, "cache": "miss"}

            except Exception as e:
                logger.warning(
                    "WebCrawl blog crawling failed for %s: %s", destination, str(e)
                )

            # Fallback: Return a structured error
            return {
                "error": "Could not crawl travel blogs",
                "destination": destination,
                "note": "Blog crawling requires WebCrawl MCP integration",
            }

        except Exception as e:
            logger.error("Error crawling travel blogs: %s", str(e))
            return {"error": f"Blog crawling error: {str(e)}"}

    def _build_destination_query(self, destination: str, topic: str) -> str:
        """Build an optimized search query for a destination and topic.

        Args:
            destination: Name of the destination
            topic: Type of information to search for

        Returns:
            A formatted search query string
        """
        template = self.query_templates.get(
            topic, "travel information about {destination} {topic}"
        )
        return template.format(destination=destination, topic=topic)

    def _determine_cache_ttl(self, topic: str) -> int:
        """Determine appropriate cache TTL based on content volatility.

        Args:
            topic: Topic of the information

        Returns:
            TTL in seconds
        """
        ttl_map = {
            "weather": 3600,  # 1 hour
            "attractions": 86400,  # 1 day
            "safety": 86400 * 7,  # 1 week
            "transportation": 86400 * 3,  # 3 days
            "best_time": 86400 * 30,  # 30 days
            "culture": 86400 * 30,  # 30 days
            "general": 86400 * 14,  # 2 weeks
            "budget": 86400 * 7,  # 1 week
            "food": 86400 * 14,  # 2 weeks
            "day_trips": 86400 * 14,  # 2 weeks
            "family": 86400 * 14,  # 2 weeks
        }
        return ttl_map.get(topic, 86400)  # 1 day default
