"""
Pydantic models for Webcrawl MCP client.

This module defines the parameter and response models for the Webcrawl MCP Client,
providing proper validation and type safety.
"""

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class BaseParams(BaseModel):
    """Base model for all parameter models."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")


class BaseResponse(BaseModel):
    """Base model for all response models."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class WebAction(BaseModel):
    """Model for a web action to perform before scraping."""

    type: str = Field(..., description="Type of action to perform (click, wait, etc.)")
    selector: Optional[str] = Field(
        None, description="CSS selector for the target element"
    )
    text: Optional[str] = Field(None, description="Text to input")
    milliseconds: Optional[int] = Field(
        None, ge=0, le=60000, description="Time to wait in milliseconds"
    )
    key: Optional[str] = Field(None, description="Key to press")
    script: Optional[str] = Field(None, description="JavaScript code to execute")
    direction: Optional[str] = Field(None, description="Scroll direction (up or down)")
    fullPage: Optional[bool] = Field(
        None, description="Whether to take full page screenshot"
    )

    model_config = ConfigDict(extra="allow")

    @model_validator(mode="after")
    def validate_action(self) -> "WebAction":
        """Validate action parameters based on action type."""
        if self.type == "click" and not self.selector:
            raise ValueError("Selector is required for click action")
        elif self.type == "wait" and not self.milliseconds:
            raise ValueError("Milliseconds is required for wait action")
        elif self.type == "write" and (not self.selector or self.text is None):
            raise ValueError("Selector and text are required for write action")
        elif self.type == "press" and not self.key:
            raise ValueError("Key is required for press action")
        elif self.type == "executeJavascript" and not self.script:
            raise ValueError("Script is required for executeJavascript action")
        elif self.type == "scroll" and not self.direction:
            raise ValueError("Direction is required for scroll action")
        return self


class ScrapeParams(BaseParams):
    """Parameters for scraping a webpage."""

    url: str = Field(..., description="URL to scrape")
    actions: Optional[List[WebAction]] = Field(
        None, description="Actions to perform before scraping"
    )
    formats: Optional[List[str]] = Field(None, description="Content formats to extract")
    onlyMainContent: Optional[bool] = Field(
        None, description="Extract only main content"
    )
    waitFor: Optional[int] = Field(
        None, ge=0, le=60000, description="Time to wait for dynamic content"
    )
    includeTags: Optional[List[str]] = Field(None, description="HTML tags to include")
    excludeTags: Optional[List[str]] = Field(None, description="HTML tags to exclude")
    removeBase64Images: Optional[bool] = Field(
        None, description="Remove base64 encoded images"
    )
    mobile: Optional[bool] = Field(None, description="Use mobile viewport")
    skipTlsVerification: Optional[bool] = Field(
        None, description="Skip TLS verification"
    )
    extract: Optional[Dict[str, Any]] = Field(
        None, description="Settings for structured extraction"
    )

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate URL format."""
        if not v or not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("URL must be a valid HTTP or HTTPS URL")
        return v


class MapParams(BaseParams):
    """Parameters for discovering URLs from a starting point."""

    url: str = Field(..., description="Starting URL for URL discovery")
    sitemapOnly: Optional[bool] = Field(
        None, description="Only use sitemap.xml for discovery"
    )
    ignoreSitemap: Optional[bool] = Field(
        None, description="Skip sitemap.xml discovery"
    )
    limit: Optional[int] = Field(
        None, ge=1, le=1000, description="Maximum number of URLs to return"
    )
    search: Optional[str] = Field(None, description="Search term to filter URLs")
    includeSubdomains: Optional[bool] = Field(
        None, description="Include URLs from subdomains"
    )

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate URL format."""
        if not v or not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("URL must be a valid HTTP or HTTPS URL")
        return v


