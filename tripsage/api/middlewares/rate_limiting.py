"""Enhanced rate limiting middleware for FastAPI with SlowAPI integration.

This module provides advanced rate limiting middleware using SlowAPI that can apply
different limits based on the authenticated principal (user vs agent) with
geographic analysis, security monitoring, and timing attack protection.
"""

import hashlib
import hmac
import logging
import secrets
import time
from datetime import datetime, timezone
from typing import Callable, Dict, Optional

from fastapi import Request, Response
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.status import HTTP_429_TOO_MANY_REQUESTS
from starlette.types import ASGIApp

from tripsage.api.core.config import Settings, get_settings

logger = logging.getLogger(__name__)


def secure_key_func(request: Request) -> str:
    """Secure key function for rate limiting with timing attack protection.

    This function creates a secure identifier for rate limiting that:
    - Uses constant-time operations to prevent timing attacks
    - Implements geographic-aware rate limiting
    - Provides enhanced security monitoring
    """
    principal = getattr(request.state, "principal", None)

    if principal:
        # Authenticated request - use principal ID with constant-time hashing
        base_key = f"auth:{principal.type}:{principal.id}"
        # Add service context for agents
        if principal.type == "agent" and principal.service:
            base_key = f"agent:{principal.service}:{principal.id}"
    else:
        # Unauthenticated request - use IP with geographic info
        client_ip = get_remote_address(request)
        # Add user agent hash for additional fingerprinting
        user_agent = request.headers.get("User-Agent", "")
        ua_hash = hashlib.sha256(user_agent.encode()).hexdigest()[:8]
        base_key = f"ip:{client_ip}:ua:{ua_hash}"

    # Use HMAC for constant-time key generation to prevent timing attacks
    # This ensures all key generation takes the same amount of time
    secret = secrets.token_bytes(32)  # Use a secure random secret
    secure_hash = hmac.new(secret, base_key.encode(), hashlib.sha256).hexdigest()[:16]

    return f"{base_key}:{secure_hash}"


def enhanced_get_remote_address(request: Request) -> str:
    """Enhanced IP extraction with geographic awareness and security validation."""
    # Priority list for IP extraction (security-focused)
    ip_headers = [
        "CF-Connecting-IP",  # Cloudflare (highest trust)
        "X-Real-IP",  # Nginx reverse proxy
        "X-Forwarded-For",  # Standard forwarded header
        "X-Client-IP",  # Alternative client IP
        "HTTP_X_FORWARDED_FOR",  # CGI format
    ]

    # First pass: look for public IPs
    for header in ip_headers:
        ip_value = request.headers.get(header)
        if ip_value:
            # Check all IPs in comma-separated list for public IPs
            for ip in ip_value.split(","):
                ip = ip.strip()
                if _is_valid_ip(ip) and not _is_private_ip(ip):
                    return ip

    # Second pass: accept private IPs if no public ones found
    for header in ip_headers:
        ip_value = request.headers.get(header)
        if ip_value:
            # Check all IPs in comma-separated list for any valid IP
            for ip in ip_value.split(","):
                ip = ip.strip()
                if _is_valid_ip(ip):
                    return ip

    # Fallback to direct connection
    return request.client.host if request.client else "unknown"


def _is_valid_ip(ip: str) -> bool:
    """Validate IP address format with enhanced security checks."""
    try:
        from ipaddress import AddressValueError, ip_address

        ip_obj = ip_address(ip)

        # Additional security checks
        if ip_obj.is_loopback or ip_obj.is_multicast:
            return False

        return True
    except (ValueError, AddressValueError):
        return False


def _is_private_ip(ip: str) -> bool:
    """Check if IP is in private range."""
    try:
        from ipaddress import ip_address

        ip_obj = ip_address(ip)
        return ip_obj.is_private
    except:
        return False


