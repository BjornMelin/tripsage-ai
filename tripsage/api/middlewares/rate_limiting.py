"""Enhanced rate limiting middleware for FastAPI.

This module provides production-ready rate limiting with:
- Per-API-key configurable limits
- Service-specific rate limits
- Integration with API key monitoring
- DragonflyDB distributed rate limiting
- Sliding window and token bucket algorithms
- Graceful degradation on cache failures
- Comprehensive rate limit headers
- Audit logging for rate limit violations
"""

import json
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, Optional

from fastapi import Request, Response
from pydantic import BaseModel, Field
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.status import HTTP_429_TOO_MANY_REQUESTS
from starlette.types import ASGIApp

from tripsage.api.core.config import Settings, get_settings
from tripsage_core.services.business.audit_logging_service import (
    AuditEventType,
    AuditOutcome,
    AuditSeverity,
    audit_api_key,
    audit_security_event,
)

logger = logging.getLogger(__name__)


class RateLimitConfig(BaseModel):
    """Configuration for rate limiting with enhanced features."""

    # Basic rate limits
    requests_per_minute: int = Field(default=60, gt=0)
    requests_per_hour: int = Field(default=1000, gt=0)
    requests_per_day: int = Field(default=10000, gt=0)

    # Token bucket configuration
    burst_size: int = Field(default=10, gt=0)
    refill_rate: float = Field(default=1.0, gt=0)  # tokens per second

    # Service-specific multipliers
    service_multipliers: Dict[str, float] = Field(default_factory=dict)

    # Advanced features
    enable_sliding_window: bool = True
    enable_token_bucket: bool = True
    enable_burst_protection: bool = True

    # Custom limits per endpoint pattern
    endpoint_overrides: Dict[str, Dict[str, int]] = Field(default_factory=dict)

    def get_effective_limits(
        self, service: Optional[str] = None, endpoint: Optional[str] = None
    ) -> Dict[str, int]:
        """Get effective rate limits for a service/endpoint combination."""
        multiplier = self.service_multipliers.get(service, 1.0) if service else 1.0

        # Check for endpoint-specific overrides
        if endpoint and endpoint in self.endpoint_overrides:
            overrides = self.endpoint_overrides[endpoint]
            return {
                "requests_per_minute": int(
                    overrides.get("requests_per_minute", self.requests_per_minute)
                    * multiplier
                ),
                "requests_per_hour": int(
                    overrides.get("requests_per_hour", self.requests_per_hour)
                    * multiplier
                ),
                "requests_per_day": int(
                    overrides.get("requests_per_day", self.requests_per_day)
                    * multiplier
                ),
                "burst_size": int(
                    overrides.get("burst_size", self.burst_size) * multiplier
                ),
            }

        return {
            "requests_per_minute": int(self.requests_per_minute * multiplier),
            "requests_per_hour": int(self.requests_per_hour * multiplier),
            "requests_per_day": int(self.requests_per_day * multiplier),
            "burst_size": int(self.burst_size * multiplier),
        }


class RateLimitResult(BaseModel):
    """Result of a rate limit check."""

    is_limited: bool
    limit_type: str  # 'minute', 'hour', 'day', 'burst'
    current_usage: int
    limit_value: int
    remaining: int
    reset_time: datetime
    retry_after_seconds: int = 0

    # Additional metadata
    tokens_remaining: Optional[float] = None
    window_start: Optional[datetime] = None
    algorithm: str = "sliding_window"  # 'sliding_window', 'token_bucket'


class RateLimiter:
    """Base rate limiter interface with enhanced capabilities."""

    async def check_rate_limit(
        self,
        key: str,
        config: RateLimitConfig,
        service: Optional[str] = None,
        endpoint: Optional[str] = None,
        cost: int = 1,
    ) -> RateLimitResult:
        """Check if a request should be rate limited.

        Args:
            key: The rate limit key (e.g., API key, user ID, IP)
            config: Rate limit configuration
            service: Service name for service-specific limits
            endpoint: Endpoint for endpoint-specific limits
            cost: Cost of this request (default 1)

        Returns:
            RateLimitResult with detailed rate limit information
        """
        raise NotImplementedError

    async def reset_rate_limit(self, key: str) -> bool:
        """Reset rate limit for a key.

        Args:
            key: The rate limit key to reset

        Returns:
            True if reset successful, False otherwise
        """
        raise NotImplementedError


