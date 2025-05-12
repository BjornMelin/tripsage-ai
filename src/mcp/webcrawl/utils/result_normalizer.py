"""Utility functions for normalizing results from different web sources.

This module provides tools for standardizing data structures, confidence scores,
and metadata from different web crawling sources to ensure consistent results
regardless of the underlying source.
"""

import datetime
import re
from typing import Any, Dict

from src.utils.logging import get_logger

# Initialize logger
logger = get_logger(__name__)


class ResultNormalizer:
    """Normalizes web crawl results for consistent output structure.

    This class ensures consistent data structures, confidence scores,
    and metadata from different web sources regardless of their specific
    formats and structures.
    """

    def __init__(self):
        """Initialize the result normalizer."""
        # Default confidence levels by source
        self.default_confidence = {
            "crawl4ai": 0.85,
            "playwright": 0.75,
            "websearch": 0.65,
            "unknown": 0.50,
        }

        # Keywords for category detection
        self.category_keywords = {
            "attraction": [
                "attraction",
                "landmark",
                "monument",
                "sight",
                "museum",
                "gallery",
                "park",
                "garden",
                "palace",
                "castle",
                "temple",
            ],
            "restaurant": [
                "restaurant",
                "dining",
                "cafe",
                "bistro",
                "eatery",
                "food",
                "cuisine",
                "dish",
                "meal",
                "eat",
                "dinner",
            ],
            "hotel": [
                "hotel",
                "accommodation",
                "lodging",
                "motel",
                "inn",
                "hostel",
                "resort",
                "stay",
                "room",
                "suite",
                "airbnb",
            ],
            "transport": [
                "transport",
                "travel",
                "bus",
                "train",
                "subway",
                "metro",
                "taxi",
                "uber",
                "car",
                "bike",
                "scooter",
                "flight",
            ],
            "activity": [
                "activity",
                "tour",
                "experience",
                "adventure",
                "excursion",
                "trip",
                "visit",
                "hiking",
                "biking",
                "sightseeing",
            ],
            "shopping": [
                "shopping",
                "shop",
                "store",
                "mall",
                "market",
                "boutique",
                "outlet",
                "souvenir",
                "buy",
                "purchase",
                "sale",
            ],
        }

    def normalize_destination_results(
        self, results: Dict[str, Any], source_type: str
    ) -> Dict[str, Any]:
        """Normalize destination search results.

        Args:
            results: Raw search results from a source
            source_type: Type of source ("crawl4ai", "playwright", or "websearch")

        Returns:
            Normalized results with consistent structure and metadata
        """
        try:
            normalized = {
                "destination": results.get("destination", ""),
                "topics": {},
                "sources": results.get("sources", []),
                "metadata": {
                    "source": source_type,
                    "normalization_timestamp": datetime.datetime.utcnow().isoformat(),
                    "original_timestamp": results.get("search_timestamp", ""),
                    "confidence": self.default_confidence.get(source_type, 0.5),
                },
            }

            # Handle potential error/fallback case
            if "error" in results or "fallback_type" in results:
                normalized["metadata"]["has_error"] = True
                normalized["metadata"]["error_message"] = results.get(
                    "error", "Unknown error"
                )

                # Pass through any fallback guidance
                if "websearch_tool_guidance" in results:
                    normalized["websearch_tool_guidance"] = results[
                        "websearch_tool_guidance"
                    ]

                return normalized

            # Process each topic
            for topic, topic_results in results.get("topics", {}).items():
                normalized_topic_results = []

                for result in topic_results:
                    normalized_result = self._normalize_content_item(
                        item=result, topic=topic, source_type=source_type
                    )
                    normalized_topic_results.append(normalized_result)

                normalized["topics"][topic] = normalized_topic_results

            return normalized

        except Exception as e:
            logger.error(f"Error normalizing destination results: {str(e)}")
            # Return a minimal normalized structure with error info
            return {
                "destination": results.get("destination", ""),
                "topics": {},
                "sources": results.get("sources", []),
                "metadata": {
                    "source": source_type,
                    "normalization_timestamp": datetime.datetime.utcnow().isoformat(),
                    "has_error": True,
                    "error_message": f"Normalization error: {str(e)}",
                },
            }

    def normalize_events_results(
        self, results: Dict[str, Any], source_type: str
    ) -> Dict[str, Any]:
        """Normalize events search results.

        Args:
            results: Raw events results from a source
            source_type: Type of source ("crawl4ai", "playwright", or "websearch")

        Returns:
            Normalized events results with consistent structure and metadata
        """
        try:
            normalized = {
                "destination": results.get("destination", ""),
                "date_range": results.get("date_range", {}),
                "events": [],
                "sources": results.get("sources", []),
                "metadata": {
                    "source": source_type,
                    "normalization_timestamp": datetime.datetime.utcnow().isoformat(),
                    "original_timestamp": results.get("search_timestamp", ""),
                    "confidence": self.default_confidence.get(source_type, 0.5),
                },
            }

            # Handle potential error case
            if "error" in results:
                normalized["metadata"]["has_error"] = True
                normalized["metadata"]["error_message"] = results["error"]
                return normalized

            # Process each event
            for event in results.get("events", []):
                normalized_event = self._normalize_event_item(
                    event=event, source_type=source_type
                )
                normalized["events"].append(normalized_event)

            return normalized

        except Exception as e:
            logger.error(f"Error normalizing events results: {str(e)}")
            # Return a minimal normalized structure with error info
            return {
                "destination": results.get("destination", ""),
                "date_range": results.get("date_range", {}),
                "events": [],
                "sources": results.get("sources", []),
                "metadata": {
                    "source": source_type,
                    "normalization_timestamp": datetime.datetime.utcnow().isoformat(),
                    "has_error": True,
                    "error_message": f"Normalization error: {str(e)}",
                },
            }

    def normalize_blog_results(
        self, results: Dict[str, Any], source_type: str
    ) -> Dict[str, Any]:
        """Normalize blog crawl results.

        Args:
            results: Raw blog results from a source
            source_type: Type of source ("crawl4ai", "playwright", or "websearch")

        Returns:
            Normalized blog results with consistent structure and metadata
        """
        try:
            normalized = {
                "destination": results.get("destination", ""),
                "topics": {},
                "sources": results.get("sources", []),
                "extraction_date": results.get(
                    "extraction_date", datetime.datetime.utcnow().isoformat()
                ),
                "metadata": {
                    "source": source_type,
                    "normalization_timestamp": datetime.datetime.utcnow().isoformat(),
                    "confidence": self.default_confidence.get(source_type, 0.5),
                },
            }

            # Handle potential error case
            if "error" in results:
                normalized["metadata"]["has_error"] = True
                normalized["metadata"]["error_message"] = results["error"]
                return normalized

            # Process each topic
            for topic, topic_results in results.get("topics", {}).items():
                normalized_topic_results = []

                for result in topic_results:
                    normalized_result = self._normalize_blog_topic(
                        topic_item=result, topic=topic, source_type=source_type
                    )
                    normalized_topic_results.append(normalized_result)

                normalized["topics"][topic] = normalized_topic_results

            return normalized

        except Exception as e:
            logger.error(f"Error normalizing blog results: {str(e)}")
            # Return a minimal normalized structure with error info
            return {
                "destination": results.get("destination", ""),
                "topics": {},
                "sources": results.get("sources", []),
                "extraction_date": datetime.datetime.utcnow().isoformat(),
                "metadata": {
                    "source": source_type,
                    "normalization_timestamp": datetime.datetime.utcnow().isoformat(),
                    "has_error": True,
                    "error_message": f"Normalization error: {str(e)}",
                },
            }

    def _normalize_content_item(
        self, item: Dict[str, Any], topic: str, source_type: str
    ) -> Dict[str, Any]:
        """Normalize a single content item from destination results.

        Args:
            item: Raw content item
            topic: Topic for context
            source_type: Type of source

        Returns:
            Normalized content item with consistent fields
        """
        # Start with a base normalized item with all potentially missing fields
        normalized = {
            "title": item.get("title", ""),
            "content": item.get("content", ""),
            "summary": item.get(
                "summary", self._generate_summary(item.get("content", ""))
            ),
            "source": item.get("source", ""),
            "url": item.get("url", ""),
            "image_url": item.get("image_url", ""),
            "category": item.get("category", self._detect_category(item, topic)),
            "confidence": item.get(
                "confidence", self.default_confidence.get(source_type, 0.5)
            ),
            "metadata": {
                "source_type": source_type,
                "extraction_method": item.get("extraction_method", source_type),
                "extraction_timestamp": item.get(
                    "timestamp", datetime.datetime.utcnow().isoformat()
                ),
                "normalized": True,
            },
        }

        # Add any additional fields from the original item
        for key, value in item.items():
            if key not in normalized and key not in ["metadata"]:
                normalized[key] = value

        return normalized

    def _normalize_event_item(
        self, event: Dict[str, Any], source_type: str
    ) -> Dict[str, Any]:
        """Normalize a single event item.

        Args:
            event: Raw event data
            source_type: Type of source

        Returns:
            Normalized event item with consistent fields
        """
        # Create a normalized event with all potentially missing fields
        normalized = {
            "name": event.get("name", ""),
            "description": event.get("description", ""),
            "category": event.get("category", self._detect_category(event, "event")),
            "date": event.get("date", ""),
            "time": event.get("time", ""),
            "venue": event.get("venue", ""),
            "address": event.get("address", ""),
            "url": event.get("url", ""),
            "price_range": event.get("price_range", ""),
            "image_url": event.get("image_url", ""),
            "source": event.get("source", ""),
            "confidence": event.get(
                "confidence", self.default_confidence.get(source_type, 0.5)
            ),
            "metadata": {
                "source_type": source_type,
                "extraction_method": event.get("extraction_method", source_type),
                "extraction_timestamp": event.get(
                    "timestamp", datetime.datetime.utcnow().isoformat()
                ),
                "normalized": True,
            },
        }

        # Add any additional fields from the original event
        for key, value in event.items():
            if key not in normalized and key not in ["metadata"]:
                normalized[key] = value

        return normalized

    def _normalize_blog_topic(
        self, topic_item: Dict[str, Any], topic: str, source_type: str
    ) -> Dict[str, Any]:
        """Normalize a single blog topic.

        Args:
            topic_item: Raw blog topic data
            topic: Topic context
            source_type: Type of source

        Returns:
            Normalized blog topic with consistent fields
        """
        # Create a normalized blog topic with all potentially missing fields
        normalized = {
            "title": topic_item.get("title", ""),
            "summary": topic_item.get("summary", ""),
            "key_points": topic_item.get("key_points", []),
            "sentiment": topic_item.get(
                "sentiment", self._detect_sentiment(topic_item)
            ),
            "source_index": topic_item.get("source_index", 0),
            "confidence": topic_item.get(
                "confidence", self.default_confidence.get(source_type, 0.5)
            ),
            "metadata": {
                "source_type": source_type,
                "extraction_method": topic_item.get("extraction_method", source_type),
                "extraction_timestamp": topic_item.get(
                    "timestamp", datetime.datetime.utcnow().isoformat()
                ),
                "normalized": True,
            },
        }

        # Add any additional fields from the original topic item
        for key, value in topic_item.items():
            if key not in normalized and key not in ["metadata"]:
                normalized[key] = value

        return normalized

    def _generate_summary(self, content: str, max_length: int = 300) -> str:
        """Generate a summary from content if not provided.

        Args:
            content: Content to summarize
            max_length: Maximum summary length

        Returns:
            Generated summary
        """
        if not content:
            return ""

        # Simple summarization: take first 2-3 sentences or first paragraph
        sentences = content.split(". ")
        if len(sentences) > 2:
            summary = ". ".join(sentences[:3])
            if not summary.endswith("."):
                summary += "."

            if len(summary) > max_length:
                return summary[:max_length] + "..."
            return summary

        # If few sentences, take a substring
        if len(content) > max_length:
            return content[:max_length] + "..."

        return content

    def _detect_category(self, item: Dict[str, Any], context: str) -> str:
        """Detect the category of an item based on content.

        Args:
            item: The item to categorize
            context: Context (topic or section) for additional clues

        Returns:
            Detected category
        """
        # If category is already provided, use it
        if "category" in item:
            return item["category"]

        # Use context as a primary clue
        if context in ["attractions", "landmarks", "sights"]:
            return "attraction"
        if context in ["restaurants", "food", "dining", "cuisine"]:
            return "restaurant"
        if context in ["hotels", "accommodations", "lodging"]:
            return "hotel"
        if context in ["transportation", "transport", "transit"]:
            return "transport"
        if context in ["activities", "tours", "excursions"]:
            return "activity"
        if context in ["shopping", "shops", "stores"]:
            return "shopping"

        # Search the title and content for category keywords
        search_text = ""
        if "title" in item and item["title"]:
            search_text += item["title"].lower() + " "
        if "content" in item and item["content"]:
            # Use first 200 chars of content for efficiency
            search_text += item["content"][:200].lower() + " "
        if "description" in item and item["description"]:
            search_text += item["description"][:200].lower() + " "

        # Count keyword matches for each category
        category_scores = {}
        for category, keywords in self.category_keywords.items():
            score = 0
            for keyword in keywords:
                if keyword in search_text:
                    score += 1
            if score > 0:
                category_scores[category] = score

        # Return the category with the highest score, or default
        if category_scores:
            return max(category_scores.items(), key=lambda x: x[1])[0]

        return "general"

    def _detect_sentiment(self, item: Dict[str, Any]) -> str:
        """Detect sentiment from content if not provided.

        Args:
            item: Item containing text content

        Returns:
            Detected sentiment (positive, neutral, negative)
        """
        # If sentiment is already provided, use it
        if "sentiment" in item:
            return item["sentiment"]

        # Simple rule-based sentiment detection
        positive_words = [
            "great",
            "excellent",
            "good",
            "best",
            "recommend",
            "amazing",
            "wonderful",
            "beautiful",
            "enjoy",
            "love",
            "favorite",
            "worth",
            "perfect",
            "fantastic",
            "spectacular",
        ]

        negative_words = [
            "bad",
            "poor",
            "terrible",
            "avoid",
            "disappointing",
            "overrated",
            "expensive",
            "crowded",
            "dirty",
            "dangerous",
            "waste",
            "mediocre",
            "terrible",
            "worst",
        ]

        # Collect text to analyze
        text = ""
        if "summary" in item and item["summary"]:
            text += item["summary"].lower() + " "
        if "key_points" in item and item["key_points"]:
            text += " ".join(item["key_points"]).lower() + " "

        # Count sentiment words
        positive_count = 0
        negative_count = 0

        for word in positive_words:
            positive_count += len(re.findall(r"\b" + word + r"\b", text))

        for word in negative_words:
            negative_count += len(re.findall(r"\b" + word + r"\b", text))

        # Determine sentiment based on word counts
        if positive_count > negative_count * 2:
            return "positive"
        elif negative_count > positive_count * 2:
            return "negative"
        elif positive_count > negative_count:
            return "slightly positive"
        elif negative_count > positive_count:
            return "slightly negative"
        else:
            return "neutral"


# Singleton instance for the result normalizer
_normalizer = None


def get_result_normalizer() -> ResultNormalizer:
    """Get or create the result normalizer instance.

    Returns:
        Result normalizer instance
    """
    global _normalizer

    if _normalizer is None:
        _normalizer = ResultNormalizer()

    return _normalizer
