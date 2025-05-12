"""
Crawl4AI MCP client adapter.

This module provides an adapter for the Crawl4AI MCP server to be used by TripSage
agent tools.
"""

from typing import Any, Dict, Optional

import httpx

from src.utils.config import AppSettings
from src.utils.logging import get_logger

logger = get_logger(__name__)


class Crawl4AIClient:
    """Client adapter for the Crawl4AI MCP server."""

    def __init__(self):
        """Initialize the Crawl4AI client adapter."""
        self.settings = AppSettings()
        self.api_key = self.settings.crawl4ai_api_key
        self.base_url = self.settings.crawl4ai_base_url
        self.timeout = 120.0  # 2 minutes timeout

        if not self.api_key:
            logger.warning("CRAWL4AI_API_KEY not set in environment variables")

        if not self.base_url:
            # Use default MCP base URL if not specified
            self.base_url = "http://localhost:11235"
            logger.info(f"Using default Crawl4AI MCP base URL: {self.base_url}")

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
                response = await client.post(
                    endpoint, json=payload, headers=headers, timeout=self.timeout
                )
                response.raise_for_status()
                result = response.json()

                if not result.get("success", False):
                    error_msg = result.get(
                        "error", "Unknown error in Crawl4AI scraping"
                    )
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
            error_msg = (
                f"Crawl4AI HTTP error {e.response.status_code}: {e.response.text}"
            )
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

    async def crawl_blog(
        self, url: str, extract_type: str, max_pages: int = 1
    ) -> Dict[str, Any]:
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
                response = await client.post(
                    endpoint, json=payload, headers=headers, timeout=self.timeout
                )
                response.raise_for_status()
                result = response.json()

                if not result.get("success", False):
                    error_msg = result.get(
                        "error", "Unknown error in Crawl4AI blog crawl"
                    )
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
        crawl_data = (
            result["data"][0] if isinstance(result["data"], list) else result["data"]
        )

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

    def _format_blog_result(
        self, result: Dict[str, Any], url: str, extract_type: str
    ) -> Dict[str, Any]:
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


# Singleton instance
crawl4ai_client = Crawl4AIClient()


def get_client() -> Crawl4AIClient:
    """Get the singleton instance of the Crawl4AI client.

    Returns:
        The client instance
    """
    return crawl4ai_client
