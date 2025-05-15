"""
Crawl4AI MCP Client for TripSage web crawling integration.

This client integrates with the Crawl4AI MCP server (https://github.com/unclecode/crawl4ai)
to provide web crawling, content extraction, and question-answering capabilities.
The server exposes both WebSocket and Server-Sent Events (SSE) endpoints for MCP communication.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
import websockets
from pydantic import BaseModel, Field, field_validator

from tripsage.config.mcp_settings import Crawl4AIMCPConfig, get_mcp_settings
from tripsage.utils.cache import ContentType, WebOperationsCache, web_cache
from tripsage.utils.error_handling import with_error_handling

logger = logging.getLogger(__name__)


class Crawl4AICrawlParams(BaseModel):
    """Parameters for crawling a URL with Crawl4AI."""

    url: str
    session_id: Optional[str] = Field(default=None, alias="sessionId")
    markdown: bool = Field(default=True)
    html: bool = Field(default=False)
    screenshot: bool = Field(default=False)
    pdf: bool = Field(default=False)
    wait_for: str = Field(default="", alias="waitFor")
    css: Optional[str] = None
    extraction_strategy: Optional[str] = Field(default=None, alias="extractionStrategy")
    seed_urls: Optional[List[str]] = Field(default=None, alias="seedUrls")
    max_pages: Optional[int] = Field(default=None, alias="maxPages")
    allowed_domains: Optional[List[str]] = Field(default=None, alias="allowedDomains")
    exclude_patterns: Optional[List[str]] = Field(default=None, alias="excludePatterns")
    
    model_config = {"populate_by_name": True}


class Crawl4AIExecuteJsParams(BaseModel):
    """Parameters for executing JavaScript on a page."""

    url: str
    js_code: str = Field(alias="jsCode")
    session_id: Optional[str] = Field(default=None, alias="sessionId")
    wait_for: str = Field(default="", alias="waitFor")
    
    model_config = {"populate_by_name": True}


class Crawl4AIAskParams(BaseModel):
    """Parameters for asking questions about crawled content."""

    urls: List[str]
    question: str
    markdown: bool = Field(default=True)
    session_id: Optional[str] = Field(default=None, alias="sessionId")
    
    model_config = {"populate_by_name": True}


class Crawl4AIMCPRequest(BaseModel):
    """MCP request structure for Crawl4AI."""

    jsonrpc: str = "2.0"
    method: str = "tools/call"
    id: str = Field(default_factory=lambda: f"crawl4ai-{datetime.now().timestamp()}")
    params: Dict[str, Any]


class Crawl4AIMCPClient:
    """Client for interacting with the Crawl4AI MCP server."""

    _instance: Optional["Crawl4AIMCPClient"] = None

    def __new__(cls) -> "Crawl4AIMCPClient":
        """Implement singleton pattern for the client."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the Crawl4AI MCP client."""
        if hasattr(self, "_initialized"):
            return

        # Get configuration from settings
        settings = get_mcp_settings()
        config = settings.crawl4ai
        if not config:
            raise ValueError("Crawl4AI MCP configuration not found")

        self._config: Crawl4AIMCPConfig = config
        self._cache: WebOperationsCache = web_cache
        
        # Parse the URL to determine protocol
        url_str = str(self._config.url)
        if url_str.startswith("ws://") or url_str.startswith("wss://"):
            self._use_websocket = True
            self._ws_url = url_str
        else:
            self._use_websocket = False
            # Default to SSE endpoint
            base_url = url_str.rstrip("/")
            self._sse_url = f"{base_url}/mcp/sse"
            
            # Initialize HTTP client for SSE
            self._client = httpx.AsyncClient(
                base_url=base_url,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "text/event-stream",
                    "Cache-Control": "no-cache",
                },
                timeout=self._config.timeout,
            )

        self._initialized = True
        connection_type = "WebSocket" if self._use_websocket else "SSE"
        logger.info(
            f"Initialized Crawl4AIMCPClient with {connection_type} connection to "
            f"{self._config.url}"
        )

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def close(self):
        """Close the connection to the server."""
        if hasattr(self, "_client") and not self._use_websocket:
            await self._client.aclose()

    def _build_mcp_request(
        self, tool_name: str, arguments: Dict[str, Any]
    ) -> Crawl4AIMCPRequest:
        """Build an MCP request for the given tool and arguments."""
        return Crawl4AIMCPRequest(params={"name": tool_name, "arguments": arguments})

    async def _send_request_ws(
        self, tool_name: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send a request via WebSocket."""
        request = self._build_mcp_request(tool_name, arguments)
        
        try:
            async with websockets.connect(self._ws_url) as websocket:
                # Send the request
                await websocket.send(json.dumps(request.model_dump()))
                
                # Receive the response
                response_data = await websocket.recv()
                response = json.loads(response_data)
                
                # Extract the result
                if "result" in response:
                    return response["result"]
                else:
                    return response
                    
        except Exception as e:
            logger.error(f"WebSocket error calling {tool_name}: {e}")
            raise

    async def _send_request_sse(
        self, tool_name: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send a request via Server-Sent Events."""
        request = self._build_mcp_request(tool_name, arguments)
        
        try:
            # Send the request as a POST with event-stream response
            response = await self._client.post(
                self._sse_url,
                json=request.model_dump(),
                headers={"Accept": "text/event-stream"},
            )
            response.raise_for_status()
            
            # Parse SSE response
            result_data = None
            for line in response.text.split('\n'):
                if line.startswith('data: '):
                    data_str = line[6:]  # Remove 'data: ' prefix
                    if data_str.strip():
                        data = json.loads(data_str)
                        if "result" in data:
                            result_data = data["result"]
                        else:
                            result_data = data
                        break
            
            if result_data is None:
                raise ValueError("No result data received from SSE stream")
                
            return result_data
            
        except httpx.HTTPError as e:
            logger.error(f"HTTP error calling {tool_name}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error calling {tool_name}: {e}")
            raise

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
                return cached_result

        try:
            # Send the request using the appropriate transport
            if self._use_websocket:
                result = await self._send_request_ws(tool_name, arguments)
            else:
                result = await self._send_request_sse(tool_name, arguments)

            # Cache the result if cache key is provided
            if cache_key:
                await self._cache.set(
                    cache_key,
                    result,
                    content_type=content_type,
                    ttl=ttl_minutes * 60 if ttl_minutes else None,
                )
                logger.info(f"Cached result for key: {cache_key}")

            return result

        except Exception as e:
            logger.error(f"Error calling {tool_name}: {e}")
            raise

    @with_error_handling
    async def crawl_url(
        self,
        url: str,
        params: Optional[Crawl4AICrawlParams] = None,
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        """
        Crawl a URL and extract content in various formats.

        Args:
            url: The URL to crawl
            params: Optional crawling parameters
            use_cache: Whether to use caching

        Returns:
            The crawled content in requested formats
        """
        if params is None:
            params = Crawl4AICrawlParams(url=url)
        else:
            params.url = url

        # Prepare cache key
        cache_key = None
        if use_cache:
            cache_key = f"crawl4ai:crawl:{url}"

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

        logger.info(f"Crawling URL: {url} with Crawl4AI MCP")

        # Convert Pydantic model to dict and use alias mapping
        arguments = params.model_dump(by_alias=True, exclude_none=True)

        return await self._send_request(
            tool_name="crawl",
            arguments=arguments,
            cache_key=cache_key,
            content_type=ContentType.MARKDOWN,
            ttl_minutes=ttl_minutes,
        )

    @with_error_handling
    async def extract_markdown(
        self,
        url: str,
        session_id: Optional[str] = None,
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        """
        Extract markdown content from a URL.

        Args:
            url: The URL to extract markdown from
            session_id: Optional session ID for stateful crawling
            use_cache: Whether to use caching

        Returns:
            The extracted markdown content
        """
        params = Crawl4AICrawlParams(
            url=url,
            markdown=True,
            html=False,
            session_id=session_id,
        )

        # Prepare cache key
        cache_key = None
        if use_cache:
            cache_key = f"crawl4ai:md:{url}"

        logger.info(f"Extracting markdown from URL: {url} with Crawl4AI MCP")

        arguments = params.model_dump(by_alias=True, exclude_none=True)

        return await self._send_request(
            tool_name="md",
            arguments=arguments,
            cache_key=cache_key,
            content_type=ContentType.MARKDOWN,
            ttl_minutes=1440,  # 24 hours for markdown content
        )

    @with_error_handling
    async def extract_html(
        self,
        url: str,
        session_id: Optional[str] = None,
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        """
        Extract HTML content from a URL.

        Args:
            url: The URL to extract HTML from
            session_id: Optional session ID for stateful crawling
            use_cache: Whether to use caching

        Returns:
            The extracted HTML content
        """
        params = Crawl4AICrawlParams(
            url=url,
            markdown=False,
            html=True,
            session_id=session_id,
        )

        # Prepare cache key
        cache_key = None
        if use_cache:
            cache_key = f"crawl4ai:html:{url}"

        logger.info(f"Extracting HTML from URL: {url} with Crawl4AI MCP")

        arguments = params.model_dump(by_alias=True, exclude_none=True)

        return await self._send_request(
            tool_name="html",
            arguments=arguments,
            cache_key=cache_key,
            content_type=ContentType.HTML,
            ttl_minutes=1440,  # 24 hours for HTML content
        )

    @with_error_handling
    async def screenshot(
        self,
        url: str,
        session_id: Optional[str] = None,
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        """
        Take a screenshot of a URL.

        Args:
            url: The URL to screenshot
            session_id: Optional session ID for stateful crawling
            use_cache: Whether to use caching

        Returns:
            The screenshot data (base64 encoded image)
        """
        # Prepare cache key
        cache_key = None
        if use_cache:
            cache_key = f"crawl4ai:screenshot:{url}"

        logger.info(f"Taking screenshot of URL: {url} with Crawl4AI MCP")

        arguments = {
            "url": url,
            "sessionId": session_id,
        }

        return await self._send_request(
            tool_name="screenshot",
            arguments=arguments,
            cache_key=cache_key,
            content_type=ContentType.BINARY,
            ttl_minutes=720,  # 12 hours for screenshots
        )

    @with_error_handling
    async def pdf(
        self,
        url: str,
        session_id: Optional[str] = None,
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        """
        Generate a PDF of a URL.

        Args:
            url: The URL to convert to PDF
            session_id: Optional session ID for stateful crawling
            use_cache: Whether to use caching

        Returns:
            The PDF data (base64 encoded)
        """
        # Prepare cache key
        cache_key = None
        if use_cache:
            cache_key = f"crawl4ai:pdf:{url}"

        logger.info(f"Generating PDF of URL: {url} with Crawl4AI MCP")

        arguments = {
            "url": url,
            "sessionId": session_id,
        }

        return await self._send_request(
            tool_name="pdf",
            arguments=arguments,
            cache_key=cache_key,
            content_type=ContentType.BINARY,
            ttl_minutes=1440,  # 24 hours for PDFs
        )

    @with_error_handling
    async def execute_js(
        self,
        url: str,
        js_code: str,
        params: Optional[Crawl4AIExecuteJsParams] = None,
        use_cache: bool = False,  # Default to False for dynamic JS execution
    ) -> Dict[str, Any]:
        """
        Execute JavaScript code on a page.

        Args:
            url: The URL to execute JavaScript on
            js_code: The JavaScript code to execute
            params: Optional execution parameters
            use_cache: Whether to use caching (default False for dynamic content)

        Returns:
            The result of the JavaScript execution
        """
        if params is None:
            params = Crawl4AIExecuteJsParams(url=url, js_code=js_code)
        else:
            params.url = url
            params.js_code = js_code

        # Prepare cache key
        cache_key = None
        if use_cache:
            # Include JS code hash in cache key
            js_hash = hash(js_code)
            cache_key = f"crawl4ai:js:{url}:{js_hash}"

        logger.info(f"Executing JavaScript on URL: {url} with Crawl4AI MCP")

        arguments = params.model_dump(by_alias=True, exclude_none=True)

        return await self._send_request(
            tool_name="execute_js",
            arguments=arguments,
            cache_key=cache_key,
            content_type=ContentType.JSON,
            ttl_minutes=5,  # 5 minutes for dynamic JS results
        )

    @with_error_handling
    async def ask(
        self,
        urls: List[str],
        question: str,
        params: Optional[Crawl4AIAskParams] = None,
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        """
        Ask a question about content from one or more URLs.

        Args:
            urls: List of URLs to analyze
            question: The question to ask about the content
            params: Optional question parameters
            use_cache: Whether to use caching

        Returns:
            The answer to the question
        """
        if params is None:
            params = Crawl4AIAskParams(urls=urls, question=question)
        else:
            params.urls = urls
            params.question = question

        # Prepare cache key
        cache_key = None
        if use_cache:
            # Create cache key based on URLs and question
            urls_key = ":".join(sorted(urls))
            cache_key = f"crawl4ai:ask:{urls_key}:{question[:50]}"

        logger.info(
            f"Asking question about {len(urls)} URLs with Crawl4AI MCP: {question[:50]}..."
        )

        arguments = params.model_dump(by_alias=True, exclude_none=True)

        return await self._send_request(
            tool_name="ask",
            arguments=arguments,
            cache_key=cache_key,
            content_type=ContentType.JSON,
            ttl_minutes=720,  # 12 hours for Q&A results
        )

    @with_error_handling
    async def batch_crawl(
        self,
        urls: List[str],
        markdown: bool = True,
        html: bool = False,
        use_cache: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Crawl multiple URLs in batch.

        Args:
            urls: List of URLs to crawl
            markdown: Whether to extract markdown
            html: Whether to extract HTML
            use_cache: Whether to use caching

        Returns:
            List of crawl results
        """
        logger.info(f"Batch crawling {len(urls)} URLs with Crawl4AI MCP")

        results = []
        for url in urls:
            try:
                params = Crawl4AICrawlParams(
                    url=url,
                    markdown=markdown,
                    html=html,
                )
                result = await self.crawl_url(url, params, use_cache)
                results.append(result)
            except Exception as e:
                logger.error(f"Error crawling {url}: {e}")
                results.append({"url": url, "error": str(e)})

        return results


# Convenience function to get a singleton instance
def get_crawl4ai_client() -> Crawl4AIMCPClient:
    """Get the singleton instance of Crawl4AIMCPClient."""
    return Crawl4AIMCPClient()