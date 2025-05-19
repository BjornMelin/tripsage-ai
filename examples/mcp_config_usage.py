"""Example usage of the MCP Configuration Management System.

This example demonstrates how to import and use the MCP settings in TripSage.
"""

from typing import Any, Dict

# Import the MCP settings singleton
from tripsage.config.mcp_settings import mcp_settings


def configure_playwright_client() -> Dict[str, Any]:
    """Example of configuring a Playwright MCP client using the settings."""

    # Get the Playwright MCP configuration
    playwright_config = mcp_settings.playwright

    # Use configuration values to initialize a client
    client_config = {
        "url": str(playwright_config.url),
        "timeout": playwright_config.timeout,
        "headers": {
            "Authorization": f"Bearer {playwright_config.api_key.get_secret_value()}"
            if playwright_config.api_key
            else ""
        },
        "browser_type": playwright_config.browser_type,
        "headless": playwright_config.headless,
    }

    # Additional configuration based on other settings
    if playwright_config.screenshot_dir:
        client_config["screenshot_dir"] = playwright_config.screenshot_dir

    return client_config


def configure_crawl4ai_client() -> Dict[str, Any]:
    """Example of configuring a Crawl4AI MCP client using the settings."""

    # Get the Crawl4AI MCP configuration
    crawl4ai_config = mcp_settings.crawl4ai

    # Use configuration values to initialize a client
    client_config = {
        "url": str(crawl4ai_config.url),
        "timeout": crawl4ai_config.timeout,
        "headers": {
            "Authorization": f"Bearer {crawl4ai_config.api_key.get_secret_value()}"
            if crawl4ai_config.api_key
            else ""
        },
        "max_pages": crawl4ai_config.max_pages,
        "rag_enabled": crawl4ai_config.rag_enabled,
        "cache_ttl": crawl4ai_config.cache_ttl,
        "allowed_domains": crawl4ai_config.allowed_domains,
        "blocked_domains": crawl4ai_config.blocked_domains,
    }

    return client_config


def get_all_enabled_mcps() -> Dict[str, Any]:
    """Get a dictionary of all enabled MCP configurations."""
    return mcp_settings.get_enabled_mcps()


def main():
    """Main example function."""
    # Display the current MCP settings configuration
    print("=== MCP Settings Configuration ===")

    # Get Playwright MCP configuration
    playwright_config = configure_playwright_client()
    print("\nPlaywright MCP Configuration:")
    for key, value in playwright_config.items():
        # Mask sensitive information in the example output
        if key == "headers" and "Authorization" in value:
            masked_headers = value.copy()
            if masked_headers["Authorization"]:
                masked_headers["Authorization"] = "Bearer ********"
            print(f"  {key}: {masked_headers}")
        else:
            print(f"  {key}: {value}")

    # Get Crawl4AI MCP configuration
    crawl4ai_config = configure_crawl4ai_client()
    print("\nCrawl4AI MCP Configuration:")
    for key, value in crawl4ai_config.items():
        # Mask sensitive information in the example output
        if key == "headers" and "Authorization" in value:
            masked_headers = value.copy()
            if masked_headers["Authorization"]:
                masked_headers["Authorization"] = "Bearer ********"
            print(f"  {key}: {masked_headers}")
        else:
            print(f"  {key}: {value}")

    # Show all enabled MCPs
    enabled_mcps = get_all_enabled_mcps()
    print(f"\nEnabled MCPs: {', '.join(enabled_mcps.keys())}")


if __name__ == "__main__":
    main()
