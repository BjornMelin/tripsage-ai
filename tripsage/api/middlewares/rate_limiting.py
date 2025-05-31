"""Enhanced rate limiting middleware for FastAPI.

This module provides middleware for rate limiting that can apply different
limits based on the authenticated principal (user vs agent).
"""

import logging
import time
from datetime import datetime, timezone
from typing import Callable, Dict, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.status import HTTP_429_TOO_MANY_REQUESTS
from starlette.types import ASGIApp

from tripsage.api.core.config import Settings, get_settings

logger = logging.getLogger(__name__)


class RateLimitConfig:
    """Configuration for rate limiting."""

    def __init__(
        self,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
        burst_size: int = 10,
    ):
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.burst_size = burst_size


class RateLimiter:
    """Base rate limiter interface."""

    async def is_rate_limited(
        self, key: str, config: RateLimitConfig
    ) -> tuple[bool, dict]:
        """Check if a key is rate limited.

        Args:
            key: The key to check
            config: Rate limit configuration

        Returns:
            Tuple of (is_limited, metadata)
        """
        raise NotImplementedError


class InMemoryRateLimiter(RateLimiter):
    """Simple in-memory rate limiter with sliding window."""

    def __init__(self):
        self.requests: Dict[str, list] = {}

    async def is_rate_limited(
        self, key: str, config: RateLimitConfig
    ) -> tuple[bool, dict]:
        """Check if a key is rate limited using sliding window algorithm."""
        current_time = time.time()
        minute_ago = current_time - 60
        hour_ago = current_time - 3600

        # Get or create request history for key
        if key not in self.requests:
            self.requests[key] = []

        # Remove expired entries
        self.requests[key] = [
            req_time for req_time in self.requests[key] if req_time > hour_ago
        ]

        # Count requests in different windows
        minute_count = sum(1 for t in self.requests[key] if t > minute_ago)
        hour_count = len(self.requests[key])

        # Check limits
        if minute_count >= config.requests_per_minute:
            return True, {
                "limit": config.requests_per_minute,
                "window": "minute",
                "retry_after": 60 - int(current_time - minute_ago),
            }

        if hour_count >= config.requests_per_hour:
            return True, {
                "limit": config.requests_per_hour,
                "window": "hour",
                "retry_after": 3600 - int(current_time - hour_ago),
            }

        # Add current request
        self.requests[key].append(current_time)

        return False, {
            "requests_per_minute": minute_count + 1,
            "requests_per_hour": hour_count + 1,
            "remaining_per_minute": config.requests_per_minute - minute_count - 1,
            "remaining_per_hour": config.requests_per_hour - hour_count - 1,
        }


class DragonflyRateLimiter(RateLimiter):
    """DragonflyDB-based rate limiter using token bucket algorithm."""

    def __init__(self):
        self.cache_service = None

    async def _ensure_cache(self):
        """Ensure cache service is initialized."""
        if not self.cache_service:
            from tripsage_core.services.infrastructure import get_cache_service

            self.cache_service = await get_cache_service()

    async def is_rate_limited(
        self, key: str, config: RateLimitConfig
    ) -> tuple[bool, dict]:
        """Check if a key is rate limited using token bucket algorithm."""
        await self._ensure_cache()

        try:
            # Implement token bucket algorithm
            bucket_key = f"rate_limit:bucket:{key}"
            last_refill_key = f"rate_limit:refill:{key}"

            current_time = time.time()

            # Get current bucket state
            tokens_str = await self.cache_service.get(bucket_key)
            last_refill_str = await self.cache_service.get(last_refill_key)

            if tokens_str is None:
                # Initialize bucket
                tokens = float(config.burst_size)
                last_refill = current_time
            else:
                tokens = float(tokens_str)
                last_refill = float(last_refill_str or current_time)

            # Calculate tokens to add based on time passed
            time_passed = current_time - last_refill
            refill_rate = config.requests_per_minute / 60.0  # tokens per second
            tokens_to_add = time_passed * refill_rate

            # Add tokens up to burst size
            tokens = min(tokens + tokens_to_add, config.burst_size)

            # Check if we have tokens available
            if tokens < 1:
                # Calculate retry after
                tokens_needed = 1 - tokens
                retry_after = int(tokens_needed / refill_rate) + 1

                return True, {
                    "limit": config.requests_per_minute,
                    "burst_size": config.burst_size,
                    "retry_after": retry_after,
                }

            # Consume a token
            tokens -= 1

            # Save state
            await self.cache_service.set(bucket_key, str(tokens), ex=3600)
            await self.cache_service.set(last_refill_key, str(current_time), ex=3600)

            return False, {
                "tokens_remaining": int(tokens),
                "burst_size": config.burst_size,
                "refill_rate": refill_rate,
            }

        except Exception as e:
            logger.warning(f"DragonflyDB rate limiting failed: {e}, allowing request")
            return False, {}


