"""Example configuration for domain-based web crawler routing.

This file demonstrates how to configure domain routing for the hybrid web crawling
strategy in TripSage. These settings would typically be set via environment variables
or a configuration file.
"""

import os

from tripsage.config.mcp_settings import get_mcp_settings
from tripsage.tools.webcrawl.source_selector import get_source_selector

# Example: Setting domain routing via environment variables
# These would typically be set in your .env file or deployment configuration

# Add custom domains optimized for Crawl4AI
os.environ["TRIPSAGE_MCP_CRAWL4AI__DOMAIN_ROUTING__CRAWL4AI_DOMAINS"] = (
    '["nomadicmatt.com", "thepointsguy.com", "ricksteves.com"]'
)

# Add custom domains optimized for Firecrawl
os.environ["TRIPSAGE_MCP_FIRECRAWL__DOMAIN_ROUTING__FIRECRAWL_DOMAINS"] = (
    '["vrbo.com", "expedia.com", "marriott.com"]'
)

# Other WebCrawl configurations
os.environ["TRIPSAGE_MCP_CRAWL4AI__CACHE_TTL"] = "7200"  # 2 hours
os.environ["TRIPSAGE_MCP_FIRECRAWL__CACHE_TTL"] = "3600"  # 1 hour

# Enable/disable specific crawlers
os.environ["TRIPSAGE_MCP_CRAWL4AI__ENABLED"] = "true"
os.environ["TRIPSAGE_MCP_FIRECRAWL__ENABLED"] = "true"

# Get the configured settings
settings = get_mcp_settings()

# Access the domain routing configuration
crawl4ai_config = settings.crawl4ai
firecrawl_config = settings.firecrawl

print("Crawl4AI additional domains:", crawl4ai_config.domain_routing.crawl4ai_domains)
print(
    "Firecrawl additional domains:", firecrawl_config.domain_routing.firecrawl_domains
)

selector = get_source_selector()

# Test domain routing
test_urls = [
    # Should use Firecrawl (default domain)
    "https://www.airbnb.com/rooms/12345",
    # Should use Crawl4AI (custom domain)
    "https://www.nomadicmatt.com/travel-guides/tokyo-travel-tips",
    # Should use Firecrawl (custom domain)
    "https://www.vrbo.com/vacation-rentals/usa/florida",
    # Should use Crawl4AI (default domain)
    "https://www.wikipedia.org/wiki/Paris",
]

for url in test_urls:
    crawler = selector.select_crawler(url)
    print(f"URL: {url} -> Selected crawler: {crawler}")

# Example .env file contents for domain routing:
"""
# Domain routing for web crawlers
TRIPSAGE_MCP_CRAWL4AI__DOMAIN_ROUTING__CRAWL4AI_DOMAINS='[
    "nomadicmatt.com",
    "thepointsguy.com",
    "ricksteves.com",
    "travelandleisure.com",
]
'
TRIPSAGE_MCP_FIRECRAWL__DOMAIN_ROUTING__FIRECRAWL_DOMAINS='[
    "vrbo.com",
    "priceline.com",
    "hotwire.com",
    "travelocity.com",
]
'

# Cache TTL settings
TRIPSAGE_MCP_CRAWL4AI__CACHE_TTL=7200
TRIPSAGE_MCP_FIRECRAWL__CACHE_TTL=3600

# Enable both crawlers
TRIPSAGE_MCP_CRAWL4AI__ENABLED=true
TRIPSAGE_MCP_FIRECRAWL__ENABLED=true
"""
