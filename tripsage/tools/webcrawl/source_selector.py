"""Content-type heuristics that tune Crawl4AI scraping behavior."""

from typing import ClassVar

from tripsage_core.utils.logging_utils import get_logger


logger = get_logger(__name__)


class WebCrawlSourceSelector:
    """Optimized content type selector for direct Crawl4AI SDK integration.

    This class provides content-type-specific optimizations for the direct
    Crawl4AI SDK integration, ensuring optimal extraction patterns for
    different types of web content.
    """

    # Content type specific optimization settings
    CONTENT_TYPE_CONFIG: ClassVar[dict[str, dict[str, bool]]] = {
        "travel_blog": {
            "javascript_enabled": False,  # Most blogs are static
            "extract_markdown": True,
            "extract_structured_data": True,
        },
        "booking": {
            "javascript_enabled": True,  # Booking sites need JS
            "extract_markdown": True,
            "extract_structured_data": True,
        },
        "events": {
            "javascript_enabled": True,  # Event sites often need JS
            "extract_markdown": True,
            "extract_structured_data": True,
        },
        "destination_info": {
            "javascript_enabled": False,  # Most info sites are static
            "extract_markdown": True,
            "extract_structured_data": True,
        },
        "reviews": {
            "javascript_enabled": True,  # Review sites often need JS
            "extract_markdown": True,
            "extract_structured_data": False,  # Focus on text content
        },
        "general": {
            "javascript_enabled": False,  # Default to static
            "extract_markdown": True,
            "extract_structured_data": False,
        },
    }

    def get_optimized_config(
        self,
        content_type: str | None = None,
        requires_javascript: bool | None = None,
        extract_structured_data: bool | None = None,
    ) -> dict[str, bool]:
        """Get optimized configuration for the given content type.

        Args:
            content_type: Type of content being extracted
            requires_javascript: Override for JavaScript requirement
            extract_structured_data: Override for structured data extraction

        Returns:
            Dictionary with optimized configuration settings
        """
        # Get base config for content type
        base_config = self.CONTENT_TYPE_CONFIG.get(
            content_type or "general", self.CONTENT_TYPE_CONFIG["general"]
        ).copy()

        # Apply overrides if provided
        if requires_javascript is not None:
            base_config["javascript_enabled"] = requires_javascript

        if extract_structured_data is not None:
            base_config["extract_structured_data"] = extract_structured_data

        logger.debug(
            "Optimized config for content_type='%s': %s", content_type, base_config
        )

        return base_config

    def is_javascript_required(
        self,
        url: str,
        content_type: str | None = None,
        requires_javascript: bool | None = None,
    ) -> bool:
        """Determine if JavaScript is required for the given URL/content type.

        Args:
            url: The URL being crawled
            content_type: Type of content being extracted
            requires_javascript: Explicit override

        Returns:
            True if JavaScript should be enabled
        """
        if requires_javascript is not None:
            return requires_javascript

        # Use content type configuration
        config = self.get_optimized_config(content_type)
        return config["javascript_enabled"]

    def should_extract_structured_data(
        self,
        content_type: str | None = None,
        extract_structured_data: bool | None = None,
    ) -> bool:
        """Determine if structured data extraction should be enabled.

        Args:
            content_type: Type of content being extracted
            extract_structured_data: Explicit override

        Returns:
            True if structured data extraction should be enabled
        """
        if extract_structured_data is not None:
            return extract_structured_data

        # Use content type configuration
        config = self.get_optimized_config(content_type)
        return config["extract_structured_data"]
