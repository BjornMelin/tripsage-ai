# Web Crawling Integration Guide

This document provides comprehensive instructions for setting up and using Crawl4AI to enhance TripSage with web crawling capabilities.

## Overview

Crawl4AI is an open-source web crawling and scraping tool specifically optimized for Large Language Models (LLMs). Key features include:

- Asynchronous web crawling for efficient data collection
- Multiple output formats (Markdown, JSON, HTML)
- Customizable extraction strategies
- Self-hostable with no subscription fees or API key requirements
- Apache 2.0 license

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

### 3. Implementation

#### Basic Crawler Service

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

#### Travel Information Extractor

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

    def _extract_best_time_to_visit(self, content: str) -> str:
        """Extract best time to visit information."""
        # Find sections about timing
        time_sections = self._find_sections(content,
                                          ["when to visit", "best time", "weather",
                                           "season", "climate", "visit time"])

        # Extract sentences about timing
        if time_sections:
            # Extract complete sentences mentioning months or seasons
            sentences = re.findall(r'[^.!?]*(?:January|February|March|April|May|June|July|August|September|October|November|December|Spring|Summer|Fall|Autumn|Winter)[^.!?]*[.!?]',
                                 time_sections[0])

            if sentences:
                return " ".join(sentences[:3])  # Return up to first 3 relevant sentences

        return "Information not available"

    def _extract_safety_tips(self, content: str) -> List[str]:
        """Extract safety tips for the destination."""
        safety_sections = self._find_sections(content,
                                            ["safety", "safe", "security", "precaution",
                                             "warning", "danger", "health"])

        tips = []

        if safety_sections:
            # Extract bullet points or sentences containing safety terms
            items = re.findall(r'[*-] ([^\n]+)', safety_sections[0])
            for item in items:
                clean_item = item.strip()
                if len(clean_item) > 10:
                    tips.append(clean_item)

            # If no bullet points, extract sentences
            if not tips:
                sentences = re.findall(r'[^.!?]*(?:safety|caution|aware|careful|avoid|risk|danger)[^.!?]*[.!?]',
                                     safety_sections[0])
                tips = [s.strip() for s in sentences if len(s.strip()) > 10]

        return tips[:5]  # Limit to top 5 safety tips

    def _extract_local_transportation(self, content: str) -> Dict[str, List[str]]:
        """Extract local transportation information."""
        transport_sections = self._find_sections(content,
                                               ["transportation", "transport", "getting around",
                                                "travel", "bus", "train", "subway", "metro",
                                                "taxi", "how to get"])

        transport_info = {
            "methods": [],
            "tips": []
        }

        if transport_sections:
            # Extract transportation methods
            methods = re.findall(r'[*-] ([^\n]+)', transport_sections[0])

            for method in methods:
                clean_method = method.strip()
                if len(clean_method) > 5:
                    transport_info["methods"].append(clean_method)

            # Extract sentences containing transportation information
            sentences = re.findall(r'[^.!?]*(?:bus|train|metro|subway|taxi|transport|rent|car|bicycle|bike|walk|tour)[^.!?]*[.!?]',
                                 transport_sections[0])

            for sentence in sentences:
                clean_sentence = sentence.strip()
                if len(clean_sentence) > 10 and clean_sentence not in transport_info["methods"]:
                    transport_info["tips"].append(clean_sentence)

        return transport_info

    def _extract_currency(self, content: str) -> str:
        """Extract currency information."""
        currency_match = re.search(r'(?:currency|currencies|money)[^.!?]*?(?:is|are)[^.!?]*?([^.!?]*)[.!?]',
                                 content, re.I)

        if currency_match:
            return currency_match.group(1).strip()

        # Look for common currency names
        currency_names = ["Euro", "Dollar", "Pound", "Yen", "Yuan", "Rupee", "Ruble",
                         "Baht", "Peso", "Ringgit", "Dirham", "Krona", "Franc"]

        for currency in currency_names:
            if re.search(r'\b' + currency + r'\b', content, re.I):
                return currency

        return "Information not available"

    def _extract_language(self, content: str) -> str:
        """Extract language information."""
        language_match = re.search(r'(?:language|languages|speak|spoken)[^.!?]*?(?:is|are)[^.!?]*?([^.!?]*)[.!?]',
                                 content, re.I)

        if language_match:
            return language_match.group(1).strip()

        # Look for common language names
        language_names = ["English", "Spanish", "French", "German", "Italian", "Portuguese",
                         "Russian", "Chinese", "Japanese", "Arabic", "Hindi", "Thai", "Dutch"]

        for language in language_names:
            if re.search(r'\b' + language + r'\b', content, re.I):
                return language

        return "Information not available"

    def _find_sections(self, content: str, keywords: List[str]) -> List[str]:
        """
        Find sections in the content that match any of the given keywords.

        Args:
            content: Text content to search in
            keywords: List of keywords to match

        Returns:
            List of matching sections
        """
        sections = []

        # Pattern to match Markdown headers (# Header) or emphasized text (* Header: *)
        header_patterns = [
            r'#+\s+([^\n]*(?:' + '|'.join(keywords) + r')[^\n]*)\n',  # Markdown header
            r'\*+\s*([^\n]*(?:' + '|'.join(keywords) + r')[^\n]*)\s*\*+',  # Emphasized
            r'__([^\n]*(?:' + '|'.join(keywords) + r')[^\n]*)__',  # Bold
        ]

        for pattern in header_patterns:
            matches = re.finditer(pattern, content, re.I)

            for match in matches:
                header = match.group(1)
                header_start = match.end()

                # Find the end of the section (next header or end of content)
                next_header = re.search(r'#+\s+', content[header_start:])

                if next_header:
                    section_end = header_start + next_header.start()
                    section = content[header_start:section_end]
                else:
                    section = content[header_start:]

                sections.append(section.strip())

        # If no sections were found by headers, look for paragraphs containing keywords
        if not sections:
            paragraphs = re.split(r'\n\n+', content)

            for paragraph in paragraphs:
                if any(keyword in paragraph.lower() for keyword in keywords):
                    sections.append(paragraph.strip())

        return sections
