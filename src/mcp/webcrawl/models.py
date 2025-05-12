"""
WebCrawl MCP models for the TripSage travel planning system.

This module provides data models for the WebCrawl MCP client, which accesses
web crawling capabilities through external MCPs (Crawl4AI and Firecrawl).
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, HttpUrl


class WebAction(Enum):
    """Enumeration of web actions that can be performed."""
    
    CLICK = "click"
    SCREENSHOT = "screenshot"
    WAIT = "wait"
    WRITE = "write"
    PRESS = "press"
    SCROLL = "scroll"


class ScrapeOptions(BaseModel):
    """Options for scraping a URL."""
    
    bypass_cache: bool = Field(False, description="Whether to bypass cache")
    full_page: bool = Field(False, description="Whether to scrape the full page")
    js_enabled: bool = Field(True, description="Whether JavaScript is enabled")
    process_iframes: bool = Field(False, description="Whether to process iframes")
    include_links: bool = Field(False, description="Whether to include links")
    include_screenshots: bool = Field(False, description="Whether to include screenshots")
    css_selector: Optional[str] = Field(
        None, description="CSS selector to extract specific content"
    )
    wait_time: Optional[int] = Field(
        None, description="Time to wait for dynamic content (ms)"
    )


class ScrapeParams(BaseModel):
    """Parameters for scraping a URL."""
    
    url: str = Field(..., description="URL to scrape")
    options: Optional[ScrapeOptions] = Field(
        None, description="Scrape options"
    )


class ScrapeResponse(BaseModel):
    """Response for a scrape request."""
    
    success: bool = Field(..., description="Whether the scrape was successful")
    content: str = Field(..., description="Scraped content")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Metadata about the page"
    )
    links: Dict[str, Any] = Field(
        default_factory=dict, description="Links from the page"
    )
    error: Optional[str] = Field(None, description="Error message if unsuccessful")
    url: Optional[str] = Field(None, description="URL that was scraped")
    title: Optional[str] = Field(None, description="Page title")
    formats: Optional[Dict[str, str]] = Field(
        None, description="Different content formats"
    )


class SearchParams(BaseModel):
    """Parameters for searching the web."""
    
    query: str = Field(..., description="Search query")
    limit: Optional[int] = Field(5, description="Maximum number of results")
    filter: Optional[str] = Field(None, description="Search filter")
    country: Optional[str] = Field(None, description="Country code for search")
    tbs: Optional[str] = Field(None, description="Time-based search filter")


class SearchResult(BaseModel):
    """A single search result."""
    
    title: str = Field(..., description="Result title")
    url: str = Field(..., description="Result URL")
    snippet: Optional[str] = Field(None, description="Result snippet")
    content: Optional[str] = Field(None, description="Result full content")
    source: Optional[str] = Field(None, description="Source of the result")
    description: Optional[str] = Field(None, description="Result description")


class SearchResponse(BaseModel):
    """Response for a search request."""
    
    success: bool = Field(..., description="Whether the search was successful")
    query: Optional[str] = Field(None, description="Original search query")
    results: List[SearchResult] = Field(
        default_factory=list, description="Search results"
    )
    error: Optional[str] = Field(None, description="Error message if unsuccessful")
    count: Optional[int] = Field(None, description="Number of results")


class ExtractParams(BaseModel):
    """Parameters for extracting structured content from a URL."""
    
    url: str = Field(..., description="URL to extract from")
    extract_type: str = Field(
        ..., description="Type of content to extract (article, product, etc.)"
    )
    prompt: Optional[str] = Field(
        None, description="Custom extraction prompt"
    )
    schema: Optional[Dict[str, Any]] = Field(
        None, description="Schema for structured extraction"
    )


class ExtractResponse(BaseModel):
    """Response for an extract request."""
    
    success: bool = Field(..., description="Whether the extraction was successful")
    content: Dict[str, Any] = Field(
        default_factory=dict, description="Extracted structured content"
    )
    url: Optional[str] = Field(None, description="Source URL")
    error: Optional[str] = Field(None, description="Error message if unsuccessful")


class MapParams(BaseModel):
    """Parameters for mapping a website."""
    
    url: str = Field(..., description="URL to map")
    include_subdomains: Optional[bool] = Field(
        False, description="Whether to include subdomains"
    )
    limit: Optional[int] = Field(
        100, description="Maximum number of URLs to map"
    )


class MapResponse(BaseModel):
    """Response for a map request."""
    
    success: bool = Field(..., description="Whether the mapping was successful")
    urls: List[str] = Field(default_factory=list, description="Mapped URLs")
    error: Optional[str] = Field(None, description="Error message if unsuccessful")


class CrawlParams(BaseModel):
    """Parameters for crawling a website."""
    
    url: str = Field(..., description="URL to crawl")
    limit: Optional[int] = Field(
        10, description="Maximum number of pages to crawl"
    )
    max_depth: Optional[int] = Field(
        2, description="Maximum link depth to crawl"
    )
    scrape_options: Optional[ScrapeOptions] = Field(
        None, description="Scrape options for each page"
    )


class CrawlResponse(BaseModel):
    """Response for a crawl request."""
    
    success: bool = Field(..., description="Whether the crawl was successful")
    crawl_id: str = Field(..., description="ID of the crawl job")
    url: str = Field(..., description="Original crawl URL")
    status: str = Field(..., description="Crawl job status")
    error: Optional[str] = Field(None, description="Error message if unsuccessful")


class CrawlStatusParams(BaseModel):
    """Parameters for checking crawl status."""
    
    crawl_id: str = Field(..., description="ID of the crawl job")


class CrawlStatusResponse(BaseModel):
    """Response for a crawl status request."""
    
    success: bool = Field(..., description="Whether the status check was successful")
    status: str = Field(..., description="Crawl job status")
    url: str = Field(..., description="Original crawl URL")
    pages_crawled: int = Field(
        0, description="Number of pages crawled so far"
    )
    total_pages: int = Field(
        0, description="Total number of pages to crawl"
    )
    results: List[Dict[str, Any]] = Field(
        default_factory=list, description="Crawl results if available"
    )
    error: Optional[str] = Field(None, description="Error message if unsuccessful")


class DeepResearchParams(BaseModel):
    """Parameters for deep research on a topic."""
    
    query: str = Field(..., description="Research query")
    max_depth: Optional[int] = Field(
        3, description="Maximum research depth"
    )
    max_urls: Optional[int] = Field(
        5, description="Maximum number of URLs to analyze"
    )
    time_limit: Optional[int] = Field(
        60, description="Time limit in seconds"
    )


class DeepResearchResponse(BaseModel):
    """Response for a deep research request."""
    
    success: bool = Field(..., description="Whether the research was successful")
    query: str = Field(..., description="Original research query")
    summary: str = Field(..., description="Research summary")
    sources: List[Dict[str, Any]] = Field(
        default_factory=list, description="Research sources"
    )
    insights: Optional[List[str]] = Field(
        None, description="Key insights from research"
    )
    error: Optional[str] = Field(None, description="Error message if unsuccessful")


class GenerateLLMsTxtParams(BaseModel):
    """Parameters for generating LLMs.txt for a website."""
    
    url: str = Field(..., description="URL to generate LLMs.txt for")
    max_urls: Optional[int] = Field(
        10, description="Maximum number of URLs to process"
    )
    show_full_text: Optional[bool] = Field(
        False, description="Whether to show the full text"
    )


class GenerateLLMsTxtResponse(BaseModel):
    """Response for a generate LLMs.txt request."""
    
    success: bool = Field(..., description="Whether the generation was successful")
    url: str = Field(..., description="Original URL")
    llms_txt: str = Field(..., description="Generated LLMs.txt content")
    full_text: Optional[str] = Field(
        None, description="Full LLMs-full.txt content if requested"
    )
    error: Optional[str] = Field(None, description="Error message if unsuccessful")


class CheckCrawlStatusParams(BaseModel):
    """Parameters for checking crawl status."""
    
    id: str = Field(..., description="ID of the crawl job")