"""Configuration settings for the Browser MCP server."""

import os
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Configuration settings for the Browser MCP server."""

    # Server configuration
    SERVER_HOST = os.getenv("BROWSER_SERVER_HOST", "0.0.0.0")
    SERVER_PORT = int(os.getenv("BROWSER_SERVER_PORT", "3002"))

    # Playwright configuration
    PLAYWRIGHT_HEADLESS = os.getenv("PLAYWRIGHT_HEADLESS", "true").lower() == "true"
    PLAYWRIGHT_SLOW_MO = int(
        os.getenv("PLAYWRIGHT_SLOW_MO", "50")
    )  # Milliseconds between actions
    VIEWPORT_WIDTH = int(os.getenv("PLAYWRIGHT_VIEWPORT_WIDTH", "1280"))
    VIEWPORT_HEIGHT = int(os.getenv("PLAYWRIGHT_VIEWPORT_HEIGHT", "720"))
    IGNORE_HTTPS_ERRORS = (
        os.getenv("PLAYWRIGHT_IGNORE_HTTPS_ERRORS", "false").lower() == "true"
    )

    # Request timeouts
    DEFAULT_TIMEOUT = int(
        os.getenv("PLAYWRIGHT_DEFAULT_TIMEOUT", "30000")
    )  # 30 seconds
    NAVIGATION_TIMEOUT = int(
        os.getenv("PLAYWRIGHT_NAVIGATION_TIMEOUT", "60000")
    )  # 60 seconds

    # Context management
    CONTEXT_MAX_IDLE_TIME = int(os.getenv("CONTEXT_MAX_IDLE_TIME", "300"))  # 5 minutes
    CONTEXT_CLEANUP_INTERVAL = int(
        os.getenv("CONTEXT_CLEANUP_INTERVAL", "60")
    )  # 1 minute
    MAX_CONTEXTS = int(os.getenv("MAX_BROWSER_CONTEXTS", "10"))

    # Geolocation (optional)
    GEOLOCATION_ENABLED = os.getenv("GEOLOCATION_ENABLED", "false").lower() == "true"
    GEOLOCATION_LATITUDE = float(
        os.getenv("GEOLOCATION_LATITUDE", "40.7128")
    )  # New York
    GEOLOCATION_LONGITUDE = float(os.getenv("GEOLOCATION_LONGITUDE", "-74.0060"))
    GEOLOCATION_ACCURACY = float(os.getenv("GEOLOCATION_ACCURACY", "100.0"))

    # HTTP authentication (optional)
    HTTP_CREDENTIALS_ENABLED = (
        os.getenv("HTTP_CREDENTIALS_ENABLED", "false").lower() == "true"
    )
    HTTP_CREDENTIALS = os.getenv(
        "HTTP_CREDENTIALS", ""
    )  # base64 encoded username:password

    # Browser permissions
    BROWSER_PERMISSIONS: List[str] = []  # e.g., ['geolocation', 'camera']

    # User agent pool for rotation
    USER_AGENT_POOL = [
        # Chrome on Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.51 Safari/537.36",
        # Chrome on macOS
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.51 Safari/537.36",
        # Firefox on Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:97.0) Gecko/20100101 Firefox/97.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:98.0) Gecko/20100101 Firefox/98.0",
        # Firefox on macOS
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:97.0) Gecko/20100101 Firefox/97.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:98.0) Gecko/20100101 Firefox/98.0",
        # Safari on macOS
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.3 Safari/605.1.15",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.4 Safari/605.1.15",
    ]

    # Website specific configuration
    # URL mappings for flight status and check-in pages
    AIRLINE_STATUS_URLS = {
        "AA": "https://www.aa.com/travelInformation/flights/status",
        "DL": "https://www.delta.com/flight-status-lookup",
        "UA": "https://www.united.com/en/us/flightstatus",
        "WN": "https://www.southwest.com/air/flight-status",
        "AS": "https://www.alaskaair.com/status",
        "B6": "https://www.jetblue.com/flight-status",
        "F9": "https://www.flyfrontier.com/flight-status/",
        "NK": "https://www.spirit.com/flight-status",
        "HA": "https://www.hawaiianairlines.com/flight-status",
        "G4": "https://www.allegiantair.com/flight-status",
    }

    AIRLINE_CHECKIN_URLS = {
        "AA": "https://www.aa.com/reservation/view/find-your-reservation",
        "DL": "https://www.delta.com/checkin/search",
        "UA": "https://www.united.com/en/us/checkin",
        "WN": "https://www.southwest.com/air/check-in/index.html",
        "AS": "https://www.alaskaair.com/checkin",
        "B6": "https://www.jetblue.com/manage-trips/check-in",
        "F9": "https://www.flyfrontier.com/check-in/",
        "NK": "https://www.spirit.com/check-in",
        "HA": "https://www.hawaiianairlines.com/check-in",
        "G4": "https://www.allegiantair.com/online-check-in",
    }

    # Booking verification URL patterns
    BOOKING_VERIFICATION_URLS = {
        "flight": {
            "AA": "https://www.aa.com/reservation/view/find-your-reservation",
            "DL": "https://www.delta.com/mytrips/find",
            "UA": "https://www.united.com/en/us/manageres/mytrips",
            "WN": "https://www.southwest.com/air/manage-reservation/index.html",
        },
        "hotel": {
            "hilton": "https://www.hilton.com/en/find-reservation/",
            "marriott": "https://www.marriott.com/reservation/lookup.mi",
            "hyatt": "https://www.hyatt.com/en-US/account/manage-reservation",
            "ihg": "https://www.ihg.com/hotels/us/en/global/customer_care/check_reservation",
        },
        "car": {
            "hertz": "https://www.hertz.com/rentacar/reservation/retrieveConfirmation.do",
            "avis": "https://www.avis.com/en/reservation/view-modify-cancel",
            "enterprise": "https://www.enterprise.com/en/reserve/manage.html",
            "budget": "https://www.budget.com/en/reservation/view-modify-cancel",
        },
    }

    # Error patterns to detect across various sites
    COMMON_ERROR_PATTERNS = [
        "no reservations found",
        "could not find your reservation",
        "unable to find",
        "invalid confirmation",
        "invalid reservation",
        "no matching records",
        "reservation not found",
        "check-in is not available",
        "incorrect information",
        "please verify the information",
        "access denied",
        "authentication failed",
    ]

    # Response cache configuration
    CACHE_ENABLED = True
    CACHE_TTL_DEFAULT = 24 * 60 * 60  # 24 hours (in seconds)
    CACHE_TTL_FLIGHT_STATUS = 60 * 30  # 30 minutes
    CACHE_TTL_BOOKING_VERIFICATION = 60 * 60  # 1 hour
    CACHE_TTL_PRICE_MONITOR = 60 * 15  # 15 minutes