class EnhancedRateLimitMiddleware(BaseHTTPMiddleware):
    """Enhanced rate limiting middleware with principal-based limits.

    This middleware applies different rate limits based on:
    - Unauthenticated requests (most restrictive)
    - Authenticated users (standard limits)
    - API key/agent requests (higher limits)
    - Service-specific limits for agents
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
            self.rate_limiter = DragonflyRateLimiter()
        else:
            self.rate_limiter = InMemoryRateLimiter()

        # Define rate limit configurations
        self.configs = {
            "unauthenticated": RateLimitConfig(
                requests_per_minute=20,
                requests_per_hour=100,
                burst_size=5,
            ),
            "user": RateLimitConfig(
                requests_per_minute=60,
                requests_per_hour=1000,
                burst_size=10,
            ),
            "agent": RateLimitConfig(
                requests_per_minute=300,
                requests_per_hour=10000,
                burst_size=50,
            ),
            # Service-specific limits
            "agent_openai": RateLimitConfig(
                requests_per_minute=500,
                requests_per_hour=20000,
                burst_size=100,
            ),
        }

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Response]
    ) -> Response:
        """Process the request and handle rate limiting.

        Args:
            request: The incoming request
            call_next: The next middleware or endpoint handler

        Returns:
            The response from the next middleware or endpoint
        """
        # Skip rate limiting for certain paths
        if self._should_skip_rate_limit(request.url.path):
            return await call_next(request)

        # Get rate limit key and config based on principal
        key, config = self._get_rate_limit_key_and_config(request)

        # Check if the key is rate limited
        is_limited, metadata = await self.rate_limiter.is_rate_limited(key, config)

        if is_limited:
            # Log rate limit exceeded
            logger.warning(
                "Rate limit exceeded",
                extra={
                    "key": key,
                    "path": request.url.path,
                    "principal_id": getattr(
                        getattr(request.state, "principal", None), "id", None
                    ),
                    **metadata,
                },
            )

            retry_after = metadata.get("retry_after", 60)

            return Response(
                content=f"Rate limit exceeded. Try again in {retry_after} seconds.",
                status_code=HTTP_429_TOO_MANY_REQUESTS,
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(metadata.get("limit", "N/A")),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(
                        int(datetime.now(timezone.utc).timestamp()) + retry_after
                    ),
                },
            )

        # Continue with the request
        response = await call_next(request)

        # Add rate limit headers
        if "remaining_per_minute" in metadata:
            response.headers["X-RateLimit-Limit"] = str(config.requests_per_minute)
            response.headers["X-RateLimit-Remaining"] = str(
                metadata["remaining_per_minute"]
            )
            response.headers["X-RateLimit-Reset"] = str(
                int(datetime.now(timezone.utc).timestamp()) + 60
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

    def _get_rate_limit_key_and_config(
        self, request: Request
    ) -> tuple[str, RateLimitConfig]:
        """Get rate limit key and configuration based on request.

        Args:
            request: The incoming request

        Returns:
            Tuple of (key, config)
        """
        principal = getattr(request.state, "principal", None)

        if principal:
            # Authenticated request
            if principal.type == "user":
                # Regular user
                return f"user:{principal.id}", self.configs["user"]
            elif principal.type == "agent":
                # Agent/API key
                service = principal.service
                service_config_key = f"agent_{service}"

                # Use service-specific config if available
                if service_config_key in self.configs:
                    config = self.configs[service_config_key]
                else:
                    config = self.configs["agent"]

                return f"agent:{principal.id}", config

        # Unauthenticated request - use IP address
        client_host = request.client.host if request.client else "unknown"
        return f"ip:{client_host}", self.configs["unauthenticated"]
