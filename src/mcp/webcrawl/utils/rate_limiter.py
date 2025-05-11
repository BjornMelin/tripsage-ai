"""Rate limiting utilities for WebCrawl MCP."""

import asyncio
import time
from collections import defaultdict
from typing import Dict, Optional

from src.mcp.webcrawl.config import Config
from src.utils.logging import get_logger

# Initialize logger
logger = get_logger(__name__)


class RateLimiter:
    """Rate limiter for web requests.

    This class implements a domain-based rate limiting strategy to ensure
    that requests to the same domain are not sent too frequently.
    """

    def __init__(
        self,
        requests_per_second: float = Config.RATE_LIMIT_DEFAULT,
        window_size: int = Config.RATE_LIMIT_WINDOW,
    ):
        """Initialize the rate limiter.

        Args:
            requests_per_second: Maximum requests per second per domain
            window_size: Window size in seconds for rate limiting
        """
        self.requests_per_second = requests_per_second
        self.window_size = window_size

        # Maps domain -> list of request timestamps
        self._domain_timestamps: Dict[str, list] = defaultdict(list)

        # Maps domain -> minimum wait time
        self._domain_min_wait: Dict[str, float] = {}

        # Lock for thread safety
        self._lock = asyncio.Lock()

    async def acquire(self, domain: str) -> None:
        """Acquire permission to make a request to a domain.

        This method will block until it's safe to make a request to the
        specified domain according to the rate limiting rules.

        Args:
            domain: The domain to make a request to
        """
        async with self._lock:
            # Calculate wait time
            wait_time = await self._calculate_wait_time(domain)

            if wait_time > 0:
                logger.debug(f"Rate limiting: waiting {wait_time:.2f}s for {domain}")
                # Release lock while waiting
                await asyncio.sleep(wait_time)

            # Record request timestamp
            now = time.time()
            self._domain_timestamps[domain].append(now)

            # Clean up old timestamps
            self._clean_timestamps(domain, now)

    async def _calculate_wait_time(self, domain: str) -> float:
        """Calculate how long to wait before making a request.

        Args:
            domain: The domain to calculate wait time for

        Returns:
            Wait time in seconds
        """
        now = time.time()

        # Clean up old timestamps
        self._clean_timestamps(domain, now)

        # Check if we already have the maximum allowed requests in the window
        timestamps = self._domain_timestamps[domain]

        if len(timestamps) < self.window_size * self.requests_per_second:
            # We haven't reached the limit yet
            return 0

        # Calculate time since oldest request
        oldest = timestamps[0]
        time_since_oldest = now - oldest

        # Calculate time until we can make a new request
        if time_since_oldest < self.window_size:
            # We need to wait until the oldest request leaves the window
            return self.window_size - time_since_oldest

        return 0

    def _clean_timestamps(self, domain: str, now: float) -> None:
        """Clean up old timestamps for a domain.

        Args:
            domain: The domain to clean timestamps for
            now: Current timestamp
        """
        # Keep only timestamps within the window
        cutoff = now - self.window_size
        self._domain_timestamps[domain] = [
            ts for ts in self._domain_timestamps[domain] if ts > cutoff
        ]

    def update_domain_rate(self, domain: str, rate: float) -> None:
        """Update the rate limit for a specific domain.

        Args:
            domain: The domain to update rate for
            rate: New rate limit in requests per second
        """
        if rate <= 0:
            raise ValueError("Rate must be positive")

        # Store domain-specific minimum wait time (seconds between requests)
        self._domain_min_wait[domain] = 1.0 / rate

    def get_domain_rate(self, domain: str) -> float:
        """Get the rate limit for a specific domain.

        Args:
            domain: The domain to get rate for

        Returns:
            Rate limit in requests per second
        """
        if domain in self._domain_min_wait:
            return 1.0 / self._domain_min_wait[domain]

        return self.requests_per_second


