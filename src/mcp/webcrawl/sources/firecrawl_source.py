"""Implementation of the Firecrawl source for web crawling."""

import json
from typing import Any, Dict, List, Optional
from datetime import datetime

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


class FirecrawlSource(CrawlSource):
    """Implementation of the Firecrawl source for web crawling."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the Firecrawl source.

        Args:
            api_key: Optional API key, defaults to Config.FIRECRAWL_API_KEY
        """
        self.api_key = api_key or settings.webcrawl_mcp.firecrawl_api_key.get_secret_value()
        self.api_url = "https://api.firecrawl.dev/v1"

    async def _make_request(
        self, endpoint: str, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Make a request to the Firecrawl API.

        Args:
            endpoint: API endpoint (e.g., '/scrape')
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

                logger.debug(f"Making request to Firecrawl API: {url}")

                async with session.post(
                    url, headers=headers, json=data, timeout=Config.REQUEST_TIMEOUT
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(
                            f"Firecrawl API error: {response.status} - {error_text}"
                        )

                    return await response.json()
        except aiohttp.ClientError as e:
            logger.error(f"Network error when calling Firecrawl API: {str(e)}")
            raise Exception(f"Failed to connect to Firecrawl API: {str(e)}") from e
        except json.JSONDecodeError as e:
            logger.error("Failed to parse JSON response from Firecrawl API")
            raise Exception("Invalid response format from Firecrawl API") from e
        except Exception as e:
            logger.error(f"Unexpected error when calling Firecrawl API: {str(e)}")
            raise

    async def extract_page_content(
        self, url: str, options: Optional[ExtractionOptions] = None
    ) -> ExtractedContent:
        """Extract content from a webpage using Firecrawl.

        Args:
            url: The URL of the webpage to extract content from
            options: Optional extraction options

        Returns:
            The extracted content

        Raises:
            Exception: If the extraction fails
        """
        options = options or {}

        try:
            # Prepare scrape request
            scrape_request = {
                "url": url,
                "formats": [options.get("format", "markdown")],
                "onlyMainContent": True,
                "includeTags": options.get("selectors", []),
                "excludeTags": [],
                "waitFor": options.get("wait", 0),
                "timeout": options.get("timeout", Config.REQUEST_TIMEOUT * 1000),
            }

            # Add images if requested
            if options.get("include_images", False):
                scrape_request["formats"].append("screenshot")

            # Call Firecrawl API
            result = await self._make_request("/scrape", scrape_request)

            if not result.get("success"):
                raise Exception(f"Firecrawl scraping failed: {result.get('error')}")

            data = result.get("data", {})
            
            # Extract metadata from the result
            metadata = data.get("metadata", {})
            
            # Process and return the result
            return {
                "url": url,
                "title": metadata.get("title", self._extract_title_from_url(url)),
                "content": data.get(options.get("format", "markdown"), ""),
                "images": data.get("screenshot") if options.get("include_images") else None,
                "metadata": {
                    "author": metadata.get("author"),
                    "publish_date": metadata.get("publishDate"),
                    "last_modified": metadata.get("lastModified"),
                    "site_name": metadata.get("ogSiteName"),
                    "language": metadata.get("language"),
                    "description": metadata.get("description"),
                },
                "format": options.get("format", "markdown"),
            }
        except Exception as e:
            logger.error(f"Error extracting content from {url} with Firecrawl: {str(e)}")
            raise Exception(f"Failed to extract page content with Firecrawl: {str(e)}") from e

    async def search_destination_info(
        self, destination: str, topics: Optional[List[str]] = None, max_results: int = 5
    ) -> DestinationInfo:
        """Search for information about a travel destination using Firecrawl.

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

            # Initialize result structure
            result: DestinationInfo = {
                "destination": destination,
                "topics": {},
                "sources": [],
            }

            # For each topic, perform a search and extract content
            for topic in search_topics:
                # Build search query
                query = f"{destination} {topic} travel guide"
                
                # Configure search request
                search_request = {
                    "query": query,
                    "limit": max_results,
                    "scrapeOptions": {
                        "formats": ["markdown"],
                        "onlyMainContent": True
                    }
                }
                
                # Call Firecrawl search API
                search_result = await self._make_request("/search", search_request)
                
                if not search_result.get("success"):
                    logger.warning(f"Firecrawl search failed for {query}: {search_result.get('error')}")
                    continue
                
                # Initialize topic results
                result["topics"][topic] = []
                
                # Process search results
                for item in search_result.get("data", []):
                    # Extract domain from URL
                    source_url = item.get("url", "")
                    domain = self._extract_domain(source_url)
                    
                    # Create topic result
                    topic_result: TopicResult = {
                        "title": item.get("title", ""),
                        "content": item.get("markdown", item.get("snippet", "")),
                        "source": domain,
                        "url": source_url,
                        "confidence": 0.8,  # Firecrawl doesn't provide confidence scores
                    }
                    
                    result["topics"][topic].append(topic_result)
                    
                    # Add source to sources list if not already there
                    if domain and domain not in result["sources"]:
                        result["sources"].append(domain)

            return result
        except Exception as e:
            logger.error(f"Error searching destination info with Firecrawl for {destination}: {str(e)}")
            raise Exception(f"Failed to search destination information with Firecrawl: {str(e)}") from e

    async def monitor_price_changes(
        self, url: str, price_selector: str, options: Optional[MonitorOptions] = None
    ) -> PriceMonitorResult:
        """Set up monitoring for price changes on a webpage using Firecrawl.

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
            # First, extract the current price to establish a baseline
            current_price_request = {
                "url": url,
                "actions": [
                    {"type": "wait", "milliseconds": 2000},
                    {"type": "scrape"}
                ],
                "formats": ["json"],
                "jsonOptions": {
                    "prompt": f"Extract the current price from the element matching selector '{price_selector}'. Return just the price as a number and the currency code.",
                    "mode": "llm-extraction"
                }
            }
            
            # Call Firecrawl API to get current price
            current_price_result = await self._make_request("/scrape", current_price_request)
            
            if not current_price_result.get("success"):
                raise Exception(f"Failed to extract current price: {current_price_result.get('error')}")
            
            # Extract price information from the result
            price_data = current_price_result.get("data", {}).get("json", {})
            
            # Generate a monitoring ID
            monitoring_id = f"monitor_{url.split('/')[-1]}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            # Create PriceInfo object
            price_info = {
                "amount": float(price_data.get("price", 0)),
                "currency": price_data.get("currency", "USD"),
                "timestamp": datetime.now().isoformat()
            }
            
            # Build the result
            return {
                "url": url,
                "initial_price": price_info,
                "current_price": price_info,
                "monitoring_id": monitoring_id,
                "status": "scheduled",
                "history": [
                    {
                        "timestamp": price_info["timestamp"],
                        "amount": price_info["amount"],
                        "currency": price_info["currency"],
                        "change_percent": 0.0
                    }
                ],
                "next_check": self._calculate_next_check(options.get("frequency", "daily"))
            }
        except Exception as e:
            logger.error(f"Error setting up price monitoring with Firecrawl for {url}: {str(e)}")
            raise Exception(f"Failed to monitor price changes with Firecrawl: {str(e)}") from e

    async def get_latest_events(
        self,
        destination: str,
        start_date: str,
        end_date: str,
        categories: Optional[List[str]] = None,
    ) -> EventList:
        """Get latest events for a destination using Firecrawl.

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
            # Build search query for events
            category_str = ""
            if categories and len(categories) > 0:
                category_str = " " + " ".join(categories)
            
            query = f"events in {destination}{category_str} from {start_date} to {end_date}"
            
            # Use deep research for comprehensive event information
            deep_research_request = {
                "query": query,
                "maxDepth": 3,
                "timeLimit": 120,
                "maxUrls": 20
            }
            
            # Call Firecrawl deep research API
            research_result = await self._make_request("/deep-research", deep_research_request)
            
            if not research_result.get("success"):
                raise Exception(f"Firecrawl deep research failed: {research_result.get('error')}")
            
            # Extract events data using structured extraction
            extract_request = {
                "urls": research_result.get("data", {}).get("sources", [])[:5],
                "schema": {
                    "type": "object",
                    "properties": {
                        "events": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "description": {"type": "string"},
                                    "category": {"type": "string"},
                                    "date": {"type": "string"},
                                    "time": {"type": "string"},
                                    "venue": {"type": "string"},
                                    "address": {"type": "string"},
                                    "url": {"type": "string"},
                                    "price_range": {"type": "string"},
                                }
                            }
                        }
                    }
                },
                "prompt": f"Extract event information for {destination} between {start_date} and {end_date}. Focus on extracting well-structured event data with accurate dates and details."
            }
            
            # Call Firecrawl extract API
            extract_result = await self._make_request("/extract", extract_request)
            
            if not extract_result.get("success"):
                raise Exception(f"Firecrawl extraction failed: {extract_result.get('error')}")
            
            # Process the extracted events
            extracted_data = extract_result.get("data", {})
            events_data = []
            
            # Combine events from all URLs
            for url_data in extracted_data:
                if "events" in url_data:
                    for event in url_data["events"]:
                        event["source"] = self._extract_domain(url_data.get("url", ""))
                        events_data.append(event)
            
            # Map to our interface
            return {
                "destination": destination,
                "date_range": {"start_date": start_date, "end_date": end_date},
                "events": [
                    {
                        "name": event.get("name", ""),
                        "description": event.get("description", ""),
                        "category": event.get("category", "General"),
                        "date": event.get("date", ""),
                        "time": event.get("time"),
                        "venue": event.get("venue"),
                        "address": event.get("address"),
                        "url": event.get("url"),
                        "price_range": event.get("price_range"),
                        "image_url": event.get("image_url"),
                        "source": event.get("source", ""),
                    }
                    for event in events_data
                ],
                "sources": list(set(event.get("source", "") for event in events_data)),
            }
        except Exception as e:
            logger.error(f"Error getting events with Firecrawl for {destination}: {str(e)}")
            raise Exception(f"Failed to get latest events with Firecrawl: {str(e)}") from e

    async def crawl_travel_blog(
        self,
        destination: str,
        topics: Optional[List[str]] = None,
        max_blogs: int = 3,
        recent_only: bool = True,
    ) -> BlogInsights:
        """Extract insights from travel blogs using Firecrawl.

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
            # Build search query for travel blogs
            topic_str = ""
            if topics and len(topics) > 0:
                topic_str = " " + " ".join(topics)
            
            time_str = ""
            if recent_only:
                time_str = " last year"
            
            query = f"travel blog {destination}{topic_str}{time_str}"
            
            # Search for travel blogs
            search_request = {
                "query": query,
                "limit": max_blogs,
                "scrapeOptions": {
                    "formats": ["markdown"],
                    "onlyMainContent": True
                }
            }
            
            # Call Firecrawl search API
            search_result = await self._make_request("/search", search_request)
            
            if not search_result.get("success"):
                raise Exception(f"Firecrawl search failed: {search_result.get('error')}")
            
            # Extract blog URLs
            blog_urls = [item.get("url") for item in search_result.get("data", [])]
            
            # Extract insights from blogs
            extract_request = {
                "urls": blog_urls,
                "schema": {
                    "type": "object",
                    "properties": {
                        "topics": {
                            "type": "object",
                            "additionalProperties": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "title": {"type": "string"},
                                        "summary": {"type": "string"},
                                        "key_points": {"type": "array", "items": {"type": "string"}},
                                        "sentiment": {"type": "string", "enum": ["positive", "neutral", "negative"]},
                                    }
                                }
                            }
                        }
                    }
                },
                "prompt": f"Extract travel insights about {destination} from these blogs. Organize the insights by topic and include a summary and key points for each topic. Also analyze the sentiment of each topic (positive, neutral, or negative)."
            }
            
            # Call Firecrawl extract API
            extract_result = await self._make_request("/extract", extract_request)
            
            if not extract_result.get("success"):
                raise Exception(f"Firecrawl extraction failed: {extract_result.get('error')}")
            
            # Process the extracted insights
            extracted_data = extract_result.get("data", {})
            
            # Build blog sources
            blog_sources = []
            for i, url in enumerate(blog_urls):
                # Get blog metadata from search results
                blog_meta = search_result.get("data", [])[i] if i < len(search_result.get("data", [])) else {}
                
                blog_sources.append({
                    "url": url,
                    "title": blog_meta.get("title", f"Blog {i+1}"),
                    "author": blog_meta.get("author"),
                    "publish_date": blog_meta.get("publishDate"),
                    "reputation_score": 0.8  # Default score
                })
            
            # Process topics
            processed_topics = {}
            for url_data in extracted_data:
                if "topics" in url_data:
                    for topic_name, topic_items in url_data["topics"].items():
                        if topic_name not in processed_topics:
                            processed_topics[topic_name] = []
                        
                        for i, item in enumerate(topic_items):
                            # Add source index
                            item["source_index"] = blog_urls.index(url_data.get("url")) if url_data.get("url") in blog_urls else 0
                            processed_topics[topic_name].append(item)
            
            # Return the blog insights
            return {
                "destination": destination,
                "topics": processed_topics,
                "sources": blog_sources,
                "extraction_date": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error(f"Error crawling travel blogs with Firecrawl for {destination}: {str(e)}")
            raise Exception(f"Failed to crawl travel blogs with Firecrawl: {str(e)}") from e

    def _extract_title_from_url(self, url: str) -> str:
        """Extract a title from a URL.

        Args:
            url: The URL to extract a title from

        Returns:
            The extracted title
        """
        try:
            from urllib.parse import urlparse
            
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
            from urllib.parse import urlparse
            
            parsed_url = urlparse(url)
            return parsed_url.netloc
        except Exception:
            return url
            
    def _calculate_next_check(self, frequency: str) -> str:
        """Calculate the next check time based on frequency.

        Args:
            frequency: Check frequency ('hourly', 'daily', 'weekly')

        Returns:
            ISO formatted timestamp for next check
        """
        from datetime import datetime, timedelta
        
        now = datetime.now()
        
        if frequency == "hourly":
            next_time = now + timedelta(hours=1)
        elif frequency == "weekly":
            next_time = now + timedelta(weeks=1)
        else:
            # Default to daily
            next_time = now + timedelta(days=1)
            
        return next_time.isoformat()