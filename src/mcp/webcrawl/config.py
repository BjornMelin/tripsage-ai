"""Configuration settings for the WebCrawl MCP server."""

import os

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Configuration settings for the WebCrawl MCP server."""

    # API Keys and endpoints
    CRAWL4AI_API_URL = os.getenv("CRAWL4AI_API_URL", "http://localhost:8000/api")
    CRAWL4AI_API_KEY = os.getenv("CRAWL4AI_API_KEY", "")

    # Playwright configuration
    PLAYWRIGHT_MCP_ENDPOINT = os.getenv("PLAYWRIGHT_MCP_ENDPOINT", "")
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
    SERVER_HOST = os.getenv("WEBCRAWL_SERVER_HOST", "0.0.0.0")
    SERVER_PORT = int(os.getenv("WEBCRAWL_SERVER_PORT", "3001"))

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
