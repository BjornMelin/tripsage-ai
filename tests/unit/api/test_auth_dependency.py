"""Unit tests for principal-based auth dependencies."""

import pytest
from starlette.requests import Request

from tripsage.api.core.dependencies import (
    get_current_principal,
    get_principal_id,
    require_admin_principal,
    require_principal,
)
from tripsage.api.middlewares.authentication import Principal
from tripsage_core.exceptions.exceptions import (
    CoreAuthenticationError,
    CoreAuthorizationError,
)


def _make_request_with_principal(principal: Principal | None) -> Request:
    """Make a request with a principal."""
    scope: dict[str, object] = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [],
    }
    req = Request(scope)  # type: ignore[arg-type]
    if principal is not None:
        req.state.principal = principal
    return req


@pytest.mark.asyncio
async def test_require_principal_success() -> None:
    """require_principal returns the principal when present on request.state."""
    principal = Principal(id="user-123", type="user", auth_method="jwt")
    req = _make_request_with_principal(principal)
    result = await require_principal(req)
    assert result.id == "user-123"
    assert get_principal_id(result) == "user-123"


@pytest.mark.asyncio
async def test_require_principal_missing_raises() -> None:
    """require_principal raises CoreAuthenticationError when unauthenticated."""
    req = _make_request_with_principal(None)
    with pytest.raises(CoreAuthenticationError):
        await require_principal(req)


@pytest.mark.asyncio
async def test_get_current_principal_optional() -> None:
    """get_current_principal returns principal or None without raising."""
    principal = Principal(id="user-xyz", type="user", auth_method="jwt")
    req = _make_request_with_principal(principal)
    assert await get_current_principal(req) is principal
    req2 = _make_request_with_principal(None)
    assert await get_current_principal(req2) is None


@pytest.mark.asyncio
async def test_require_admin_principal_accepts_admin_roles() -> None:
    """require_admin_principal allows principals with admin role metadata."""
    principal = Principal(
        id="admin-1",
        type="user",
        auth_method="jwt",
        metadata={"role": "admin"},
    )
    req = _make_request_with_principal(principal)
    result = await require_admin_principal(req)
    assert result.id == "admin-1"


@pytest.mark.asyncio
async def test_require_admin_principal_rejects_non_admin_users() -> None:
    """Non-admin principals should trigger CoreAuthorizationError."""
    principal = Principal(
        id="user-1",
        type="user",
        auth_method="jwt",
        metadata={"role": "editor"},
    )
    req = _make_request_with_principal(principal)
    with pytest.raises(CoreAuthorizationError):
        await require_admin_principal(req)


@pytest.mark.asyncio
async def test_require_admin_principal_rejects_agents() -> None:
    """API key principals (agents) should not satisfy admin requirements."""
    principal = Principal(
        id="agent-openai",
        type="agent",
        service="openai",
        auth_method="api_key",
        metadata={"service": "openai"},
    )
    req = _make_request_with_principal(principal)
    with pytest.raises(CoreAuthorizationError):
        await require_admin_principal(req)
