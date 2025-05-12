"""Configuration settings for the WebCrawl MCP server."""

from ...utils.settings import settings


class Config:
    """Configuration settings for the WebCrawl MCP server."""

    # API Keys and endpoints
    CRAWL4AI_API_URL = settings.webcrawl_mcp.crawl4ai_api_url
    CRAWL4AI_API_KEY = settings.webcrawl_mcp.crawl4ai_api_key.get_secret_value()

    # Firecrawl configuration
    FIRECRAWL_API_URL = settings.webcrawl_mcp.firecrawl_api_url
    FIRECRAWL_API_KEY = settings.webcrawl_mcp.firecrawl_api_key.get_secret_value()

    # Redis cache configuration
    REDIS_URL = settings.webcrawl_mcp.redis_url or "redis://localhost:6379/0"

    # Playwright configuration
    PLAYWRIGHT_MCP_ENDPOINT = settings.webcrawl_mcp.playwright_mcp_endpoint or ""
    PLAYWRIGHT_CONFIG = {
        "browser": "chromium",
        "headless": True,
        "slow_mo": 50,  # Slow down operations by 50ms to avoid detection
        "viewport": {"width": 1280, "height": 720},
    }

    # Caching configuration
    CACHE_TTL_DEFAULT = 24 * 60 * 60  # 24 hours
    CACHE_TTL_NEWS = 60 * 60  # 1 hour for news sites
    CACHE_TTL_DESTINATION_INFO = 7 * 24 * 60 * 60  # 1 week
    CACHE_TTL_EVENTS = 24 * 60 * 60  # 1 day
    CACHE_TTL_BLOG = 7 * 24 * 60 * 60  # 1 week

    # Rate limiting
    RATE_LIMIT_DEFAULT = 1  # 1 request per domain per second
    RATE_LIMIT_WINDOW = 5  # 5 second window

    # Request timeouts
    REQUEST_TIMEOUT = 30  # 30 seconds

    # Server settings
    SERVER_HOST = (
        settings.webcrawl_mcp.endpoint.split("://")[1].split(":")[0]
        if "://" in settings.webcrawl_mcp.endpoint
        else "0.0.0.0"
    )
    SERVER_PORT = (
        int(settings.webcrawl_mcp.endpoint.split(":")[-1])
        if ":" in settings.webcrawl_mcp.endpoint
        else 3001
    )

    # Known dynamic sites that require browser rendering
    DYNAMIC_SITES = [
        "tripadvisor.com",
        "airbnb.com",
        "booking.com",
        "expedia.com",
        "hotels.com",
        "kayak.com",
        "orbitz.com",
        "hotwire.com",
    ]

    # Sites that require authentication
    AUTH_SITES = [
        "booking.com/reservations",
        "airbnb.com/reservations",
        "expedia.com/trips",
        "hotels.com/account",
    ]

    # Interactive sites that require browser interaction
    INTERACTIVE_SITES = [
        "booking.com/hotel",
        "airbnb.com/rooms",
        "hotels.com/ho",
        "expedia.com/hotel",
        "tripadvisor.com/Hotel_Review",
        "agoda.com/hotel",
    ]

    # Dynamic event cities that typically need browser automation
    DYNAMIC_EVENT_CITIES = [
        "New York",
        "Las Vegas",
        "London",
        "Tokyo",
        "Paris",
        "Singapore",
        "Dubai",
        "San Francisco",
        "Berlin",
    ]

    # News and frequently updated sites
    FREQUENT_UPDATE_DOMAINS = [
        "cnn.com",
        "bbc.com",
        "nytimes.com",
        "theguardian.com",
        "weather.com",
        "accuweather.com",
    ]
