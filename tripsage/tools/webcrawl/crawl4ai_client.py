"""
Crawl4AI MCP client adapter.

This module provides an adapter for the Crawl4AI MCP server to be used by TripSage
agent tools.
"""

from typing import Any, Dict, Optional

import httpx

from tripsage.tools.memory_tools import ConversationMessage
from tripsage_core.config import get_settings
from tripsage_core.services.business.memory_service import MemoryService
from tripsage_core.utils.logging_utils import get_logger

settings = get_settings()

logger = get_logger(__name__)


class Crawl4AIClient:
    """Client adapter for the Crawl4AI MCP server."""

    def __init__(self):
        """Initialize the Crawl4AI client adapter."""
        self.api_key = settings.crawl4ai_mcp.api_key
        self.base_url = settings.crawl4ai_mcp.endpoint
        self.timeout = settings.crawl4ai_mcp.timeout

        if not self.api_key:
            logger.warning("CRAWL4AI_API_KEY not set in environment variables")

        if not self.base_url:
            # Use default MCP base URL if not specified
            self.base_url = "http://localhost:11235"
            logger.info(f"Using default Crawl4AI MCP base URL: {self.base_url}")

        # Initialize memory service for content extraction
        self.memory_service = MemoryService()
        self._memory_initialized = False

    async def scrape_url(
        self,
        url: str,
        full_page: bool = False,
        extract_images: bool = False,
        extract_links: bool = False,
        specific_selector: Optional[str] = None,
        js_enabled: bool = True,
    ) -> Dict[str, Any]:
        """Scrape content from a URL using Crawl4AI.

        Args:
            url: The URL to scrape
            full_page: Whether to get the full page content
            extract_images: Whether to extract image data
            extract_links: Whether to extract links
            specific_selector: CSS selector to target specific content
            js_enabled: Whether to enable JavaScript execution

        Returns:
            The scraped content
        """
        try:
            endpoint = f"{self.base_url}/crawl"

            browser_config = {
                "type": "BrowserConfig",
                "params": {"headless": True, "java_script_enabled": js_enabled},
            }

            crawler_config = {
                "type": "CrawlerRunConfig",
                "params": {
                    "cache_mode": "bypass",
                    "process_iframes": False,  # Usually not needed for travel content
                    "word_count_threshold": 10,  # Filter out very small content blocks
                },
            }

            # Add specific selector if provided
            if specific_selector:
                crawler_config["params"]["css_selector"] = specific_selector

            payload = {
                "urls": [url],
                "browser_config": browser_config,
                "crawler_config": crawler_config,
            }

            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            async with httpx.AsyncClient() as client:
                response = await client.post(endpoint, json=payload, headers=headers, timeout=self.timeout)
                response.raise_for_status()
                result = response.json()

                if not result.get("success", False):
                    error_msg = result.get("error", "Unknown error in Crawl4AI scraping")
                    logger.error(f"Crawl4AI scraping error: {error_msg}")
                    return {"success": False, "error": error_msg}

                # Extract and format the result
                parsed_result = self._format_result(result, url)
                return parsed_result

        except httpx.RequestError as e:
            error_msg = f"Crawl4AI network error: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
        except httpx.HTTPStatusError as e:
            error_msg = f"Crawl4AI HTTP error {e.response.status_code}: {e.response.text}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
        except Exception as e:
            error_msg = f"Crawl4AI unexpected error: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

    async def search_web(self, query: str, depth: str = "standard") -> Dict[str, Any]:
        """Search the web for information using Crawl4AI.

        Args:
            query: Search query
            depth: Search depth (standard or deep)

        Returns:
            Search results
        """
        # Replace with actual implementation
        # This could integrate with Crawl4AI's search capabilities
        # For now, returning a mock response
        return {
            "success": True,
            "query": query,
            "results": [
                {"title": "Mock result 1", "snippet": "This is a mock search result 1"},
                {"title": "Mock result 2", "snippet": "This is a mock search result 2"},
            ],
        }

    async def crawl_blog(self, url: str, extract_type: str, max_pages: int = 1) -> Dict[str, Any]:
        """Crawl a travel blog using Crawl4AI.

        Args:
            url: The blog URL
            extract_type: Type of extraction (insights, itinerary, tips, places)
            max_pages: Maximum number of pages to crawl

        Returns:
            The extracted blog content
        """
        try:
            # We'll use the scrape_url function but with config specific for blogs
            endpoint = f"{self.base_url}/crawl"

            browser_config = {
                "type": "BrowserConfig",
                "params": {"headless": True, "java_script_enabled": True},
            }

            # Configure deep crawl if max_pages > 1
            deep_crawl_strategy = None
            if max_pages > 1:
                deep_crawl_strategy = {
                    "type": "BFSDeepCrawlStrategy",
                    "params": {
                        "max_depth": max_pages - 1,
                        "max_pages": max_pages,
                        "same_domain_only": True,
                    },
                }

            crawler_config = {
                "type": "CrawlerRunConfig",
                "params": {
                    "cache_mode": "bypass",
                    "process_iframes": False,
                    "word_count_threshold": 50,  # Higher threshold for blogs
                    "deep_crawl_strategy": deep_crawl_strategy,
                },
            }

            payload = {
                "urls": [url],
                "browser_config": browser_config,
                "crawler_config": crawler_config,
            }

            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            async with httpx.AsyncClient() as client:
                response = await client.post(endpoint, json=payload, headers=headers, timeout=self.timeout)
                response.raise_for_status()
                result = response.json()

                if not result.get("success", False):
                    error_msg = result.get("error", "Unknown error in Crawl4AI blog crawl")
                    logger.error(f"Crawl4AI blog crawl error: {error_msg}")
                    return {"success": False, "error": error_msg}

                # Process the blog-specific results based on extract_type
                formatted_result = self._format_blog_result(result, url, extract_type)
                return formatted_result

        except Exception as e:
            error_msg = f"Crawl4AI blog crawl error: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

    def _format_result(self, result: Dict[str, Any], url: str) -> Dict[str, Any]:
        """Format the crawl result into a standardized structure.

        Args:
            result: The raw API response
            url: The URL that was crawled

        Returns:
            A formatted result dictionary
        """
        if not result.get("success", False) or not result.get("data", []):
            return {
                "success": False,
                "url": url,
                "error": result.get("error", "No data returned from Crawl4AI"),
            }

        # Extract from the first result (since we only send one URL)
        crawl_data = result["data"][0] if isinstance(result["data"], list) else result["data"]

        formatted_result = {
            "success": True,
            "url": url,
            "items": [
                {
                    "title": crawl_data.get("title", ""),
                    "content": crawl_data.get("markdown", ""),
                    "url": url,
                    "metadata": {
                        "word_count": len(crawl_data.get("markdown", "").split()),
                        "links": crawl_data.get("links", {}),
                    },
                }
            ],
            "formatted": f"Successfully extracted content from {url}",
        }

        return formatted_result

    def _format_blog_result(self, result: Dict[str, Any], url: str, extract_type: str) -> Dict[str, Any]:
        """Format the blog crawl result based on the extract type.

        Args:
            result: The raw API response
            url: The URL that was crawled
            extract_type: Type of extraction (insights, itinerary, tips, places)

        Returns:
            A formatted result dictionary
        """
        # This would be expanded in a real implementation to handle
        # different extract_types appropriately
        return self._format_result(result, url)

    async def _ensure_memory_initialized(self) -> None:
        """Ensure memory service is connected for content extraction."""
        if not self._memory_initialized:
            try:
                await self.memory_service.connect()
                self._memory_initialized = True
                logger.debug("Memory service initialized for Crawl4AI client")
            except Exception as e:
                logger.warning(f"Failed to initialize memory service: {e}")

    async def extract_travel_insights(
        self,
        content: str,
        url: str,
        user_id: Optional[str] = None,
        content_type: str = "web_content",
    ) -> Dict[str, Any]:
        """Extract travel-related insights from web content using Mem0.

        Args:
            content: Text content to analyze
            url: Source URL
            user_id: Optional user ID for personalized extraction
            content_type: Type of content (web_content, blog, review, etc.)

        Returns:
            Extracted insights and memory storage result
        """
        try:
            await self._ensure_memory_initialized()

            # Create conversation messages for memory extraction
            system_prompt = (
                "Extract travel-related information from web content. "
                "Focus on destinations, activities, tips, recommendations, "
                f"and practical travel advice. Source: {url}"
            )

            messages = [
                ConversationMessage(role="system", content=system_prompt),
                ConversationMessage(
                    role="user",
                    content=f"Web content from {url}:\n\n{content[:2000]}...",
                ),
            ]

            # Extract memories using Mem0
            memory_result = await self.memory_service.add_conversation_memory(
                messages=messages,
                user_id=user_id or "web_crawler",
                metadata={
                    "source_url": url,
                    "content_type": content_type,
                    "extraction_type": "travel_insights",
                    "domain": "travel_planning",
                },
            )

            # Parse extracted insights
            insights = self._parse_travel_insights(memory_result, content, url)

            insight_count = len(insights.get("insights", []))
            logger.info(f"Extracted travel insights from {url}", insights_count=insight_count)

            return {
                "success": True,
                "url": url,
                "insights": insights,
                "memory_result": memory_result,
                "extracted_count": len(memory_result.get("results", [])),
            }

        except Exception as e:
            logger.error(f"Failed to extract travel insights: {e}")
            return {"success": False, "url": url, "error": str(e), "insights": {}}

    def _parse_travel_insights(self, memory_result: Dict[str, Any], content: str, url: str) -> Dict[str, Any]:
        """Parse and categorize travel insights from memory extraction result.

        Args:
            memory_result: Result from memory service
            content: Original content
            url: Source URL

        Returns:
            Categorized travel insights
        """
        insights = {
            "destinations": [],
            "activities": [],
            "tips": [],
            "recommendations": [],
            "practical_info": [],
            "budget_info": [],
            "timing": [],
        }

        # Extract memories and categorize them
        for memory in memory_result.get("results", []):
            memory_text = memory.get("memory", "")
            memory_lower = memory_text.lower()

            # Categorize based on content keywords
            destination_words = ["visit", "destination", "city", "country", "place"]
            activity_words = ["activity", "do", "experience", "tour", "attraction"]
            tip_words = ["tip", "advice", "recommend", "suggest", "should"]
            recommendation_words = ["restaurant", "hotel", "stay", "eat", "food"]
            practical_words = [
                "transport",
                "flight",
                "train",
                "bus",
                "visa",
                "passport",
            ]
            budget_words = ["cost", "price", "budget", "money", "expensive", "cheap"]
            timing_words = ["time", "season", "weather", "month", "when"]

            if any(word in memory_lower for word in destination_words):
                insights["destinations"].append(memory_text)
            elif any(word in memory_lower for word in activity_words):
                insights["activities"].append(memory_text)
            elif any(word in memory_lower for word in tip_words):
                insights["tips"].append(memory_text)
            elif any(word in memory_lower for word in recommendation_words):
                insights["recommendations"].append(memory_text)
            elif any(word in memory_lower for word in practical_words):
                insights["practical_info"].append(memory_text)
            elif any(word in memory_lower for word in budget_words):
                insights["budget_info"].append(memory_text)
            elif any(word in memory_lower for word in timing_words):
                insights["timing"].append(memory_text)

        # Add content statistics
        insights["metadata"] = {
            "url": url,
            "content_length": len(content),
            "total_memories": len(memory_result.get("results", [])),
            "extraction_successful": memory_result.get("success", False),
        }

        return insights

    async def scrape_with_memory_extraction(
        self,
        url: str,
        user_id: Optional[str] = None,
        full_page: bool = False,
        extract_images: bool = False,
        extract_links: bool = False,
        specific_selector: Optional[str] = None,
        js_enabled: bool = True,
    ) -> Dict[str, Any]:
        """Scrape URL and extract travel insights to memory.

        This method combines web scraping with automatic travel insight extraction
        and storage in the user's memory for future personalization.

        Args:
            url: The URL to scrape
            user_id: User ID for personalized memory storage
            full_page: Whether to get the full page content
            extract_images: Whether to extract image data
            extract_links: Whether to extract links
            specific_selector: CSS selector to target specific content
            js_enabled: Whether to enable JavaScript execution

        Returns:
            Combined scraping and memory extraction result
        """
        # First, scrape the content
        scrape_result = await self.scrape_url(
            url=url,
            full_page=full_page,
            extract_images=extract_images,
            extract_links=extract_links,
            specific_selector=specific_selector,
            js_enabled=js_enabled,
        )

        if not scrape_result.get("success"):
            return scrape_result

        # Extract content for memory processing
        content = ""
        items = scrape_result.get("items", [])
        if items:
            content = items[0].get("content", "")

        # Extract travel insights if content is available
        insights_result = {}
        if content and len(content.strip()) > 50:  # Only process substantial content
            insights_result = await self.extract_travel_insights(
                content=content, url=url, user_id=user_id, content_type="web_scrape"
            )

        # Combine results
        combined_result = {
            **scrape_result,
            "memory_extraction": insights_result,
            "has_insights": insights_result.get("success", False),
            "insights_count": insights_result.get("extracted_count", 0),
        }

        return combined_result


# Singleton instance
crawl4ai_client = Crawl4AIClient()


def get_client() -> Crawl4AIClient:
    """Get the singleton instance of the Crawl4AI client.

    Returns:
        The client instance
    """
    return crawl4ai_client
