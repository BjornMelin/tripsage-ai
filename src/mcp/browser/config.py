"""Configuration settings for the Browser MCP server."""

from typing import List

from ...utils.settings import settings


class Config:
    """Configuration settings for the Browser MCP server."""

    # Server configuration
    SERVER_HOST = (
        settings.browser_mcp.endpoint.split("://")[1].split(":")[0]
        if "://" in settings.browser_mcp.endpoint
        else "0.0.0.0"
    )
    SERVER_PORT = (
        int(settings.browser_mcp.endpoint.split(":")[-1])
        if ":" in settings.browser_mcp.endpoint
        else 3002
    )

    # Playwright configuration
    PLAYWRIGHT_HEADLESS = settings.browser_mcp.headless
    PLAYWRIGHT_SLOW_MO = settings.browser_mcp.slow_mo  # Milliseconds between actions
    VIEWPORT_WIDTH = settings.browser_mcp.viewport_width
    VIEWPORT_HEIGHT = settings.browser_mcp.viewport_height
    IGNORE_HTTPS_ERRORS = settings.browser_mcp.ignore_https_errors

    # Request timeouts
    DEFAULT_TIMEOUT = settings.browser_mcp.default_timeout  # 30 seconds
    NAVIGATION_TIMEOUT = settings.browser_mcp.navigation_timeout  # 60 seconds

    # Context management
    CONTEXT_MAX_IDLE_TIME = settings.browser_mcp.context_max_idle_time  # 5 minutes
    CONTEXT_CLEANUP_INTERVAL = settings.browser_mcp.context_cleanup_interval  # 1 minute
    MAX_CONTEXTS = settings.browser_mcp.max_contexts

    # Geolocation (optional)
    GEOLOCATION_ENABLED = settings.browser_mcp.geolocation_enabled
    GEOLOCATION_LATITUDE = 40.7128  # New York
    GEOLOCATION_LONGITUDE = -74.0060
    GEOLOCATION_ACCURACY = 100.0

    # HTTP authentication (optional)
    HTTP_CREDENTIALS_ENABLED = False
    HTTP_CREDENTIALS = ""  # base64 encoded username:password

    # Browser permissions
    BROWSER_PERMISSIONS: List[str] = []  # e.g., ['geolocation', 'camera']

    # User agent pool for rotation
    USER_AGENT_POOL = [
        # Chrome on Windows
        (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/98.0.4758.102 Safari/537.36"
        ),
        (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/99.0.4844.51 Safari/537.36"
        ),
        # Chrome on macOS
        (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/98.0.4758.102 Safari/537.36"
        ),
        (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.51 Safari/537.36"
        ),
        # Firefox on Windows
        (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:97.0) "
            "Gecko/20100101 Firefox/97.0"
        ),
        (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:98.0) "
            "Gecko/20100101 Firefox/98.0"
        ),
        # Firefox on macOS
        (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:97.0) "
            "Gecko/20100101 Firefox/97.0"
        ),
        (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:98.0) "
            "Gecko/20100101 Firefox/98.0"
        ),
        # Safari on macOS
        (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.3 Safari/605.1.15"
        ),
        (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.4 Safari/605.1.15"
        ),
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