class CrawlParams(BaseParams):
    """Parameters for crawling multiple pages from a starting URL."""

    url: str = Field(..., description="Starting URL for the crawl")
    maxDepth: Optional[int] = Field(
        None, ge=1, le=10, description="Maximum link depth to crawl"
    )
    limit: Optional[int] = Field(
        None, ge=1, le=1000, description="Maximum number of pages to crawl"
    )
    includePaths: Optional[List[str]] = Field(
        None, description="Only crawl these URL paths"
    )
    excludePaths: Optional[List[str]] = Field(
        None, description="URL paths to exclude from crawling"
    )
    scrapeOptions: Optional[Dict[str, Any]] = Field(
        None, description="Options for scraping each page"
    )
    webhook: Optional[Union[str, Dict[str, Any]]] = Field(
        None, description="Webhook URL or config"
    )
    allowExternalLinks: Optional[bool] = Field(
        None, description="Allow crawling links to external domains"
    )
    allowBackwardLinks: Optional[bool] = Field(
        None, description="Allow links that point to parent directories"
    )
    deduplicateSimilarURLs: Optional[bool] = Field(
        None, description="Remove similar URLs during crawl"
    )
    ignoreQueryParameters: Optional[bool] = Field(
        None, description="Ignore query parameters when comparing URLs"
    )
    ignoreSitemap: Optional[bool] = Field(
        None, description="Skip sitemap.xml discovery"
    )

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate URL format."""
        if not v or not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("URL must be a valid HTTP or HTTPS URL")
        return v


class CheckCrawlStatusParams(BaseParams):
    """Parameters for checking crawl status."""

    id: str = Field(..., description="Crawl job ID to check")


class ScrapeOptions(BaseModel):
    """Options for scraping search results."""

    formats: List[str] = Field(["markdown"], description="Content formats to extract")
    onlyMainContent: Optional[bool] = Field(
        True, description="Extract only main content"
    )
    waitFor: Optional[int] = Field(
        None, ge=0, le=60000, description="Wait time in milliseconds"
    )

    model_config = ConfigDict(extra="allow")


class SearchParams(BaseParams):
    """Parameters for web search."""

    query: str = Field(..., description="Search query")
    limit: Optional[int] = Field(
        5, ge=1, le=100, description="Maximum number of results"
    )
    scrapeOptions: Optional[ScrapeOptions] = Field(
        None, description="Options for scraping results"
    )
    tbs: Optional[str] = Field(None, description="Time-based search filter")
    filter: Optional[str] = Field(None, description="Search filter")
    lang: Optional[str] = Field("en", description="Language code")
    country: Optional[str] = Field("us", description="Country code")

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        """Validate search query."""
        if not v or len(v.strip()) == 0:
            raise ValueError("Search query cannot be empty")
        return v


class ExtractParams(BaseParams):
    """Parameters for structured information extraction."""

    urls: List[str] = Field(..., min_length=1, description="URLs to extract from")
    prompt: Optional[str] = Field(None, description="Prompt for LLM extraction")
    schema: Optional[Dict[str, Any]] = Field(
        None, description="JSON schema for extraction"
    )
    systemPrompt: Optional[str] = Field(None, description="System prompt for LLM")
    enableWebSearch: Optional[bool] = Field(
        None, description="Enable web search for context"
    )
    allowExternalLinks: Optional[bool] = Field(
        None, description="Allow extraction from external links"
    )
    includeSubdomains: Optional[bool] = Field(
        None, description="Include subdomains in extraction"
    )

    @field_validator("urls")
    @classmethod
    def validate_urls(cls, v: List[str]) -> List[str]:
        """Validate URL formats."""
        for url in v:
            if not url or not (url.startswith("http://") or url.startswith("https://")):
                raise ValueError(f"URL '{url}' must be a valid HTTP or HTTPS URL")
        return v


class DeepResearchParams(BaseParams):
    """Parameters for deep research on a query."""

    query: str = Field(..., description="Research query")
    maxDepth: Optional[int] = Field(
        3, ge=1, le=10, description="Maximum research depth"
    )
    maxUrls: Optional[int] = Field(
        20, ge=1, le=1000, description="Maximum URLs to analyze"
    )
    timeLimit: Optional[int] = Field(
        120, ge=30, le=300, description="Time limit in seconds"
    )

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        """Validate research query."""
        if not v or len(v.strip()) == 0:
            raise ValueError("Research query cannot be empty")
        return v


class GenerateLLMsTxtParams(BaseParams):
    """Parameters for generating LLMs.txt file."""

    url: str = Field(..., description="URL to generate LLMs.txt from")
    maxUrls: Optional[int] = Field(
        10, ge=1, le=100, description="Maximum URLs to process"
    )
    showFullText: Optional[bool] = Field(False, description="Show full LLMs-full.txt")

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate URL format."""
        if not v or not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("URL must be a valid HTTP or HTTPS URL")
        return v


