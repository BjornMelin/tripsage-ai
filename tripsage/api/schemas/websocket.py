"""WebSocket API schemas using Pydantic V2.

This module defines Pydantic models for WebSocket-related API requests and responses.
Consolidates both request and response schemas for WebSocket operations.
"""

from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

# ===== Request Schemas =====


class WebSocketAuthRequest(BaseModel):
    """WebSocket authentication request."""

    token: str = Field(..., description="JWT authentication token")
    session_id: Optional[UUID] = Field(None, description="Optional session ID to join")
    channels: List[str] = Field(
        default_factory=list, description="Channels to subscribe to"
    )


class WebSocketSubscribeRequest(BaseModel):
    """WebSocket channel subscription request."""

    channels: List[str] = Field(..., description="Channels to subscribe to")
    unsubscribe_channels: List[str] = Field(
        default_factory=list, description="Channels to unsubscribe from"
    )


# ===== Response Schemas =====


class WebSocketAuthResponse(BaseModel):
    """WebSocket authentication response."""

    success: bool = Field(..., description="Authentication success")
    connection_id: str = Field(..., description="Connection ID")
    user_id: Optional[UUID] = Field(None, description="Authenticated user ID")
    session_id: Optional[UUID] = Field(None, description="Session ID")
    error: Optional[str] = Field(
        None, description="Error message if authentication failed"
    )
    available_channels: List[str] = Field(
        default_factory=list, description="Available channels"
    )


class WebSocketSubscribeResponse(BaseModel):
    """WebSocket channel subscription response."""

    success: bool = Field(..., description="Subscription success")
    subscribed_channels: List[str] = Field(
        default_factory=list, description="Successfully subscribed channels"
    )
    failed_channels: List[str] = Field(
        default_factory=list, description="Failed subscription channels"
    )
    error: Optional[str] = Field(None, description="Error message")
