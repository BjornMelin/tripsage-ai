"""Handler for the crawl_travel_blog MCP tool."""

import datetime
import logging
from typing import Any, Dict, List, Optional

from src.mcp.webcrawl.sources.crawl4ai_source import Crawl4AISource
from src.mcp.webcrawl.sources.playwright_source import PlaywrightSource
from src.utils.logging import get_logger

# Initialize logger
logger = get_logger(__name__)


async def crawl_travel_blog(
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

    # Validate input
    if not destination:
        raise ValueError("Destination is required")

    if max_blogs < 1 or max_blogs > 10:
        raise ValueError(f"Invalid max_blogs: {max_blogs}. Must be between 1 and 10")

    # Initialize Crawl4AI source (primary for blog crawling)
    primary_source = Crawl4AISource()

    try:
        # Crawl travel blogs
        results = await primary_source.crawl_travel_blog(
            destination=destination,
            topics=topics,
            max_blogs=max_blogs,
            recent_only=recent_only,
        )

        # Return formatted results
        return _format_blog_response(results)
    except Exception as e:
        logger.error(f"Primary source blog crawl failed for {destination}: {str(e)}")

        # Try fallback to Playwright
        try:
            logger.info(f"Trying Playwright fallback for {destination} blog crawl")
            fallback_source = PlaywrightSource()
            results = await fallback_source.crawl_travel_blog(
                destination=destination,
                topics=topics,
                max_blogs=max_blogs,
                recent_only=recent_only,
            )

            return _format_blog_response(results)
        except Exception as fallback_e:
            logger.error(
                f"Fallback source blog crawl failed for {destination}: {str(fallback_e)}"
            )
            raise Exception(f"All blog crawl attempts failed for {destination}")


def _format_blog_response(results: Dict[str, Any]) -> Dict[str, Any]:
    """Format blog crawl results for standard MCP response.

    Args:
        results: Raw blog crawl results

    Returns:
        Formatted MCP response
    """
    # Process topics
    topics_data = {}
    for topic_name, topic_insights in results.get("topics", {}).items():
        topics_data[topic_name] = []

        for insight in topic_insights:
            # Get source from source_index if available
            source = {}
            source_index = insight.get("source_index")
            if (
                source_index is not None
                and "sources" in results
                and 0 <= source_index < len(results["sources"])
            ):
                source = results["sources"][source_index]

            # Format insight
            formatted_insight = {
                "title": insight.get("title", ""),
                "summary": insight.get("summary", ""),
                "key_points": insight.get("key_points", []),
                "sentiment": insight.get("sentiment", "neutral"),
                "source": {
                    "url": source.get("url", ""),
                    "title": source.get("title", ""),
                    "author": source.get("author", ""),
                },
            }

            topics_data[topic_name].append(formatted_insight)

    # Group insights by sentiment for each topic
    sentiment_analysis = {}
    for topic, insights in topics_data.items():
        sentiment_analysis[topic] = {"positive": 0, "neutral": 0, "negative": 0}

        for insight in insights:
            sentiment = insight.get("sentiment", "neutral")
            if sentiment in sentiment_analysis[topic]:
                sentiment_analysis[topic][sentiment] += 1

    return {
        "destination": results.get("destination", ""),
        "topics": topics_data,
        "sources": [
            {
                "url": source.get("url", ""),
                "title": source.get("title", ""),
                "author": source.get("author", ""),
                "publish_date": source.get("publish_date", ""),
            }
            for source in results.get("sources", [])
        ],
        "sentiment_analysis": sentiment_analysis,
        "extraction_date": results.get(
            "extraction_date", datetime.datetime.now().isoformat()
        ),
    }
