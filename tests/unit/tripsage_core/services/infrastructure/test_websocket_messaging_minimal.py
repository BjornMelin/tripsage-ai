"""Minimal tests for WebSocket messaging event model."""

from tripsage_core.services.infrastructure.websocket_messaging_service import (
    WebSocketEvent,
    WebSocketEventType,
)


def test_websocket_event_to_dict_serialization() -> None:
    """WebSocketEvent serializes to a dict with ISO timestamps."""
    ev = WebSocketEvent(type=WebSocketEventType.MESSAGE_SENT, payload={"x": 1})
    data = ev.to_dict()
    assert data["type"] == WebSocketEventType.MESSAGE_SENT
    assert isinstance(data["timestamp"], str)
    assert data["payload"] == {"x": 1}