```

#### Main Integration Example

```python
# trip_sage_crawler_integration.py
import asyncio
import argparse
import logging
import json
from pathlib import Path

from travel_crawler import TravelCrawlerService
from travel_extractor import TravelInfoExtractor

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("TripSage-Crawler-Integration")

async def crawl_destination(url: str, output_dir: str = None):
    """
    Crawl a destination URL and extract travel information.

    Args:
        url: URL of the destination to crawl
        output_dir: Directory to save the results (optional)
    """
    # Initialize crawler service
    crawler_service = TravelCrawlerService(cache_dir="crawl_cache")
    await crawler_service.warmup()

    # Crawl the URL
    result = await crawler_service.crawl_url(url)

    # Initialize extractor and extract travel information
    extractor = TravelInfoExtractor(use_markdown=True)
    destination_info = extractor.extract_destination_info(result)

    logger.info(f"Extracted information for destination: {destination_info['destination_name']}")
    logger.info(f"Found {len(destination_info['attractions'])} attractions")

    # Save the results if output_dir is provided
    if output_dir:
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True, parents=True)

        dest_name = destination_info["destination_name"]
        safe_filename = "".join(c if c.isalnum() else "_" for c in dest_name)

        # Save extraction result
        with open(output_path / f"{safe_filename}_info.json", 'w', encoding='utf-8') as f:
            json.dump(destination_info, f, ensure_ascii=False, indent=2)

        # Save raw markdown
        with open(output_path / f"{safe_filename}_raw.md", 'w', encoding='utf-8') as f:
            f.write(result.markdown or "")

        logger.info(f"Saved extraction results to {output_path}")

    return destination_info

