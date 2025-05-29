"""Rate limiting middleware for FastAPI.

This module provides middleware for rate limiting in FastAPI,
supporting both in-memory and DragonflyDB-based rate limiters.
"""

import logging
import time
from datetime import datetime
from typing import Callable, Dict, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.status import HTTP_429_TOO_MANY_REQUESTS
from starlette.types import ASGIApp

from tripsage.api.core.config import Settings, get_settings

logger = logging.getLogger(__name__)


class InMemoryRateLimiter:
    """Simple in-memory rate limiter.

    This class provides a simple in-memory rate limiter for development
    and testing purposes. It should not be used in production.
    """

    def __init__(self, rate_limit: int, timeframe: int):
        """Initialize the rate limiter.

        Args:
            rate_limit: Maximum number of requests allowed in the timeframe
            timeframe: Timeframe in seconds
        """
        self.rate_limit = rate_limit
        self.timeframe = timeframe
        self.requests: Dict[str, list] = {}

    def is_rate_limited(self, key: str) -> bool:
        """Check if a key is rate limited.

        Args:
            key: The key to check (usually user ID or IP address)

        Returns:
            True if the key is rate limited, False otherwise
        """
        current_time = time.time()

        # Remove expired requests
        if key in self.requests:
            self.requests[key] = [
                req_time
                for req_time in self.requests[key]
                if current_time - req_time < self.timeframe
            ]
        else:
            self.requests[key] = []

        # Check if the key is rate limited
        if len(self.requests[key]) >= self.rate_limit:
            return True

        # Add the current request
        self.requests[key].append(current_time)
        return False