class ScrapeResponse(BaseResponse):
    """Response for webpage scraping."""

    url: str = Field(..., description="Scraped URL")
    title: Optional[str] = Field(None, description="Page title")
    formats: Dict[str, Any] = Field(
        {}, description="Formatted content in requested formats"
    )
    error: Optional[str] = Field(None, description="Error message if scraping failed")


class MapResponse(BaseResponse):
    """Response for URL discovery."""

    urls: List[str] = Field([], description="Discovered URLs")
    count: int = Field(0, description="Number of URLs discovered")
    source: str = Field(..., description="Source URL")
    error: Optional[str] = Field(None, description="Error message if mapping failed")


class CrawlResponse(BaseResponse):
    """Response for web crawling."""

    id: str = Field(..., description="Crawl job ID")
    status: str = Field(..., description="Crawl status")
    url: str = Field(..., description="Starting URL")
    crawled_count: int = Field(0, description="Number of pages crawled so far")
    total_count: Optional[int] = Field(None, description="Total pages to crawl")
    progress: float = Field(0.0, description="Crawl progress (0-1)")
    error: Optional[str] = Field(None, description="Error message if crawling failed")


class CrawlStatusResponse(BaseResponse):
    """Response for crawl status check."""

    id: str = Field(..., description="Crawl job ID")
    status: str = Field(..., description="Crawl status")
    crawled_count: int = Field(0, description="Number of pages crawled so far")
    total_count: Optional[int] = Field(None, description="Total pages to crawl")
    progress: float = Field(0.0, description="Crawl progress (0-1)")
    results: Optional[Dict[str, Any]] = Field(
        None, description="Crawl results if completed"
    )
    error: Optional[str] = Field(
        None, description="Error message if status check failed"
    )


class SearchResult(BaseModel):
    """Model for a search result."""

    url: str = Field(..., description="Result URL")
    title: str = Field(..., description="Result title")
    description: str = Field(..., description="Result description")
    content: Optional[Dict[str, Any]] = Field(
        None, description="Scraped content if requested"
    )

    model_config = ConfigDict(extra="allow")


class SearchResponse(BaseResponse):
    """Response for web search."""

    results: List[SearchResult] = Field([], description="Search results")
    count: int = Field(0, description="Number of results")
    query: str = Field(..., description="Search query")
    error: Optional[str] = Field(None, description="Error message if search failed")


class ExtractResponse(BaseResponse):
    """Response for structured information extraction."""

    extractions: List[Dict[str, Any]] = Field(
        [], description="Extracted information from URLs"
    )
    count: int = Field(0, description="Number of extractions")
    schema: Optional[Dict[str, Any]] = Field(
        None, description="Schema used for extraction"
    )
    error: Optional[str] = Field(None, description="Error message if extraction failed")


class DeepResearchResponse(BaseResponse):
    """Response for deep research."""

    query: str = Field(..., description="Research query")
    summary: str = Field(..., description="Research summary")
    sources: List[Dict[str, Any]] = Field([], description="Sources used in research")
    insights: Optional[List[str]] = Field(
        None, description="Key insights from research"
    )
    error: Optional[str] = Field(None, description="Error message if research failed")


class GenerateLLMsTxtResponse(BaseResponse):
    """Response for LLMs.txt generation."""

    llms_txt: str = Field(..., description="Generated LLMs.txt content")
    llms_full_txt: Optional[str] = Field(None, description="Full LLMs.txt content")
    url: str = Field(..., description="Base URL")
    error: Optional[str] = Field(None, description="Error message if generation failed")
