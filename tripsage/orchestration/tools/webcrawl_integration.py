"""
LangGraph integration for webcrawl tools.

This module provides LangGraph-compatible tool wrappers for the webcrawl
functionality, including the new direct Crawl4AI SDK integration.
"""

import json

from langchain_core.tools import BaseTool
from langchain_core.tools.base import ToolException

from tripsage.tools.webcrawl_tools import (
    crawl_booking_site,
    crawl_event_listing,
    crawl_travel_blog,
    crawl_website_content,
)
from tripsage.utils.logging import get_logger

logger = get_logger(__name__)


class WebCrawlTool(BaseTool):
    """
    LangGraph-compatible tool for web crawling operations.

    This tool uses the new direct Crawl4AI SDK integration with automatic
    fallback to MCP services and Playwright when needed.
    """

    name: str = "crawl_website_content"
    description: str = (
        "Crawl a website using the most appropriate crawler with Playwright fallback. "
        "Automatically selects between Crawl4AI and Firecrawl based on URL domain, "
        "content type, and extraction requirements."
    )

    def _run(self, **kwargs) -> str:
        """
        Execute web crawling synchronously.

        Args:
            **kwargs: Parameters including url, extract_structured_data,
                     content_type, requires_javascript, use_cache,
                     enable_playwright_fallback

        Returns:
            JSON string containing the crawl result
        """
        # Import asyncio here to avoid potential import issues
        import asyncio

        try:
            # Run the async function in the current event loop or create one
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If in an async context, we need to handle this differently
                    logger.warning(
                        "Running async webcrawl in sync context with active event loop"
                    )
                    import nest_asyncio

                    nest_asyncio.apply()
                    result = loop.run_until_complete(crawl_website_content(**kwargs))
                else:
                    result = loop.run_until_complete(crawl_website_content(**kwargs))
            except RuntimeError:
                # No event loop exists, create one
                result = asyncio.run(crawl_website_content(**kwargs))

            # Convert result to JSON for LangGraph compatibility
            return json.dumps(
                {
                    "url": result.url,
                    "title": result.title,
                    "main_content_text": result.main_content_text,
                    "html_content": result.html_content,
                    "status": result.status,
                    "source_crawler": result.source_crawler,
                    "metadata": result.metadata,
                    "error_message": result.error_message,
                    "has_content": result.has_content(),
                }
            )

        except Exception as e:
            error_msg = f"Web crawling failed: {str(e)}"
            logger.error(error_msg)
            raise ToolException(error_msg) from e

    async def _arun(self, **kwargs) -> str:
        """
        Execute web crawling asynchronously.

        Args:
            **kwargs: Parameters for web crawling

        Returns:
            JSON string containing the crawl result
        """
        try:
            result = await crawl_website_content(**kwargs)

            # Convert result to JSON for LangGraph compatibility
            return json.dumps(
                {
                    "url": result.url,
                    "title": result.title,
                    "main_content_text": result.main_content_text,
                    "html_content": result.html_content,
                    "status": result.status,
                    "source_crawler": result.source_crawler,
                    "metadata": result.metadata,
                    "error_message": result.error_message,
                    "has_content": result.has_content(),
                }
            )

        except Exception as e:
            error_msg = f"Web crawling failed: {str(e)}"
            logger.error(error_msg)
            raise ToolException(error_msg) from e


class TravelBlogCrawlTool(BaseTool):
    """LangGraph-compatible tool for crawling travel blogs."""

    name: str = "crawl_travel_blog"
    description: str = (
        "Crawl a travel blog with optimized settings for blog content. "
        "Automatically extracts travel insights and uses cache when available."
    )

    def _run(
        self, url: str, extract_insights: bool = True, use_cache: bool = True
    ) -> str:
        """Execute travel blog crawling synchronously."""
        import asyncio

        try:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    import nest_asyncio

                    nest_asyncio.apply()
                    result = loop.run_until_complete(
                        crawl_travel_blog(url, extract_insights, use_cache)
                    )
                else:
                    result = loop.run_until_complete(
                        crawl_travel_blog(url, extract_insights, use_cache)
                    )
            except RuntimeError:
                result = asyncio.run(
                    crawl_travel_blog(url, extract_insights, use_cache)
                )

            return json.dumps(
                {
                    "url": result.url,
                    "title": result.title,
                    "main_content_text": result.main_content_text,
                    "status": result.status,
                    "source_crawler": result.source_crawler,
                    "metadata": result.metadata,
                    "has_content": result.has_content(),
                }
            )

        except Exception as e:
            error_msg = f"Travel blog crawling failed: {str(e)}"
            logger.error(error_msg)
            raise ToolException(error_msg) from e

    async def _arun(
        self, url: str, extract_insights: bool = True, use_cache: bool = True
    ) -> str:
        """Execute travel blog crawling asynchronously."""
        try:
            result = await crawl_travel_blog(url, extract_insights, use_cache)

            return json.dumps(
                {
                    "url": result.url,
                    "title": result.title,
                    "main_content_text": result.main_content_text,
                    "status": result.status,
                    "source_crawler": result.source_crawler,
                    "metadata": result.metadata,
                    "has_content": result.has_content(),
                }
            )

        except Exception as e:
            error_msg = f"Travel blog crawling failed: {str(e)}"
            logger.error(error_msg)
            raise ToolException(error_msg) from e


