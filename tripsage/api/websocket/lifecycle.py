"""Connection lifecycle utilities for the TripSage WebSocket router."""

from __future__ import annotations

import logging
from collections.abc import Iterable
from urllib.parse import urlparse
from uuid import UUID

from fastapi import WebSocket

from tripsage.api.core.config import Settings
from tripsage.api.websocket.context import ConnectionContext
from tripsage.api.websocket.exceptions import (
    WebSocketAuthenticationError,
    WebSocketOriginError,
)
from tripsage.api.websocket.validators import parse_and_validate
from tripsage_core.services.infrastructure.websocket_auth_service import (
    WebSocketAuthRequest,
    WebSocketAuthResponse,
)
from tripsage_core.services.infrastructure.websocket_connection_service import (
    WebSocketConnection,
)
from tripsage_core.services.infrastructure.websocket_manager import WebSocketManager
from tripsage_core.services.infrastructure.websocket_validation import (
    WebSocketAuthMessage,
)


logger = logging.getLogger(__name__)


def ensure_origin_allowed(websocket: WebSocket, settings: Settings) -> None:
    """Validate the Origin header according to configured CORS policy.

    Args:
        websocket: Incoming WebSocket connection.
        settings: Application settings providing CORS configuration.

    Raises:
        WebSocketOriginError: If the origin is invalid for the current request.
    """
    origin = websocket.headers.get("origin")

    if origin is None:
        if settings.is_production:
            raise WebSocketOriginError("Origin header required in production")
        logger.warning("WebSocket connection without Origin header accepted in dev")
        return

    parsed = urlparse(origin)
    if not parsed.scheme or not parsed.hostname:
        raise WebSocketOriginError("Malformed origin header")

    try:
        hostname_ascii = parsed.hostname.lower().encode("idna").decode("ascii")
    except UnicodeError as exc:
        raise WebSocketOriginError(
            "Origin hostname contains invalid characters"
        ) from exc

    canonical = f"{parsed.scheme.lower()}://{hostname_ascii}"
    if parsed.port:
        canonical = f"{canonical}:{parsed.port}"

    allowed = {
        normalize_origin(allowed_origin)
        for allowed_origin in settings.cors_origins
        if allowed_origin != "*"
    }

    if "*" in settings.cors_origins:
        # Explicit wildcard override - warn once for observability.
        logger.warning("CORS wildcard enabled for WebSocket connections")
        return

    if canonical not in allowed:
        raise WebSocketOriginError("Origin not permitted")


def normalize_origin(origin: str) -> str:
    """Return a canonical representation of an origin string."""
    parsed = urlparse(origin)
    if not parsed.scheme or not parsed.hostname:
        return ""
    try:
        hostname_ascii = parsed.hostname.lower().encode("idna").decode("ascii")
    except UnicodeError:
        return ""
    canonical = f"{parsed.scheme.lower()}://{hostname_ascii}"
    if parsed.port:
        canonical = f"{canonical}:{parsed.port}"
    return canonical


async def establish_connection(
    websocket: WebSocket,
    *,
    manager: WebSocketManager,
    settings: Settings,
    default_channels: Iterable[str] | None = None,
    enforce_session_id: UUID | None = None,
) -> tuple[ConnectionContext, WebSocketAuthResponse]:
    """Perform the WebSocket handshake and authenticate the connection."""
    ensure_origin_allowed(websocket, settings)
    await websocket.accept()

    raw_auth = await websocket.receive_text()
    message_type, model = parse_and_validate(raw_auth)
    if message_type not in {"auth", "authentication"}:
        raise WebSocketAuthenticationError("Authentication payload required")
    if not isinstance(model, WebSocketAuthMessage):
        raise WebSocketAuthenticationError("Unexpected authentication payload")

    channels = list(model.channels or [])
    if default_channels:
        channels.extend(ch for ch in default_channels if ch not in channels)

    session_id = model.session_id
    if enforce_session_id and session_id and session_id != enforce_session_id:
        raise WebSocketAuthenticationError("Session identifier mismatch")
    if enforce_session_id:
        session_id = enforce_session_id

    auth_request = WebSocketAuthRequest(
        token=model.token,
        session_id=session_id,
        channels=channels,
    )

    auth_response = await manager.authenticate_connection(websocket, auth_request)
    if not auth_response.success:
        raise WebSocketAuthenticationError(
            auth_response.error or "Authentication failed"
        )

    context = ConnectionContext(
        websocket=websocket,
        manager=manager,
        connection_id=auth_response.connection_id,
        user_id=auth_response.user_id,
        session_id=auth_response.session_id or session_id,
    )

    return context, auth_response


def format_auth_response(auth_response: WebSocketAuthResponse) -> dict[str, object]:
    """Convert authentication response to JSON-serialisable dictionary."""
    data = auth_response.model_dump()
    if data.get("user_id") is not None:
        data["user_id"] = str(data["user_id"])
    if data.get("session_id") is not None:
        data["session_id"] = str(data["session_id"])
    return data


def serialize_connection(connection: WebSocketConnection) -> dict[str, object]:
    """Return an API-friendly snapshot of a connection."""
    return {
        "connection_id": connection.connection_id,
        "user_id": str(connection.user_id) if connection.user_id else None,
        "session_id": str(connection.session_id) if connection.session_id else None,
        "state": getattr(connection.state, "value", str(connection.state)),
        "connected_at": connection.connected_at.isoformat()
        if connection.connected_at
        else None,
        "last_heartbeat": connection.last_heartbeat.isoformat()
        if connection.last_heartbeat
        else None,
        "subscribed_channels": sorted(connection.subscribed_channels),
        "client_ip": connection.client_ip,
        "user_agent": connection.user_agent,
    }
