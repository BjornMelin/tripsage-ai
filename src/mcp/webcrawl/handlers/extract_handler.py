"""Handler for the extract_page_content MCP tool."""

from typing import Any, Dict, List, Optional, Union

from src.mcp.webcrawl.config import Config
from src.mcp.webcrawl.sources.crawl4ai_source import Crawl4AISource
from src.mcp.webcrawl.sources.playwright_source import PlaywrightSource
from src.mcp.webcrawl.sources.source_interface import (
    ExtractedContent,
    ExtractionOptions,
)
from src.utils.logging import get_logger

# Initialize logger
logger = get_logger(__name__)


async def extract_page_content(
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

    # Validate input
    if not url:
        raise ValueError("URL is required")

    if format not in ["markdown", "text", "html"]:
        raise ValueError(
            f"Invalid format: {format}. Must be one of: markdown, text, html"
        )

    # Prepare extraction options
    options: ExtractionOptions = {
        "selectors": selectors,
        "include_images": include_images,
        "format": format,
    }

    # Select appropriate source based on URL
    source = _select_source(url)

    try:
        # Extract content using the selected source
        result = await source.extract_page_content(url, options)

        # Format response to MCP standard
        return _format_extract_response(result)
    except Exception as e:
        logger.error(f"Error extracting content from {url}: {str(e)}")
        # Try fallback to another source if primary fails
        return await _extract_with_fallback(url, options)


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
    url: str, options: ExtractionOptions
) -> Dict[str, Any]:
    """Extract content with fallback to alternative source if primary fails.

    Args:
        url: The URL to extract from
        options: Extraction options

    Returns:
        The extracted content

    Raises:
        Exception: If all extraction attempts fail
    """
    # Define source for fallback - if primary was Crawl4AI, use Playwright 
    # and vice versa
    primary_was_crawl4ai = isinstance(_select_source(url), Crawl4AISource)

    try:
        if primary_was_crawl4ai:
            logger.info(f"Trying Playwright fallback for {url}")
            source = PlaywrightSource()
        else:
            logger.info(f"Trying Crawl4AI fallback for {url}")
            source = Crawl4AISource()

        result = await source.extract_page_content(url, options)
        return _format_extract_response(result)
    except Exception as e:
        logger.warning(f"Fallback source failed: {str(e)}")

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
