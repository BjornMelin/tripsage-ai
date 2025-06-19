"""WebSocket API schemas using Pydantic V2.

This module defines Pydantic models for WebSocket-related API requests and responses.
Consolidates both request and response schemas for WebSocket operations.
"""

from uuid import UUID

from pydantic import BaseModel, Field

# ===== Request Schemas =====


class WebSocketAuthRequest(BaseModel):
    """WebSocket authentication request."""

    token: str = Field(..., description="JWT authentication token")
    session_id: UUID | None = Field(None, description="Optional session ID to join")
    channels: list[str] = Field(
        default_factory=list, description="Channels to subscribe to"
    )


class WebSocketSubscribeRequest(BaseModel):
    """WebSocket channel subscription request."""

    channels: list[str] = Field(..., description="Channels to subscribe to")
    unsubscribe_channels: list[str] = Field(
        default_factory=list, description="Channels to unsubscribe from"
    )


# ===== Response Schemas =====


class WebSocketAuthResponse(BaseModel):
    """WebSocket authentication response."""

    success: bool = Field(..., description="Authentication success")
    connection_id: str = Field(..., description="Connection ID")
    user_id: UUID | None = Field(None, description="Authenticated user ID")
    session_id: UUID | None = Field(None, description="Session ID")
    error: str | None = Field(
        None, description="Error message if authentication failed"
    )
    available_channels: list[str] = Field(
        default_factory=list, description="Available channels"
    )


class WebSocketSubscribeResponse(BaseModel):
    """WebSocket channel subscription response."""

    success: bool = Field(..., description="Subscription success")
    subscribed_channels: list[str] = Field(
        default_factory=list, description="Successfully subscribed channels"
    )
    failed_channels: list[str] = Field(
        default_factory=list, description="Failed subscription channels"
    )
    error: str | None = Field(None, description="Error message")