async def batch_crawl_destinations(urls, output_dir=None):
    """
    Crawl multiple destination URLs in parallel.

    Args:
        urls: List of URLs to crawl
        output_dir: Directory to save the results (optional)
    """
    tasks = [crawl_destination(url, output_dir) for url in urls]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    successful_results = []

    for url, result in zip(urls, results):
        if isinstance(result, Exception):
            logger.error(f"Error processing {url}: {result}")
        else:
            successful_results.append(result)

    logger.info(f"Successfully processed {len(successful_results)}/{len(urls)} destinations")
    return successful_results

def main():
    """Run the crawler as a standalone script."""
    parser = argparse.ArgumentParser(description="TripSage Destination Crawler")
    parser.add_argument("--url", help="URL to crawl")
    parser.add_argument("--url-file", help="File containing URLs to crawl (one per line)")
    parser.add_argument("--output-dir", default="crawl_results", help="Directory to save results")
    args = parser.parse_args()

    if not args.url and not args.url_file:
        parser.error("Either --url or --url-file must be provided")

    urls = []
    if args.url:
        urls.append(args.url)

    if args.url_file:
        with open(args.url_file, 'r') as f:
            urls.extend([line.strip() for line in f if line.strip()])

    asyncio.run(batch_crawl_destinations(urls, args.output_dir))

if __name__ == "__main__":
    main()
```

## Advanced Techniques

### Destination Advisor AI

Enhance the crawler with LLM-based extraction for more accurate travel insights:

```python
# destination_advisor.py
import asyncio
from typing import Dict, List, Any
import logging
import json
from pathlib import Path

from crawl4ai import WebCrawler, CrawlResult
from travel_crawler import TravelCrawlerService

logger = logging.getLogger("TripSage-Destination-Advisor")