class InMemoryRateLimiter(RateLimiter):
    """Enhanced in-memory rate limiter with sliding window and token bucket."""

    def __init__(self):
        self.requests: Dict[str, list] = {}
        self.token_buckets: Dict[str, Dict[str, Any]] = {}

    async def check_rate_limit(
        self,
        key: str,
        config: RateLimitConfig,
        service: Optional[str] = None,
        endpoint: Optional[str] = None,
        cost: int = 1,
    ) -> RateLimitResult:
        """Check rate limit using sliding window algorithm."""
        current_time = time.time()
        current_dt = datetime.fromtimestamp(current_time, tz=timezone.utc)

        # Get effective limits
        limits = config.get_effective_limits(service, endpoint)

        # Get or create request history for key
        if key not in self.requests:
            self.requests[key] = []

        # Clean up old entries (keep 25 hours for day limits)
        day_ago = current_time - 86400  # 24 hours
        hour_ago = current_time - 3600
        minute_ago = current_time - 60

        self.requests[key] = [
            req_time for req_time in self.requests[key] if req_time > day_ago
        ]

        # Count requests in different windows
        minute_count = sum(1 for t in self.requests[key] if t > minute_ago)
        hour_count = sum(1 for t in self.requests[key] if t > hour_ago)
        day_count = len(self.requests[key])

        # Check limits in order of precedence
        if minute_count >= limits["requests_per_minute"]:
            return RateLimitResult(
                is_limited=True,
                limit_type="minute",
                current_usage=minute_count,
                limit_value=limits["requests_per_minute"],
                remaining=0,
                reset_time=current_dt.replace(second=0, microsecond=0)
                + timedelta(minutes=1),
                retry_after_seconds=60 - int(current_time % 60),
                algorithm="sliding_window",
            )

        if hour_count >= limits["requests_per_hour"]:
            return RateLimitResult(
                is_limited=True,
                limit_type="hour",
                current_usage=hour_count,
                limit_value=limits["requests_per_hour"],
                remaining=0,
                reset_time=current_dt.replace(minute=0, second=0, microsecond=0)
                + timedelta(hours=1),
                retry_after_seconds=3600 - int(current_time % 3600),
                algorithm="sliding_window",
            )

        if day_count >= limits["requests_per_day"]:
            return RateLimitResult(
                is_limited=True,
                limit_type="day",
                current_usage=day_count,
                limit_value=limits["requests_per_day"],
                remaining=0,
                reset_time=current_dt.replace(hour=0, minute=0, second=0, microsecond=0)
                + timedelta(days=1),
                retry_after_seconds=86400 - int(current_time % 86400),
                algorithm="sliding_window",
            )

        # Add current request
        for _ in range(cost):
            self.requests[key].append(current_time)

        # Return success with remaining limits
        return RateLimitResult(
            is_limited=False,
            limit_type="minute",  # Use most restrictive window for remaining count
            current_usage=minute_count + cost,
            limit_value=limits["requests_per_minute"],
            remaining=max(0, limits["requests_per_minute"] - minute_count - cost),
            reset_time=current_dt.replace(second=0, microsecond=0)
            + timedelta(minutes=1),
            algorithm="sliding_window",
        )

    async def reset_rate_limit(self, key: str) -> bool:
        """Reset rate limit for a key."""
        if key in self.requests:
            del self.requests[key]
        if key in self.token_buckets:
            del self.token_buckets[key]
        return True


