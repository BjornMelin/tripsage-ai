"""Unit tests for KeyOperationRateLimitMiddleware dispatch logic.

These tests stub the monitoring service and avoid running a full ASGI app.
"""

from __future__ import annotations

from collections.abc import Awaitable
from typing import Any

import pytest
from fastapi import Request, Response

from tripsage_core.services.infrastructure.key_monitoring_service import (
    KeyMonitoringService,
    KeyOperationRateLimitMiddleware,
)


class _StubMonitoring(KeyMonitoringService):
    """Stub monitoring service allowing rate-limit behavior control."""

    def __init__(self, limited: bool = False) -> None:
        super().__init__()
        self._limited = limited
        self.logged: list[dict[str, Any]] = []

    async def is_rate_limited(self, user_id: str, operation) -> bool:
        """Return the configured rate-limit flag."""
        return self._limited

    async def log_operation(self, *args, **kwargs) -> None:
        """Capture log operation calls for assertion."""
        self.logged.append({"args": args, "kwargs": kwargs})


def _make_request(
    path: str, method: str = "GET", user_id: str | None = "u1"
) -> Request:
    """Construct a minimal Request with optional user_id in state."""
    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "root_path": "",
        "scheme": "http",
        "server": ("test", 80),
        "client": ("testclient", 123),
        "headers": [],
    }
    req = Request(scope)
    if user_id is not None:
        req.state.user_id = user_id
    return req


def _next_ok(_: Request) -> Awaitable[Response]:
    async def _inner() -> Response:
        return Response(content="ok", status_code=200)

    return _inner()


async def _asgi_app(scope, receive, send):
    """No-op ASGI app for middleware construction."""
    return


@pytest.mark.anyio
async def test_non_key_routes_pass_through() -> None:
    """Requests not targeting key routes are passed through."""
    mw = KeyOperationRateLimitMiddleware(
        app=_asgi_app, monitoring_service=_StubMonitoring(False)
    )
    req = _make_request("/api/other")
    res = await mw.dispatch(req, _next_ok)  # type: ignore[arg-type]
    assert res.status_code == 200


@pytest.mark.anyio
async def test_key_route_without_user_id_passes() -> None:
    """Key route with missing user_id passes through by design."""
    mw = KeyOperationRateLimitMiddleware(
        app=_asgi_app, monitoring_service=_StubMonitoring(False)
    )
    req = _make_request("/api/user/keys", user_id=None)
    res = await mw.dispatch(req, _next_ok)  # type: ignore[arg-type]
    assert res.status_code == 200


@pytest.mark.anyio
async def test_key_route_not_limited_calls_next() -> None:
    """Key route allowed when not rate limited."""
    stub = _StubMonitoring(False)
    mw = KeyOperationRateLimitMiddleware(app=_asgi_app, monitoring_service=stub)
    req = _make_request("/api/user/keys", method="POST")
    res = await mw.dispatch(req, _next_ok)  # type: ignore[arg-type]
    assert res.status_code == 200


@pytest.mark.anyio
async def test_key_route_limited_returns_429_and_logs() -> None:
    """Key route returns 429 when limited and logs the operation."""
    stub = _StubMonitoring(True)
    mw = KeyOperationRateLimitMiddleware(app=_asgi_app, monitoring_service=stub)
    req = _make_request("/api/user/keys", method="POST")
    res = await mw.dispatch(req, _next_ok)  # type: ignore[arg-type]
    assert res.status_code == 429
    assert res.headers.get("Retry-After") == "60"
    assert any(
        k.get("kwargs", {}).get("metadata", {}).get("rate_limited") for k in stub.logged
    )