class BookingSiteCrawlTool(BaseTool):
    """LangGraph-compatible tool for crawling booking sites."""

    name: str = "crawl_booking_site"
    description: str = (
        "Crawl a booking site with optimized settings for price/availability data. "
        "Handles JavaScript-heavy booking sites like Airbnb, Booking.com, etc."
    )

    def _run(
        self, url: str, extract_prices: bool = True, use_cache: bool = True
    ) -> str:
        """Execute booking site crawling synchronously."""
        import asyncio

        try:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    import nest_asyncio

                    nest_asyncio.apply()
                    result = loop.run_until_complete(
                        crawl_booking_site(url, extract_prices, use_cache)
                    )
                else:
                    result = loop.run_until_complete(
                        crawl_booking_site(url, extract_prices, use_cache)
                    )
            except RuntimeError:
                result = asyncio.run(crawl_booking_site(url, extract_prices, use_cache))

            return json.dumps(
                {
                    "url": result.url,
                    "title": result.title,
                    "main_content_text": result.main_content_text,
                    "status": result.status,
                    "source_crawler": result.source_crawler,
                    "metadata": result.metadata,
                    "has_content": result.has_content(),
                }
            )

        except Exception as e:
            error_msg = f"Booking site crawling failed: {str(e)}"
            logger.error(error_msg)
            raise ToolException(error_msg) from e

    async def _arun(
        self, url: str, extract_prices: bool = True, use_cache: bool = True
    ) -> str:
        """Execute booking site crawling asynchronously."""
        try:
            result = await crawl_booking_site(url, extract_prices, use_cache)

            return json.dumps(
                {
                    "url": result.url,
                    "title": result.title,
                    "main_content_text": result.main_content_text,
                    "status": result.status,
                    "source_crawler": result.source_crawler,
                    "metadata": result.metadata,
                    "has_content": result.has_content(),
                }
            )

        except Exception as e:
            error_msg = f"Booking site crawling failed: {str(e)}"
            logger.error(error_msg)
            raise ToolException(error_msg) from e


class EventListingCrawlTool(BaseTool):
    """LangGraph-compatible tool for crawling event listings."""

    name: str = "crawl_event_listing"
    description: str = (
        "Crawl an event listing with optimized settings for event data. "
        "Extracts event dates, details, and handles JavaScript-heavy event sites."
    )

    def _run(self, url: str, extract_dates: bool = True, use_cache: bool = True) -> str:
        """Execute event listing crawling synchronously."""
        import asyncio

        try:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    import nest_asyncio

                    nest_asyncio.apply()
                    result = loop.run_until_complete(
                        crawl_event_listing(url, extract_dates, use_cache)
                    )
                else:
                    result = loop.run_until_complete(
                        crawl_event_listing(url, extract_dates, use_cache)
                    )
            except RuntimeError:
                result = asyncio.run(crawl_event_listing(url, extract_dates, use_cache))

            return json.dumps(
                {
                    "url": result.url,
                    "title": result.title,
                    "main_content_text": result.main_content_text,
                    "status": result.status,
                    "source_crawler": result.source_crawler,
                    "metadata": result.metadata,
                    "has_content": result.has_content(),
                }
            )

        except Exception as e:
            error_msg = f"Event listing crawling failed: {str(e)}"
            logger.error(error_msg)
            raise ToolException(error_msg) from e

    async def _arun(
        self, url: str, extract_dates: bool = True, use_cache: bool = True
    ) -> str:
        """Execute event listing crawling asynchronously."""
        try:
            result = await crawl_event_listing(url, extract_dates, use_cache)

            return json.dumps(
                {
                    "url": result.url,
                    "title": result.title,
                    "main_content_text": result.main_content_text,
                    "status": result.status,
                    "source_crawler": result.source_crawler,
                    "metadata": result.metadata,
                    "has_content": result.has_content(),
                }
            )

        except Exception as e:
            error_msg = f"Event listing crawling failed: {str(e)}"
            logger.error(error_msg)
            raise ToolException(error_msg) from e
