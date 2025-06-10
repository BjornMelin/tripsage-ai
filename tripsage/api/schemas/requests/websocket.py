"""WebSocket request models for TripSage API.

This module provides Pydantic v2 request models for WebSocket communication.
"""

from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


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
