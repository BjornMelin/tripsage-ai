"""
Result normalizer for web crawling tools.

This module provides functionality to normalize results from different web crawling
sources (Crawl4AI and Firecrawl) into a consistent format.
"""

from datetime import datetime
from typing import Any, Dict

from tripsage.utils.logging import get_logger

logger = get_logger(__name__)


class ResultNormalizer:
    """Normalizes results from different web crawling sources."""

    def normalize_crawl_result(
        self, result: Dict[str, Any], source: str
    ) -> Dict[str, Any]:
        """Normalize a crawl result from any source into a standardized format.

        Args:
            result: The result to normalize
            source: The source of the result (crawl4ai or firecrawl)

        Returns:
            A normalized result dictionary
        """
        # If result already indicates an error, pass it through
        if not result.get("success", False):
            return result

        # Ensure result has core fields
        normalized = {
            "success": True,
            "url": result.get("url", ""),
            "items": [],
            "timestamp": datetime.utcnow().isoformat(),
            "source": source,
        }

        # Normalize items
        items = result.get("items", [])
        normalized_items = []

        for item in items:
            normalized_item = {
                "title": item.get("title", ""),
                "content": item.get("content", ""),
                "url": item.get("url", normalized["url"]),
                "image_url": item.get("image_url", None),
                "timestamp": item.get("timestamp", normalized["timestamp"]),
                "metadata": item.get("metadata", {}),
            }
            normalized_items.append(normalized_item)

        normalized["items"] = normalized_items

        # Generate or pass through formatted summary
        if "formatted" in result:
            normalized["formatted"] = result["formatted"]
        else:
            normalized["formatted"] = self._generate_formatted_summary(normalized)

        return normalized

    def normalize_search_result(
        self, result: Dict[str, Any], source: str
    ) -> Dict[str, Any]:
        """Normalize a search result from any source into a standardized format.

        Args:
            result: The result to normalize
            source: The source of the result (crawl4ai or firecrawl)

        Returns:
            A normalized result dictionary
        """
        # If result already indicates an error, pass it through
        if not result.get("success", False):
            return result

        # Ensure result has core fields
        normalized = {
            "success": True,
            "query": result.get("query", ""),
            "items": [],
            "timestamp": datetime.utcnow().isoformat(),
            "source": source,
        }

        # Normalize items
        items = result.get("items", [])
        normalized_items = []

        for item in items:
            normalized_item = {
                "title": item.get("title", ""),
                "content": item.get("content", ""),
                "url": item.get("url", ""),
                "image_url": item.get("image_url", None),
                "timestamp": item.get("timestamp", normalized["timestamp"]),
                "metadata": item.get("metadata", {}),
            }
            normalized_items.append(normalized_item)

        normalized["items"] = normalized_items

        # Generate or pass through formatted summary
        if "formatted" in result:
            normalized["formatted"] = result["formatted"]
        else:
            normalized["formatted"] = self._generate_search_summary(normalized)

        return normalized

    def normalize_blog_result(
        self, result: Dict[str, Any], source: str, extract_type: str
    ) -> Dict[str, Any]:
        """Normalize a blog crawl result from any source into a standardized format.

        Args:
            result: The result to normalize
            source: The source of the result (crawl4ai or firecrawl)
            extract_type: Type of extraction (insights, itinerary, tips, places)

        Returns:
            A normalized result dictionary
        """
        # If result already indicates an error, pass it through
        if not result.get("success", False):
            return result

        # Start with standard normalization
        normalized = self.normalize_crawl_result(result, source)

        # Add blog-specific fields
        normalized["extract_type"] = extract_type

        # Process extracted data based on extract_type
        for item in normalized["items"]:
            extracted_data = item.get("extracted_data", {})

            if extract_type == "insights":
                item["insights"] = extracted_data.get("insights", [])
            elif extract_type == "itinerary":
                item["itinerary"] = extracted_data.get("itinerary", [])
            elif extract_type == "tips":
                item["tips"] = extracted_data.get("tips", [])
            elif extract_type == "places":
                item["places"] = extracted_data.get("places", [])

        return normalized

    def normalize_price_result(
        self, result: Dict[str, Any], source: str
    ) -> Dict[str, Any]:
        """Normalize a price monitoring result from any source
        into a standardized format.

        Args:
            result: The result to normalize
            source: The source of the result (crawl4ai or firecrawl)

        Returns:
            A normalized result dictionary
        """
        # If result already indicates an error, pass it through
        if not result.get("success", False):
            return result

        # Start with standard normalization
        normalized = self.normalize_crawl_result(result, source)

        # Add price-specific fields for each item
        for i, item in enumerate(normalized["items"]):
            # Get original item
            original_item = (
                result.get("items", [])[i] if i < len(result.get("items", [])) else {}
            )

            # Add price fields
            item["price"] = original_item.get("price", 0)
            item["currency"] = original_item.get("currency", "USD")
            item["availability"] = original_item.get("availability", "")

            # Add timestamp for price tracking
            item["price_timestamp"] = datetime.utcnow().isoformat()

        return normalized

    def normalize_events_result(
        self, result: Dict[str, Any], source: str
    ) -> Dict[str, Any]:
        """Normalize an events result from any source into a standardized format.

        Args:
            result: The result to normalize
            source: The source of the result (crawl4ai or firecrawl)

        Returns:
            A normalized result dictionary
        """
        # If result already indicates an error, pass it through
        if not result.get("success", False):
            return result

        # Ensure result has core fields
        normalized = {
            "success": True,
            "destination": result.get("destination", ""),
            "items": [],
            "timestamp": datetime.utcnow().isoformat(),
            "source": source,
            "research_summary": result.get("research_summary", ""),
        }

        # Normalize event items
        items = result.get("items", [])
        normalized_items = []

        for item in items:
            normalized_item = {
                "title": item.get("title", ""),
                "description": item.get("content", ""),
                "url": item.get("url", ""),
                "image_url": item.get("image_url", None),
                "start_date": item.get("start_date", None),
                "end_date": item.get("end_date", None),
                "location": item.get("location", ""),
                "venue": item.get("venue", ""),
                "event_type": item.get("event_type", ""),
                "timestamp": item.get("timestamp", normalized["timestamp"]),
                "metadata": item.get("metadata", {}),
            }
            normalized_items.append(normalized_item)

        normalized["items"] = normalized_items

        # Generate or pass through formatted summary
        if "formatted" in result:
            normalized["formatted"] = result["formatted"]
        else:
            normalized["formatted"] = self._generate_events_summary(normalized)

        return normalized

    def _generate_formatted_summary(self, result: Dict[str, Any]) -> str:
        """Generate a formatted summary for a crawl result.

        Args:
            result: The normalized result

        Returns:
            A human-readable summary
        """
        url = result.get("url", "")
        items = result.get("items", [])

        if not items:
            return f"Successfully crawled {url}, but no content was found."

        total_content_length = sum(len(item.get("content", "")) for item in items)

        return (
            f"Successfully crawled {url} and found {len(items)} content blocks "
            f"with a total of {total_content_length} characters."
        )

    def _generate_search_summary(self, result: Dict[str, Any]) -> str:
        """Generate a formatted summary for a search result.

        Args:
            result: The normalized result

        Returns:
            A human-readable summary
        """
        query = result.get("query", "")
        items = result.get("items", [])

        if not items:
            return f"Search for '{query}' returned no results."

        return f"Search for '{query}' returned {len(items)} results."

    def _generate_events_summary(self, result: Dict[str, Any]) -> str:
        """Generate a formatted summary for an events result.

        Args:
            result: The normalized result

        Returns:
            A human-readable summary
        """
        destination = result.get("destination", "")
        items = result.get("items", [])

        if not items:
            if result.get("research_summary"):
                return f"Found information about events in {destination}."
            return f"No events found in {destination}."

        return f"Found {len(items)} events in {destination}."


# Singleton instance
result_normalizer = ResultNormalizer()


def get_normalizer() -> ResultNormalizer:
    """Get the singleton instance of the result normalizer.

    Returns:
        The normalizer instance
    """
    return result_normalizer
