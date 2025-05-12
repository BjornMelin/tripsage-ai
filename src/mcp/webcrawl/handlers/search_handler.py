"""Handler for the search_destination_info MCP tool."""

import datetime
from typing import Any, Dict, List, Optional

from src.mcp.webcrawl.sources.crawl4ai_source import Crawl4AISource
from src.mcp.webcrawl.sources.firecrawl_source import FirecrawlSource
from src.mcp.webcrawl.sources.playwright_source import PlaywrightSource
from src.mcp.webcrawl.utils.result_normalizer import get_result_normalizer
from src.mcp.webcrawl.utils.search_helpers import create_fallback_guidance
from src.utils.logging import get_logger

# Initialize logger
logger = get_logger(__name__)

# Get the result normalizer
_normalizer = get_result_normalizer()


async def search_destination_info(
    destination: str,
    topics: Optional[List[str]] = None,
    max_results: int = 5,
    source_type: str = "crawl4ai",
    traveler_profile: Optional[str] = None,
) -> Dict[str, Any]:
    """Search for specific information about a travel destination.

    Args:
        destination: Name of the destination (city, country, attraction)
        topics: Type of information to search for (e.g., "attractions", "local_customs")
        max_results: Maximum number of results to return per topic
        source_type: Type of source to use ("crawl4ai" or "playwright")
        traveler_profile: Optional traveler profile for personalized results

    Returns:
        Dict containing extracted and structured information about the destination

    Raises:
        Exception: If the search fails
    """
    logger.info(f"Searching for information about {destination} using {source_type}")

    # Validate input
    if not destination:
        raise ValueError("Destination is required")

    if max_results < 1 or max_results > 20:
        raise ValueError(
            f"Invalid max_results: {max_results}. Must be between 1 and 20"
        )

    # Validate source_type
    if source_type not in ["crawl4ai", "firecrawl", "playwright"]:
        logger.warning(f"Invalid source_type: {source_type}, defaulting to crawl4ai")
        source_type = "crawl4ai"

    try:
        # Initialize the selected source
        if source_type == "crawl4ai":
            source = Crawl4AISource()
            logger.info(f"Using Crawl4AI source for {destination}")
        elif source_type == "firecrawl":
            source = FirecrawlSource()
            logger.info(f"Using Firecrawl source for {destination}")
        else:  # playwright
            source = PlaywrightSource()
            logger.info(f"Using Playwright source for {destination}")

        # Search for destination information
        results = await source.search_destination_info(
            destination=destination, topics=topics, max_results=max_results
        )

        # Normalize and return formatted results
        normalized_results = _normalizer.normalize_destination_results(
            results=results, source_type=source_type
        )
        return _format_search_response(normalized_results)
    except Exception as e:
        logger.error(f"{source_type} search failed for {destination}: {str(e)}")

        # Try fallback to an alternative source
        if source_type == "crawl4ai":
            fallback_type = "firecrawl"  # Try Firecrawl first
        elif source_type == "firecrawl":
            fallback_type = "playwright"  # Try Playwright next
        else:  # Playwright failed, try Crawl4AI
            fallback_type = "crawl4ai"

        try:
            logger.info(f"Trying {fallback_type} fallback for {destination}")

            if fallback_type == "crawl4ai":
                fallback_source = Crawl4AISource()
            elif fallback_type == "firecrawl":
                fallback_source = FirecrawlSource()
            else:
                fallback_source = PlaywrightSource()

            results = await fallback_source.search_destination_info(
                destination=destination, topics=topics, max_results=max_results
            )

            # Normalize and return formatted results from fallback
            normalized_results = _normalizer.normalize_destination_results(
                results=results, source_type=fallback_type
            )
            return _format_search_response(normalized_results)
        except Exception as fallback_e:
            logger.error(
                f"Fallback {fallback_type} search failed for {destination}: "
                f"{str(fallback_e)}"
            )

            # Generate structured WebSearchTool fallback guidance
            logger.info(f"Generating WebSearchTool fallback guidance for {destination}")

            all_guidance = {}
            for topic in topics or ["general"]:
                # Create structured guidance for each topic
                guidance = create_fallback_guidance(
                    destination=destination,
                    topic=topic,
                    traveler_profile=traveler_profile,
                )

                # Add timestamp
                guidance["fallback_timestamp"] = datetime.datetime.utcnow().isoformat()

                all_guidance[topic] = guidance

            # Create a structured error response with WebSearchTool guidance
            return {
                "destination": destination,
                "error": "WebCrawl extraction failed",
                "fallback_type": "websearch_tool",
                "topics": {topic: [] for topic in topics or ["general"]},
                "websearch_tool_guidance": all_guidance,
                "search_timestamp": datetime.datetime.utcnow().isoformat(),
            }


def _format_search_response(results: Dict[str, Any]) -> Dict[str, Any]:
    """Format search results for standard MCP response.

    Args:
        results: Raw search results

    Returns:
        Formatted MCP response
    """
    # Process and enrich content
    for _topic, topic_results in results.get("topics", {}).items():
        for _i, result in enumerate(topic_results):
            # Extract 1-2 sentence summary if content is very long
            if "content" in result and len(result["content"]) > 500:
                sentences = result["content"].split(". ")
                if len(sentences) > 2:
                    result["summary"] = ". ".join(sentences[:2]) + "."
                else:
                    result["summary"] = result["content"][:300] + "..."

    return {
        "destination": results.get("destination", ""),
        "topics": results.get("topics", {}),
        "sources": results.get("sources", []),
        "search_timestamp": results.get("search_timestamp", ""),
    }
