"""Unit tests for principal-based auth dependencies."""

import pytest
from starlette.requests import Request

from tripsage.api.core.dependencies import (
    get_current_principal,
    get_principal_id,
    require_principal,
)
from tripsage.api.middlewares.authentication import Principal
from tripsage_core.exceptions.exceptions import CoreAuthenticationError


def _make_request_with_principal(principal: Principal | None) -> Request:
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
