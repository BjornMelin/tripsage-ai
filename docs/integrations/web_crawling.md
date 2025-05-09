# Web Crawling Integration Guide

This document provides comprehensive instructions for integrating web crawling capabilities into TripSage using Crawl4AI. This integration enhances travel planning by providing access to current travel information, destination details, and travel advisories.

## Overview

Crawl4AI is an open-source web crawling and scraping tool specifically optimized for Large Language Models (LLMs). Key features include:

- Asynchronous web crawling for efficient data collection
- Multiple output formats (Markdown, JSON, HTML)
- Customizable extraction strategies
- Self-hostable with no subscription fees or API key requirements
- Apache 2.0 license
- High community adoption and GitHub popularity

## Selected Solution

After extensive research and evaluation, **Crawl4AI** has been selected as the optimal solution for TripSage's web crawling needs.

### Why Crawl4AI?

1. **Cost-effectiveness**:

   - Completely free and open-source
   - No subscription fees for any usage level
   - Self-hostable with no limitations

2. **Feature Completeness**:

   - Full web crawling capabilities
   - Multiple output formats (markdown, JSON, HTML)
   - Asynchronous operations for better performance
   - Support for browser automation and interaction
   - Customizable extraction strategies

3. **Personal Usage Focus**:

   - Aligns with TripSage's focus on personal usage scenarios
   - Users can run locally without external dependencies
   - No API key requirements or rate limits
   - Complete control over crawling behavior

4. **Active Development**:
   - Trending GitHub repository with active community
   - Regular updates and improvements
   - Strong user community for support

### Compared to Alternatives

Crawl4AI outperforms alternatives like Firecrawl for TripSage's specific needs:

| Feature                        | Crawl4AI                | Firecrawl                 |
| ------------------------------ | ----------------------- | ------------------------- |
| **Cost Structure**             | Free and open-source    | Freemium with paid tiers  |
| **Personal Usage Suitability** | Excellent               | Limited by credits        |
| **Python Integration**         | Native                  | Via SDK                   |
| **Data Formatting**            | LLM-optimized           | General purpose           |
| **Self-hosting**               | Fully self-hostable     | Self-hostable with limits |
| **Community Support**          | Active GitHub community | Commercial support        |

## Setup Instructions

### Prerequisites

- Python 3.9 or higher
- Access to install Python packages
- Basic knowledge of async Python programming

### 1. Installation

Install Crawl4AI using pip:

```bash
pip install "crawl4ai @ git+https://github.com/unclecode/crawl4ai.git"
```

For additional dependencies that may be needed:

```bash
pip install transformers torch nltk
```

### 2. Basic Configuration

Create a configuration module to manage crawler settings:

```python
# crawl_config.py
from crawl4ai import CrawlerConfig, ExtractionConfig, BrowserConfig
from crawl4ai.extraction_strategy import PyppeteerHTMLExtractionStrategy, PlaywrightHTMLExtractionStrategy

def get_crawler_config(headless=True, use_playwright=True, max_concurrent=5):
    """
    Create a crawler configuration for travel-related websites.

    Args:
        headless: Whether to run browser in headless mode
        use_playwright: Whether to use Playwright (True) or Pyppeteer (False)
        max_concurrent: Maximum number of concurrent browser tasks

    Returns:
        CrawlerConfig object
    """
    # Browser configuration
    browser_config = BrowserConfig(
        headless=headless,
        viewport_width=1280,
        viewport_height=800,
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        block_images=False,  # Don't block images for travel sites where images are important
        timeout=30000,  # 30 seconds timeout
        wait_until="networkidle2",  # Wait until network is idle
    )

    # Extraction configuration
    extraction_strategy = PlaywrightHTMLExtractionStrategy() if use_playwright else PyppeteerHTMLExtractionStrategy()
    extraction_config = ExtractionConfig(
        strategy=extraction_strategy,
        extract_metadata=True,  # Extract title, description, etc.
        extract_text=True,  # Extract text content
        extract_links=True,  # Extract hyperlinks
        skip_tags=["script", "style", "svg", "iframe", "noscript"],  # Skip these tags
        force_async=True,  # Use async mode
    )

    # Crawler configuration
    crawler_config = CrawlerConfig(
        browser_config=browser_config,
        extraction_config=extraction_config,
        max_concurrent_tasks=max_concurrent,
        retry_count=2,  # Number of retries on failure
        retry_delay=2,  # Delay between retries (seconds)
        cache_mode="memory",  # Use memory cache to avoid duplicate requests
        domains_allowlist=None,  # Set to specific domains if needed
        url_patterns_blocklist=[
            r".*\.(jpg|jpeg|png|gif|svg|css|js)$",  # Block direct image/asset URLs
            r".*/login.*",  # Avoid login pages
            r".*/logout.*",  # Avoid logout pages
        ]
    )

    return crawler_config
```