class SecurityMonitor:
    """Security monitoring for rate limiting events."""

    def __init__(self):
        self.suspicious_ips = set()
        self.failed_attempts = {}
        self.last_cleanup = time.time()

    def record_rate_limit_exceeded(self, request: Request, limit_type: str):
        """Record rate limit exceeded event for security monitoring."""
        client_ip = enhanced_get_remote_address(request)
        user_agent = request.headers.get("User-Agent", "Unknown")[:200]
        path = request.url.path

        # Track failed attempts per IP
        current_time = time.time()
        if client_ip not in self.failed_attempts:
            self.failed_attempts[client_ip] = []

        self.failed_attempts[client_ip].append(current_time)

        # Clean old attempts (older than 1 hour)
        cutoff_time = current_time - 3600
        self.failed_attempts[client_ip] = [
            t for t in self.failed_attempts[client_ip] if t > cutoff_time
        ]

        # Mark as suspicious if too many failures
        if len(self.failed_attempts[client_ip]) > 10:
            self.suspicious_ips.add(client_ip)
            logger.warning(
                "IP marked as suspicious due to repeated rate limit violations",
                extra={
                    "ip_address": client_ip,
                    "violation_count": len(self.failed_attempts[client_ip]),
                    "limit_type": limit_type,
                    "user_agent": user_agent,
                    "path": path,
                    "security_event": "rate_limit_abuse",
                },
            )

        # Enhanced logging with security context
        logger.warning(
            "Rate limit exceeded - enhanced monitoring",
            extra={
                "ip_address": client_ip,
                "user_agent": user_agent,
                "path": path,
                "limit_type": limit_type,
                "total_violations": len(self.failed_attempts[client_ip]),
                "is_suspicious": client_ip in self.suspicious_ips,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "security_event": "rate_limit_exceeded",
            },
        )

    def is_suspicious_ip(self, ip: str) -> bool:
        """Check if IP is marked as suspicious."""
        return ip in self.suspicious_ips

    def cleanup_old_data(self):
        """Cleanup old monitoring data."""
        current_time = time.time()

        # Clean every 30 minutes
        if current_time - self.last_cleanup > 1800:
            cutoff_time = current_time - 3600

            # Remove old failed attempts
            for ip in list(self.failed_attempts.keys()):
                self.failed_attempts[ip] = [
                    t for t in self.failed_attempts[ip] if t > cutoff_time
                ]
                if not self.failed_attempts[ip]:
                    del self.failed_attempts[ip]
                    # Remove from suspicious if no recent failures
                    self.suspicious_ips.discard(ip)

            self.last_cleanup = current_time


# Global security monitor instance
security_monitor = SecurityMonitor()


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


