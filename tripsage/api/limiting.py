"""SlowAPI limiter setup for inbound rate limiting.

This module centralizes SlowAPI configuration for the FastAPI app.

Key features:
- Per-user keying when available (request.state.principal.id),
  otherwise falls back to API key headers, then client IP.
- Default limits are derived exclusively from Settings; no env fallbacks.
- Redis storage via limits' async backends when a TCP Redis URL is available;
  use the Upstash Redis (TLS) endpoint for production. Falls back to
  in-memory storage for local/dev. Upstash REST credentials are not usable by
  SlowAPI/limits.
"""

from __future__ import annotations

from contextlib import suppress
from typing import Any, cast

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from tripsage_core.config import Settings, get_settings


def _key_func(request: Request) -> str:
    """Return the key used for rate limiting.

    Prefers an authenticated principal id when available, otherwise uses
    API-key/user headers, then the remote IP address.

    Args:
      request: Incoming request.

    Returns:
      A string key suitable for SlowAPI.
    """
    principal = getattr(request.state, "principal", None)
    if principal and getattr(principal, "id", None):
        return str(principal.id)

    # Fallbacks commonly set by clients/proxies
    for header in ("X-API-Key", "X-User-Id"):
        value = request.headers.get(header)
        if value:
            return value

    return get_remote_address(request)


def _to_async_redis_uri(url: str) -> str:
    """Convert a Redis URI to an async-compatible URI for limits.

    limits supports asyncio via schemes prefixed with ``async+`` (e.g.,
    ``async+redis://`` or ``async+rediss://``). If the provided URL is already
    async-compatible, it is returned unchanged.
    """
    if url.startswith("async+"):
        return url
    if "://" in url:
        return f"async+{url}"
    # Fallback: treat as redis host:port
    return f"async+redis://{url}"


def _build_default_limits(settings: Settings) -> list[str]:
    """Translate numeric rate settings into SlowAPI limit strings.

    The function returns a list like ["60/minute", "1000/hour", "10000/day"].
    Zero or negative values are ignored.
    """
    limits: list[str] = []
    if getattr(settings, "rate_limit_requests_per_minute", 0) > 0:
        limits.append(f"{settings.rate_limit_requests_per_minute}/minute")
    if getattr(settings, "rate_limit_requests_per_hour", 0) > 0:
        limits.append(f"{settings.rate_limit_requests_per_hour}/hour")
    if getattr(settings, "rate_limit_requests_per_day", 0) > 0:
        limits.append(f"{settings.rate_limit_requests_per_day}/day")
    return limits


# Initialize limiter with placeholder defaults; values are finalized in install().
limiter = Limiter(key_func=_key_func, default_limits=[], headers_enabled=True)


async def rate_limit_exceeded_handler(
    request: Request, exc: RateLimitExceeded
) -> JSONResponse:
    """Return an RFC 6585 compliant response for rate limit violations."""
    detail = getattr(exc, "detail", str(exc))
    response = JSONResponse(
        {"error": f"Rate limit exceeded: {detail}"},
        status_code=429,
    )

    limiter_instance = getattr(request.app.state, "limiter", None)
    view_rate_limit = getattr(request.state, "view_rate_limit", None)

    inject_headers = getattr(limiter_instance, "_inject_headers", None)
    if callable(inject_headers):
        with suppress(Exception):  # pragma: no cover - defensive
            injected = inject_headers(response, view_rate_limit)  # type: ignore[arg-type]
            if isinstance(injected, JSONResponse):
                response = injected

    return response


def install_rate_limiting(app: FastAPI, settings: Settings | None = None) -> None:
    """Install SlowAPI limiter middleware and handlers on the app.

    Args:
      app: FastAPI application instance.
      settings: Optional settings; if omitted, uses global settings.
    """
    _settings = settings or get_settings()

    # Configure limiter from Settings (single source of truth)
    limiter.enabled = bool(getattr(_settings, "rate_limit_enabled", True))
    limiter.default_limits = _build_default_limits(_settings)

    # Configure storage using Redis if available; otherwise memory
    storage_uri = "memory://"
    redis_url = getattr(_settings, "redis_url", None)
    if isinstance(redis_url, str) and redis_url.strip():
        storage_uri = _to_async_redis_uri(redis_url.strip())
    limiter.storage_uri = storage_uri  # type: ignore[attr-defined]
    # Prefer redis-py asyncio implementation when available
    with suppress(Exception):  # pragma: no cover - attribute differs by version
        limiter.storage_options = {"implementation": "redispy"}  # type: ignore[attr-defined]

    # Wire into application state and middleware/handlers
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, cast(Any, rate_limit_exceeded_handler))
    app.add_middleware(SlowAPIMiddleware)  # type: ignore[arg-type]