class AdaptiveRateLimiter(RateLimiter):
    """Adaptive rate limiter that adjusts based on server responses.

    This class extends the basic rate limiter with the ability to
    dynamically adjust rate limits based on server responses.
    """

    def __init__(
        self,
        requests_per_second: float = Config.RATE_LIMIT_DEFAULT,
        window_size: int = Config.RATE_LIMIT_WINDOW,
        backoff_factor: float = 2.0,
        recovery_factor: float = 1.5,
        min_rate: float = 0.1,  # One request per 10 seconds
        max_rate: float = 10.0,  # 10 requests per second
    ):
        """Initialize the adaptive rate limiter.

        Args:
            requests_per_second: Initial maximum requests per second per domain
            window_size: Window size in seconds for rate limiting
            backoff_factor: Factor to reduce rate by when encountering errors
            recovery_factor: Factor to increase rate by when successful
            min_rate: Minimum allowed rate in requests per second
            max_rate: Maximum allowed rate in requests per second
        """
        super().__init__(requests_per_second, window_size)
        self.backoff_factor = backoff_factor
        self.recovery_factor = recovery_factor
        self.min_rate = min_rate
        self.max_rate = max_rate

        # Maps domain -> current rate
        self._domain_rates: Dict[str, float] = {}

        # Maps domain -> success/failure counts
        self._domain_success: Dict[str, int] = defaultdict(int)
        self._domain_failure: Dict[str, int] = defaultdict(int)

    def report_success(self, domain: str) -> None:
        """Report a successful request to a domain.

        Args:
            domain: The domain that the request was made to
        """
        self._domain_success[domain] += 1

        # Maybe increase rate after 5 consecutive successes
        if self._domain_success[domain] >= 5:
            self._increase_rate(domain)
            self._domain_success[domain] = 0

    def report_failure(self, domain: str, status_code: Optional[int] = None) -> None:
        """Report a failed request to a domain.

        Args:
            domain: The domain that the request was made to
            status_code: Optional HTTP status code from the failure
        """
        # Reset success counter
        self._domain_success[domain] = 0

        # Increment failure counter
        self._domain_failure[domain] += 1

        # Immediate backoff on certain status codes
        if status_code in [429, 503]:  # Too Many Requests, Service Unavailable
            self._decrease_rate(domain, immediate=True)
        elif self._domain_failure[domain] >= 3:
            # Decrease rate after 3 consecutive failures
            self._decrease_rate(domain)
            self._domain_failure[domain] = 0

    def _increase_rate(self, domain: str) -> None:
        """Increase the rate limit for a domain.

        Args:
            domain: The domain to increase rate for
        """
        current_rate = self.get_domain_rate(domain)
        new_rate = min(current_rate * self.recovery_factor, self.max_rate)

        if new_rate > current_rate:
            logger.info(
                f"Increasing rate for {domain} from {current_rate:.2f} to {new_rate:.2f} req/s"
            )
            self._domain_rates[domain] = new_rate
            self.update_domain_rate(domain, new_rate)

    def _decrease_rate(self, domain: str, immediate: bool = False) -> None:
        """Decrease the rate limit for a domain.

        Args:
            domain: The domain to decrease rate for
            immediate: Whether to apply an immediate reduction
        """
        current_rate = self.get_domain_rate(domain)

        # Apply stronger backoff for immediate reductions
        factor = self.backoff_factor * 2 if immediate else self.backoff_factor

        new_rate = max(current_rate / factor, self.min_rate)

        logger.info(
            f"Decreasing rate for {domain} from {current_rate:.2f} to {new_rate:.2f} req/s"
        )
        self._domain_rates[domain] = new_rate
        self.update_domain_rate(domain, new_rate)

    def get_domain_rate(self, domain: str) -> float:
        """Get the current rate limit for a domain.

        Args:
            domain: The domain to get rate for

        Returns:
            Current rate limit in requests per second
        """
        if domain in self._domain_rates:
            return self._domain_rates[domain]

        return self.requests_per_second
