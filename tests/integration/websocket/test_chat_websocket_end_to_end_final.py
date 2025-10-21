"""Final-only chat websocket integration tests (router level)."""

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


def _patch_settings_ok():
    """Patch settings to return valid settings."""
    return patch(
        "tripsage.api.routers.websocket.get_settings",
        new=MagicMock(
            return_value=type(
                "S", (), {"cors_origins": ["*"], "is_production": False}
            )()
        ),
    )


def _patch_validator_passthrough():
    def _validator(raw: str):
        """Validator function."""
        data = json.loads(raw)
        return type("V", (), {"model_dump": lambda self: data})()

    return patch(
        "tripsage.api.routers.websocket.WebSocketMessageValidator.validate_message",
        new=MagicMock(side_effect=_validator),
    )


def _stub_chat_agent(response_text: str = "Hello world"):
    """Stub chat agent."""
    agent = MagicMock()
    agent.run = AsyncMock(return_value={"content": response_text})
    return agent


@pytest.mark.asyncio
async def test_chat_auth_and_message_flow(client: TestClient) -> None:
    """Authenticate on chat route and send a chat_message to trigger streaming sends."""
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
    manager.send_to_session = AsyncMock(return_value=1)
    manager.disconnect_connection = AsyncMock()
    manager.connections = {
        conn_id: MagicMock(update_heartbeat=MagicMock(), handle_pong=MagicMock())
    }

    chat_agent = _stub_chat_agent("This is a streamed response from agent")
    chat_service = MagicMock()
    chat_service.add_message = AsyncMock()

    with (
        patch("tripsage.api.routers.websocket.websocket_manager", manager),
        _patch_settings_ok(),
        _patch_validator_passthrough(),
        patch(
            "tripsage.api.routers.websocket.get_chat_agent",
            new=MagicMock(return_value=chat_agent),
        ),
        patch("tripsage.api.routers.websocket.chat_service", chat_service),
    ):
        # Use FastAPI dependency overrides to avoid DB and provide chat service
        from tripsage.api.routers import websocket as ws_mod

        async def _chat_service_override():
            return chat_service

        app.dependency_overrides[ws_mod.get_core_chat_service] = _chat_service_override
        try:
            session_id = str(uuid4())
            url = f"/api/ws/chat/{session_id}"
            with client.websocket_connect(url, headers={"origin": "http://test"}) as ws:
                ws.send_text(json.dumps({"token": "tok", "channels": []}))
                await asyncio.sleep(0.02)
                ws.send_text(
                    json.dumps(
                        {
                            "type": "chat_message",
                            "payload": {
                                "session_id": session_id,
                                "content": "Hello",
                            },
                        }
                    )
                )
                await asyncio.sleep(0.1)
                # Streaming via send_to_session should be invoked
                assert manager.send_to_session.call_count >= 2
        finally:
            app.dependency_overrides.pop(ws_mod.get_core_chat_service, None)


@pytest.mark.asyncio
async def test_chat_ping_pong(client: TestClient) -> None:
    """Test ping-pong flow on chat route."""
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
        _patch_settings_ok(),
        _patch_validator_passthrough(),
    ):
        from tripsage.api.routers import websocket as ws_mod

        async def _chat_service_override():
            return MagicMock()

        app.dependency_overrides[ws_mod.get_core_chat_service] = _chat_service_override
        try:
            session_id = str(uuid4())
            url = f"/api/ws/chat/{session_id}"
            with client.websocket_connect(url, headers={"origin": "http://test"}) as ws:
                ws.send_text(json.dumps({"token": "tok", "channels": []}))
                await asyncio.sleep(0.02)
                ws.send_text(json.dumps({"type": "ping"}))
                await asyncio.sleep(0.05)
                assert manager.send_to_connection.call_count >= 1
        finally:
            app.dependency_overrides.pop(ws_mod.get_core_chat_service, None)