class DestinationAdvisor:
    """
    AI-powered destination advisor using Crawl4AI to gather information.
    """

    def __init__(self, crawler_service=None):
        """
        Initialize the destination advisor.

        Args:
            crawler_service: Optional TravelCrawlerService instance
        """
        self.crawler_service = crawler_service or TravelCrawlerService()

    async def research_destination(self, destination_name: str, country: str = None,
                                 num_sources: int = 3) -> Dict[str, Any]:
        """
        Research a travel destination by crawling multiple relevant sources.

        Args:
            destination_name: Name of the destination
            country: Optional country name to narrow results
            num_sources: Number of sources to crawl

        Returns:
            Dictionary containing comprehensive destination information
        """
        # Generate search queries for this destination
        queries = self._generate_search_queries(destination_name, country)

        # For simplicity, we're just using the first query
        # In a real application, you would use these to find relevant URLs
        # Here we'll simulate finding URLs
        query = queries[0]
        urls = await self._get_relevant_urls(query, num_sources)

        if not urls:
            logger.warning(f"No URLs found for {destination_name}")
            return {
                "destination_name": destination_name,
                "country": country,
                "error": "No information sources found"
            }

        # Crawl all the URLs
        results = {}
        for url in urls:
            try:
                result = await self.crawler_service.crawl_url(url)
                results[url] = result
                logger.info(f"Successfully crawled {url}")
            except Exception as e:
                logger.error(f"Error crawling {url}: {e}")

        # Process and combine the information
        combined_info = await self._combine_destination_info(destination_name, country, results)
        return combined_info

    def _generate_search_queries(self, destination_name: str, country: str = None) -> List[str]:
        """Generate search queries for a destination."""
        queries = [
            f"travel guide {destination_name}",
            f"things to do in {destination_name}",
            f"best time to visit {destination_name}",
            f"{destination_name} attractions",
            f"{destination_name} travel tips"
        ]

        if country:
            queries = [f"{q} {country}" for q in queries]

        return queries

    async def _get_relevant_urls(self, query: str, num_sources: int) -> List[str]:
        """
        Get relevant URLs for a query.

        In a real application, this would use a search API or web search.
        Here we're using dummy URLs for demonstration.
        """
        # This is a simplified demonstration that would use a real search API
        # in production code
        sample_domains = [
            "wikivoyage.org",
            "lonelyplanet.com",
            "tripadvisor.com",
            "roughguides.com",
            "travelandleisure.com",
            "cntraveler.com",
            "fodors.com",
            "frommers.com",
            "timeout.com",
            "thepointsguy.com"
        ]

        # In a real application, these would be actual search results
        query_terms = query.replace(" ", "+")
        urls = [f"https://www.{domain}/search?q={query_terms}" for domain in sample_domains[:num_sources]]

        return urls

    async def _combine_destination_info(self, destination_name: str, country: str,
                                      crawl_results: Dict[str, CrawlResult]) -> Dict[str, Any]:
        """
        Combine information from multiple sources into a comprehensive guide.

        Args:
            destination_name: Name of the destination
            country: Country of the destination
            crawl_results: Dictionary mapping URLs to CrawlResult objects

        Returns:
            Combined destination information
        """
        # Create a basic structure for the combined information
        combined_info = {
            "destination_name": destination_name,
            "country": country or "Unknown",
            "overview": "",
            "sources": list(crawl_results.keys()),
            "attractions": [],
            "practical_info": {
                "best_time_to_visit": "",
                "climate": "",
                "local_transportation": [],
                "safety_tips": [],
                "currency": "",
                "language": "",
                "visa_requirements": ""
            },
            "accommodations": [],
            "food_and_drink": [],
            "sample_itineraries": []
        }

        # In a real application, you would use more sophisticated techniques
        # to combine information from multiple sources, potentially using
        # an LLM to analyze and summarize the content

        # For this example, we'll do a simple combination
        all_content = []
        for url, result in crawl_results.items():
            if result.markdown:
                all_content.append(result.markdown)

        # Simulate creating an overview by taking the first few paragraphs
        # In reality, you'd use NLP or LLM methods for better extraction
        if all_content:
            paragraphs = []
            for content in all_content:
                paragraphs.extend([p for p in content.split("\n\n") if len(p) > 100 and not p.startswith("#")])

            if paragraphs:
                combined_info["overview"] = paragraphs[0]

        # Add some sample attractions (in production, use proper extraction)
        sample_attractions = [
            {"name": f"Popular Spot in {destination_name} 1", "description": "A wonderful attraction to visit."},
            {"name": f"Museum of {destination_name}", "description": "A cultural highlight."},
            {"name": f"{destination_name} Park", "description": "A relaxing place to enjoy nature."}
        ]
        combined_info["attractions"] = sample_attractions

        # Fill in some practical info
        combined_info["practical_info"]["best_time_to_visit"] = "Spring and fall for moderate temperatures and fewer crowds."
        combined_info["practical_info"]["local_transportation"] = ["Public Transportation", "Taxis", "Rental Cars"]
        combined_info["practical_info"]["safety_tips"] = ["Watch your belongings in tourist areas", "Stay aware of your surroundings"]

        return combined_info
```

### Using Caching to Optimize Performance

Implement a caching system to reduce repeated crawls:

```python
# cache_manager.py
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger("TripSage-Cache-Manager")

