"""Handler for the extract_page_content MCP tool."""

from typing import Any, Dict, List, Optional, Union

from src.mcp.webcrawl.config import Config
from src.mcp.webcrawl.sources.crawl4ai_source import Crawl4AISource
from src.mcp.webcrawl.sources.playwright_source import PlaywrightSource
from src.mcp.webcrawl.sources.source_interface import (
    ExtractedContent,
    ExtractionOptions,
)
from src.mcp.webcrawl.utils.result_normalizer import get_result_normalizer
from src.utils.logging import get_logger

# Initialize logger
logger = get_logger(__name__)

# Get the result normalizer
_normalizer = get_result_normalizer()


async def extract_page_content(
    url: str,
    selectors: Optional[List[str]] = None,
    include_images: bool = False,
    format: str = "markdown",
    source_type: str = "crawl4ai",
) -> Dict[str, Any]:
    """Extract content from a webpage.

    Args:
        url: The URL of the webpage to extract content from
        selectors: Optional CSS selectors to target specific content
        include_images: Whether to include image URLs in the extracted content
        format: Format of the extracted content (markdown, text, html)
        source_type: Type of source to use ("crawl4ai" or "playwright")

    Returns:
        The extracted content

    Raises:
        Exception: If the extraction fails
    """
    logger.info(f"Extracting content from {url} using {source_type}")

    # Validate input
    if not url:
        raise ValueError("URL is required")

    if format not in ["markdown", "text", "html"]:
        raise ValueError(
            f"Invalid format: {format}. Must be one of: markdown, text, html"
        )

    # Validate source_type
    if source_type not in ["crawl4ai", "playwright"]:
        logger.warning(f"Invalid source_type: {source_type}, defaulting to crawl4ai")
        source_type = "crawl4ai"

    # Prepare extraction options
    options: ExtractionOptions = {
        "selectors": selectors,
        "include_images": include_images,
        "format": format,
    }

    try:
        # Initialize the selected source
        if source_type == "crawl4ai":
            source = Crawl4AISource()
            logger.info(f"Using Crawl4AI source for {url}")
        else:  # playwright
            source = PlaywrightSource()
            logger.info(f"Using Playwright source for {url}")

        # Extract content using the selected source
        result = await source.extract_page_content(url, options)

        # Format response to MCP standard
        return _format_extract_response(result)
    except Exception as e:
        logger.error(f"{source_type} extraction failed for {url}: {str(e)}")

        # Try fallback to the other source
        fallback_type = "playwright" if source_type == "crawl4ai" else "crawl4ai"
        return await _extract_with_fallback(url, options, fallback_type)


def _select_source(url: str) -> Union[Crawl4AISource, PlaywrightSource]:
    """Select the appropriate source based on URL patterns.

    Args:
        url: The URL to analyze

    Returns:
        The appropriate source
    """
    # Check if it's a dynamic site that requires browser rendering
    if any(dynamic_site in url for dynamic_site in Config.DYNAMIC_SITES):
        logger.info(f"Using Playwright for dynamic site: {url}")
        return PlaywrightSource()

    # Check if it's a site that requires authentication
    if any(auth_site in url for auth_site in Config.AUTH_SITES):
        logger.info(f"Using Playwright for authenticated site: {url}")
        return PlaywrightSource()

    # Check if it's an interactive site
    if any(interactive_site in url for interactive_site in Config.INTERACTIVE_SITES):
        logger.info(f"Using Playwright for interactive site: {url}")
        return PlaywrightSource()

    # Default to Crawl4AI for most URLs
    logger.info(f"Using Crawl4AI for site: {url}")
    return Crawl4AISource()


async def _extract_with_fallback(
    url: str, options: ExtractionOptions, fallback_type: str = "playwright"
) -> Dict[str, Any]:
    """Extract content with fallback to alternative source if primary fails.

    Args:
        url: The URL to extract from
        options: Extraction options
        fallback_type: Type of source to use for fallback ("crawl4ai" or "playwright")

    Returns:
        The extracted content

    Raises:
        Exception: If all extraction attempts fail
    """
    logger.info(f"Trying {fallback_type} fallback for {url}")

    try:
        # Initialize the fallback source
        if fallback_type == "crawl4ai":
            source = Crawl4AISource()
        else:  # playwright
            source = PlaywrightSource()

        result = await source.extract_page_content(url, options)
        return _format_extract_response(result)
    except Exception as e:
        logger.warning(f"{fallback_type} fallback failed for {url}: {str(e)}")

    # If all sources fail, return an error response
    raise Exception(f"All extraction attempts failed for {url}")


def _format_extract_response(result: ExtractedContent) -> Dict[str, Any]:
    """Format extraction result to standard MCP response format.

    Args:
        result: The extraction result

    Returns:
        Formatted MCP response
    """
    return {
        "url": result["url"],
        "title": result["title"],
        "content": result["content"],
        "images": result["images"] if "images" in result else None,
        "metadata": result["metadata"] if "metadata" in result else {},
        "format": result["format"],
    }
