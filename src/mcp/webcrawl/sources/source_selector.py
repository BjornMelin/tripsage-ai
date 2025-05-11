"""Intelligent source selection for web crawling."""

import re
from typing import Dict, List, Set

from src.mcp.webcrawl.config import Config
from src.mcp.webcrawl.sources.source_interface import SourceSelector
from src.mcp.webcrawl.utils.url_validator import extract_domain
from src.utils.logging import get_logger

# Initialize logger
logger = get_logger(__name__)


class IntelligentSourceSelector(SourceSelector):
    """Intelligent source selector for web crawling.

    This selector chooses between Crawl4AI and Playwright sources based on
    URL characteristics, destination properties, and known patterns.
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

        # Initialize analytics for adaptive improvement
        self.success_rate: Dict[str, Dict[str, float]] = {
            "crawl4ai": {"success": 0, "total": 0},
            "playwright": {"success": 0, "total": 0},
        }

    def select_source_for_url(self, url: str) -> str:
        """Select the appropriate source for a URL.

        Args:
            url: The URL to select a source for

        Returns:
            The name of the selected source ("crawl4ai" or "playwright")
        """
        # Extract domain
        domain = extract_domain(url)

        # Check if this is a known dynamic site
        if domain in self.dynamic_domains:
            logger.debug(f"Selected Playwright for known dynamic domain: {domain}")
            return "playwright"

        # Check for auth requirements
        for auth_domain, auth_paths in self.auth_domains_patterns.items():
            if domain == auth_domain and any(
                path in url for path in auth_paths if path
            ):
                logger.debug(f"Selected Playwright for auth required domain: {domain}")
                return "playwright"

        # Check for interactive requirements
        for (
            interact_domain,
            interact_paths,
        ) in self.interactive_domains_patterns.items():
            if domain == interact_domain and any(
                path in url for path in interact_paths if path
            ):
                logger.debug(f"Selected Playwright for interactive domain: {domain}")
                return "playwright"

        # Default to Crawl4AI (more efficient for most static content)
        logger.debug(f"Selected Crawl4AI (default) for domain: {domain}")
        return "crawl4ai"

    def select_source_for_destination(self, destination: str, action: str) -> str:
        """Select the appropriate source for a destination and action.

        Args:
            destination: The destination name
            action: The action to perform (e.g., "search", "events", "blogs")

        Returns:
            The name of the selected source ("crawl4ai" or "playwright")
        """
        # Check if this is a large city that may need browser rendering for events
        normalized_destination = destination.lower()
        is_major_city = any(
            city.lower() in normalized_destination for city in self.dynamic_event_cities
        )

        # Select based on action and destination properties
        if action == "events" and is_major_city:
            logger.debug(f"Selected Playwright for events in major city: {destination}")
            return "playwright"

        if action == "blogs":
            # Blog crawling is usually more reliable with browser automation
            # since blogs often have dynamic content
            logger.debug(f"Selected Playwright for blog crawling: {destination}")
            return "playwright"

        # For general search and other actions, use Crawl4AI by default
        logger.debug(f"Selected Crawl4AI (default) for {action} on {destination}")
        return "crawl4ai"

    def report_success(self, source: str, success: bool) -> None:
        """Report success or failure for a source.

        This helps the selector adapt over time based on success rates.

        Args:
            source: The source that was used ("crawl4ai" or "playwright")
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
