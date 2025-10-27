"""Security-focused tests for authentication helpers (Supabase-backed)."""

from __future__ import annotations

from typing import Any

import pytest
from starlette.requests import Request

from tripsage.api.core.dependencies import get_current_principal, require_principal
from tripsage.api.middlewares.authentication import Principal


def _http_scope() -> dict[str, Any]:
    """Return a minimal ASGI scope for HTTP requests."""
    headers: list[tuple[bytes, bytes]] = []
    return {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": headers,
    }


@pytest.mark.security
@pytest.mark.asyncio
async def test_require_principal_requires_bearer() -> None:
    """Reject requests missing the required Bearer token header."""
    from tripsage_core.exceptions.exceptions import CoreAuthenticationError

    with pytest.raises(CoreAuthenticationError):
        await require_principal(Request(_http_scope()))


@pytest.mark.security
@pytest.mark.asyncio
async def test_get_current_principal_optional() -> None:
    """get_current_principal returns None if principal is not set."""
    req = Request(_http_scope())
    assert await get_current_principal(req) is None


@pytest.mark.security
@pytest.mark.asyncio
async def test_require_principal_returns_subject() -> None:
    """require_principal yields state principal when present."""
    principal = Principal(id="user-123", type="user", auth_method="jwt")
    req = Request(_http_scope())
    req.state.principal = principal
    p = await require_principal(req)
    assert p.id == "user-123"


@pytest.mark.security
@pytest.mark.asyncio
async def test_require_principal_error_shape() -> None:
    """require_principal should surface an HTTP-like error when missing."""
    req = Request(_http_scope())
    from tripsage_core.exceptions.exceptions import CoreAuthenticationError

    with pytest.raises(CoreAuthenticationError):
        await require_principal(req)


@pytest.mark.security
@pytest.mark.asyncio
async def test_get_current_principal_after_state_set() -> None:
    """get_current_principal returns principal when present on state."""
    principal = Principal(id="optional-999", type="user", auth_method="jwt")
    req = Request(_http_scope())
    req.state.principal = principal
    result = await get_current_principal(req)
    assert result and result.id == "optional-999"


@pytest.mark.security
@pytest.mark.asyncio
async def test_get_current_principal_returns_subject() -> None:
    """get_current_principal returns id from state principal when present."""
    principal = Principal(id="optional-999", type="user", auth_method="jwt")
    req = Request(_http_scope())
    req.state.principal = principal
    result = await get_current_principal(req)
    assert result and result.id == "optional-999"