## Integration with TripSage

Web crawling enhances TripSage in several key areas:

### 1. Travel Advisories and Entry Requirements

Use Crawl4AI to gather current information about:

- Government travel advisories for destinations
- Visa and entry requirements
- Health and safety information
- COVID-19 restrictions and requirements

### 2. Destination Research Enhancement

Enrich destination information with:

- Current local events and festivals
- Seasonal information
- Operating hours for attractions
- Recent traveler experiences and reviews

### 3. Price and Availability Verification

Validate pricing and availability information:

- Check for special offers directly from provider websites
- Verify operating hours and availability for attractions
- Monitor for price changes on travel services

### 4. Itinerary Enrichment

Enhance travel itineraries with:

- Detailed attraction information
- Local transportation options
- Restaurant menus and reviews
- Event schedules and ticket availability

## Implementation Guide

### 1. Basic Crawler Service

Create a crawler service for TripSage:

```python
# travel_crawler.py
import asyncio
from typing import Dict, List, Optional, Union, Any
import logging
from pathlib import Path
import json
import os

from crawl4ai import WebCrawler, CrawlResult
from crawl4ai.utils import get_domain
from crawl_config import get_crawler_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("TripSage-Crawler")

class TravelCrawlerService:
    """Service for crawling travel-related websites."""

    def __init__(self, config=None, cache_dir=None):
        """
        Initialize the travel crawler service.

        Args:
            config: Optional crawler configuration
            cache_dir: Directory to save crawl results (if None, results are not saved)
        """
        self.config = config or get_crawler_config()
        self.cache_dir = cache_dir
        if cache_dir:
            os.makedirs(cache_dir, exist_ok=True)
        self.crawler = WebCrawler(self.config)

    async def warmup(self):
        """Warm up the crawler (load necessary models)."""
        await self.crawler.warmup()
        logger.info("Crawler warmed up and ready")

    async def crawl_url(self, url: str) -> CrawlResult:
        """
        Crawl a single URL.

        Args:
            url: The URL to crawl

        Returns:
            CrawlResult object containing the crawled data
        """
        logger.info(f"Crawling URL: {url}")
        result = await self.crawler.run(url=url)

        # Save result to cache if cache_dir is set
        if self.cache_dir:
            domain = get_domain(url)
            filename = f"{domain}_{hash(url)}.json"
            cache_path = Path(self.cache_dir) / filename

            # Save basic metadata about the crawl
            metadata = {
                "url": url,
                "title": result.title,
                "timestamp": result.timestamp.isoformat(),
                "num_links": len(result.links) if result.links else 0,
                "content_length": len(result.markdown) if result.markdown else 0,
            }

            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)

            logger.info(f"Saved crawl metadata to {cache_path}")

        return result

    async def crawl_multiple(self, urls: List[str]) -> Dict[str, CrawlResult]:
        """
        Crawl multiple URLs in parallel.

        Args:
            urls: List of URLs to crawl

        Returns:
            Dictionary mapping URLs to their CrawlResult objects
        """
        logger.info(f"Crawling {len(urls)} URLs")
        tasks = [self.crawl_url(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out exceptions and create URL -> result mapping
        url_to_result = {}
        for url, result in zip(urls, results):
            if isinstance(result, Exception):
                logger.error(f"Error crawling {url}: {result}")
            else:
                url_to_result[url] = result

        logger.info(f"Successfully crawled {len(url_to_result)}/{len(urls)} URLs")
        return url_to_result

    async def extract_travel_info(self, url: str) -> Dict[str, Any]:
        """
        Extract travel-specific information from a URL.

        Args:
            url: URL of travel content to analyze

        Returns:
            Dictionary of extracted travel information
        """
        # First crawl the URL
        result = await self.crawl_url(url)

        # Process the result to extract structured travel information
        # This is a simplified example - you would use more sophisticated
        # extraction or LLM processing in a real implementation
        travel_info = {
            "url": url,
            "title": result.title,
            "summary": result.markdown[:500] + "..." if result.markdown and len(result.markdown) > 500 else result.markdown,
            "attractions": [],
            "accommodation_mentions": [],
            "transportation_info": [],
            "travel_tips": []
        }

        # Add basic link categorization
        if result.links:
            for link in result.links:
                link_text = link.get("text", "").lower()
                link_url = link.get("href", "")

                if any(term in link_text for term in ["hotel", "hostel", "apartment", "stay", "accommodation"]):
                    travel_info["accommodation_mentions"].append({
                        "text": link.get("text"),
                        "url": link_url
                    })

                if any(term in link_text for term in ["attraction", "visit", "sight", "tour", "museum"]):
                    travel_info["attractions"].append({
                        "text": link.get("text"),
                        "url": link_url
                    })

                if any(term in link_text for term in ["transport", "bus", "train", "airport", "flight"]):
                    travel_info["transportation_info"].append({
                        "text": link.get("text"),
                        "url": link_url
                    })

        logger.info(f"Extracted travel info from {url} with {len(travel_info['attractions'])} attractions, "
                   f"{len(travel_info['accommodation_mentions'])} accommodations, "
                   f"{len(travel_info['transportation_info'])} transportation mentions")

        return travel_info
```

