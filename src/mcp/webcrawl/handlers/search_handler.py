"""Handler for the search_destination_info MCP tool."""

from typing import Any, Dict, List, Optional

from src.mcp.webcrawl.sources.crawl4ai_source import Crawl4AISource
from src.mcp.webcrawl.sources.playwright_source import PlaywrightSource
from src.utils.logging import get_logger

# Initialize logger
logger = get_logger(__name__)


async def search_destination_info(
    destination: str, topics: Optional[List[str]] = None, max_results: int = 5
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

    # Validate input
    if not destination:
        raise ValueError("Destination is required")

    if max_results < 1 or max_results > 20:
        raise ValueError(
            f"Invalid max_results: {max_results}. Must be between 1 and 20"
        )

    # Initialize Crawl4AI source (primary for destination research)
    primary_source = Crawl4AISource()

    try:
        # Search for destination information
        results = await primary_source.search_destination_info(
            destination=destination, topics=topics, max_results=max_results
        )

        # Return formatted results
        return _format_search_response(results)
    except Exception as e:
        logger.error(f"Primary source search failed for {destination}: {str(e)}")

        # Try fallback to Playwright
        try:
            logger.info(f"Trying Playwright fallback for {destination}")
            fallback_source = PlaywrightSource()
            results = await fallback_source.search_destination_info(
                destination=destination, topics=topics, max_results=max_results
            )

            return _format_search_response(results)
        except Exception as fallback_e:
            logger.error(
                f"Fallback source search failed for {destination}: {str(fallback_e)}"
            )
            raise Exception(
                f"All search attempts failed for {destination}"
            ) from fallback_e


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
