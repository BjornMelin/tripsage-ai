"""Implementation of the Crawl4AI source for web crawling."""

import json
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import aiohttp

from src.mcp.webcrawl.config import Config
from src.mcp.webcrawl.sources.source_interface import (
    BlogInsights,
    CrawlSource,
    DestinationInfo,
    EventList,
    ExtractedContent,
    ExtractionOptions,
    MonitorOptions,
    PriceMonitorResult,
    TopicResult,
)
from src.utils.logging import get_logger

# Initialize logger
logger = get_logger(__name__)


class Crawl4AISource(CrawlSource):
    """Implementation of the Crawl4AI source for web crawling."""

    def __init__(self, api_url: Optional[str] = None, api_key: Optional[str] = None):
        """Initialize the Crawl4AI source.

        Args:
            api_url: Optional API URL, defaults to Config.CRAWL4AI_API_URL
            api_key: Optional API key, defaults to Config.CRAWL4AI_API_KEY
        """
        self.api_url = api_url or Config.CRAWL4AI_API_URL
        self.api_key = api_key or Config.CRAWL4AI_API_KEY

    async def _make_request(
        self, endpoint: str, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Make a request to the Crawl4AI API.

        Args:
            endpoint: API endpoint (e.g., '/extract')
            data: Request data

        Returns:
            API response data

        Raises:
            Exception: If the API request fails
        """
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.api_url}{endpoint}"
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                }

                logger.debug(f"Making request to {url}")

                async with session.post(
                    url, headers=headers, json=data, timeout=Config.REQUEST_TIMEOUT
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(
                            f"Crawl4AI API error: {response.status} - {error_text}"
                        )

                    return await response.json()
        except aiohttp.ClientError as e:
            logger.error(f"Network error when calling Crawl4AI API: {str(e)}")
            raise Exception(f"Failed to connect to Crawl4AI API: {str(e)}") from e
        except json.JSONDecodeError as e:
            logger.error("Failed to parse JSON response from Crawl4AI API")
            raise Exception("Invalid response format from Crawl4AI API") from e
        except Exception as e:
            logger.error(f"Unexpected error when calling Crawl4AI API: {str(e)}")
            raise

    async def extract_page_content(
        self, url: str, options: Optional[ExtractionOptions] = None
    ) -> ExtractedContent:
        """Extract content from a webpage using Crawl4AI.

        Args:
            url: The URL of the webpage to extract content from
            options: Optional extraction options

        Returns:
            The extracted content

        Raises:
            Exception: If the extraction fails
        """
        options = options or {}

        # Prepare extraction request
        extraction_request = {
            "url": url,
            "output_format": options.get("format", "markdown"),
            "selectors": options.get("selectors", []),
            "include_images": options.get("include_images", False),
            "wait_time": options.get("wait", 0),
            "timeout": options.get(
                "timeout", Config.REQUEST_TIMEOUT * 1000
            ),  # Convert to milliseconds
        }

        try:
            # Call Crawl4AI API
            result = await self._make_request("/extract", extraction_request)

            # Process and return the result
            return {
                "url": url,
                "title": result.get("title", self._extract_title_from_url(url)),
                "content": result.get("content", ""),
                "images": (
                    result.get("images") if options.get("include_images") else None
                ),
                "metadata": {
                    "author": result.get("metadata", {}).get("author"),
                    "publish_date": result.get("metadata", {}).get("publish_date"),
                    "last_modified": result.get("metadata", {}).get("last_modified"),
                    "site_name": result.get("metadata", {}).get("site_name"),
                },
                "format": options.get("format", "markdown"),
            }
        except Exception as e:
            logger.error(f"Error extracting content from {url}: {str(e)}")
            raise Exception(f"Failed to extract page content: {str(e)}") from e

    async def search_destination_info(
        self, destination: str, topics: Optional[List[str]] = None, max_results: int = 5
    ) -> DestinationInfo:
        """Search for information about a travel destination using Crawl4AI.

        Args:
            destination: The name of the destination
            topics: Optional list of topics to search for
            max_results: Maximum number of results per topic

        Returns:
            Information about the destination

        Raises:
            Exception: If the search fails
        """
        try:
            # Prepare search topics if not provided
            search_topics = topics or [
                "attractions",
                "things to do",
                "best time to visit",
                "local cuisine",
                "transportation",
            ]

            # Prepare batch search request
            search_requests = [
                {
                    "query": f"{destination} {topic}",
                    "max_results": max_results,
                    "extract_content": True,
                }
                for topic in search_topics
            ]

            # Call Crawl4AI batch search API
            batch_results = await self._make_request(
                "/batch_search", {"searches": search_requests}
            )

            # Initialize result structure
            result: DestinationInfo = {
                "destination": destination,
                "topics": {},
                "sources": [],
            }

            # Process batch search results
            for i, topic in enumerate(search_topics):
                result["topics"][topic] = []

                if (
                    "results" in batch_results
                    and i < len(batch_results["results"])
                    and "items" in batch_results["results"][i]
                ):
                    for item in batch_results["results"][i]["items"]:
                        # Extract domain from URL
                        domain = self._extract_domain(item.get("url", ""))

                        # Create topic result
                        topic_result: TopicResult = {
                            "title": item.get("title", ""),
                            "content": item.get("content", item.get("snippet", "")),
                            "source": item.get("domain", domain),
                            "url": item.get("url", ""),
                            "confidence": item.get("relevance_score", 0.8),
                        }

                        result["topics"][topic].append(topic_result)

                        # Add source to sources list if not already there
                        if (
                            topic_result["source"]
                            and topic_result["source"] not in result["sources"]
                        ):
                            result["sources"].append(topic_result["source"])

            return result
        except Exception as e:
            logger.error(
                f"Error searching destination info for {destination}: {str(e)}"
            )
            raise Exception(
                f"Failed to search destination information: {str(e)}"
            ) from e

    async def monitor_price_changes(
        self, url: str, price_selector: str, options: Optional[MonitorOptions] = None
    ) -> PriceMonitorResult:
        """Set up monitoring for price changes on a webpage using Crawl4AI.

        Args:
            url: The URL of the webpage to monitor
            price_selector: CSS selector for the price element
            options: Optional monitoring options

        Returns:
            The price monitoring result

        Raises:
            Exception: If the monitoring setup fails
        """
        options = options or {}

        try:
            # Set up price monitoring with Crawl4AI
            monitor_request = {
                "url": url,
                "selector": price_selector,
                "frequency": options.get("frequency", "daily"),
                "threshold_percent": options.get("notification_threshold", 5),
                "start_date": options.get("start_date"),
                "end_date": options.get("end_date"),
            }

            # Call Crawl4AI price monitoring API
            result = await self._make_request("/monitor_price", monitor_request)

            # Process result into PriceMonitorResult structure
            initial_price = result.get("initial_price")
            current_price = result.get("current_price")

            return {
                "url": url,
                "initial_price": (
                    {
                        "amount": initial_price["amount"],
                        "currency": initial_price["currency"],
                        "timestamp": initial_price["timestamp"],
                    }
                    if initial_price
                    else None
                ),
                "current_price": (
                    {
                        "amount": current_price["amount"],
                        "currency": current_price["currency"],
                        "timestamp": current_price["timestamp"],
                    }
                    if current_price
                    else None
                ),
                "monitoring_id": result.get("monitoring_id", ""),
                "status": result.get("status", "scheduled"),
                "history": result.get("history"),
                "next_check": result.get("next_check"),
            }
        except Exception as e:
            logger.error(f"Error setting up price monitoring for {url}: {str(e)}")
            raise Exception(f"Failed to monitor price changes: {str(e)}") from e

    async def get_latest_events(
        self,
        destination: str,
        start_date: str,
        end_date: str,
        categories: Optional[List[str]] = None,
    ) -> EventList:
        """Get latest events for a destination using Crawl4AI.

        Args:
            destination: The name of the destination
            start_date: Start date (ISO format)
            end_date: End date (ISO format)
            categories: Optional list of event categories

        Returns:
            List of events

        Raises:
            Exception: If the event search fails
        """
        try:
            # Prepare event search request
            event_request = {
                "destination": destination,
                "date_range": {"start_date": start_date, "end_date": end_date},
                "categories": categories or [],
            }

            # Call Crawl4AI event search API
            result = await self._make_request("/events", event_request)

            # Map to our interface
            return {
                "destination": destination,
                "date_range": {"start_date": start_date, "end_date": end_date},
                "events": [
                    {
                        "name": event.get("name", ""),
                        "description": event.get("description", ""),
                        "category": event.get("category", ""),
                        "date": event.get("date", ""),
                        "time": event.get("time"),
                        "venue": event.get("venue"),
                        "address": event.get("address"),
                        "url": event.get("url"),
                        "price_range": event.get("price_range"),
                        "image_url": event.get("image_url"),
                        "source": event.get("source", ""),
                    }
                    for event in result.get("events", [])
                ],
                "sources": result.get("sources", []),
            }
        except Exception as e:
            logger.error(f"Error getting events for {destination}: {str(e)}")
            raise Exception(f"Failed to get latest events: {str(e)}") from e

    async def crawl_travel_blog(
        self,
        destination: str,
        topics: Optional[List[str]] = None,
        max_blogs: int = 3,
        recent_only: bool = True,
    ) -> BlogInsights:
        """Extract insights from travel blogs using Crawl4AI.

        Args:
            destination: The name of the destination
            topics: Optional list of topics to extract
            max_blogs: Maximum number of blogs to crawl
            recent_only: Whether to only crawl recent blogs

        Returns:
            The extracted insights

        Raises:
            Exception: If the blog crawling fails
        """
        try:
            # Prepare blog crawl request
            blog_request = {
                "destination": destination,
                "topics": topics or [],
                "max_blogs": max_blogs,
                "recent_only": recent_only,
            }

            # Call Crawl4AI blog crawl API
            result = await self._make_request("/crawl_blogs", blog_request)

            # Map to our interface
            return {
                "destination": destination,
                "topics": result.get("topics", {}),
                "sources": result.get("sources", []),
                "extraction_date": result.get("extraction_date", ""),
            }
        except Exception as e:
            logger.error(f"Error crawling travel blogs for {destination}: {str(e)}")
            raise Exception(f"Failed to crawl travel blogs: {str(e)}") from e

    def _extract_title_from_url(self, url: str) -> str:
        """Extract a title from a URL.

        Args:
            url: The URL to extract a title from

        Returns:
            The extracted title
        """
        try:
            parsed_url = urlparse(url)
            path_segments = parsed_url.path.split("/")

            # Filter out empty segments
            path_segments = [segment for segment in path_segments if segment]

            if path_segments:
                # Get the last segment
                last_segment = path_segments[-1]

                # Remove file extensions
                last_segment = last_segment.split(".")[0]

                # Replace hyphens with spaces
                last_segment = last_segment.replace("-", " ").replace("_", " ")

                # Capitalize words
                return " ".join(word.capitalize() for word in last_segment.split())

            return parsed_url.netloc
        except Exception:
            return url

    def _extract_domain(self, url: str) -> str:
        """Extract domain from a URL.

        Args:
            url: The URL to extract a domain from

        Returns:
            The extracted domain
        """
        try:
            parsed_url = urlparse(url)
            return parsed_url.netloc
        except Exception:
            return url
