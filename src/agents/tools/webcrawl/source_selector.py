"""
Source selector for web crawling tools.

This module provides functionality to select the appropriate web crawling source
(Crawl4AI or Firecrawl) based on content type, URL, and other factors.
"""

import re
from enum import Enum
from typing import Dict, Optional, Set

from src.utils.logging import get_logger

logger = get_logger(__name__)


class SourceType(str, Enum):
    """Enumeration of available external web crawling sources."""

    CRAWL4AI = "crawl4ai"
    FIRECRAWL = "firecrawl"


class SourceSelector:
    """Intelligent source selector for web crawling operations.

    This class selects the appropriate source (Crawl4AI or Firecrawl) based on:
    1. Content type (travel blog, events, pricing, etc.)
    2. URL patterns and domain specific optimizations
    3. Historical performance
    """

    # Domain patterns that perform better with specific sources
    CRAWL4AI_OPTIMIZED_DOMAINS: Set[str] = {
        "tripadvisor.com",
        "wikitravel.org",
        "wikipedia.org",
        "lonelyplanet.com",
        "travel.state.gov",
        "flyertalk.com",
    }

    FIRECRAWL_OPTIMIZED_DOMAINS: Set[str] = {
        "airbnb.com",
        "booking.com",
        "expedia.com",
        "hotels.com",
        "kayak.com",
        "trip.com",
        "eventbrite.com",
        "timeout.com",
    }

    # Content type to source mapping
    CONTENT_TYPE_MAPPING: Dict[str, SourceType] = {
        "price_monitor": SourceType.FIRECRAWL,  # Firecrawl better at dynamic price data
        "travel_blog": SourceType.CRAWL4AI,  # Crawl4AI better at blog content
        "events": SourceType.FIRECRAWL,  # Firecrawl better at event listings
        # Crawl4AI better at general travel info
        "destination_info": SourceType.CRAWL4AI,
    }

    def __init__(self):
        """Initialize the source selector."""
        # Could be extended to load historical performance data
        pass

    def select_source(
        self,
        url: str,
        content_type: Optional[str] = None,
        full_page: bool = False,
        dynamic_content: bool = False,
        extraction_complexity: str = "simple",
    ) -> SourceType:
        """Select the appropriate source for web crawling.

        Args:
            url: The URL to crawl
            content_type: Type of content to extract (price_monitor, travel_blog, etc.)
            full_page: Whether the full page needs to be crawled
            dynamic_content: Whether the page has dynamic JavaScript content
            extraction_complexity: Complexity of extraction
                ("simple", "moderate", "complex")

        Returns:
            The selected source type (CRAWL4AI or FIRECRAWL)
        """
        # Default to Crawl4AI as the more general-purpose option
        selected_source = SourceType.CRAWL4AI

        # 1. Check content type mapping
        if content_type and content_type in self.CONTENT_TYPE_MAPPING:
            selected_source = self.CONTENT_TYPE_MAPPING[content_type]
            logger.debug(
                f"Selected {selected_source} based on content type: {content_type}"
            )
            return selected_source

        # 2. Check domain-specific optimizations
        domain = self._extract_domain(url)
        if domain:
            if domain in self.FIRECRAWL_OPTIMIZED_DOMAINS:
                selected_source = SourceType.FIRECRAWL
                logger.debug(
                    f"Selected {selected_source} based on optimized domain: {domain}"
                )
                return selected_source
            elif domain in self.CRAWL4AI_OPTIMIZED_DOMAINS:
                selected_source = SourceType.CRAWL4AI
                logger.debug(
                    f"Selected {selected_source} based on optimized domain: {domain}"
                )
                return selected_source

        # 3. Consider dynamic content needs
        if dynamic_content:
            selected_source = SourceType.FIRECRAWL  # Firecrawl handles JS better
            logger.debug(f"Selected {selected_source} for dynamic content")
            return selected_source

        # 4. Consider extraction complexity
        if extraction_complexity == "complex":
            selected_source = (
                SourceType.FIRECRAWL
            )  # Firecrawl's structured extraction is better
            logger.debug(f"Selected {selected_source} for complex extraction")
            return selected_source

        logger.debug(f"Selected {selected_source} as default for {url}")
        return selected_source

    def _extract_domain(self, url: str) -> Optional[str]:
        """Extract the domain from a URL.

        Args:
            url: The URL to extract the domain from

        Returns:
            The domain name or None if not found
        """
        pattern = r"https?://(?:www\.)?([a-zA-Z0-9.-]+)(?:/|$)"
        match = re.search(pattern, url)
        if match:
            return match.group(1)
        return None


# Create singleton instance
source_selector = SourceSelector()


def get_source_selector() -> SourceSelector:
    """Get the singleton instance of the source selector.

    Returns:
        The source selector instance
    """
    return source_selector
