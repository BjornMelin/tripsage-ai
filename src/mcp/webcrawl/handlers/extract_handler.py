"""Handler for the extract_page_content MCP tool."""

from typing import Any, Dict, List, Optional, Union

from src.mcp.webcrawl.sources.crawl4ai_source import Crawl4AISource
from src.mcp.webcrawl.sources.firecrawl_source import FirecrawlSource
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
    if source_type not in ["crawl4ai", "firecrawl", "playwright"]:
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
        elif source_type == "firecrawl":
            source = FirecrawlSource()
            logger.info(f"Using Firecrawl source for {url}")
        else:  # playwright
            source = PlaywrightSource()
            logger.info(f"Using Playwright source for {url}")

        # Extract content using the selected source
        result = await source.extract_page_content(url, options)

        # Format response to MCP standard
        return _format_extract_response(result)
    except Exception as e:
        logger.error(f"{source_type} extraction failed for {url}: {str(e)}")

        # Try fallback to an alternative source
        if source_type == "crawl4ai":
            fallback_type = (
                "firecrawl"  # Try Firecrawl first, then Playwright if needed
            )
        elif source_type == "firecrawl":
            fallback_type = "playwright"  # Try Playwright next
        else:  # If Playwright failed, try Crawl4AI
            fallback_type = "crawl4ai"
        return await _extract_with_fallback(url, options, fallback_type)


def _select_source(
    url: str,
) -> Union[Crawl4AISource, FirecrawlSource, PlaywrightSource]:
    """Select the appropriate source based on URL patterns.

    Args:
        url: The URL to analyze

    Returns:
        The appropriate source
    """
    # Use the source selector for intelligent source selection
    from src.mcp.webcrawl.sources.source_selector import get_source_selector

    selector = get_source_selector()
    source_type = selector.select_source_for_url(url)

    logger.info(f"Source selector chose {source_type} for {url}")

    # Initialize the appropriate source
    if source_type == "firecrawl":
        return FirecrawlSource()
    elif source_type == "playwright":
        return PlaywrightSource()
    else:  # Default to Crawl4AI
        return Crawl4AISource()


async def _extract_with_fallback(
    url: str, options: ExtractionOptions, fallback_type: str = "playwright"
) -> Dict[str, Any]:
    """Extract content with fallback to alternative source if primary fails.

    Args:
        url: The URL to extract from
        options: Extraction options
        fallback_type: Type of source to use for fallback ("crawl4ai",
            "firecrawl", or "playwright")

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
        elif fallback_type == "firecrawl":
            source = FirecrawlSource()
        else:  # playwright
            source = PlaywrightSource()

        result = await source.extract_page_content(url, options)
        return _format_extract_response(result)
    except Exception as e:
        logger.warning(f"{fallback_type} fallback failed for {url}: {str(e)}")

        # Try second fallback if we haven't tried all sources yet
        if fallback_type == "firecrawl":
            logger.info(f"Trying second fallback with playwright for {url}")
            try:
                source = PlaywrightSource()
                result = await source.extract_page_content(url, options)
                return _format_extract_response(result)
            except Exception as e2:
                logger.warning(f"Second fallback failed for {url}: {str(e2)}")
        elif fallback_type == "playwright" and "crawl4ai" not in str(e).lower():
            logger.info(f"Trying second fallback with crawl4ai for {url}")
            try:
                source = Crawl4AISource()
                result = await source.extract_page_content(url, options)
                return _format_extract_response(result)
            except Exception as e2:
                logger.warning(f"Second fallback failed for {url}: {str(e2)}")

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