class DragonflyRateLimiter(RateLimiter):
    """Production-ready DragonflyDB-based rate limiter with hybrid algorithms."""

    def __init__(self, monitoring_service=None):
        self.cache_service = None
        self.monitoring_service = monitoring_service
        self.fallback_limiter = InMemoryRateLimiter()

    async def _ensure_cache(self):
        """Ensure cache service is initialized."""
        if not self.cache_service:
            try:
                from tripsage_core.services.infrastructure import get_cache_service

                self.cache_service = await get_cache_service()
            except Exception as e:
                logger.warning(f"Failed to initialize cache service: {e}")
                self.cache_service = None

    async def check_rate_limit(
        self,
        key: str,
        config: RateLimitConfig,
        service: Optional[str] = None,
        endpoint: Optional[str] = None,
        cost: int = 1,
    ) -> RateLimitResult:
        """Check rate limit using hybrid sliding window + token bucket algorithm."""
        await self._ensure_cache()

        # Fallback to in-memory if cache unavailable
        if not self.cache_service:
            logger.warning(
                "Cache service unavailable, falling back to in-memory rate limiting"
            )
            return await self.fallback_limiter.check_rate_limit(
                key, config, service, endpoint, cost
            )

        try:
            # Get effective limits
            limits = config.get_effective_limits(service, endpoint)
            current_time = time.time()
            current_dt = datetime.fromtimestamp(current_time, tz=timezone.utc)

            # Use token bucket for burst control and sliding window for sustained limits
            if config.enable_token_bucket:
                bucket_result = await self._check_token_bucket(
                    key, config, limits, cost, current_time, current_dt
                )
                if bucket_result.is_limited:
                    await self._track_rate_limit_hit(
                        key, service, "token_bucket", bucket_result
                    )
                    return bucket_result

            # Check sliding windows for sustained rate limits
            if config.enable_sliding_window:
                window_result = await self._check_sliding_windows(
                    key,
                    config,
                    limits,
                    cost,
                    current_time,
                    current_dt,
                    service,
                    endpoint,
                )
                if window_result.is_limited:
                    await self._track_rate_limit_hit(
                        key, service, window_result.limit_type, window_result
                    )
                    return window_result

                # Record successful request for monitoring
                await self._record_request(key, service, endpoint, current_time)
                return window_result

            # If both algorithms disabled, allow request
            logger.warning(f"Both rate limiting algorithms disabled for key {key}")
            return RateLimitResult(
                is_limited=False,
                limit_type="disabled",
                current_usage=0,
                limit_value=999999,
                remaining=999999,
                reset_time=current_dt + timedelta(hours=1),
                algorithm="disabled",
            )

        except Exception as e:
            logger.error(
                f"DragonflyDB rate limiting failed: {e}, falling back to in-memory"
            )
            return await self.fallback_limiter.check_rate_limit(
                key, config, service, endpoint, cost
            )

    async def _check_token_bucket(
        self,
        key: str,
        config: RateLimitConfig,
        limits: Dict[str, int],
        cost: int,
        current_time: float,
        current_dt: datetime,
    ) -> RateLimitResult:
        """Check token bucket for burst control."""
        bucket_key = f"rate_limit:bucket:{key}"
        refill_key = f"rate_limit:refill:{key}"

        # Use Redis pipeline for atomic operations
        pipe = self.cache_service.pipeline()
        pipe.get(bucket_key)
        pipe.get(refill_key)
        results = await pipe.execute()

        tokens_str, last_refill_str = results
        burst_size = limits["burst_size"]

        if tokens_str is None:
            # Initialize bucket
            tokens = float(burst_size)
            last_refill = current_time
        else:
            tokens = float(tokens_str)
            last_refill = float(last_refill_str or current_time)

        # Calculate tokens to add based on time passed
        time_passed = current_time - last_refill
        refill_rate = config.refill_rate or (limits["requests_per_minute"] / 60.0)
        tokens_to_add = time_passed * refill_rate

        # Add tokens up to burst size
        tokens = min(tokens + tokens_to_add, burst_size)

        # Check if we have enough tokens
        if tokens < cost:
            tokens_needed = cost - tokens
            retry_after = max(1, int(tokens_needed / refill_rate))

            return RateLimitResult(
                is_limited=True,
                limit_type="burst",
                current_usage=int(burst_size - tokens),
                limit_value=burst_size,
                remaining=0,
                reset_time=current_dt + timedelta(seconds=retry_after),
                retry_after_seconds=retry_after,
                tokens_remaining=tokens,
                algorithm="token_bucket",
            )

        # Consume tokens
        tokens -= cost

        # Save state atomically
        pipe = self.cache_service.pipeline()
        pipe.set(bucket_key, str(tokens), ex=3600)
        pipe.set(refill_key, str(current_time), ex=3600)
        await pipe.execute()

        return RateLimitResult(
            is_limited=False,
            limit_type="burst",
            current_usage=int(burst_size - tokens),
            limit_value=burst_size,
            remaining=int(tokens),
            reset_time=current_dt
            + timedelta(seconds=int((burst_size - tokens) / refill_rate)),
            tokens_remaining=tokens,
            algorithm="token_bucket",
        )

    async def _check_sliding_windows(
        self,
        key: str,
        config: RateLimitConfig,
        limits: Dict[str, int],
        cost: int,
        current_time: float,
        current_dt: datetime,
        service: Optional[str],
        endpoint: Optional[str],
    ) -> RateLimitResult:
        """Check sliding windows for sustained rate limits."""
        windows = [
            ("minute", 60, limits["requests_per_minute"]),
            ("hour", 3600, limits["requests_per_hour"]),
            ("day", 86400, limits["requests_per_day"]),
        ]

        # Check all windows and find the most restrictive
        for window_name, window_seconds, limit in windows:
            window_key = f"rate_limit:window:{window_name}:{key}"
            window_start = current_time - window_seconds

            # Remove expired entries and count current
            pipe = self.cache_service.pipeline()
            pipe.zremrangebyscore(window_key, 0, window_start)
            pipe.zcard(window_key)
            await pipe.execute()

            current_count = await self.cache_service.zcard(window_key)

            if current_count + cost > limit:
                # Calculate precise reset time
                if window_name == "minute":
                    reset_time = current_dt.replace(
                        second=0, microsecond=0
                    ) + timedelta(minutes=1)
                elif window_name == "hour":
                    reset_time = current_dt.replace(
                        minute=0, second=0, microsecond=0
                    ) + timedelta(hours=1)
                else:  # day
                    reset_time = current_dt.replace(
                        hour=0, minute=0, second=0, microsecond=0
                    ) + timedelta(days=1)

                retry_after = int((reset_time - current_dt).total_seconds())

                return RateLimitResult(
                    is_limited=True,
                    limit_type=window_name,
                    current_usage=current_count,
                    limit_value=limit,
                    remaining=0,
                    reset_time=reset_time,
                    retry_after_seconds=retry_after,
                    window_start=datetime.fromtimestamp(window_start, tz=timezone.utc),
                    algorithm="sliding_window",
                )

        # All windows passed, record the request
        for window_name, window_seconds, _limit in windows:
            window_key = f"rate_limit:window:{window_name}:{key}"

            # Add request timestamps with cost
            for i in range(cost):
                score = current_time + (i * 0.001)  # Slight offset for multiple cost
                await self.cache_service.zadd(window_key, {str(score): score})

            # Set expiration
            await self.cache_service.expire(
                window_key, int(window_seconds * 1.1)
            )  # 10% buffer

        # Return success with most restrictive remaining count (minute window)
        minute_count = await self.cache_service.zcard(f"rate_limit:window:minute:{key}")

        return RateLimitResult(
            is_limited=False,
            limit_type="minute",
            current_usage=minute_count,
            limit_value=limits["requests_per_minute"],
            remaining=max(0, limits["requests_per_minute"] - minute_count),
            reset_time=current_dt.replace(second=0, microsecond=0)
            + timedelta(minutes=1),
            algorithm="sliding_window",
        )

    async def _track_rate_limit_hit(
        self, key: str, service: Optional[str], limit_type: str, result: RateLimitResult
    ):
        """Track rate limit hits for monitoring."""
        if self.monitoring_service:
            try:
                await self.monitoring_service.track_usage(
                    key_id=key,
                    user_id="unknown",  # Will be populated by middleware
                    service=service or "unknown",
                    endpoint="rate_limit_check",
                    success=False,
                    latency_ms=0,
                    error_code="RATE_LIMIT_EXCEEDED",
                    error_message=f"Rate limit exceeded: {limit_type}",
                    metadata={
                        "limit_type": limit_type,
                        "current_usage": result.current_usage,
                        "limit_value": result.limit_value,
                        "algorithm": result.algorithm,
                    },
                )
            except Exception as e:
                logger.warning(f"Failed to track rate limit hit: {e}")

    async def _record_request(
        self,
        key: str,
        service: Optional[str],
        endpoint: Optional[str],
        timestamp: float,
    ):
        """Record successful request for analytics."""
        try:
            # Store request metadata for analytics
            analytics_key = f"rate_limit:analytics:{key}"
            request_data = {
                "timestamp": timestamp,
                "service": service,
                "endpoint": endpoint,
            }

            await self.cache_service.lpush(analytics_key, json.dumps(request_data))
            await self.cache_service.ltrim(
                analytics_key, 0, 999
            )  # Keep last 1000 requests
            await self.cache_service.expire(analytics_key, 86400)  # 24 hours

        except Exception as e:
            logger.debug(f"Failed to record request analytics: {e}")

    async def reset_rate_limit(self, key: str) -> bool:
        """Reset all rate limits for a key."""
        await self._ensure_cache()

        if not self.cache_service:
            return await self.fallback_limiter.reset_rate_limit(key)

        try:
            # Get all rate limit keys for this key
            patterns = [
                f"rate_limit:bucket:{key}",
                f"rate_limit:refill:{key}",
                f"rate_limit:window:*:{key}",
                f"rate_limit:analytics:{key}",
            ]

            keys_to_delete = []
            for pattern in patterns:
                if "*" in pattern:
                    keys = await self.cache_service.keys(pattern)
                    keys_to_delete.extend(keys)
                else:
                    keys_to_delete.append(pattern)

            if keys_to_delete:
                await self.cache_service.delete(*keys_to_delete)

            return True

        except Exception as e:
            logger.error(f"Failed to reset rate limits for {key}: {e}")
            return False