### 2. Travel Information Extractor

Create a specialized extractor for travel information:

```python
# travel_extractor.py
import re
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger("TripSage-Extractor")

class TravelInfoExtractor:
    """Extract structured travel information from crawled content."""

    def __init__(self, use_markdown=True):
        """
        Initialize the travel information extractor.

        Args:
            use_markdown: Whether to extract from markdown (True) or HTML (False)
        """
        self.use_markdown = use_markdown

    def extract_destination_info(self, crawl_result) -> Dict[str, Any]:
        """
        Extract destination information from a crawl result.

        Args:
            crawl_result: CrawlResult from Crawl4AI

        Returns:
            Dictionary containing structured destination information
        """
        # Use markdown or HTML content based on configuration
        content = crawl_result.markdown if self.use_markdown else crawl_result.html

        if not content:
            logger.warning("No content available for extraction")
            return {
                "destination_name": crawl_result.title,
                "extracted_content": {}
            }

        # Extract destination information
        info = {
            "destination_name": crawl_result.title,
            "overview": self._extract_overview(content),
            "attractions": self._extract_attractions(content),
            "practical_info": {
                "best_time_to_visit": self._extract_best_time_to_visit(content),
                "safety_tips": self._extract_safety_tips(content),
                "local_transportation": self._extract_local_transportation(content),
                "currency": self._extract_currency(content),
                "language": self._extract_language(content)
            }
        }

        return info

    def _extract_overview(self, content: str) -> str:
        """Extract an overview/summary of the destination."""
        # Simple heuristic: get the first substantial paragraph
        paragraphs = re.split(r'\n\n+', content)

        for paragraph in paragraphs:
            # Clean up the paragraph
            clean_paragraph = paragraph.strip()

            # Skip short paragraphs, headers, and navigation elements
            if (len(clean_paragraph) > 100 and
                not clean_paragraph.startswith('#') and
                not clean_paragraph.startswith('*') and
                not re.search(r'copyright|cookie|privacy|terms', clean_paragraph, re.I)):

                return clean_paragraph

        # Fallback: return the first paragraph if no suitable one was found
        return paragraphs[0] if paragraphs else ""

    def _extract_attractions(self, content: str) -> List[Dict[str, str]]:
        """Extract attractions from the content."""
        attractions = []

        # Extract sections that might contain attractions
        attraction_sections = self._find_sections(content,
                                                ["attraction", "sight", "place", "monument",
                                                 "what to see", "what to do", "visit"])

        for section in attraction_sections:
            # Extract list items that might be attractions
            items = re.findall(r'[*-] ([^\n]+)', section)

            for item in items:
                # Clean and validate the attraction
                clean_item = item.strip()
                if len(clean_item) > 3 and not re.search(r'copyright|cookie|privacy|terms', clean_item, re.I):
                    attractions.append({
                        "name": clean_item,
                        "description": ""  # Description extraction would require more context
                    })

        # As a fallback, try to extract any bullet points if no attractions found
        if not attractions:
            items = re.findall(r'[*-] ([^\n]+)', content)
            for item in items:
                clean_item = item.strip()
                if len(clean_item) > 3 and not re.search(r'copyright|cookie|privacy|terms', clean_item, re.I):
                    attractions.append({
                        "name": clean_item,
                        "description": ""
                    })

        return attractions[:10]  # Limit to top 10 to avoid noise

    # Additional extraction helper methods...
    # (The rest of the methods as in the original file)
```

