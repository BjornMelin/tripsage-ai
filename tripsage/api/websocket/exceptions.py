"""WebSocket-specific exception hierarchy for the TripSage API."""

from __future__ import annotations

from tripsage_core.exceptions import CoreServiceError as ServiceError


class WebSocketError(ServiceError):
    """Base class for WebSocket router errors."""


class WebSocketOriginError(WebSocketError):
    """Raised when an Origin header fails validation."""


class WebSocketAuthenticationError(WebSocketError):
    """Raised when authentication fails during the handshake."""


class WebSocketMessageError(WebSocketError):
    """Raised when an inbound message cannot be processed."""
