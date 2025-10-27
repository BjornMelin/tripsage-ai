"""Unit tests for WebSocketAuthService claims-first token verification."""

from typing import Any
from uuid import UUID

import pytest

from tripsage_core.exceptions.exceptions import CoreAuthorizationError
from tripsage_core.services.infrastructure.websocket_auth_service import (
    WebSocketAuthService,
)


@pytest.mark.asyncio
async def test_authenticate_token_success(monkeypatch: Any) -> None:
    """Authenticate token returns valid payload and channels."""

    async def fake_verify(jwt: str):
        return {"sub": "11111111-1111-1111-1111-111111111111", "email": "a@b.com"}

    import tripsage_core.services.infrastructure.websocket_auth_service as was

    monkeypatch.setattr(was, "verify_and_get_claims", fake_verify)

    svc = WebSocketAuthService()
    result: dict[str, Any] = await svc.authenticate_token("token")  # type: ignore[reportUnknownMemberType]
    assert result["valid"] is True
    assert result["user_id"] == "11111111-1111-1111-1111-111111111111"
    assert "channels" in result


@pytest.mark.asyncio
async def test_verify_channel_access_denied_for_other_user() -> None:
    """Deny access when attempting to join another user's channel."""
    svc = WebSocketAuthService()
    user_id = "11111111-1111-1111-1111-111111111111"
    with pytest.raises(CoreAuthorizationError):
        await svc.verify_channel_access(user_id, "user:someone-else")


@pytest.mark.asyncio
async def test_verify_session_access_denies_by_default() -> None:
    """Deny session access until policy is implemented (secure default)."""
    svc = WebSocketAuthService()
    session_uuid = UUID("00000000-0000-0000-0000-000000000001")
    with pytest.raises(CoreAuthorizationError):
        await svc.verify_session_access("user-1", session_uuid, token=None)