class EnhancedRateLimitMiddleware(BaseHTTPMiddleware):
    """Production-ready rate limiting middleware with comprehensive features.

    Features:
    - Per-API-key configurable limits with persistent storage
    - Service-specific rate limits (OpenAI, Weather, etc.)
    - Integration with API key monitoring service
    - DragonflyDB distributed rate limiting with graceful fallback
    - Comprehensive rate limit headers (RFC 6585 compliant)
    - Sliding window and token bucket algorithms
    - Endpoint-specific overrides
    - Real-time analytics and monitoring
    """

    def __init__(
        self,
        app: ASGIApp,
        settings: Optional[Settings] = None,
        use_dragonfly: bool = True,
        monitoring_service=None,
    ):
        """Initialize EnhancedRateLimitMiddleware.

        Args:
            app: The ASGI application
            settings: API settings or None to use the default
            use_dragonfly: Whether to use DragonflyDB for distributed rate limiting
            monitoring_service: API key monitoring service for tracking rate limit hits
        """
        super().__init__(app)
        self.settings = settings or get_settings()
        self.monitoring_service = monitoring_service

        # Initialize monitoring service if not provided
        if not self.monitoring_service and use_dragonfly:
            try:
                from tripsage_core.services.infrastructure import (
                    key_monitoring_service,
                )

                ApiKeyMonitoringService = key_monitoring_service.KeyMonitoringService

                self.monitoring_service = ApiKeyMonitoringService()
            except Exception as e:
                logger.warning(f"Failed to initialize monitoring service: {e}")

        # Create rate limiter
        if use_dragonfly:
            self.rate_limiter = DragonflyRateLimiter(
                monitoring_service=self.monitoring_service
            )
        else:
            self.rate_limiter = InMemoryRateLimiter()

        # Define comprehensive rate limit configurations
        self.configs = self._create_rate_limit_configs()

    def _create_rate_limit_configs(self) -> Dict[str, RateLimitConfig]:
        """Create comprehensive rate limit configurations."""
        return {
            # Base configurations
            "unauthenticated": RateLimitConfig(
                requests_per_minute=20,
                requests_per_hour=100,
                requests_per_day=500,
                burst_size=5,
                refill_rate=0.33,  # 20 requests per minute
                enable_burst_protection=True,
            ),
            "user": RateLimitConfig(
                requests_per_minute=60,
                requests_per_hour=1000,
                requests_per_day=5000,
                burst_size=15,
                refill_rate=1.0,
                service_multipliers={
                    "openai": 1.5,
                    "weather": 2.0,
                    "flights": 1.2,
                    "hotels": 1.2,
                },
            ),
            "agent": RateLimitConfig(
                requests_per_minute=300,
                requests_per_hour=10000,
                requests_per_day=50000,
                burst_size=50,
                refill_rate=5.0,
                service_multipliers={
                    "openai": 2.0,
                    "weather": 3.0,
                    "flights": 1.5,
                    "hotels": 1.5,
                },
                endpoint_overrides={
                    "/api/ai/chat": {
                        "requests_per_minute": 100,
                        "burst_size": 20,
                    },
                    "/api/search/flights": {
                        "requests_per_minute": 200,
                        "burst_size": 30,
                    },
                },
            ),
            # Service-specific high-throughput configurations
            "agent_openai": RateLimitConfig(
                requests_per_minute=500,
                requests_per_hour=20000,
                requests_per_day=100000,
                burst_size=100,
                refill_rate=8.33,
                enable_burst_protection=True,
            ),
            "agent_weather": RateLimitConfig(
                requests_per_minute=1000,
                requests_per_hour=30000,
                requests_per_day=150000,
                burst_size=150,
                refill_rate=16.67,
            ),
            # Premium tier configurations
            "premium_user": RateLimitConfig(
                requests_per_minute=200,
                requests_per_hour=5000,
                requests_per_day=25000,
                burst_size=40,
                refill_rate=3.33,
                service_multipliers={
                    "openai": 3.0,
                    "weather": 4.0,
                    "flights": 2.0,
                    "hotels": 2.0,
                },
            ),
            "premium_agent": RateLimitConfig(
                requests_per_minute=1000,
                requests_per_hour=50000,
                requests_per_day=250000,
                burst_size=200,
                refill_rate=16.67,
                service_multipliers={
                    "openai": 5.0,
                    "weather": 10.0,
                },
            ),
        }

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Response]
    ) -> Response:
        """Process the request with enhanced rate limiting.

        Args:
            request: The incoming request
            call_next: The next middleware or endpoint handler

        Returns:
            The response with rate limit headers
        """
        start_time = time.time()

        # Skip rate limiting for certain paths
        if self._should_skip_rate_limit(request.url.path):
            return await call_next(request)

        # Get rate limit context
        rate_limit_context = self._get_rate_limit_context(request)

        # Check rate limits
        result = await self.rate_limiter.check_rate_limit(
            key=rate_limit_context["key"],
            config=rate_limit_context["config"],
            service=rate_limit_context["service"],
            endpoint=rate_limit_context["endpoint"],
            cost=rate_limit_context["cost"],
        )

        if result.is_limited:
            # Track rate limit hit
            await self._track_rate_limit_violation(request, rate_limit_context, result)

            # Return 429 response with comprehensive headers
            return self._create_rate_limit_response(result, rate_limit_context)

        # Continue with the request
        response = await call_next(request)

        # Add comprehensive rate limit headers
        self._add_rate_limit_headers(response, result, rate_limit_context)

        # Track successful request
        await self._track_successful_request(
            request, rate_limit_context, start_time, response
        )

        return response

    def _get_rate_limit_context(self, request: Request) -> Dict[str, Any]:
        """Get comprehensive rate limit context for the request."""
        principal = getattr(request.state, "principal", None)
        path = request.url.path
        method = request.method

        # Determine endpoint pattern for overrides
        endpoint = self._normalize_endpoint_pattern(path)

        # Calculate request cost (can be customized based on endpoint)
        cost = self._calculate_request_cost(endpoint, method)

        if principal:
            # Authenticated request
            if hasattr(principal, "type") and principal.type == "user":
                # Check for premium user
                tier = getattr(principal, "tier", "standard")
                config_key = "premium_user" if tier == "premium" else "user"

                return {
                    "key": f"user:{principal.id}",
                    "config": self.configs[config_key],
                    "service": getattr(principal, "service", None),
                    "endpoint": endpoint,
                    "cost": cost,
                    "principal_type": "user",
                    "principal_id": principal.id,
                    "tier": tier,
                }

            elif hasattr(principal, "type") and principal.type == "agent":
                # API key/agent request
                service = getattr(principal, "service", None)
                tier = getattr(principal, "tier", "standard")

                # Determine configuration key
                if tier == "premium":
                    config_key = "premium_agent"
                elif service and f"agent_{service}" in self.configs:
                    config_key = f"agent_{service}"
                else:
                    config_key = "agent"

                return {
                    "key": f"agent:{principal.id}",
                    "config": self.configs[config_key],
                    "service": service,
                    "endpoint": endpoint,
                    "cost": cost,
                    "principal_type": "agent",
                    "principal_id": principal.id,
                    "tier": tier,
                }

        # Unauthenticated request - use IP address
        client_host = request.client.host if request.client else "unknown"
        real_ip = (
            request.headers.get("X-Real-IP")
            or request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
            or client_host
        )

        return {
            "key": f"ip:{real_ip}",
            "config": self.configs["unauthenticated"],
            "service": None,
            "endpoint": endpoint,
            "cost": cost,
            "principal_type": "unauthenticated",
            "principal_id": real_ip,
            "tier": "free",
        }

    def _normalize_endpoint_pattern(self, path: str) -> str:
        """Normalize endpoint path to pattern for configuration lookup."""
        # Remove API prefix
        if path.startswith("/api"):
            path = path[4:]

        # Replace dynamic segments with placeholders
        import re

        # Replace UUIDs and numeric IDs
        path = re.sub(
            r"/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
            "/{id}",
            path,
        )
        path = re.sub(r"/\d+", "/{id}", path)

        # Normalize common patterns
        patterns = {
            r"/users/[^/]+": "/users/{id}",
            r"/trips/[^/]+": "/trips/{id}",
            r"/bookings/[^/]+": "/bookings/{id}",
        }

        for pattern, replacement in patterns.items():
            path = re.sub(pattern, replacement, path)

        return f"/api{path}" if path != "/" else path

    def _calculate_request_cost(self, endpoint: str, method: str) -> int:
        """Calculate the cost of a request based on endpoint and method."""
        # Base cost by method
        method_costs = {
            "GET": 1,
            "POST": 2,
            "PUT": 2,
            "PATCH": 1,
            "DELETE": 1,
        }

        base_cost = method_costs.get(method, 1)

        # Endpoint-specific cost multipliers
        high_cost_endpoints = {
            "/api/ai/chat": 3,
            "/api/ai/generate": 5,
            "/api/search/flights": 2,
            "/api/search/hotels": 2,
            "/api/bookings": 3,
        }

        for pattern, multiplier in high_cost_endpoints.items():
            if endpoint.startswith(pattern):
                return base_cost * multiplier

        return base_cost

    def _should_skip_rate_limit(self, path: str) -> bool:
        """Check if rate limiting should be skipped for a path."""
        skip_paths = [
            "/api/docs",
            "/api/redoc",
            "/api/openapi.json",
            "/api/health",
            "/api/metrics",
            "/favicon.ico",
            "/robots.txt",
        ]

        return any(path.startswith(skip_path) for skip_path in skip_paths)

    def _create_rate_limit_response(
        self, result: RateLimitResult, context: Dict[str, Any]
    ) -> Response:
        """Create a comprehensive 429 response."""
        retry_after = result.retry_after_seconds

        # Create user-friendly error message
        if result.limit_type == "minute":
            message = (
                f"Rate limit exceeded: {result.limit_value} requests per minute "
                f"allowed. Try again in {retry_after} seconds."
            )
        elif result.limit_type == "hour":
            message = (
                f"Hourly rate limit exceeded: {result.limit_value} requests per hour "
                f"allowed. Resets in {retry_after // 60} minutes."
            )
        elif result.limit_type == "day":
            message = (
                f"Daily rate limit exceeded: {result.limit_value} requests per day "
                f"allowed. Resets in {retry_after // 3600} hours."
            )
        elif result.limit_type == "burst":
            message = (
                f"Burst limit exceeded. Please slow down your requests. "
                f"Try again in {retry_after} seconds."
            )
        else:
            message = f"Rate limit exceeded. Try again in {retry_after} seconds."

        # Create comprehensive headers (RFC 6585 compliant)
        headers = {
            "Retry-After": str(retry_after),
            "X-RateLimit-Limit": str(result.limit_value),
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": str(int(result.reset_time.timestamp())),
            "X-RateLimit-Reset-After": str(retry_after),
            "X-RateLimit-Scope": result.limit_type,
            "X-RateLimit-Policy": f"{result.limit_value};w={result.limit_type}",
        }

        # Add algorithm-specific headers
        if result.algorithm == "token_bucket" and result.tokens_remaining is not None:
            headers["X-RateLimit-Tokens-Remaining"] = str(int(result.tokens_remaining))

        # Add service context if available
        if context.get("service"):
            headers["X-RateLimit-Service"] = context["service"]

        return Response(
            content=json.dumps(
                {
                    "error": "rate_limit_exceeded",
                    "message": message,
                    "retry_after": retry_after,
                    "limit": result.limit_value,
                    "scope": result.limit_type,
                    "reset_time": result.reset_time.isoformat(),
                }
            ),
            status_code=HTTP_429_TOO_MANY_REQUESTS,
            headers=headers,
            media_type="application/json",
        )

    def _add_rate_limit_headers(
        self, response: Response, result: RateLimitResult, context: Dict[str, Any]
    ):
        """Add comprehensive rate limit headers to successful responses."""
        headers = {
            "X-RateLimit-Limit": str(result.limit_value),
            "X-RateLimit-Remaining": str(result.remaining),
            "X-RateLimit-Reset": str(int(result.reset_time.timestamp())),
            "X-RateLimit-Scope": result.limit_type,
            "X-RateLimit-Policy": f"{result.limit_value};w={result.limit_type}",
        }

        # Add algorithm-specific headers
        if result.algorithm == "token_bucket" and result.tokens_remaining is not None:
            headers["X-RateLimit-Tokens-Remaining"] = str(int(result.tokens_remaining))

        # Add service context if available
        if context.get("service"):
            headers["X-RateLimit-Service"] = context["service"]

        # Add cost information
        if context.get("cost", 1) > 1:
            headers["X-RateLimit-Cost"] = str(context["cost"])

        for key, value in headers.items():
            response.headers[key] = value

    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address with proper header precedence."""
        # Check forwarded headers in order of preference
        forwarded_headers = [
            "X-Forwarded-For",
            "X-Real-IP",
            "CF-Connecting-IP",  # Cloudflare
            "X-Client-IP",
        ]

        for header in forwarded_headers:
            ip = request.headers.get(header)
            if ip:
                # Take first IP if comma-separated
                ip = ip.split(",")[0].strip()
                if self._is_valid_ip_format(ip):
                    return ip

        # Fall back to direct connection IP
        if hasattr(request.client, "host"):
            return request.client.host

        return "unknown"

    def _is_valid_ip_format(self, ip: str) -> bool:
        """Check if string is a valid IP address format."""
        try:
            from ipaddress import AddressValueError, ip_address

            ip_address(ip)
            return True
        except (ValueError, AddressValueError):
            return False

    async def _track_rate_limit_violation(
        self, request: Request, context: Dict[str, Any], result: RateLimitResult
    ):
        """Track rate limit violations for monitoring and analytics."""
        if self.monitoring_service:
            try:
                await self.monitoring_service.track_usage(
                    key_id=context["principal_id"],
                    user_id=context["principal_id"]
                    if context["principal_type"] == "user"
                    else "unknown",
                    service=context.get("service", "unknown"),
                    endpoint=context["endpoint"],
                    success=False,
                    latency_ms=0,
                    error_code="RATE_LIMIT_EXCEEDED",
                    error_message=f"Rate limit exceeded: {result.limit_type}",
                    metadata={
                        "limit_type": result.limit_type,
                        "current_usage": result.current_usage,
                        "limit_value": result.limit_value,
                        "algorithm": result.algorithm,
                        "principal_type": context["principal_type"],
                        "tier": context.get("tier", "unknown"),
                        "cost": context["cost"],
                        "user_agent": request.headers.get("User-Agent", "unknown"),
                        "referer": request.headers.get("Referer", "unknown"),
                    },
                )
            except Exception as e:
                logger.warning(f"Failed to track rate limit violation: {e}")

        # Get client IP for audit logging
        client_ip = self._get_client_ip(request)

        # Log rate limit violation to audit system
        try:
            if context["principal_type"] == "agent":
                # API key rate limit violation
                await audit_api_key(
                    event_type=AuditEventType.API_KEY_RATE_LIMITED,
                    outcome=AuditOutcome.FAILURE,
                    key_id=context["principal_id"],
                    service=context.get("service", "unknown"),
                    ip_address=client_ip,
                    message=f"Rate limit exceeded for {result.limit_type} window",
                    limit_type=result.limit_type,
                    current_usage=result.current_usage,
                    limit_value=result.limit_value,
                    algorithm=result.algorithm,
                    endpoint=context["endpoint"],
                    cost=context["cost"],
                    tier=context.get("tier", "standard"),
                )
            else:
                # User rate limit violation
                await audit_security_event(
                    event_type=AuditEventType.RATE_LIMIT_EXCEEDED,
                    severity=AuditSeverity.MEDIUM,
                    message=f"Rate limit exceeded for {result.limit_type} window",
                    actor_id=context["principal_id"],
                    ip_address=client_ip,
                    target_resource=context["endpoint"],
                    risk_score=40,
                    limit_type=result.limit_type,
                    current_usage=result.current_usage,
                    limit_value=result.limit_value,
                    algorithm=result.algorithm,
                    principal_type=context["principal_type"],
                    cost=context["cost"],
                    tier=context.get("tier", "standard"),
                    user_agent=request.headers.get("User-Agent"),
                )
        except Exception as e:
            logger.warning(f"Failed to audit rate limit violation: {e}")

        # Also log the violation
        logger.warning(
            "Rate limit exceeded",
            extra={
                "key": context["key"],
                "path": context["endpoint"],
                "principal_type": context["principal_type"],
                "principal_id": context["principal_id"],
                "service": context.get("service"),
                "limit_type": result.limit_type,
                "current_usage": result.current_usage,
                "limit_value": result.limit_value,
                "algorithm": result.algorithm,
                "cost": context["cost"],
                "tier": context.get("tier"),
            },
        )

    async def _track_successful_request(
        self,
        request: Request,
        context: Dict[str, Any],
        start_time: float,
        response: Response,
    ):
        """Track successful requests for monitoring and analytics."""
        if self.monitoring_service and context["principal_type"] != "unauthenticated":
            try:
                latency_ms = (time.time() - start_time) * 1000

                await self.monitoring_service.track_usage(
                    key_id=context["principal_id"],
                    user_id=context["principal_id"]
                    if context["principal_type"] == "user"
                    else "unknown",
                    service=context.get("service", "api"),
                    endpoint=context["endpoint"],
                    success=response.status_code < 400,
                    latency_ms=latency_ms,
                    error_code=str(response.status_code)
                    if response.status_code >= 400
                    else None,
                    error_message=None,
                    request_size=len(
                        await request.body() if hasattr(request, "body") else b""
                    ),
                    response_size=len(response.body)
                    if hasattr(response, "body")
                    else 0,
                    metadata={
                        "method": request.method,
                        "principal_type": context["principal_type"],
                        "tier": context.get("tier", "unknown"),
                        "cost": context["cost"],
                        "status_code": response.status_code,
                    },
                )
            except Exception as e:
                logger.debug(f"Failed to track successful request: {e}")


# Configuration helper functions
def create_rate_limit_config_from_dict(config_dict: Dict[str, Any]) -> RateLimitConfig:
    """Create a RateLimitConfig from a dictionary (useful for dynamic configuration)."""
    return RateLimitConfig(**config_dict)


def create_rate_limit_config_from_settings(
    settings: Settings, tier: str = "user"
) -> RateLimitConfig:
    """Create a RateLimitConfig from application settings.

    Args:
        settings: Application settings
        tier: The tier to create config for ('user', 'agent', 'premium_user', etc.)

    Returns:
        RateLimitConfig configured from settings
    """
    base_config = RateLimitConfig(
        requests_per_minute=settings.rate_limit_requests_per_minute,
        requests_per_hour=settings.rate_limit_requests_per_hour,
        requests_per_day=settings.rate_limit_requests_per_day,
        burst_size=settings.rate_limit_burst_size,
        enable_sliding_window=settings.rate_limit_enable_sliding_window,
        enable_token_bucket=settings.rate_limit_enable_token_bucket,
        enable_burst_protection=settings.rate_limit_enable_burst_protection,
    )

    # Apply tier-specific multipliers
    tier_multipliers = {
        "user": 1.0,
        "agent": 3.0,
        "premium_user": 2.0,
        "premium_agent": 10.0,
        "unauthenticated": 0.2,
    }

    multiplier = tier_multipliers.get(tier, 1.0)

    if multiplier != 1.0:
        base_config.requests_per_minute = int(
            base_config.requests_per_minute * multiplier
        )
        base_config.requests_per_hour = int(base_config.requests_per_hour * multiplier)
        base_config.requests_per_day = int(base_config.requests_per_day * multiplier)
        base_config.burst_size = int(base_config.burst_size * multiplier)

    return base_config


def get_default_rate_limit_middleware(
    app: ASGIApp,
    settings: Optional[Settings] = None,
    use_dragonfly: Optional[bool] = None,
    monitoring_service=None,
) -> EnhancedRateLimitMiddleware:
    """Get a pre-configured rate limiting middleware with sensible defaults."""
    if settings is None:
        settings = get_settings()

    if use_dragonfly is None:
        use_dragonfly = settings.rate_limit_use_dragonfly

    return EnhancedRateLimitMiddleware(
        app=app,
        settings=settings,
        use_dragonfly=use_dragonfly,
        monitoring_service=monitoring_service,
    )


def create_middleware_from_settings(
    app: ASGIApp, settings: Optional[Settings] = None
) -> Optional[EnhancedRateLimitMiddleware]:
    """Create rate limiting middleware from settings if enabled.

    Args:
        app: ASGI application
        settings: Application settings (will use default if None)

    Returns:
        EnhancedRateLimitMiddleware if enabled in settings, None otherwise
    """
    if settings is None:
        settings = get_settings()

    if not settings.rate_limit_enabled:
        return None

    # Initialize monitoring service if enabled
    monitoring_service = None
    if settings.rate_limit_enable_monitoring:
        try:
            from tripsage_core.services.infrastructure.key_monitoring_service import (
                KeyMonitoringService as ApiKeyMonitoringService,
            )

            monitoring_service = ApiKeyMonitoringService()
        except Exception as e:
            logger.warning(f"Failed to initialize monitoring service: {e}")

    # Create middleware with settings-based configuration
    middleware = EnhancedRateLimitMiddleware(
        app=app,
        settings=settings,
        use_dragonfly=settings.rate_limit_use_dragonfly,
        monitoring_service=monitoring_service,
    )

    # Override default configs with settings-based configs
    middleware.configs.update(
        {
            "user": create_rate_limit_config_from_settings(settings, "user"),
            "agent": create_rate_limit_config_from_settings(settings, "agent"),
            "premium_user": create_rate_limit_config_from_settings(
                settings, "premium_user"
            ),
            "premium_agent": create_rate_limit_config_from_settings(
                settings, "premium_agent"
            ),
            "unauthenticated": create_rate_limit_config_from_settings(
                settings, "unauthenticated"
            ),
        }
    )

    return middleware
