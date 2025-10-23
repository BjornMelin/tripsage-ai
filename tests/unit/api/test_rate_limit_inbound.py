"""Inbound rate limiting tests using SlowAPI on a minimal app.

These tests validate that the SlowAPI integration enforces limits and
produces 429 when exceeding per-route limits.
"""

from __future__ import annotations

from fastapi import FastAPI, Request, Response
from fastapi.testclient import TestClient
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address


def _build_app() -> FastAPI:
    limiter = Limiter(key_func=get_remote_address, headers_enabled=True)
    app = FastAPI()
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

    @app.post("/limited")
    @limiter.limit("3/minute")
    async def limited(request: Request, response: Response):
        """Simple limited endpoint."""
        return {"ok": True}

    return app


def test_per_route_limit_triggers_429():
    """Verify SlowAPI returns 429 on the 4th call for a 3/min route."""
    app = _build_app()
    client = TestClient(app)
    # First 3 succeed
    for _ in range(3):
        r = client.post("/limited")
        assert r.status_code < 400
    # 4th should be rate limited
    r = client.post("/limited")
    assert r.status_code == 429
    # Check at least one standard header exists when enabled
    assert "X-RateLimit-Limit" in r.headers or "Retry-After" in r.headers
