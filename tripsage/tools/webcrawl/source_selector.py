"""
Source selector for web crawling tools.

This module provides functionality to select the appropriate web crawling source
(Crawl4AI or Firecrawl) based on content type, URL, and other factors.
"""

import re
from enum import Enum
from typing import TYPE_CHECKING, Dict, Optional, Set, Union

from tripsage.config.mcp_settings import get_mcp_settings
from tripsage.utils.logging import get_logger

# Import client types for type checking only
if TYPE_CHECKING:
    from tripsage.clients.webcrawl.crawl4ai_mcp_client import Crawl4AIMCPClient
    from tripsage.clients.webcrawl.firecrawl_mcp_client import FirecrawlMCPClient
    from tripsage.tools.browser.playwright_mcp_client import PlaywrightMCPClient

logger = get_logger(__name__)


class CrawlerType(str, Enum):
    """Enumeration of available web crawling sources."""

    CRAWL4AI = "crawl4ai"
    CRAWL4AI_DIRECT = "crawl4ai_direct"  # Direct SDK integration
    FIRECRAWL = "firecrawl"
    PLAYWRIGHT = "playwright"  # For direct Playwright usage


class WebCrawlSourceSelector:
    """Intelligent source selector for web crawling operations.

    This class selects the appropriate crawler (Crawl4AI, Firecrawl, or
    Playwright) based on:
    1. Domain-based routing configuration
    2. Content type requirements
    3. Dynamic content needs
    4. Extraction complexity
    5. Known problematic domains that require Playwright
    """

    # Default domain patterns that perform better with specific sources
    DEFAULT_CRAWL4AI_DOMAINS: Set[str] = {
        "tripadvisor.com",
        "wikitravel.org",
        "wikipedia.org",
        "lonelyplanet.com",
        "nomadlist.com",
        "travel.state.gov",
        "flyertalk.com",
        "github.io",  # Travel blogs often hosted here
        "blogspot.com",
        "wordpress.com",
        "medium.com",
    }

    DEFAULT_FIRECRAWL_DOMAINS: Set[str] = {
        "airbnb.com",
        "booking.com",
        "expedia.com",
        "hotels.com",
        "kayak.com",
        "trip.com",
        "agoda.com",
        "skyscanner.com",
        "eventbrite.com",
        "timeout.com",
        "ticketmaster.com",
        "viator.com",
    }

    # Domains that require Playwright due to heavy JS or anti-scraping measures
    DEFAULT_PLAYWRIGHT_ONLY_DOMAINS: Set[str] = {
        "zillow.com",
        "netflix.com",
        "linkedin.com",
        "facebook.com",
        "instagram.com",
        "twitter.com",
        "x.com",
        "google.com/travel",
        "google.com/flights",
        "maps.google.com",
    }

    # Content type to crawler mapping
    CONTENT_TYPE_MAPPING: Dict[str, CrawlerType] = {
        "price_monitor": CrawlerType.FIRECRAWL,  # Better at dynamic price data
        "travel_blog": CrawlerType.CRAWL4AI_DIRECT,  # Better at blog content extraction
        "events": CrawlerType.FIRECRAWL,  # Better at event listings
        "destination_info": CrawlerType.CRAWL4AI_DIRECT,  # Better at general travel info
        "booking": CrawlerType.FIRECRAWL,  # Better at booking site data
        "reviews": CrawlerType.CRAWL4AI_DIRECT,  # Better at review content
    }

    def __init__(self):
        """Initialize the source selector with configurable domain mappings."""
        self.settings = get_mcp_settings()

        # Get configured domain mappings or use defaults
        self.crawl4ai_domains = set(self.DEFAULT_CRAWL4AI_DOMAINS)
        self.firecrawl_domains = set(self.DEFAULT_FIRECRAWL_DOMAINS)
        self.playwright_only_domains = set(self.DEFAULT_PLAYWRIGHT_ONLY_DOMAINS)

        # Add any custom domain mappings from Crawl4AI config
        if self.settings.crawl4ai.domain_routing:
            self.crawl4ai_domains.update(
                self.settings.crawl4ai.domain_routing.crawl4ai_domains
            )

        # Add any custom domain mappings from Firecrawl config
        if self.settings.firecrawl.domain_routing:
            self.firecrawl_domains.update(
                self.settings.firecrawl.domain_routing.firecrawl_domains
            )

        # Add any custom Playwright-only domains from config if available
        # This assumes playwright config might have domain_routing in the future
        if hasattr(self.settings, "playwright") and hasattr(
            self.settings.playwright, "domain_routing"
        ):
            if hasattr(
                self.settings.playwright.domain_routing, "playwright_only_domains"
            ):
                self.playwright_only_domains.update(
                    self.settings.playwright.domain_routing.playwright_only_domains
                )

    def select_crawler(
        self,
        url: str,
        content_type: Optional[str] = None,
        prefer_structured_data: bool = False,
        requires_javascript: bool = False,
        extraction_complexity: str = "simple",
        force_playwright: bool = False,
    ) -> CrawlerType:
        """Select the appropriate crawler for web crawling.

        Args:
            url: The URL to crawl
            content_type: Type of content to extract
            prefer_structured_data: Whether structured data extraction is needed
            requires_javascript: Whether the page requires JavaScript execution
            extraction_complexity: Complexity level ("simple", "moderate", "complex")
            force_playwright: Force Playwright selection regardless of other factors

        Returns:
            The selected crawler type
        """
        # Force Playwright if requested
        if force_playwright:
            return CrawlerType.PLAYWRIGHT

        # Extract domain for checking
        domain = self._extract_domain(url)

        # Check if domain requires Playwright
        if domain and any(domain.endswith(pd) for pd in self.playwright_only_domains):
            logger.debug(
                f"Selected Playwright for domain {domain} (Playwright-only domain)"
            )
            return CrawlerType.PLAYWRIGHT

        # Default to direct Crawl4AI for general content
        selected_crawler = CrawlerType.CRAWL4AI_DIRECT

        # 1. Check content type mapping
        if content_type and content_type in self.CONTENT_TYPE_MAPPING:
            selected_crawler = self.CONTENT_TYPE_MAPPING[content_type]
            logger.debug(
                f"Selected {selected_crawler} based on content type: {content_type}"
            )
            return selected_crawler

        # 2. Check domain-specific optimizations
        domain = self._extract_domain(url)
        if domain:
            if any(domain.endswith(fd) for fd in self.firecrawl_domains):
                selected_crawler = CrawlerType.FIRECRAWL
                logger.debug(
                    f"Selected {selected_crawler} based on optimized domain: {domain}"
                )
                return selected_crawler
            elif any(domain.endswith(cd) for cd in self.crawl4ai_domains):
                selected_crawler = CrawlerType.CRAWL4AI_DIRECT
                logger.debug(
                    f"Selected {selected_crawler} based on optimized domain: {domain}"
                )
                return selected_crawler

        # 3. Consider JavaScript requirements
        if requires_javascript:
            selected_crawler = CrawlerType.FIRECRAWL  # Better at JS execution
            logger.debug(f"Selected {selected_crawler} for JavaScript content")
            return selected_crawler

        # 4. Consider structured data needs
        if prefer_structured_data:
            selected_crawler = CrawlerType.FIRECRAWL  # Better at structured extraction
            logger.debug(f"Selected {selected_crawler} for structured data")
            return selected_crawler

        # 5. Consider extraction complexity
        if extraction_complexity in ["moderate", "complex"]:
            selected_crawler = CrawlerType.FIRECRAWL  # More robust extraction
            logger.debug(
                f"Selected {selected_crawler} for {extraction_complexity} extraction"
            )
            return selected_crawler

        # 6. Use default for general content
        logger.debug(f"Selected {selected_crawler} as default for {url}")
        return selected_crawler

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
            return match.group(1).lower()
        return None

    def get_client_for_url(
        self, url: str, **kwargs
    ) -> Union["FirecrawlMCPClient", "Crawl4AIMCPClient", "PlaywrightMCPClient", str]:
        """Get the appropriate client instance for a given URL.

        Args:
            url: The URL to crawl
            **kwargs: Additional arguments for crawler selection

        Returns:
            Either FirecrawlMCPClient, Crawl4AIMCPClient, PlaywrightMCPClient instance, or "direct" for direct SDK
        """
        crawler_type = self.select_crawler(url, **kwargs)

        if crawler_type == CrawlerType.CRAWL4AI_DIRECT:
            # Return a special marker for direct SDK usage
            return "direct"
        elif crawler_type == CrawlerType.FIRECRAWL:
            from tripsage.clients.webcrawl.firecrawl_mcp_client import (
                FirecrawlMCPClient,
            )

            return FirecrawlMCPClient()
        elif crawler_type == CrawlerType.PLAYWRIGHT:
            from tripsage.tools.browser.playwright_mcp_client import (
                PlaywrightMCPClient,
            )

            return PlaywrightMCPClient()
        else:
            from tripsage.clients.webcrawl.crawl4ai_mcp_client import Crawl4AIMCPClient

            return Crawl4AIMCPClient()


# Create singleton instance
source_selector = WebCrawlSourceSelector()


def get_source_selector() -> WebCrawlSourceSelector:
    """Get the singleton instance of the source selector.

    Returns:
        The source selector instance
    """
    return source_selector