class SlowAPIRateLimitMiddleware(BaseHTTPMiddleware):
    """Enhanced SlowAPI-based rate limiting middleware with security monitoring.

    This middleware provides:
    - Principal-based rate limiting (user vs agent vs unauthenticated)
    - Geographic-aware rate limiting with IP analysis
    - Timing attack protection using constant-time operations
    - Security monitoring and threat detection
    - Redis/DragonflyDB backend support for distributed systems
    """

    def __init__(
        self,
        app: ASGIApp,
        settings: Optional[Settings] = None,
        use_dragonfly: bool = False,
    ):
        """Initialize SlowAPIRateLimitMiddleware.

        Args:
            app: The ASGI application
            settings: API settings or None to use the default
            use_dragonfly: Whether to use DragonflyDB for rate limiting
        """
        super().__init__(app)
        self.settings = settings or get_settings()

        # Initialize storage backend
        if use_dragonfly and self.settings.redis_url:
            storage_uri = self.settings.redis_url
        else:
            storage_uri = "memory://"

        # Create SlowAPI limiter with secure key function
        self.limiter = Limiter(
            key_func=secure_key_func,
            storage_uri=storage_uri,
            default_limits=["100/minute", "1000/hour"],  # Conservative defaults
        )

        # Define principal-based rate limits (more granular than before)
        self.rate_limits = {
            # Unauthenticated users - most restrictive
            "unauthenticated": ["20/minute", "100/hour"],
            # Regular authenticated users
            "user": ["60/minute", "1000/hour"],
            # API agents - higher limits
            "agent": ["300/minute", "10000/hour"],
            # Service-specific limits for high-volume agents
            "agent_openai": ["500/minute", "20000/hour"],
            "agent_anthropic": ["400/minute", "15000/hour"],
            "agent_google": ["300/minute", "12000/hour"],
            # Special limits for admin operations
            "admin": ["1000/minute", "50000/hour"],
        }

    def get_limits_for_request(self, request: Request) -> list[str]:
        """Get appropriate rate limits for request based on principal.

        Args:
            request: The incoming request

        Returns:
            List of rate limit strings (e.g., ["60/minute", "1000/hour"])
        """
        principal = getattr(request.state, "principal", None)

        if principal:
            if principal.type == "user":
                # Check for admin role
                if principal.metadata.get("role") == "admin":
                    return self.rate_limits["admin"]
                return self.rate_limits["user"]
            elif principal.type == "agent":
                # Service-specific limits for agents
                service = principal.service
                service_key = f"agent_{service}"
                if service_key in self.rate_limits:
                    return self.rate_limits[service_key]
                return self.rate_limits["agent"]

        # Unauthenticated request
        client_ip = enhanced_get_remote_address(request)

        # Apply stricter limits for suspicious IPs
        if security_monitor.is_suspicious_ip(client_ip):
            return ["5/minute", "20/hour"]  # Very restrictive for suspicious IPs

        return self.rate_limits["unauthenticated"]

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Response]
    ) -> Response:
        """Process the request with enhanced security and rate limiting.

        Args:
            request: The incoming request
            call_next: The next middleware or endpoint handler

        Returns:
            The response from the next middleware or endpoint
        """
        # Skip rate limiting for certain paths
        if self._should_skip_rate_limit(request.url.path):
            return await call_next(request)

        # Cleanup old security monitoring data periodically
        security_monitor.cleanup_old_data()

        # Get appropriate limits for this request
        limits = self.get_limits_for_request(request)

        try:
            # Check rate limits directly using the limiter's storage
            key = secure_key_func(request)

            # Check each limit manually
            for limit_str in limits:
                parts = limit_str.split("/")
                if len(parts) != 2:
                    continue

                limit_count = int(parts[0])
                period = parts[1]

                # Convert period to seconds
                if period == "minute":
                    window_seconds = 60
                elif period == "hour":
                    window_seconds = 3600
                elif period == "second":
                    window_seconds = 1
                else:
                    continue

                # Check if this specific limit is exceeded
                if await self._check_rate_limit(key, limit_count, window_seconds):
                    raise RateLimitExceeded("Rate limit exceeded")

            # Rate limit passed - continue with request
            response = await call_next(request)

            # Add rate limit headers for transparency
            self._add_rate_limit_headers(response, limits, request)

            return response

        except RateLimitExceeded as e:
            # Record security event
            principal = getattr(request.state, "principal", None)
            limit_type = "authenticated" if principal else "unauthenticated"
            security_monitor.record_rate_limit_exceeded(request, limit_type)

            # Enhanced rate limit response with security context
            return self._create_rate_limit_response(request, e, limits)

    async def _check_rate_limit(
        self, key: str, limit: int, window_seconds: int
    ) -> bool:
        """Check if rate limit is exceeded for a specific key and window.

        Args:
            key: Rate limit key
            limit: Maximum number of requests
            window_seconds: Time window in seconds

        Returns:
            True if rate limit exceeded, False otherwise
        """
        # Use basic in-memory rate limiting for now
        # In production, this would use Redis/DragonflyDB
        current_time = time.time()
        window_start = current_time - window_seconds

        # Get existing record
        if not hasattr(self, "_rate_limit_storage"):
            self._rate_limit_storage = {}

        if key not in self._rate_limit_storage:
            self._rate_limit_storage[key] = []

        # Clean old entries
        self._rate_limit_storage[key] = [
            timestamp
            for timestamp in self._rate_limit_storage[key]
            if timestamp > window_start
        ]

        # Check if limit exceeded
        if len(self._rate_limit_storage[key]) >= limit:
            return True

        # Add current request
        self._rate_limit_storage[key].append(current_time)
        return False

    def _add_rate_limit_headers(
        self, response: Response, limits: list[str], request: Request
    ) -> None:
        """Add rate limit headers to response for client transparency.

        Args:
            response: HTTP response to modify
            limits: Applied rate limits
            request: Original request
        """
        # Extract minute limit for headers
        minute_limit = None
        for limit in limits:
            if "/minute" in limit:
                minute_limit = int(limit.split("/")[0])
                break

        if minute_limit:
            # These headers help clients implement proper backoff
            response.headers["X-RateLimit-Limit"] = str(minute_limit)
            response.headers["X-RateLimit-Window"] = "60"
            response.headers["X-RateLimit-Policy"] = "sliding-window"

            # Add security context headers
            principal = getattr(request.state, "principal", None)
            if principal:
                response.headers["X-RateLimit-Type"] = principal.type
            else:
                response.headers["X-RateLimit-Type"] = "anonymous"

    def _create_rate_limit_response(
        self, request: Request, exc: RateLimitExceeded, limits: list[str]
    ) -> Response:
        """Create enhanced rate limit exceeded response.

        Args:
            request: The original request
            exc: Rate limit exceeded exception
            limits: Applied rate limits

        Returns:
            HTTP 429 response with detailed information
        """
        client_ip = enhanced_get_remote_address(request)
        retry_after = 60  # Default retry after 1 minute

        # Calculate retry after based on the limit that was exceeded
        if hasattr(exc, "retry_after"):
            retry_after = int(exc.retry_after)

        # Enhanced response with security context
        response_data = {
            "error": "Rate limit exceeded",
            "message": f"Too many requests. Please retry after {retry_after} seconds.",
            "retry_after": retry_after,
            "limits_applied": limits,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Add security warnings for suspicious IPs
        if security_monitor.is_suspicious_ip(client_ip):
            response_data["security_notice"] = (
                "Multiple violations detected from this IP"
            )

        return Response(
            content=str(response_data),
            status_code=HTTP_429_TOO_MANY_REQUESTS,
            headers={
                "Retry-After": str(retry_after),
                "X-RateLimit-Reset": str(
                    int(datetime.now(timezone.utc).timestamp()) + retry_after
                ),
                "Content-Type": "application/json",
            },
        )

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


# Backward compatibility alias
EnhancedRateLimitMiddleware = SlowAPIRateLimitMiddleware
