"""Utility functions for structured WebSearchTool fallbacks in WebCrawl MCP.

This module provides helper functions for constructing structured guidance
when falling back to WebSearchTool from WebCrawl MCP, including query
templates, response parsers, and information extraction utilities.
"""

from typing import Any, Dict, List, Optional

from src.utils.logging import get_logger

# Initialize logger
logger = get_logger(__name__)


class WebSearchFallbackGuide:
    """Structured guidance for WebSearchTool fallbacks.

    This class provides structured templates and extraction patterns for
    falling back to WebSearchTool from WebCrawl MCP, including topic-specific
    query patterns, search strategies, and response processing.
    """

    def __init__(self):
        """Initialize the WebSearchFallbackGuide."""
        # Topic-specific query templates for better search results
        self.query_templates = {
            "general": "comprehensive travel guide {destination}",
            "attractions": "top attractions in {destination} must-see landmarks",
            "safety": "{destination} travel safety information warnings",
            "transportation": (
                "{destination} public transportation " "options getting around"
            ),
            "best_time": "best time to visit {destination} weather seasons",
            "budget": "{destination} travel cost budget accommodation food",
            "food": "best local cuisine {destination} traditional dishes",
            "culture": "{destination} cultural customs etiquette information",
            "day_trips": "best day trips from {destination} nearby attractions",
            "family": "{destination} family-friendly activities with kids",
            "events": "upcoming events festivals {destination} {date_range}",
            "weather": "{destination} weather forecast {month} climate",
            "accessibility": (
                "{destination} accessibility information wheelchair "
                "disabilities"
            ),
            "nightlife": "{destination} nightlife bars clubs entertainment",
            "shopping": "shopping districts markets {destination} souvenirs",
        }

        # Structured information extraction patterns
        self.extraction_patterns = {
            "attractions": [
                "Name of attraction",
                "Brief description",
                "Key features",
                "Typical visit duration",
                "Opening hours",
                "Admission fee or cost",
                "Location/address",
                "Transportation options",
                "Best time to visit",
                "Visitor tips",
            ],
            "safety": [
                "Overall safety rating",
                "Common safety concerns",
                "Areas to avoid",
                "Local emergency numbers",
                "Healthcare information",
                "Travel advisories",
                "Safety tips for tourists",
                "Scams to watch out for",
                "Natural disaster risks",
                "Political situation",
            ],
            "transportation": [
                "Public transportation options",
                "Cost of different transport modes",
                "Payment methods",
                "Operating hours",
                "Coverage area",
                "Reliability assessment",
                "Accessibility",
                "Tourist passes available",
                "Transport from airport to city",
                "Ride-sharing services",
            ],
            "events": [
                "Event name",
                "Date and time",
                "Location",
                "Description",
                "Admission details",
                "Target audience",
                "Cultural significance",
                "Booking requirements",
                "Local popularity",
                "Transportation options",
            ],
        }

        # Information prioritization based on traveler needs
        self.information_priorities = {
            "safety_first": ["safety", "transportation", "healthcare", "weather"],
            "family_focused": [
                "family",
                "safety",
                "attractions",
                "food",
                "accommodation",
            ],
            "budget_traveler": ["budget", "transportation", "free_activities", "food"],
            "luxury_experience": ["high_end", "exclusive", "fine_dining", "premium"],
            "cultural_immersion": ["culture", "local_customs", "food", "history"],
            "adventure_seeker": [
                "outdoor_activities",
                "adventure",
                "nature",
                "thrills",
            ],
        }

        # Search domain filtering for targeted results
        self.domain_configurations = {
            "official_sources": {
                "allowed_domains": ["gov", "org", "edu", "travel.state.gov"],
                "blocked_domains": ["pinterest", "quora", "reddit"],
            },
            "traveler_reviews": {
                "allowed_domains": ["tripadvisor", "yelp", "google.com/maps"],
                "blocked_domains": ["pinterest", "facebook"],
            },
            "travel_guides": {
                "allowed_domains": [
                    "lonelyplanet",
                    "frommers",
                    "fodors",
                    "timeout",
                    "wikitravel",
                ],
                "blocked_domains": ["pinterest", "instagram"],
            },
        }

    def get_query_for_topic(
        self,
        destination: str,
        topic: str,
        additional_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Construct an optimized search query for a specific topic.

        Args:
            destination: The name of the travel destination
            topic: The specific topic to search for
            additional_context: Additional parameters to format into the template

        Returns:
            Formatted search query string
        """
        # Get the template for the specific topic, or use a generic one
        template = self.query_templates.get(
            topic, "travel information {destination} {topic}"
        )

        # Create context dictionary for template formatting
        context = {"destination": destination, "topic": topic}
        if additional_context:
            context.update(additional_context)

        # Format and return the query
        formatted_query = template.format(**context)
        logger.info(f"Generated optimized query: {formatted_query}")
        return formatted_query

    def get_extraction_guidance(self, topic: str) -> List[str]:
        """Get structured information extraction guidance for a topic.

        Args:
            topic: The topic for information extraction

        Returns:
            List of information points to extract
        """
        # Get the extraction pattern for the topic, or return a generic one
        extraction_points = self.extraction_patterns.get(
            topic, ["Name", "Description", "Key features", "Practical information"]
        )

        return extraction_points

    def get_domain_configuration(self, search_type: str) -> Dict[str, List[str]]:
        """Get domain configuration for targeted search.

        Args:
            search_type: Type of search ("official_sources", "traveler_reviews", etc.)

        Returns:
            Dict with allowed_domains and blocked_domains lists
        """
        # Get the domain configuration for the search type, or return empty lists
        config = self.domain_configurations.get(
            search_type, {"allowed_domains": [], "blocked_domains": []}
        )

        return config

    def get_structured_search_plan(
        self, destination: str, topic: str, traveler_profile: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate a structured search plan for WebSearchTool fallback.

        Args:
            destination: The travel destination
            topic: The information topic
            traveler_profile: Optional traveler profile for prioritization

        Returns:
            Dict containing complete search plan with queries,
                priorities and extraction guidance
        """
        # Initialize the search plan
        search_plan = {
            "destination": destination,
            "topic": topic,
            "traveler_profile": traveler_profile,
            "queries": [],
            "domain_configuration": {},
            "extraction_guidance": self.get_extraction_guidance(topic),
        }

        # Generate main query
        main_query = self.get_query_for_topic(destination, topic)
        search_plan["queries"].append({"query": main_query, "priority": "high"})

        # Generate auxiliary queries for completeness
        if topic == "attractions":
            search_plan["queries"].append(
                {
                    "query": (
                        f"hidden gems secret spots {destination} "
                        "off the beaten path"
                    ),
                    "priority": "medium",
                }
            )
        elif topic == "safety":
            search_plan["queries"].append(
                {
                    "query": f"latest travel advisories {destination} safety updates",
                    "priority": "high",
                }
            )

        # Add domain configuration based on topic
        if topic in ["safety", "health"]:
            search_plan["domain_configuration"] = self.get_domain_configuration(
                "official_sources"
            )
        elif topic in ["attractions", "food", "restaurants"]:
            search_plan["domain_configuration"] = self.get_domain_configuration(
                "traveler_reviews"
            )
        else:
            search_plan["domain_configuration"] = self.get_domain_configuration(
                "travel_guides"
            )

        # Add information priorities based on traveler profile
        if traveler_profile and traveler_profile in self.information_priorities:
            search_plan["information_priorities"] = self.information_priorities[
                traveler_profile
            ]

        return search_plan

    def get_response_format_guide(self, topic: str) -> Dict[str, Any]:
        """Generate guidance for formatting search results.

        Args:
            topic: The information topic

        Returns:
            Dict containing response format specifications
        """
        # Base response format
        response_format = {
            "format_version": "1.0",
            "structure": "topic_specific",
            "sections": [],
            "metadata": {
                "include_sources": True,
                "confidence_scoring": True,
                "timestamp_info": True,
            },
        }

        # Topic-specific sections
        if topic == "attractions":
            response_format["sections"] = [
                {"name": "top_attractions", "count": 5, "include_details": True},
                {"name": "hidden_gems", "count": 3, "include_details": True},
                {"name": "practical_info", "count": 1, "include_details": True},
            ]
        elif topic == "safety":
            response_format["sections"] = [
                {"name": "safety_overview", "count": 1, "include_details": True},
                {"name": "areas_to_avoid", "count": 1, "include_details": True},
                {"name": "health_information", "count": 1, "include_details": True},
                {"name": "emergency_contacts", "count": 1, "include_details": True},
            ]
        elif topic == "events":
            response_format["sections"] = [
                {"name": "upcoming_events", "count": 5, "include_details": True},
                {"name": "annual_festivals", "count": 3, "include_details": True},
                {"name": "booking_information", "count": 1, "include_details": True},
            ]
        else:
            # Generic format for other topics
            response_format["sections"] = [
                {"name": "overview", "count": 1, "include_details": True},
                {"name": "key_information", "count": 5, "include_details": True},
                {"name": "practical_tips", "count": 3, "include_details": True},
            ]

        return response_format


def create_fallback_guidance(
    destination: str, topic: str, traveler_profile: Optional[str] = None
) -> Dict[str, Any]:
    """Create structured guidance for WebSearchTool fallback.

    This is the main entry point for generating structured guidance
    when falling back to WebSearchTool.

    Args:
        destination: The travel destination
        topic: The information topic
        traveler_profile: Optional traveler profile

    Returns:
        Dict containing complete structured guidance
    """
    guide = WebSearchFallbackGuide()

    # Create complete guidance with search plan and response format
    guidance = {
        "search_plan": guide.get_structured_search_plan(
            destination, topic, traveler_profile
        ),
        "response_format": guide.get_response_format_guide(topic),
        "fallback_reason": "WebCrawl MCP extraction failed",
        "fallback_timestamp": None,  # Will be filled at runtime
    }

    return guidance
