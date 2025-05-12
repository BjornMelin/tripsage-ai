"""
TripSage Travel Insights Agent.

This module implements an agent for extracting travel-related information
using the WebCrawl MCP client. It demonstrates how to use the Crawl4AI MCP
server and Firecrawl for web crawling and extraction.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from src.mcp.webcrawl.client import WebCrawlMCPClient
from src.utils.logging import get_logger

# Initialize logger
logger = get_logger(__name__)


class TravelInsightsAgent:
    """
    Travel insights agent that uses WebCrawl MCP for destination research.

    This agent demonstrates how to leverage the Crawl4AI MCP server and Firecrawl
    for extracting travel-related information from the web.
    """

    def __init__(self):
        """Initialize the travel insights agent."""
        self.webcrawl_client = WebCrawlMCPClient()
        logger.info("Travel insights agent initialized")

    async def get_destination_insights(
        self, destination: str, topics: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Get comprehensive insights about a travel destination.

        Args:
            destination: The name of the destination
            topics: Optional list of specific topics to focus on

        Returns:
            A dictionary containing structured information about the destination
        """
        logger.info(f"Getting destination insights for {destination}")

        # Use WebCrawl MCP to search for destination information
        search_results = await self.webcrawl_client.search_destination_info(
            destination=destination,
            topics=topics or [
                "attractions",
                "best time to visit",
                "local cuisine",
                "transportation",
                "safety",
            ],
            max_results=5,
        )

        # Get travel blog insights for the destination
        blog_insights = await self.webcrawl_client.crawl_travel_blog(
            destination=destination,
            topics=["hidden gems", "local tips", "budget travel"],
            max_blogs=3,
        )

        # Calculate date range for upcoming events (next 30 days)
        today = datetime.now().date()
        end_date = (today + timedelta(days=30)).isoformat()

        # Get upcoming events at the destination
        try:
            events = await self.webcrawl_client.get_latest_events(
                destination=destination,
                start_date=today.isoformat(),
                end_date=end_date,
                categories=["cultural", "music", "food", "festivals"],
            )
        except Exception as e:
            logger.warning(f"Could not fetch events for {destination}: {str(e)}")
            events = {"events": []}

        # Combine all data into a structured response
        return {
            "destination": destination,
            "general_info": search_results,
            "blog_insights": blog_insights,
            "upcoming_events": events,
            "generated_at": datetime.now().isoformat(),
        }

    async def extract_from_travel_site(self, url: str) -> Dict[str, Any]:
        """
        Extract content from a travel-related website.

        Args:
            url: URL of the travel website to extract from

        Returns:
            A dictionary containing the extracted content
        """
        logger.info(f"Extracting content from {url}")

        # Extract content using the WebCrawl MCP client
        # The source selection (Crawl4AI, Firecrawl, or Playwright)
        # is automatically handled by the intelligent source selector
        content = await self.webcrawl_client.extract_page_content(
            url=url,
            include_images=True,
            format="markdown",
        )

        return {
            "url": url,
            "title": content.get("title", ""),
            "content": content.get("content", ""),
            "metadata": content.get("metadata", {}),
            "extracted_at": datetime.now().isoformat(),
        }

    async def monitor_accommodation_prices(
        self, url: str, price_selector: str
    ) -> Dict[str, Any]:
        """
        Set up price monitoring for accommodation.

        Args:
            url: URL of the accommodation listing
            price_selector: CSS selector for the price element

        Returns:
            A dictionary containing the price monitoring configuration
        """
        logger.info(f"Setting up price monitoring for {url}")

        # Use WebCrawl MCP to monitor price changes
        monitoring_config = await self.webcrawl_client.monitor_price_changes(
            url=url,
            price_selector=price_selector,
            frequency="daily",
            notification_threshold=5.0,  # 5% price change notification threshold
        )

        return {
            "url": url,
            "monitoring_id": monitoring_config.get("monitoring_id", ""),
            "current_price": monitoring_config.get("current_price", {}),
            "status": monitoring_config.get("status", ""),
            "next_check": monitoring_config.get("next_check", ""),
        }

    async def search_for_events(
        self, destination: str, start_date: str, end_date: str
    ) -> Dict[str, Any]:
        """
        Search for events at a destination during a specific time period.

        Args:
            destination: The name of the destination
            start_date: Start date in ISO format (YYYY-MM-DD)
            end_date: End date in ISO format (YYYY-MM-DD)

        Returns:
            A dictionary containing event listings with details
        """
        logger.info(
            f"Searching for events in {destination} from {start_date} to {end_date}"
        )

        # Use WebCrawl MCP to search for events
        events = await self.webcrawl_client.get_latest_events(
            destination=destination,
            start_date=start_date,
            end_date=end_date,
            categories=["all"],
        )

        # Process and categorize events
        categorized_events = {}
        for event in events.get("events", []):
            category = event.get("category", "Other")
            if category not in categorized_events:
                categorized_events[category] = []
            categorized_events[category].append(event)

        return {
            "destination": destination,
            "date_range": {"start_date": start_date, "end_date": end_date},
            "events_by_category": categorized_events,
            "total_events": len(events.get("events", [])),
            "sources": events.get("sources", []),
        }


# Example usage
async def main():
    """Run a simple demo of the travel insights agent."""
    agent = TravelInsightsAgent()
    
    # Get insights for Tokyo
    insights = await agent.get_destination_insights("Tokyo, Japan")
    print(f"Found {len(insights['general_info'].get('topics', {}))} topics for Tokyo")
    
    # Extract from a travel site
    content = await agent.extract_from_travel_site(
        "https://www.japan-guide.com/e/e2164.html"
    )
    print(f"Extracted content from {content['url']}: {content['title']}")


if __name__ == "__main__":
    asyncio.run(main())