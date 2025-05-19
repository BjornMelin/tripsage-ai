"""Example of initializing MCP clients with the new configuration system.

This example shows how to properly initialize MCP clients using the centralized
MCP Configuration Management System.
"""

import logging
from typing import Optional

import httpx

from tripsage.config.mcp_settings import mcp_settings


class BaseMCPClient:
    """Base class for all MCP clients."""

    def __init__(self, mcp_name: str):
        """Initialize with a specific MCP configuration."""
        self.mcp_config = getattr(mcp_settings, mcp_name, None)
        if not self.mcp_config:
            raise ValueError(f"No configuration found for MCP: {mcp_name}")

        if not self.mcp_config.enabled:
            logging.warning(f"MCP '{mcp_name}' is disabled in configuration")

        self.logger = logging.getLogger(f"tripsage.mcp.{mcp_name}")
        self.logger.setLevel(self.mcp_config.log_level)


class RestMCPClient(BaseMCPClient):
    """Base client for REST API based MCPs."""

    def __init__(self, mcp_name: str):
        """Initialize REST API client with MCP configuration."""
        super().__init__(mcp_name)

        # Create HTTP client with proper configuration
        self.client = httpx.AsyncClient(
            base_url=str(self.mcp_config.url),
            timeout=self.mcp_config.timeout,
            headers=self._get_headers(),
            limits=httpx.Limits(
                max_connections=getattr(self.mcp_config, "max_connections", 10),
                max_keepalive_connections=getattr(
                    self.mcp_config, "max_connections", 10
                )
                // 2,
            ),
        )

        self.logger.info(
            f"Initialized {mcp_name} client with URL: {self.mcp_config.url}"
        )

    def _get_headers(self) -> dict:
        """Get HTTP headers for requests."""
        headers = {"Content-Type": "application/json"}

        # Add authorization header if API key is available
        if hasattr(self.mcp_config, "api_key") and self.mcp_config.api_key:
            headers["Authorization"] = (
                f"Bearer {self.mcp_config.api_key.get_secret_value()}"
            )

        # Add custom headers from configuration
        if hasattr(self.mcp_config, "headers"):
            headers.update(self.mcp_config.headers)

        return headers

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


# Example implementation of a specific MCP client
class PlaywrightMCPClient(RestMCPClient):
    """Client for interacting with Playwright MCP server."""

    def __init__(self):
        """Initialize the Playwright MCP client."""
        super().__init__("playwright")

        # Initialize browser-specific configuration
        self.browser_type = self.mcp_config.browser_type
        self.headless = self.mcp_config.headless
        self.screenshot_dir = getattr(self.mcp_config, "screenshot_dir", None)

        self.logger.info(
            f"Configured Playwright with browser: {self.browser_type}, "
            f"headless: {self.headless}"
        )

    async def navigate(self, url: str, wait_until: Optional[str] = None) -> dict:
        """Navigate to a URL using the Playwright MCP."""
        payload = {"url": url}

        if wait_until:
            payload["waitUntil"] = wait_until

        if self.headless:
            payload["headless"] = True

        response = await self.client.post("/navigate", json=payload)
        response.raise_for_status()

        return response.json()


# Example implementation of another MCP client
class Crawl4AIMCPClient(RestMCPClient):
    """Client for interacting with Crawl4AI MCP server."""

    def __init__(self):
        """Initialize the Crawl4AI MCP client."""
        super().__init__("crawl4ai")

        # Initialize web crawling specific configuration
        self.max_pages = self.mcp_config.max_pages
        self.rag_enabled = self.mcp_config.rag_enabled
        self.extract_images = self.mcp_config.extract_images
        self.allowed_domains = self.mcp_config.allowed_domains
        self.blocked_domains = self.mcp_config.blocked_domains

        self.logger.info(
            f"Configured Crawl4AI with max_pages: {self.max_pages}, "
            f"RAG enabled: {self.rag_enabled}"
        )

    async def crawl(self, url: str) -> dict:
        """Crawl a URL using the Crawl4AI MCP."""
        payload = {
            "url": url,
            "max_pages": self.max_pages,
            "rag_enabled": self.rag_enabled,
            "extract_images": self.extract_images,
        }

        if self.allowed_domains:
            payload["allowed_domains"] = self.allowed_domains

        if self.blocked_domains:
            payload["blocked_domains"] = self.blocked_domains

        response = await self.client.post("/crawl", json=payload)
        response.raise_for_status()

        return response.json()


# Example usage
async def main():
    """Example of using the MCP clients."""
    # Initialize clients
    playwright_client = PlaywrightMCPClient()
    crawl4ai_client = Crawl4AIMCPClient()

    try:
        # Use the clients
        result = await playwright_client.navigate("https://example.com")
        print(f"Playwright navigation result: {result}")

        result = await crawl4ai_client.crawl("https://example.com")
        print(f"Crawl4AI crawl result: {result}")

    finally:
        # Properly close the clients
        await playwright_client.close()
        await crawl4ai_client.close()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
