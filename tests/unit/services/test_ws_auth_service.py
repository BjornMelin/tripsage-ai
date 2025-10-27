"""Unit tests for WebSocketAuthService claims-first token verification."""

from typing import Any

import pytest

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
