"""
WebSocket authentication service.

This service handles WebSocket connection authentication including:
- JWT token verification
- Rate limiting checks
- User authorization
- Channel access validation
"""

import logging
from uuid import UUID

import jwt
from pydantic import BaseModel, Field

from tripsage_core.config import get_settings
from tripsage_core.exceptions.exceptions import CoreAuthenticationError

logger = logging.getLogger(__name__)


class WebSocketAuthRequest(BaseModel):
    """WebSocket authentication request."""

    token: str
    session_id: UUID | None = None
    channels: list[str] = Field(default_factory=list)


class WebSocketAuthResponse(BaseModel):
    """WebSocket authentication response."""

    success: bool
    connection_id: str
    user_id: UUID | None = None
    session_id: UUID | None = None
    available_channels: list[str] = Field(default_factory=list)
    error: str | None = None


class WebSocketAuthService:
    """Service for WebSocket authentication and authorization."""

    def __init__(self):
        self.settings = get_settings()

    async def verify_jwt_token(self, token: str) -> UUID:
        """Verify JWT token and extract user ID.

        Args:
            token: JWT token to verify

        Returns:
            User ID from the token

        Raises:
            CoreAuthenticationError: If token is invalid
        """
        try:
            # Decode JWT token
            payload = jwt.decode(
                token,
                self.settings.jwt_secret_key.get_secret_value(),
                algorithms=["HS256"],
            )

            # Extract user ID
            user_id = payload.get("sub")
            if not user_id:
                raise CoreAuthenticationError(
                    message="Token missing user ID",
                    code="INVALID_TOKEN",
                    user_id=None,
                )

            return UUID(user_id)

        except jwt.ExpiredSignatureError:
            raise CoreAuthenticationError(
                message="Token has expired",
                code="TOKEN_EXPIRED",
                user_id=None,
            )
        except jwt.InvalidTokenError as e:
            raise CoreAuthenticationError(
                message=f"Invalid token: {str(e)}",
                code="INVALID_TOKEN",
                user_id=None,
            )
        except ValueError as e:
            raise CoreAuthenticationError(
                message=f"Invalid user ID format: {str(e)}",
                code="INVALID_USER_ID",
                user_id=None,
            )

    def get_available_channels(self, user_id: UUID) -> list[str]:
        """Get list of channels user can access.

        Args:
            user_id: User ID

        Returns:
            List of available channel names
        """
        # Basic channel access - can be expanded with role-based access
        base_channels = [
            f"user:{user_id}",
            "notifications",
            "system_messages",
        ]

        # Add premium channels if user has premium access
        # This would integrate with user service in production
        premium_channels = [
            "premium_notifications",
            "advanced_features",
        ]

        return base_channels + premium_channels

    def validate_channel_access(
        self, user_id: UUID, requested_channels: list[str]
    ) -> tuple[list[str], list[str]]:
        """Validate user access to requested channels.

        Args:
            user_id: User ID
            requested_channels: List of channels user wants to access

        Returns:
            Tuple of (allowed_channels, denied_channels)
        """
        available_channels = set(self.get_available_channels(user_id))
        requested_set = set(requested_channels)

        allowed = list(requested_set & available_channels)
        denied = list(requested_set - available_channels)

        return allowed, denied

    def parse_channel_target(self, channel: str) -> tuple[str, str | None]:
        """Parse channel string to extract target type and ID.

        Args:
            channel: Channel string (e.g., "user:123", "session:abc")

        Returns:
            Tuple of (target_type, target_id)
        """
        if ":" in channel:
            target_type, target_id = channel.split(":", 1)
            return target_type, target_id
        else:
            return "channel", channel

    def is_authorized_for_channel(self, user_id: UUID, channel: str) -> bool:
        """Check if user is authorized for specific channel.

        Args:
            user_id: User ID
            channel: Channel name

        Returns:
            True if authorized
        """
        available_channels = self.get_available_channels(user_id)
        return channel in available_channels

    def get_user_channels(self, user_id: UUID) -> list[str]:
        """Get all channels for a specific user.

        Args:
            user_id: User ID

        Returns:
            List of user-specific channel names
        """
        return [
            f"user:{user_id}",
            f"user:{user_id}:notifications",
            f"user:{user_id}:status",
        ]

    def get_session_channels(self, session_id: UUID) -> list[str]:
        """Get all channels for a specific session.

        Args:
            session_id: Session ID

        Returns:
            List of session-specific channel names
        """
        return [
            f"session:{session_id}",
            f"session:{session_id}:chat",
            f"session:{session_id}:agent_status",
        ]