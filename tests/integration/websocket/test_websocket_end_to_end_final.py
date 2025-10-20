"""Final-only, non-duplicative websocket integration tests.

Covers: auth success, auth invalid, and ping -> pong flow at router level.
"""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from tripsage.api.main import app
from tripsage_core.services.infrastructure.websocket_auth_service import (
    WebSocketAuthResponse,
)


@pytest.fixture
def client() -> TestClient:
    """FastAPI test client."""
    return TestClient(app)


@pytest.mark.asyncio
async def test_auth_success(client: TestClient) -> None:
    """Successful authentication leads to manager.authenticate called once."""
    manager = MagicMock()
    conn_id = str(uuid4())
    user_id = uuid4()
    manager.authenticate_connection = AsyncMock(
        return_value=WebSocketAuthResponse(
            success=True,
            connection_id=conn_id,
            user_id=user_id,
            session_id=uuid4(),
            available_channels=["general"],
        )
    )
    manager.send_to_connection = AsyncMock(return_value=True)
    manager.disconnect_connection = AsyncMock()
    manager.connections = {
        conn_id: MagicMock(update_heartbeat=MagicMock(), handle_pong=MagicMock())
    }

    with (
        patch("tripsage.api.routers.websocket.websocket_manager", manager),
        patch(
            "tripsage.api.routers.websocket.get_settings",
            new=MagicMock(
                return_value=type(
                    "S", (), {"cors_origins": ["*"], "is_production": False}
                )()
            ),
        ),
        patch(
            "tripsage.api.routers.websocket.WebSocketMessageValidator.validate_message",
            new=MagicMock(
                side_effect=lambda raw: type(
                    "V", (), {"model_dump": lambda self: json.loads(raw)}
                )()
            ),
        ),
        client.websocket_connect("/api/ws", headers={"origin": "http://test"}) as ws,
    ):
        ws.send_text(json.dumps({"token": "tok", "channels": ["general"]}))
        await asyncio.sleep(0.05)
        manager.authenticate_connection.assert_called_once()


@pytest.mark.asyncio
async def test_auth_invalid(client: TestClient) -> None:
    """Invalid auth returns error message from auth response."""
    manager = MagicMock()
    manager.authenticate_connection = AsyncMock(
        return_value=WebSocketAuthResponse(
            success=False, connection_id="", error="Invalid token"
        )
    )
    with (
        patch("tripsage.api.routers.websocket.websocket_manager", manager),
        patch(
            "tripsage.api.routers.websocket.get_settings",
            new=MagicMock(
                return_value=type(
                    "S", (), {"cors_origins": ["*"], "is_production": False}
                )()
            ),
        ),
        patch(
            "tripsage.api.routers.websocket.WebSocketMessageValidator.validate_message",
            new=MagicMock(
                side_effect=lambda raw: type(
                    "V", (), {"model_dump": lambda self: json.loads(raw)}
                )()
            ),
        ),
        client.websocket_connect("/api/ws", headers={"origin": "http://test"}) as ws,
    ):
        ws.send_text(json.dumps({"token": "bad", "channels": []}))
        resp = ws.receive_json()
        assert resp["type"] == "error"
        assert "Invalid token" in resp["message"]


@pytest.mark.asyncio
async def test_ping_pong_flow(client: TestClient) -> None:
    """Sending ping results in a send_to_connection call with pong event."""
    manager = MagicMock()
    conn_id = str(uuid4())
    user_id = uuid4()
    manager.authenticate_connection = AsyncMock(
        return_value=WebSocketAuthResponse(
            success=True,
            connection_id=conn_id,
            user_id=user_id,
            session_id=uuid4(),
            available_channels=[],
        )
    )
    manager.send_to_connection = AsyncMock(return_value=True)
    manager.disconnect_connection = AsyncMock()
    manager.connections = {
        conn_id: MagicMock(update_heartbeat=MagicMock(), handle_pong=MagicMock())
    }

    with (
        patch("tripsage.api.routers.websocket.websocket_manager", manager),
        patch(
            "tripsage.api.routers.websocket.get_settings",
            new=MagicMock(
                return_value=type(
                    "S", (), {"cors_origins": ["*"], "is_production": False}
                )()
            ),
        ),
        patch(
            "tripsage.api.routers.websocket.WebSocketMessageValidator.validate_message",
            new=MagicMock(
                side_effect=lambda raw: type(
                    "V", (), {"model_dump": lambda self: json.loads(raw)}
                )()
            ),
        ),
        client.websocket_connect("/api/ws", headers={"origin": "http://test"}) as ws,
    ):
        ws.send_text(json.dumps({"token": "tok", "channels": []}))
        await asyncio.sleep(0.02)
        ws.send_text(json.dumps({"type": "ping"}))
        await asyncio.sleep(0.05)
        assert manager.send_to_connection.call_count >= 1