class CrawlCacheManager:
    """Manage caching of crawl results."""

    def __init__(self, cache_dir: str, ttl_days: int = 7):
        """
        Initialize the cache manager.

        Args:
            cache_dir: Directory to store cache files
            ttl_days: Time-to-live for cache entries in days
        """
        self.cache_dir = Path(cache_dir)
        self.ttl_days = ttl_days
        self.cache_dir.mkdir(exist_ok=True, parents=True)

    def get_cached_result(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Get cached crawl result for a URL.

        Args:
            url: URL to get cached result for

        Returns:
            Cached result or None if not available
        """
        cache_file = self._get_cache_file_path(url)

        if not cache_file.exists():
            return None

        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Check if cache is expired
            cache_date = datetime.fromisoformat(data.get('timestamp', '2000-01-01'))
            if datetime.now() - cache_date > timedelta(days=self.ttl_days):
                logger.info(f"Cache expired for {url}")
                return None

            return data

        except Exception as e:
            logger.error(f"Error reading cache for {url}: {e}")
            return None

    def save_to_cache(self, url: str, result: Dict[str, Any]) -> bool:
        """
        Save crawl result to cache.

        Args:
            url: URL of the crawled page
            result: Crawl result to cache

        Returns:
            True if saved successfully, False otherwise
        """
        cache_file = self._get_cache_file_path(url)

        try:
            # Add timestamp to result
            result['timestamp'] = datetime.now().isoformat()

            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)

            logger.info(f"Saved result to cache: {cache_file}")
            return True

        except Exception as e:
            logger.error(f"Error saving cache for {url}: {e}")
            return False

    def clear_expired_cache(self) -> int:
        """
        Clear expired cache entries.

        Returns:
            Number of entries cleared
        """
        cleared_count = 0

        for cache_file in self.cache_dir.glob('*.json'):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                cache_date = datetime.fromisoformat(data.get('timestamp', '2000-01-01'))

                if datetime.now() - cache_date > timedelta(days=self.ttl_days):
                    os.remove(cache_file)
                    cleared_count += 1

            except Exception as e:
                logger.error(f"Error processing cache file {cache_file}: {e}")

        logger.info(f"Cleared {cleared_count} expired cache entries")
        return cleared_count

    def _get_cache_file_path(self, url: str) -> Path:
        """Generate cache file path for a URL."""
        # Create a filename from the URL
        safe_filename = "".join(c if c.isalnum() else "_" for c in url)

        # Limit filename length
        if len(safe_filename) > 100:
            safe_filename = safe_filename[:100] + "_" + str(hash(url))

        return self.cache_dir / f"{safe_filename}.json"
```

## Implementation Checklist

- [ ] Install Crawl4AI and dependencies
- [ ] Set up TravelCrawlerService for basic web crawling
- [ ] Implement TravelInfoExtractor for parsing travel content
- [ ] Set up CrawlCacheManager for optimizing repeat crawls
- [ ] Create DestinationAdvisor for AI-enhanced research
- [ ] Test with sample travel destinations
- [ ] Implement error handling and logging
- [ ] Document usage for other developers
- [ ] Integrate with other TripSage components

## Testing Your Setup

Test the crawling implementation with:

```bash
python trip_sage_crawler_integration.py --url "https://www.lonelyplanet.com/japan/tokyo" --output-dir "crawl_results"
```

To test with multiple URLs, create a text file with URLs (one per line) and run:

```bash
python trip_sage_crawler_integration.py --url-file "destination_urls.txt" --output-dir "crawl_results"
```

## Troubleshooting

### Common Issues

1. **Installation Errors**:

   - Make sure you have Python 3.9+ installed
   - Install with the git+ URL to get the latest version

2. **Browser Automation Failures**:

   - Install playwright browser dependencies:
     ```bash
     python -m playwright install chromium
     ```
   - Adjust browser_config timeout settings for slower connections

3. **Rate Limiting or IP Blocking**:

   - Implement proper delays between requests
   - Consider adding proxy support for high-volume crawling
   - Respect robots.txt and terms of service for all sites

4. **Memory Issues with Large Crawls**:
   - Reduce max_concurrent_tasks in the crawler configuration
   - Implement proper pagination or batching for large crawl jobs

## Conclusion

This integration guide provides a comprehensive setup for using Crawl4AI with TripSage. The implementation includes:

- Basic web crawling with Crawl4AI
- Travel-specific information extraction
- Caching for performance optimization
- Advanced destination research capabilities

This approach leverages Crawl4AI's open-source nature to provide powerful web crawling capabilities without subscription fees or API key requirements, making it ideal for personal projects where users provide their own resources.

## Next Steps

- Enhance extraction with destination-specific patterns
- Implement LLM-based content analysis for deeper insights
- Add support for crawling travel forums and review sites
- Integrate with other TripSage components like weather and calendar
