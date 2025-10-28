"""SlowAPI limiter setup for inbound rate limiting.

This module centralizes SlowAPI configuration for the FastAPI app.

Key features:
- Per-user keying when available (request.state.principal.id),
  otherwise falls back to API key headers, then client IP.
- Global default limits via environment variable ``DEFAULT_RATE_LIMIT``
  (e.g., "120/minute"). If unset, uses a safe default.
- Redis/Valkey storage via limits' async backends when a TCP Redis URL is
  available; falls back to in-memory storage for local/dev.

Note on Upstash Redis:
- The project uses the ``upstash-redis`` library for caching. SlowAPI/limits
  requires a TCP-compatible Redis URI (e.g., ``async+redis://``). If only
  ``UPSTASH_REDIS_REST_URL`` is configured (HTTP REST), limits cannot use it.
  In this case we fall back to ``memory://`` while continuing to use Upstash
  for general caching elsewhere.
"""

from __future__ import annotations

import os

from fastapi import FastAPI, Request
from slowapi import Limiter, _rate_limit_exceeded_handler
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


# Instantiate the Limiter with sane defaults; app/state wiring happens in install.
_default_limit = os.getenv("DEFAULT_RATE_LIMIT", "120/minute")


# Initialize limiter with in-memory defaults; rebind storage at install()
limiter = Limiter(
    key_func=_key_func,
    default_limits=[_default_limit],
    headers_enabled=True,
)


def install_rate_limiting(app: FastAPI, settings: Settings | None = None) -> None:
    """Install SlowAPI limiter middleware and handlers on the app.

    Args:
      app: FastAPI application instance.
      settings: Optional settings; if omitted, uses global settings.
    """
    _settings = settings or get_settings()

    # Re-bind storage if settings change at runtime (tests).
    app.state.limiter = limiter
    from typing import Any, cast

    app.add_exception_handler(
        RateLimitExceeded, cast(Any, _rate_limit_exceeded_handler)
    )
    app.add_middleware(SlowAPIMiddleware)
