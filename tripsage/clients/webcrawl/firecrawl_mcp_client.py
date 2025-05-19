"""
Firecrawl MCP Client for TripSage web crawling integration.

This client integrates with the Firecrawl MCP server (https://github.com/mendableai/firecrawl-mcp-server)
to provide web scraping, crawling, and structured data extraction capabilities.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
from pydantic import BaseModel, Field

from tripsage.config.mcp_settings import FirecrawlMCPConfig, get_mcp_settings
from tripsage.utils.cache import ContentType, WebOperationsCache, web_cache
from tripsage.utils.error_handling import with_error_handling

logger = logging.getLogger(__name__)


class FirecrawlScrapeParams(BaseModel):
    """Parameters for scraping a single URL."""

    url: str
    formats: List[str] = Field(default=["markdown"])
    only_main_content: bool = Field(default=True, alias="onlyMainContent")
    wait_for: Optional[int] = Field(default=None, alias="waitFor")
    timeout: Optional[int] = Field(default=30000)
    mobile: bool = Field(default=False)
    include_tags: Optional[List[str]] = Field(default=None, alias="includeTags")
    exclude_tags: Optional[List[str]] = Field(default=None, alias="excludeTags")

    model_config = {"populate_by_name": True}


class FirecrawlCrawlParams(BaseModel):
    """Parameters for crawling a website."""

    url: str
    max_depth: int = Field(default=2, alias="maxDepth")
    limit: int = Field(default=100)
    allow_external_links: bool = Field(default=False, alias="allowExternalLinks")
    deduplicate_similar_urls: bool = Field(default=True, alias="deduplicateSimilarURLs")

    model_config = {"populate_by_name": True}


class FirecrawlExtractParams(BaseModel):
    """Parameters for extracting structured data from URLs."""

    urls: List[str]
    prompt: str
    system_prompt: Optional[str] = Field(default=None, alias="systemPrompt")
    schema: Optional[Dict[str, Any]] = Field(default=None)
    allow_external_links: bool = Field(default=False, alias="allowExternalLinks")
    enable_web_search: bool = Field(default=False, alias="enableWebSearch")
    include_subdomains: bool = Field(default=False, alias="includeSubdomains")

    model_config = {"populate_by_name": True}


class FirecrawlMCPRequest(BaseModel):
    """Base model for MCP requests."""

    jsonrpc: str = "2.0"
    method: str = "tools/call"
    id: str = Field(default_factory=lambda: f"firecrawl-{datetime.now().timestamp()}")
    params: Dict[str, Any]


class FirecrawlMCPClient:
    """Client for interacting with the Firecrawl MCP server."""

    _instance: Optional["FirecrawlMCPClient"] = None

    def __new__(cls) -> "FirecrawlMCPClient":
        """Implement singleton pattern for the client."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the Firecrawl MCP client."""
        if hasattr(self, "_initialized"):
            return

        # Get configuration from settings
        settings = get_mcp_settings()
        config = settings.firecrawl
        if not config:
            raise ValueError("Firecrawl MCP configuration not found")

        self._config: FirecrawlMCPConfig = config
        self._cache: WebOperationsCache = web_cache

        # Initialize HTTP client
        self._client = httpx.AsyncClient(
            base_url=self._config.mcp_server_url,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            timeout=60.0,
        )

        self._initialized = True
        logger.info(
            f"Initialized FirecrawlMCPClient with server URL: "
            f"{self._config.mcp_server_url}"
        )

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def close(self):
        """Close the HTTP client."""
        if hasattr(self, "_client"):
            await self._client.aclose()

    def _build_mcp_request(
        self, tool_name: str, arguments: Dict[str, Any]
    ) -> FirecrawlMCPRequest:
        """Build an MCP request for the given tool and arguments."""
        return FirecrawlMCPRequest(params={"name": tool_name, "arguments": arguments})

    async def _send_request(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        cache_key: Optional[str] = None,
        content_type: ContentType = ContentType.MARKDOWN,
        ttl_minutes: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Send a request to the MCP server with optional caching."""
        # Check cache first if cache key is provided
        if cache_key:
            cached_result = await self._cache.get(cache_key)
            if cached_result:
                logger.info(f"Cache hit for key: {cache_key}")
                await self._cache.record_hit(cache_key)
                return cached_result

        # Build and send the request
        request = self._build_mcp_request(tool_name, arguments)

        try:
            response = await self._client.post(
                "/",
                json=request.model_dump(),
            )
            response.raise_for_status()

            result = response.json()

            # Extract the actual response data from MCP response structure
            if "result" in result:
                data = result["result"]
            else:
                data = result

            # Cache the result if cache key is provided
            if cache_key:
                await self._cache.set(
                    cache_key,
                    data,
                    content_type=content_type,
                    ttl_minutes=ttl_minutes,
                    source="firecrawl_mcp",
                )
                logger.info(f"Cached result for key: {cache_key}")

            return data

        except httpx.HTTPError as e:
            logger.error(f"HTTP error calling {tool_name}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error calling {tool_name}: {e}")
            raise

    @with_error_handling
    async def scrape_url(
        self,
        url: str,
        params: Optional[FirecrawlScrapeParams] = None,
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        """
        Scrape content from a single URL.

        Args:
            url: The URL to scrape
            params: Optional scraping parameters
            use_cache: Whether to use caching

        Returns:
            The scraped content and metadata
        """
        if params is None:
            params = FirecrawlScrapeParams(url=url)
        else:
            params.url = url

        # Prepare cache key
        cache_key = None
        if use_cache:
            cache_key = f"firecrawl:scrape:{url}"

        # Determine TTL based on content
        ttl_minutes = None
        if use_cache:
            # For booking sites, use shorter TTL due to dynamic pricing
            if any(
                domain in url for domain in ["airbnb.com", "booking.com", "hotels.com"]
            ):
                ttl_minutes = 60  # 1 hour
            else:
                ttl_minutes = 1440  # 24 hours

        logger.info(f"Scraping URL: {url} with Firecrawl MCP")

        # Convert Pydantic model to dict and use alias mapping
        arguments = params.model_dump(by_alias=True, exclude_none=True)

        return await self._send_request(
            tool_name="firecrawl_scrape",
            arguments=arguments,
            cache_key=cache_key,
            content_type=ContentType.MARKDOWN,
            ttl_minutes=ttl_minutes,
        )

    @with_error_handling
    async def crawl_url(
        self,
        url: str,
        params: Optional[FirecrawlCrawlParams] = None,
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        """
        Start a crawl of a website.

        Args:
            url: The URL to start crawling from
            params: Optional crawling parameters
            use_cache: Whether to use caching

        Returns:
            The crawl job ID and status
        """
        if params is None:
            params = FirecrawlCrawlParams(url=url)
        else:
            params.url = url

        # Prepare cache key
        cache_key = None
        if use_cache:
            cache_key = f"firecrawl:crawl:{url}:{params.max_depth}"

        logger.info(f"Starting crawl of URL: {url} with Firecrawl MCP")

        arguments = params.model_dump(by_alias=True, exclude_none=True)

        return await self._send_request(
            tool_name="firecrawl_crawl",
            arguments=arguments,
            cache_key=cache_key,
            content_type=ContentType.MARKDOWN,
            ttl_minutes=1440,  # 24 hours for crawl results
        )

    @with_error_handling
    async def extract_structured_data(
        self,
        urls: List[str],
        prompt: str,
        params: Optional[FirecrawlExtractParams] = None,
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        """
        Extract structured data from URLs using LLM.

        Args:
            urls: List of URLs to extract data from
            prompt: The extraction prompt
            params: Optional extraction parameters
            use_cache: Whether to use caching

        Returns:
            The extracted structured data
        """
        if params is None:
            params = FirecrawlExtractParams(urls=urls, prompt=prompt)
        else:
            params.urls = urls
            params.prompt = prompt

        # Prepare cache key
        cache_key = None
        if use_cache:
            # Create cache key based on URLs and prompt
            urls_key = ":".join(sorted(urls))
            cache_key = f"firecrawl:extract:{urls_key}:{prompt[:50]}"

        logger.info(
            f"Extracting structured data from {len(urls)} URLs with Firecrawl MCP"
        )

        arguments = params.model_dump(by_alias=True, exclude_none=True)

        return await self._send_request(
            tool_name="firecrawl_extract",
            arguments=arguments,
            cache_key=cache_key,
            content_type=ContentType.JSON,
            ttl_minutes=1440,  # 24 hours for extracted data
        )

    @with_error_handling
    async def search_web(
        self,
        query: str,
        limit: int = 5,
        scrape_results: bool = True,
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        """
        Search the web and optionally scrape the results.

        Args:
            query: The search query
            limit: Maximum number of results
            scrape_results: Whether to scrape the search results
            use_cache: Whether to use caching

        Returns:
            The search results
        """
        # Prepare cache key
        cache_key = None
        if use_cache:
            cache_key = f"firecrawl:search:{query}:{limit}:{scrape_results}"

        logger.info(f"Searching web for: {query} with Firecrawl MCP")

        arguments = {"query": query, "limit": limit}

        if scrape_results:
            arguments["scrapeOptions"] = {
                "formats": ["markdown"],
                "onlyMainContent": True,
            }

        return await self._send_request(
            tool_name="firecrawl_search",
            arguments=arguments,
            cache_key=cache_key,
            content_type=ContentType.MARKDOWN,
            ttl_minutes=720,  # 12 hours for search results
        )

    @with_error_handling
    async def check_crawl_status(self, job_id: str) -> Dict[str, Any]:
        """
        Check the status of a crawl job.

        Args:
            job_id: The crawl job ID

        Returns:
            The crawl job status and data
        """
        logger.info(f"Checking crawl status for job: {job_id}")

        return await self._send_request(
            tool_name="firecrawl_check_crawl_status", arguments={"id": job_id}
        )

    @with_error_handling
    async def batch_scrape(
        self,
        urls: List[str],
        options: Optional[Dict[str, Any]] = None,
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        """
        Scrape multiple URLs in batch.

        Args:
            urls: List of URLs to scrape
            options: Optional scraping options
            use_cache: Whether to use caching

        Returns:
            The batch operation ID
        """
        # Prepare cache key
        cache_key = None
        if use_cache:
            urls_key = ":".join(sorted(urls))
            cache_key = f"firecrawl:batch:{urls_key}"

        logger.info(f"Starting batch scrape of {len(urls)} URLs with Firecrawl MCP")

        arguments = {
            "urls": urls,
            "options": options or {"formats": ["markdown"], "onlyMainContent": True},
        }

        return await self._send_request(
            tool_name="firecrawl_batch_scrape",
            arguments=arguments,
            cache_key=cache_key,
            content_type=ContentType.MARKDOWN,
            ttl_minutes=1440,  # 24 hours for batch results
        )


# Convenience function to get a singleton instance
def get_firecrawl_client() -> FirecrawlMCPClient:
    """Get the singleton instance of FirecrawlMCPClient."""
    return FirecrawlMCPClient()
