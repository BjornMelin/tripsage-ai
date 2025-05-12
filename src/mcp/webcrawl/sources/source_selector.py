"""Intelligent source selection for web crawling."""

import re
from enum import Enum
from typing import Dict, List, Optional, Set

from src.mcp.webcrawl.config import Config
from src.mcp.webcrawl.sources.source_interface import SourceSelector
from src.mcp.webcrawl.utils.url_validator import extract_domain
from src.utils.logging import get_logger

# Initialize logger
logger = get_logger(__name__)


class SourceType(str, Enum):
    """Available source types for web crawling."""

    CRAWL4AI = "crawl4ai"
    FIRECRAWL = "firecrawl"
    PLAYWRIGHT = "playwright"


class IntelligentSourceSelector(SourceSelector):
    """Intelligent source selector for web crawling.

    This selector chooses between Crawl4AI, Firecrawl, and Playwright sources based on
    URL characteristics, destination properties, content types, and known patterns.
    """

    def __init__(self):
        """Initialize the intelligent source selector."""
        # Known dynamic sites that require browser rendering
        self.dynamic_domains: Set[str] = set(Config.DYNAMIC_SITES)

        # Sites that require authentication
        self.auth_domains_patterns: Dict[str, List[str]] = {
            domain: re.split(r"[/,]", path)
            for domain, path in (
                item.split("/", 1) if "/" in item else (item, "")
                for item in Config.AUTH_SITES
            )
        }

        # Interactive sites that require browser interaction
        self.interactive_domains_patterns: Dict[str, List[str]] = {
            domain: re.split(r"[/,]", path)
            for domain, path in (
                item.split("/", 1) if "/" in item else (item, "")
                for item in Config.INTERACTIVE_SITES
            )
        }

        # Cities that often need browser automation for events
        self.dynamic_event_cities: Set[str] = set(Config.DYNAMIC_EVENT_CITIES)

        # Domains better suited for Firecrawl (AI-optimized extraction)
        self.ai_optimized_domains: Set[str] = {
            "wikipedia.org",
            "wikitravel.org",
            "tripadvisor.com",
            "lonelyplanet.com",
            "booking.com",
            "airbnb.com",
            "expedia.com",
            "hotels.com",
            "viator.com",
            "getyourguide.com",
            "visitacity.com",
            "timeout.com",
            "thepointsguy.com",
            "travelandleisure.com",
            "cntraveler.com",
            "frommers.com",
            "fodors.com",
            "ricksteves.com",
            "roughguides.com",
        }

        # Content types better suited for different sources
        self.content_type_preferences: Dict[str, SourceType] = {
            "event_extraction": SourceType.FIRECRAWL,
            "destination_research": SourceType.FIRECRAWL,
            "blog_analysis": SourceType.FIRECRAWL,
            "price_monitoring": SourceType.CRAWL4AI,
            "static_content": SourceType.CRAWL4AI,
            "interactive_content": SourceType.PLAYWRIGHT,
        }

        # Initialize analytics for adaptive improvement
        self.success_rate: Dict[str, Dict[str, float]] = {
            SourceType.CRAWL4AI: {"success": 0, "total": 0},
            SourceType.FIRECRAWL: {"success": 0, "total": 0},
            SourceType.PLAYWRIGHT: {"success": 0, "total": 0},
        }

    def select_source_for_url(
        self, url: str, content_type: Optional[str] = None
    ) -> str:
        """Select the appropriate source for a URL.

        Args:
            url: The URL to select a source for
            content_type: Optional content type to consider in selection

        Returns:
            The name of the selected source (crawl4ai, firecrawl, or playwright)
        """
        # Extract domain
        domain = extract_domain(url)

        # Consider content type first if provided
        if content_type and content_type in self.content_type_preferences:
            logger.debug(
                f"Selected {self.content_type_preferences[content_type]} "
                f"based on content type: {content_type}"
            )
            return self.content_type_preferences[content_type]

        # Check if this is a known dynamic site
        if domain in self.dynamic_domains:
            logger.debug(
                f"Selected {SourceType.PLAYWRIGHT} for known dynamic domain: {domain}"
            )
            return SourceType.PLAYWRIGHT

        # Check for auth requirements
        for auth_domain, auth_paths in self.auth_domains_patterns.items():
            if domain == auth_domain and any(
                path in url for path in auth_paths if path
            ):
                logger.debug(
                    f"Selected {SourceType.PLAYWRIGHT} "
                    f"for auth required domain: {domain}"
                )
                return SourceType.PLAYWRIGHT

        # Check for interactive requirements
        for (
            interact_domain,
            interact_paths,
        ) in self.interactive_domains_patterns.items():
            if domain == interact_domain and any(
                path in url for path in interact_paths if path
            ):
                logger.debug(
                    f"Selected {SourceType.PLAYWRIGHT} for interactive domain: {domain}"
                )
                return SourceType.PLAYWRIGHT

        # Check if this is a domain that benefits from AI-optimized extraction
        if domain in self.ai_optimized_domains:
            logger.debug(
                f"Selected {SourceType.FIRECRAWL} for AI-optimized domain: {domain}"
            )
            return SourceType.FIRECRAWL

        # For general web content, prefer Crawl4AI (more resource-efficient)
        logger.debug(f"Selected {SourceType.CRAWL4AI} (default) for domain: {domain}")
        return SourceType.CRAWL4AI

    def select_source_for_destination(self, destination: str, action: str) -> str:
        """Select the appropriate source for a destination and action.

        Args:
            destination: The destination name
            action: The action to perform (e.g., "search", "events", "blogs")

        Returns:
            The name of the selected source (crawl4ai, firecrawl, or playwright)
        """
        # Check if this is a large city that may need browser rendering for events
        normalized_destination = destination.lower()
        is_major_city = any(
            city.lower() in normalized_destination for city in self.dynamic_event_cities
        )

        # Map action to content type preferences
        content_type_mapping = {
            "events": "event_extraction",
            "blogs": "blog_analysis",
            "search": "destination_research",
            "destination_info": "destination_research",
            "price_monitoring": "price_monitoring",
        }

        content_type = content_type_mapping.get(action)

        # First, check content type preferences
        if content_type and content_type in self.content_type_preferences:
            source = self.content_type_preferences[content_type]

            # Special case for events in major cities
            if action == "events" and is_major_city:
                source = SourceType.PLAYWRIGHT

            logger.debug(f"Selected {source} for {action} on {destination}")
            return source

        # For events in major cities, use Playwright
        if action == "events" and is_major_city:
            logger.debug(
                f"Selected {SourceType.PLAYWRIGHT} "
                f"for events in major city: {destination}"
            )
            return SourceType.PLAYWRIGHT

        # For blog crawling, use Firecrawl (better AI extraction capabilities)
        if action == "blogs":
            logger.debug(
                f"Selected {SourceType.FIRECRAWL} for blog crawling: {destination}"
            )
            return SourceType.FIRECRAWL

        # For destination research, prefer Firecrawl
        if action in ["search", "destination_info"]:
            logger.debug(
                f"Selected {SourceType.FIRECRAWL} "
                f"for destination research: {destination}"
            )
            return SourceType.FIRECRAWL

        # For general and unspecified actions, use Crawl4AI by default
        logger.debug(
            f"Selected {SourceType.CRAWL4AI} (default) for {action} on {destination}"
        )
        return SourceType.CRAWL4AI

    def select_best_source(
        self,
        url: Optional[str] = None,
        destination: Optional[str] = None,
        action: Optional[str] = None,
        content_type: Optional[str] = None,
    ) -> str:
        """Intelligent selection of the best source based on available information.

        Args:
            url: Optional URL to crawl
            destination: Optional destination name
            action: Optional action to perform
            content_type: Optional content type

        Returns:
            The name of the selected source (crawl4ai, firecrawl, or playwright)
        """
        # If we have a URL, that takes precedence
        if url:
            return self.select_source_for_url(url, content_type)

        # If we have destination and action, use that
        if destination and action:
            return self.select_source_for_destination(destination, action)

        # If we only have content type, use the preference mapping
        if content_type and content_type in self.content_type_preferences:
            return self.content_type_preferences[content_type]

        # Default to Crawl4AI as the general purpose crawler
        return SourceType.CRAWL4AI

    def report_success(self, source: str, success: bool) -> None:
        """Report success or failure for a source.

        This helps the selector adapt over time based on success rates.

        Args:
            source: The source that was used (crawl4ai, firecrawl, or playwright)
            success: Whether the operation was successful
        """
        if source in self.success_rate:
            self.success_rate[source]["total"] += 1
            if success:
                self.success_rate[source]["success"] += 1

        # Log current success rates
        for src, rates in self.success_rate.items():
            if rates["total"] > 0:
                success_percent = (rates["success"] / rates["total"]) * 100
                logger.debug(f"{src} success rate: {success_percent:.1f}%")

    def get_success_rates(self) -> Dict[str, float]:
        """Get current success rates for all sources.

        Returns:
            Dictionary mapping source names to success rates (0.0-1.0)
        """
        return {
            source: (stats["success"] / stats["total"]) if stats["total"] > 0 else 0.0
            for source, stats in self.success_rate.items()
        }


# Singleton pattern for the source selector
_source_selector = None


def get_source_selector() -> IntelligentSourceSelector:
    """Get or create the source selector instance.

    Returns:
        Source selector instance
    """
    global _source_selector

    if _source_selector is None:
        _source_selector = IntelligentSourceSelector()

    return _source_selector