### 3. MCP Server Implementation

Create an MCP server for AI agent integration:

```python
# crawl4ai_mcp_server.py
from fastmcp import FastMCP
import asyncio
from travel_crawler import TravelCrawlerService
from travel_extractor import TravelInfoExtractor

# Initialize MCP server
mcp = FastMCP()

# Initialize crawler service
crawler_service = TravelCrawlerService(cache_dir="crawl_cache")
extractor = TravelInfoExtractor(use_markdown=True)

# Register MCP tools
@mcp.register_tool
async def crawl_url(url: str, extract_info: bool = False):
    """
    Crawl a single URL and optionally extract travel information.

    Args:
        url: The URL to crawl
        extract_info: Whether to extract structured travel information

    Returns:
        Raw crawl result or extracted travel information
    """
    await crawler_service.warmup()
    result = await crawler_service.crawl_url(url)

    if extract_info:
        return extractor.extract_destination_info(result)
    else:
        return {
            "title": result.title,
            "content": result.markdown,
            "links": result.links
        }

@mcp.register_tool
async def search_and_crawl_destination(destination: str, country: str = None, max_results: int = 3):
    """
    Search for a destination and crawl the top results.

    Args:
        destination: Destination name to search for
        country: Optional country to narrow search
        max_results: Maximum number of results to crawl

    Returns:
        Aggregated information about the destination
    """
    # This would use a search API in a real implementation
    # For now, we'll use a mock implementation
    search_query = f"{destination} travel guide"
    if country:
        search_query += f" {country}"

    # Mock search results
    search_results = [
        f"https://example.com/travel/{destination.lower().replace(' ', '-')}",
        f"https://traveltips.com/{destination.lower().replace(' ', '-')}-guide",
        f"https://wikitravel.org/en/{destination.replace(' ', '_')}"
    ][:max_results]

    # Crawl all results
    results = await crawler_service.crawl_multiple(search_results)

    # Extract and combine information
    combined_info = {
        "destination": destination,
        "country": country,
        "sources": list(results.keys()),
        "overview": "",
        "attractions": [],
        "practical_info": {}
    }

    # Process each result to build combined information
    for url, result in results.items():
        dest_info = extractor.extract_destination_info(result)

        # Add overview if not already set
        if not combined_info["overview"] and dest_info.get("overview"):
            combined_info["overview"] = dest_info["overview"]

        # Add attractions
        for attraction in dest_info.get("attractions", []):
            if attraction not in combined_info["attractions"]:
                combined_info["attractions"].append(attraction)

        # Merge practical info
        for key, value in dest_info.get("practical_info", {}).items():
            if key not in combined_info["practical_info"] and value:
                combined_info["practical_info"][key] = value

    return combined_info

@mcp.register_tool
async def get_travel_advisory(country: str):
    """
    Get travel advisory information for a country.

    Args:
        country: Country name or code

    Returns:
        Travel advisory information
    """
    # Convert country to lowercase for URL formatting
    country_formatted = country.lower().replace(" ", "-")

    # Try to crawl US travel advisory
    url = f"https://travel.state.gov/content/travel/en/traveladvisories/traveladvisories/{country_formatted}-travel-advisory.html"

    try:
        result = await crawler_service.crawl_url(url)

        # Extract advisory level and information
        advisory = {
            "country": country,
            "source": "US Department of State",
            "last_updated": result.timestamp.isoformat(),
            "content": result.markdown,
            "advisory_level": _extract_advisory_level(result.markdown),
            "key_points": _extract_key_points(result.markdown)
        }

        return advisory
    except Exception as e:
        return {
            "country": country,
            "error": f"Could not retrieve travel advisory: {str(e)}"
        }

def _extract_advisory_level(content):
    """Extract advisory level from content."""
    if "Level 4: Do Not Travel" in content:
        return {"level": 4, "description": "Do Not Travel"}
    elif "Level 3: Reconsider Travel" in content:
        return {"level": 3, "description": "Reconsider Travel"}
    elif "Level 2: Exercise Increased Caution" in content:
        return {"level": 2, "description": "Exercise Increased Caution"}
    elif "Level 1: Exercise Normal Precautions" in content:
        return {"level": 1, "description": "Exercise Normal Precautions"}
    else:
        return {"level": None, "description": "Unknown"}

def _extract_key_points(content):
    """Extract key advisory points."""
    key_points = []

    # Look for bullet points or key sections
    matches = re.findall(r'[*•-] ([^*•\n][^\n]+)', content)

    for match in matches:
        point = match.strip()
        if len(point) > 20 and not re.search(r'privacy|cookie|terms', point, re.I):
            key_points.append(point)

    return key_points[:5]  # Limit to top 5 points

# Start MCP server
if __name__ == "__main__":
    port = 3000
    print(f"Starting Crawl4AI MCP server on port {port}")
    mcp.serve(port=port)
```

