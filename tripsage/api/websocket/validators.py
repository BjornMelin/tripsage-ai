"""Inbound WebSocket message validation helpers."""

from __future__ import annotations

from pydantic import BaseModel, ValidationError

from tripsage.api.websocket.exceptions import WebSocketMessageError
from tripsage_core.services.infrastructure.websocket_manager import (
    WebSocketMessageLimits,
)
from tripsage_core.services.infrastructure.websocket_validation import (
    WebSocketMessageValidator,
)


MESSAGE_LIMITS = WebSocketMessageLimits()


def validate_size(raw_message: str, *, message_type: str) -> None:
    """Ensure a raw message does not exceed configured limits."""
    limit = MESSAGE_LIMITS.get_limit_for_message_type(message_type)
    if not WebSocketMessageValidator.validate_message_size(raw_message, limit):
        raise WebSocketMessageError(
            f"Message exceeds maximum allowed size for type '{message_type}'"
        )


def parse_message(raw_message: str) -> BaseModel:
    """Parse and validate a JSON message into a Pydantic model."""
    try:
        return WebSocketMessageValidator.validate_message(raw_message)
    except (ValueError, ValidationError) as exc:  # pragma: no cover - wrapped
        raise WebSocketMessageError(str(exc)) from exc


def parse_and_validate(raw_message: str) -> tuple[str, BaseModel]:
    """Validate message size and return (type, model)."""
    model = parse_message(raw_message)
    message_type = getattr(model, "type", None)
    if message_type is None:
        raise WebSocketMessageError("Message payload missing type")

    validate_size(raw_message, message_type=str(message_type))
    return str(message_type), model
