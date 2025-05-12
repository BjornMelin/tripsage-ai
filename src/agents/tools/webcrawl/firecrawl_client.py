"""
Firecrawl MCP client adapter.

This module provides an adapter for the Firecrawl API/MCP to be used by TripSage
agent tools.
"""

import logging
import os
import json
from typing import Any, Dict, List, Optional, Union

import httpx
from pydantic import BaseModel, HttpUrl, ValidationError

from src.utils.config import AppSettings
from src.utils.logging import get_logger

logger = get_logger(__name__)


class FirecrawlClient:
    """Client adapter for the Firecrawl API/MCP."""
    
    def __init__(self):
        """Initialize the Firecrawl client adapter."""
        self.settings = AppSettings()
        self.api_key = self.settings.firecrawl_api_key
        self.base_url = "https://api.firecrawl.dev/v1"
        self.timeout = 60.0  # 1 minute timeout
        
        if not self.api_key:
            logger.warning("FIRECRAWL_API_KEY not set in environment variables")
    
    async def scrape_url(
        self,
        url: str,
        full_page: bool = False,
        extract_images: bool = False,
        extract_links: bool = False,
        specific_selector: Optional[str] = None
    ) -> Dict[str, Any]:
        """Scrape content from a URL using Firecrawl.
        
        Args:
            url: The URL to scrape
            full_page: Whether to take a full page screenshot
            extract_images: Whether to extract image data
            extract_links: Whether to extract links
            specific_selector: CSS selector to target specific content
            
        Returns:
            The scraped content
        """
        try:
            endpoint = f"{self.base_url}/scrape"
            
            # Prepare the formats based on what we want to extract
            formats = ["markdown"]
            if extract_links:
                formats.append("links")
            
            payload = {
                "url": url,
                "formats": formats,
                "onlyMainContent": not full_page,
                "includeTags": specific_selector.split(",") if specific_selector else None,
                "removeBase64Images": not extract_images
            }
            
            # Add screenshot if requested
            if full_page:
                payload["formats"].append("screenshot@fullPage")
            elif extract_images:
                payload["formats"].append("screenshot")
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    endpoint, json=payload, headers=headers, timeout=self.timeout
                )
                response.raise_for_status()
                result = response.json()
                
                # Format and return the result
                return self._format_result(result, url)
                
        except httpx.RequestError as e:
            error_msg = f"Firecrawl network error: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
        except httpx.HTTPStatusError as e:
            error_msg = f"Firecrawl HTTP error {e.response.status_code}: {e.response.text}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
        except Exception as e:
            error_msg = f"Firecrawl unexpected error: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    async def search_web(
        self,
        query: str,
        depth: str = "standard",
        limit: int = 5
    ) -> Dict[str, Any]:
        """Search the web for information using Firecrawl.
        
        Args:
            query: Search query
            depth: Search depth (standard or deep)
            limit: Maximum number of results
            
        Returns:
            Search results
        """
        try:
            endpoint = f"{self.base_url}/search"
            
            # Configure scrape options to get content along with search results
            scrape_options = {
                "formats": ["markdown"],
                "onlyMainContent": True
            }
            
            payload = {
                "query": query,
                "limit": limit,
                "scrapeOptions": scrape_options
            }
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    endpoint, json=payload, headers=headers, timeout=self.timeout
                )
                response.raise_for_status()
                result = response.json()
                
                return self._format_search_result(result, query)
                
        except Exception as e:
            error_msg = f"Firecrawl search error: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    async def monitor_price(
        self,
        url: str,
        selectors: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Monitor price changes for a product URL.
        
        Args:
            url: The product URL
            selectors: CSS selectors for price elements
            
        Returns:
            The monitoring setup result
        """
        try:
            # Using the scrape endpoint with price scraping configuration
            endpoint = f"{self.base_url}/scrape"
            
            # Define extraction schema for price data
            extract_schema = {
                "price": {
                    "type": "number",
                    "description": "The current price of the product"
                },
                "currency": {
                    "type": "string",
                    "description": "The currency of the price"
                },
                "product_name": {
                    "type": "string",
                    "description": "The name of the product"
                },
                "availability": {
                    "type": "string",
                    "description": "Product availability status"
                }
            }
            
            # Add custom selectors if provided
            if selectors:
                extract_schema["_selectors"] = selectors
            
            payload = {
                "url": url,
                "formats": ["extract", "markdown"],
                "extract": {
                    "schema": extract_schema,
                    "prompt": "Extract the current price, currency, product name, and availability status from this product page."
                }
            }
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    endpoint, json=payload, headers=headers, timeout=self.timeout
                )
                response.raise_for_status()
                result = response.json()
                
                return self._format_price_result(result, url)
                
        except Exception as e:
            error_msg = f"Firecrawl price monitoring error: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    async def get_events(
        self,
        destination: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        event_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get events at a destination using Firecrawl.
        
        Args:
            destination: The destination location
            start_date: Start date for event search (YYYY-MM-DD)
            end_date: End date for event search (YYYY-MM-DD)
            event_type: Type of event (festival, concert, sports, etc.)
            
        Returns:
            List of events
        """
        try:
            # Create search query based on parameters
            query_parts = [f"events in {destination}"]
            if start_date:
                query_parts.append(f"from {start_date}")
            if end_date:
                query_parts.append(f"to {end_date}")
            if event_type:
                query_parts.append(event_type)
            
            query = " ".join(query_parts)
            
            # Use the search_web function with events-specific configuration
            search_results = await self.search_web(query, depth="deep", limit=10)
            
            # If search was successful, extract events using deep research
            if search_results.get("success", False):
                endpoint = f"{self.base_url}/deep-research"
                
                payload = {
                    "query": f"Find upcoming events in {destination}",
                    "maxUrls": 5,  # Limit to 5 event pages for efficiency
                    "maxDepth": 3,  # Go deeper in research
                    "timeLimit": 60  # 1 minute time limit
                }
                
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                }
                
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        endpoint, json=payload, headers=headers, timeout=120.0  # Longer timeout
                    )
                    response.raise_for_status()
                    result = response.json()
                    
                    return self._format_events_result(result, destination)
            
            return search_results
                
        except Exception as e:
            error_msg = f"Firecrawl events error: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    async def crawl_blog(
        self,
        url: str,
        extract_type: str,
        max_pages: int = 1
    ) -> Dict[str, Any]:
        """Crawl a travel blog using Firecrawl.
        
        Args:
            url: The blog URL
            extract_type: Type of extraction (insights, itinerary, tips, places)
            max_pages: Maximum number of pages to crawl
            
        Returns:
            The extracted blog content
        """
        try:
            # If we need to crawl multiple pages, use the crawl endpoint
            if max_pages > 1:
                endpoint = f"{self.base_url}/crawl"
                
                # Configure crawl
                payload = {
                    "url": url,
                    "limit": max_pages,
                    "scrapeOptions": {
                        "formats": ["markdown", "links"],
                        "onlyMainContent": True
                    }
                }
                
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                }
                
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        endpoint, json=payload, headers=headers, timeout=120.0  # Longer timeout for crawl
                    )
                    response.raise_for_status()
                    result = response.json()
                    
                    return self._format_blog_result(result, url, extract_type)
            
            # For single page, use the extract endpoint with schema based on extract_type
            else:
                endpoint = f"{self.base_url}/scrape"
                
                # Determine what to extract based on extract_type
                extract_prompt = ""
                if extract_type == "insights":
                    extract_prompt = "Extract key travel insights, advice, and highlights from this travel blog."
                elif extract_type == "itinerary":
                    extract_prompt = "Extract the itinerary, day-by-day activities, and travel route from this travel blog."
                elif extract_type == "tips":
                    extract_prompt = "Extract practical tips, warnings, and recommendations from this travel blog."
                elif extract_type == "places":
                    extract_prompt = "Extract all mentioned places, attractions, restaurants, and hotels from this travel blog."
                
                payload = {
                    "url": url,
                    "formats": ["extract", "markdown"],
                    "extract": {
                        "prompt": extract_prompt
                    }
                }
                
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                }
                
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        endpoint, json=payload, headers=headers, timeout=self.timeout
                    )
                    response.raise_for_status()
                    result = response.json()
                    
                    return self._format_blog_result(result, url, extract_type)
                
        except Exception as e:
            error_msg = f"Firecrawl blog crawl error: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    def _format_result(self, result: Dict[str, Any], url: str) -> Dict[str, Any]:
        """Format the scrape result into a standardized structure.
        
        Args:
            result: The raw API response
            url: The URL that was scraped
            
        Returns:
            A formatted result dictionary
        """
        if not result.get("success", False):
            return {
                "success": False,
                "url": url,
                "error": result.get("error", "Unknown error from Firecrawl")
            }
        
        formatted_result = {
            "success": True,
            "url": url,
            "items": [
                {
                    "title": result.get("data", {}).get("metadata", {}).get("title", ""),
                    "content": result.get("data", {}).get("markdown", ""),
                    "url": url,
                    "metadata": result.get("data", {}).get("metadata", {})
                }
            ],
            "formatted": f"Successfully extracted content from {url}"
        }
        
        return formatted_result
    
    def _format_search_result(self, result: Dict[str, Any], query: str) -> Dict[str, Any]:
        """Format the search result into a standardized structure.
        
        Args:
            result: The raw API response
            query: The search query
            
        Returns:
            A formatted result dictionary
        """
        if not result.get("success", False):
            return {
                "success": False,
                "query": query,
                "error": result.get("error", "Unknown error in Firecrawl search")
            }
        
        items = []
        for item in result.get("data", []):
            items.append({
                "title": item.get("title", ""),
                "content": item.get("snippet", "") or item.get("markdown", ""),
                "url": item.get("url", ""),
                "metadata": item.get("metadata", {})
            })
        
        formatted_result = {
            "success": True,
            "query": query,
            "items": items,
            "formatted": f"Found {len(items)} results for '{query}'"
        }
        
        return formatted_result
    
    def _format_price_result(self, result: Dict[str, Any], url: str) -> Dict[str, Any]:
        """Format the price monitoring result into a standardized structure.
        
        Args:
            result: The raw API response
            url: The product URL
            
        Returns:
            A formatted result dictionary
        """
        if not result.get("success", False):
            return {
                "success": False,
                "url": url,
                "error": result.get("error", "Unknown error in Firecrawl price monitoring")
            }
        
        # Extract price data from the extraction result
        extract_data = result.get("data", {}).get("extract", {})
        
        formatted_result = {
            "success": True,
            "url": url,
            "items": [
                {
                    "title": extract_data.get("product_name", ""),
                    "price": extract_data.get("price", 0),
                    "currency": extract_data.get("currency", "USD"),
                    "availability": extract_data.get("availability", ""),
                    "url": url
                }
            ],
            "formatted": f"Successfully extracted price data from {url}"
        }
        
        return formatted_result
    
    def _format_events_result(self, result: Dict[str, Any], destination: str) -> Dict[str, Any]:
        """Format the events result into a standardized structure.
        
        Args:
            result: The raw API response
            destination: The destination location
            
        Returns:
            A formatted result dictionary
        """
        if not result.get("success", False):
            return {
                "success": False,
                "destination": destination,
                "error": result.get("error", "Unknown error in Firecrawl events search")
            }
        
        # In a real implementation, we would parse the results to extract structured event data
        # For this example, we'll just return the research results
        
        formatted_result = {
            "success": True,
            "destination": destination,
            "items": [],  # Would contain structured event data
            "research_summary": result.get("data", {}).get("summary", ""),
            "formatted": f"Found events in {destination}"
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
        if not result.get("success", False):
            return {
                "success": False,
                "url": url,
                "error": result.get("error", "Unknown error in Firecrawl blog crawl")
            }
        
        # For crawl results with multiple pages
        if "results" in result.get("data", {}):
            items = []
            for page_result in result.get("data", {}).get("results", []):
                items.append({
                    "title": page_result.get("metadata", {}).get("title", ""),
                    "content": page_result.get("markdown", ""),
                    "url": page_result.get("url", ""),
                    "metadata": page_result.get("metadata", {})
                })
            
            formatted_result = {
                "success": True,
                "url": url,
                "extract_type": extract_type,
                "items": items,
                "formatted": f"Successfully crawled {len(items)} pages from {url}"
            }
            
            return formatted_result
        
        # For extract results with a single page
        extract_data = result.get("data", {}).get("extract", {})
        
        formatted_result = {
            "success": True,
            "url": url,
            "extract_type": extract_type,
            "items": [
                {
                    "title": result.get("data", {}).get("metadata", {}).get("title", ""),
                    "content": result.get("data", {}).get("markdown", ""),
                    "url": url,
                    "extracted_data": extract_data
                }
            ],
            "formatted": f"Successfully extracted {extract_type} from {url}"
        }
        
        return formatted_result


# Singleton instance
firecrawl_client = FirecrawlClient()

def get_client() -> FirecrawlClient:
    """Get the singleton instance of the Firecrawl client.
    
    Returns:
        The client instance
    """
    return firecrawl_client