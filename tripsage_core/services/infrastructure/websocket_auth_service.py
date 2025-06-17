"""
WebSocket authentication service.

This service handles WebSocket connection authentication including:
- JWT token verification
- Rate limiting checks
- User authorization
- Channel access validation
"""

import logging
from typing import List, Optional
from uuid import UUID

import jwt
from pydantic import BaseModel, Field

from tripsage_core.config import get_settings
from tripsage_core.exceptions.exceptions import CoreAuthenticationError

logger = logging.getLogger(__name__)


class WebSocketAuthRequest(BaseModel):
    """WebSocket authentication request."""

    token: str
    session_id: Optional[UUID] = None
    channels: List[str] = Field(default_factory=list)


class WebSocketAuthResponse(BaseModel):
    """WebSocket authentication response."""

    success: bool
    connection_id: str
    user_id: Optional[UUID] = None
    session_id: Optional[UUID] = None
    available_channels: List[str] = Field(default_factory=list)
    error: Optional[str] = None


class WebSocketAuthService:
    """Service for WebSocket authentication and authorization."""

    def __init__(self):
        self.settings = get_settings()

    async def verify_jwt_token(self, token: str) -> UUID:
        """Verify JWT token and extract user ID.

        Args:
            token: JWT token to verify

        Returns:
            User ID from token

        Raises:
            CoreAuthenticationError: If token is invalid
        """
        try:
            payload = jwt.decode(
                token,
                self.settings.jwt_secret_key.get_secret_value(),
                algorithms=["HS256"],
            )

            if "sub" not in payload or "user_id" not in payload:
                raise CoreAuthenticationError(
                    message="Invalid token payload",
                    details={"reason": "Missing required fields"},
                )

            return UUID(payload["user_id"])
        except jwt.InvalidTokenError as e:
            raise CoreAuthenticationError(
                message="Invalid token",
                details={"reason": str(e)},
            ) from e

    def get_available_channels(self, user_id: UUID) -> List[str]:
        """Get available channels for a user.

        Args:
            user_id: User ID

        Returns:
            List of available channels
        """
        if not user_id:
            return []

        # Base channels available to all authenticated users
        channels = [
            "general",
            "notifications",
            f"user:{user_id}",
            f"agent_status:{user_id}",
        ]

        return channels

    def validate_channel_access(
        self, user_id: UUID, channels: List[str]
    ) -> tuple[List[str], List[str]]:
        """Validate user access to requested channels.

        Args:
            user_id: User ID
            channels: Requested channels

        Returns:
            Tuple of (allowed_channels, denied_channels)
        """
        available_channels = self.get_available_channels(user_id)
        allowed = []
        denied = []

        for channel in channels:
            if channel in available_channels:
                allowed.append(channel)
            else:
                denied.append(channel)

        return allowed, denied

    def parse_channel_target(self, channel: str) -> tuple[str, Optional[str]]:
        """Parse channel string to extract target type and ID.

        Centralized channel parsing logic to address code review comment.

        Args:
            channel: Channel string (e.g., "user:123", "session:456", "agent_status"...)

        Returns:
            Tuple of (target_type, target_id)
        """
        if ":" not in channel:
            return "channel", channel

        parts = channel.split(":", 1)
        if len(parts) == 2:
            target_type, target_id = parts
            if target_type in ["user", "session", "agent_status"]:
                return target_type, target_id

        return "channel", channel