class DragonflyRateLimiter:
    """DragonflyDB-based rate limiter.

    This class provides a DragonflyDB-based rate limiter for production use.
    It uses the direct DragonflyDB service for optimal performance.
    """

    def __init__(self, rate_limit: int, timeframe: int):
        """Initialize the rate limiter.

        Args:
            rate_limit: Maximum number of requests allowed in the timeframe
            timeframe: Timeframe in seconds
        """
        self.rate_limit = rate_limit
        self.timeframe = timeframe
        self.cache_service = None

    async def initialize(self):
        """Initialize the direct DragonflyDB service."""
        if not self.cache_service:
            from tripsage.services.dragonfly_service import get_cache_service

            self.cache_service = await get_cache_service()

    async def is_rate_limited(self, key: str) -> bool:
        """Check if a key is rate limited.

        Args:
            key: The key to check (usually user ID or IP address)

        Returns:
            True if the key is rate limited, False otherwise
        """
        await self.initialize()

        # Create a cache key
        cache_key = f"rate_limit:{key}"

        # Use direct DragonflyDB service to check and update rate limit
        current_time = int(time.time())
        window_start = current_time - self.timeframe

        try:
            # Check if DragonflyDB service supports sorted sets (Redis commands)
            if hasattr(self.cache_service, "zremrangebyscore"):
                # Use Redis-like sorted set commands for precise rate limiting
                # Remove expired entries
                await self.cache_service.zremrangebyscore(cache_key, 0, window_start)
                # Count current requests in window
                current_count = await self.cache_service.zcard(cache_key)
                # Add current request
                await self.cache_service.zadd(
                    cache_key, {str(current_time): current_time}
                )
                # Set expiration
                await self.cache_service.expire(cache_key, self.timeframe)

                return current_count >= self.rate_limit
            else:
                # Fallback to simple counting approach
                return await self._simple_rate_limit(cache_key, current_time)

        except Exception as e:
            logger.warning(
                f"DragonflyDB rate limiting failed, falling back to simple method: {e}"
            )
            return await self._simple_rate_limit(cache_key, current_time)

    async def _simple_rate_limit(self, cache_key: str, current_time: int) -> bool:
        """Simple rate limiting using basic cache operations."""
        # Get current count
        count_key = f"{cache_key}:count"
        window_key = f"{cache_key}:window"

        # Check if we're in a new window
        last_window = await self.cache_service.get(window_key)
        current_window = current_time // self.timeframe

        if last_window is None or int(last_window) != current_window:
            # New window, reset count
            await self.cache_service.set(count_key, "1", ex=self.timeframe)
            await self.cache_service.set(
                window_key, str(current_window), ex=self.timeframe
            )
            return False

        # Increment count in current window
        try:
            if hasattr(self.cache_service, "incr"):
                current_count = await self.cache_service.incr(count_key)
            else:
                # Manual increment
                current_count_str = await self.cache_service.get(count_key) or "0"
                current_count = int(current_count_str) + 1
                await self.cache_service.set(
                    count_key, str(current_count), ex=self.timeframe
                )

            return current_count > self.rate_limit

        except Exception:
            # If increment fails, allow the request
            logger.warning("Rate limit increment failed, allowing request")
            return False


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware for rate limiting.

    This middleware limits the rate of requests based on user ID or IP address.
    """

    def __init__(
        self,
        app: ASGIApp,
        settings: Optional[Settings] = None,
        use_dragonfly: bool = False,
    ):
        """Initialize RateLimitMiddleware.

        Args:
            app: The ASGI application
            settings: API settings or None to use the default
            use_dragonfly: Whether to use DragonflyDB for rate limiting
        """
        super().__init__(app)
        self.settings = settings or get_settings()

        # Create rate limiter
        if use_dragonfly:
            self.rate_limiter = DragonflyRateLimiter(
                rate_limit=self.settings.rate_limit_requests,
                timeframe=self.settings.rate_limit_timeframe,
            )
        else:
            self.rate_limiter = InMemoryRateLimiter(
                rate_limit=self.settings.rate_limit_requests,
                timeframe=self.settings.rate_limit_timeframe,
            )

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Response]
    ) -> Response:
        """Process the request/response and handle rate limiting.

        Args:
            request: The incoming request
            call_next: The next middleware or endpoint handler

        Returns:
            The response from the next middleware or endpoint
        """
        # Skip rate limiting for certain paths
        if self._should_skip_rate_limit(request.url.path):
            return await call_next(request)

        # Get a key for rate limiting (user ID or IP address)
        key = self._get_rate_limit_key(request)

        # Check if the key is rate limited
        is_limited = (
            await self.rate_limiter.is_rate_limited(key)
            if isinstance(self.rate_limiter, DragonflyRateLimiter)
            else self.rate_limiter.is_rate_limited(key)
        )

        if is_limited:
            # If rate limited, return 429 Too Many Requests
            logger.warning(
                f"Rate limit exceeded for {key}",
                extra={"key": key, "path": request.url.path},
            )

            retry_after = self.settings.rate_limit_timeframe

            return Response(
                content=(f"Rate limit exceeded. Try again in {retry_after} seconds."),
                status_code=HTTP_429_TOO_MANY_REQUESTS,
                headers={"Retry-After": str(retry_after)},
            )

        # Continue with the request
        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(self.settings.rate_limit_requests)
        response.headers["X-RateLimit-Remaining"] = str(
            self.settings.rate_limit_requests - 1
        )  # Simplified, should be actual count
        response.headers["X-RateLimit-Reset"] = str(
            int(datetime.now(datetime.UTC).timestamp())
            + self.settings.rate_limit_timeframe
        )

        return response

    def _should_skip_rate_limit(self, path: str) -> bool:
        """Check if rate limiting should be skipped for a path.

        Args:
            path: The request path

        Returns:
            True if rate limiting should be skipped, False otherwise
        """
        # Skip rate limiting for docs and health check
        skip_paths = [
            "/api/docs",
            "/api/redoc",
            "/api/openapi.json",
            "/api/health",
        ]

        for skip_path in skip_paths:
            if path.startswith(skip_path):
                return True

        return False

    def _get_rate_limit_key(self, request: Request) -> str:
        """Get a key for rate limiting.

        Args:
            request: The incoming request

        Returns:
            A key for rate limiting (user ID or IP address)
        """
        # Use user ID if available
        user_id = getattr(request.state, "user_id", None)
        if user_id:
            return f"user:{user_id}"

        # Fall back to IP address
        client_host = request.client.host if request.client else "unknown"
        return f"ip:{client_host}"
