"""WebSocket response models for TripSage API.

This module provides Pydantic v2 response models for WebSocket communication.
"""

from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


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