## Usage Patterns

To maximize the value of web crawling while controlling costs, follow these usage patterns:

### 1. Selective Crawling

Only crawl when necessary, prioritizing:

- High-value information (travel advisories, entry requirements)
- Time-sensitive data (operating hours, current events)
- User-requested details (specific attraction information)

### 2. Comprehensive Caching

Implement aggressive caching based on data volatility:

- Travel advisories: 24-hour cache
- Destination information: 6-hour cache
- Attraction details: 12-hour cache
- Research topics: 3-day cache

### 3. Agent Prompt Enhancement

Update the travel agent prompt to include web crawling capabilities:

```plaintext
You are TripSage, an AI travel assistant specializing in comprehensive trip planning.

CAPABILITIES:
- Search and book flights using Duffel API
- Find accommodations through OpenBnB (Airbnb data) and Apify (Booking.com)
- Locate attractions and restaurants via Google Maps Platform
- Access real-time travel information through web search
- Get current weather data and forecasts for destinations
- Retrieve up-to-date travel advisories and destination information through web crawling

INTERACTION GUIDELINES:
1. Always gather key trip parameters first (dates, destination, budget, preferences)
2. Use appropriate API calls based on the user's query stage:
   - Initial planning: Use lightweight search APIs first
   - Specific requests: Use specialized booking APIs
3. Present options clearly with price, ratings, and key features
4. Maintain state between interactions to avoid repeating information
5. Offer recommendations based on user preferences and constraints

WEB CRAWLING INTEGRATION:
- Check current travel advisories when users ask about specific destinations
- Retrieve up-to-date destination information for richer recommendations
- Get current attraction details (hours, prices, special events)
- Conduct deep research on specialized travel topics when needed

When calling web crawling tools:
- For travel advisories: Include country code or name for accurate results
- For destination information: Use specific destination names
- For attraction details: Include both attraction name and location
- For deep research: Formulate specific topics for more targeted results

Remember to use web crawling selectively and efficiently to control costs.

IMPORTANT: Handle API errors gracefully. If data is unavailable, explain why and suggest alternatives.
```

## Implementation Checklist

- [ ] Install Crawl4AI and dependencies
- [ ] Set up TravelCrawlerService for basic web crawling
- [ ] Implement TravelInfoExtractor for parsing travel content
- [ ] Set up CrawlCacheManager for optimizing repeat crawls
- [ ] Create MCP server for AI agent integration
- [ ] Test with sample travel destinations
- [ ] Implement error handling and logging
- [ ] Document usage for other developers
- [ ] Integrate with other TripSage components

## Conclusion

This integration guide provides a comprehensive setup for using Crawl4AI with TripSage. The implementation includes:

- Basic web crawling with Crawl4AI
- Travel-specific information extraction
- MCP server for agent integration
- Caching for performance optimization
- Advanced destination research capabilities

This approach leverages Crawl4AI's open-source nature to provide powerful web crawling capabilities without subscription fees or API key requirements, making it ideal for personal projects where users provide their own resources.
