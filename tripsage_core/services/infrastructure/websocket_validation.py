"""Comprehensive Pydantic validation models for WebSocket messages.

This module provides security-focused validation for all WebSocket message types
to prevent injection vulnerabilities and ensure data integrity.
"""

import json
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator


class WebSocketMessageType(str, Enum):
    """Enumeration of valid WebSocket message types."""

    # Authentication messages
    AUTH = "auth"
    AUTHENTICATION = "authentication"

    # Connection management
    HEARTBEAT = "heartbeat"
    PING = "ping"
    PONG = "pong"
    CONNECT = "connect"
    DISCONNECT = "disconnect"

    # Chat messages
    CHAT_MESSAGE = "chat_message"
    CHAT_TYPING = "chat_typing"
    CHAT_TYPING_START = "chat_typing_start"
    CHAT_TYPING_STOP = "chat_typing_stop"
    CHAT_STATUS = "chat_status"

    # Subscription management
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"

    # Agent events
    AGENT_STATUS = "agent_status"
    AGENT_RESPONSE = "agent_response"
    AGENT_ERROR = "agent_error"

    # Error handling
    ERROR = "error"

    # Generic message
    MESSAGE = "message"

    # Echo for testing
    ECHO = "echo"


class WebSocketBaseMessage(BaseModel):
    """Base model for all WebSocket messages with security validation."""

    type: WebSocketMessageType = Field(..., description="Message type")
    timestamp: datetime | None = Field(
        default_factory=datetime.now, description="Message timestamp"
    )
    id: str | None = Field(None, max_length=128, description="Optional message ID")

    @field_validator("type")
    @classmethod
    def validate_message_type(cls, v):
        """Validate message type is allowed."""
        if isinstance(v, str) and v not in WebSocketMessageType.__members__.values():
            raise ValueError(f"Invalid message type: {v}")
        return v

    @field_validator("id")
    @classmethod
    def validate_message_id(cls, v):
        """Validate message ID format."""
        if v is not None:
            # Allow alphanumeric, hyphens, and underscores only
            if not v.replace("-", "").replace("_", "").isalnum():
                raise ValueError(
                    "Message ID must contain only alphanumeric characters, "
                    "hyphens, and underscores"
                )
        return v


class WebSocketAuthMessage(WebSocketBaseMessage):
    """Authentication message validation."""

    type: WebSocketMessageType = Field(
        default=WebSocketMessageType.AUTH, description="Message type"
    )
    token: str = Field(
        ..., min_length=1, max_length=4096, description="JWT authentication token"
    )
    session_id: UUID | None = Field(None, description="Optional session ID")
    channels: list[str] = Field(
        default_factory=list, max_items=50, description="Channels to subscribe to"
    )

    @field_validator("token")
    @classmethod
    def validate_token(cls, v):
        """Validate JWT token format."""
        if not v or not v.strip():
            raise ValueError("Token cannot be empty")
        # Basic JWT format validation (header.payload.signature)
        parts = v.split(".")
        if len(parts) != 3:
            raise ValueError("Invalid JWT token format")
        return v.strip()

    @field_validator("channels")
    @classmethod
    def validate_channels(cls, v):
        """Validate channel names."""
        if v:
            for channel in v:
                if not isinstance(channel, str):
                    raise ValueError("Channel names must be strings")
                if len(channel) > 100:
                    raise ValueError("Channel name too long")
                # Allow alphanumeric, colons, underscores, and hyphens only
                if not all(c.isalnum() or c in ":-_" for c in channel):
                    raise ValueError("Invalid characters in channel name")
        return v


class WebSocketHeartbeatMessage(WebSocketBaseMessage):
    """Heartbeat/ping/pong message validation."""

    type: WebSocketMessageType = Field(..., description="Message type")
    ping_id: str | None = Field(None, max_length=64, description="Ping identifier")
    payload: dict[str, Any] = Field(
        default_factory=dict, max_length=512, description="Heartbeat payload"
    )

    @field_validator("type")
    @classmethod
    def validate_heartbeat_type(cls, v):
        """Validate heartbeat message type."""
        allowed_types = [
            WebSocketMessageType.HEARTBEAT,
            WebSocketMessageType.PING,
            WebSocketMessageType.PONG,
        ]
        if v not in allowed_types:
            raise ValueError(f"Invalid heartbeat message type: {v}")
        return v

    @field_validator("ping_id")
    @classmethod
    def validate_ping_id(cls, v):
        """Validate ping ID format."""
        if v is not None and not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError(
                "Ping ID must contain only alphanumeric characters, "
                "hyphens, and underscores"
            )
        return v


class WebSocketChatMessage(WebSocketBaseMessage):
    """Chat message validation."""

    type: WebSocketMessageType = Field(
        default=WebSocketMessageType.CHAT_MESSAGE, description="Message type"
    )
    content: str = Field(
        ..., min_length=1, max_length=32768, description="Message content"
    )  # 32KB max
    session_id: UUID = Field(..., description="Chat session ID")
    user_id: UUID | None = Field(None, description="User ID")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )

    @field_validator("content")
    @classmethod
    def validate_content(cls, v):
        """Validate message content."""
        if not v or not v.strip():
            raise ValueError("Message content cannot be empty")

        # Check for potential script injection
        dangerous_patterns = [
            "<script",
            "javascript:",
            "vbscript:",
            "onload=",
            "onerror=",
        ]
        content_lower = v.lower()
        for pattern in dangerous_patterns:
            if pattern in content_lower:
                raise ValueError(
                    "Message content contains potentially dangerous content"
                )

        return v.strip()

    @field_validator("metadata")
    @classmethod
    def validate_metadata(cls, v):
        """Validate metadata dictionary."""
        if v:
            # Limit metadata size
            if len(json.dumps(v)) > 2048:  # 2KB max for metadata
                raise ValueError("Metadata too large")
        return v


class WebSocketSubscribeMessage(WebSocketBaseMessage):
    """Channel subscription message validation."""

    type: WebSocketMessageType = Field(
        default=WebSocketMessageType.SUBSCRIBE, description="Message type"
    )
    channels: list[str] = Field(
        default_factory=list, max_items=20, description="Channels to subscribe to"
    )
    unsubscribe_channels: list[str] = Field(
        default_factory=list, max_items=20, description="Channels to unsubscribe from"
    )

    @field_validator("channels", "unsubscribe_channels")
    @classmethod
    def validate_channel_lists(cls, v):
        """Validate channel name lists."""
        if v:
            for channel in v:
                if not isinstance(channel, str):
                    raise ValueError("Channel names must be strings")
                if len(channel) > 100:
                    raise ValueError("Channel name too long")
                # Allow alphanumeric, colons, underscores, and hyphens only
                if not all(c.isalnum() or c in ":-_" for c in channel):
                    raise ValueError("Invalid characters in channel name")
        return v

    @model_validator(mode="after")
    def validate_subscription_request(self):
        """Validate subscription request has valid data."""
        channels = getattr(self, "channels", [])
        unsubscribe_channels = getattr(self, "unsubscribe_channels", [])

        if not channels and not unsubscribe_channels:
            raise ValueError(
                "Must specify channels to subscribe to or unsubscribe from"
            )

        return self


class WebSocketErrorMessage(WebSocketBaseMessage):
    """Error message validation."""

    type: WebSocketMessageType = Field(
        default=WebSocketMessageType.ERROR, description="Message type"
    )
    error_code: str = Field(..., max_length=50, description="Error code")
    error_message: str = Field(..., max_length=1024, description="Error message")
    details: dict[str, Any] | None = Field(None, description="Additional error details")

    @field_validator("error_code")
    @classmethod
    def validate_error_code(cls, v):
        """Validate error code format."""
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError(
                "Error code must contain only alphanumeric characters, "
                "hyphens, and underscores"
            )
        return v.upper()


class WebSocketGenericMessage(WebSocketBaseMessage):
    """Generic message validation for any message type."""

    payload: dict[str, Any] = Field(default_factory=dict, description="Message payload")

    @field_validator("payload")
    @classmethod
    def validate_payload(cls, v):
        """Validate payload size and content."""
        if v:
            # Limit payload size
            payload_str = json.dumps(v, default=str)
            if len(payload_str) > 32768:  # 32KB max
                raise ValueError("Payload too large")
        return v


class WebSocketMessageValidator:
    """Validator class for WebSocket messages with automatic type detection."""

    @staticmethod
    def validate_message(raw_message: str) -> BaseModel:
        """Validate raw WebSocket message and return appropriate Pydantic model.

        Args:
            raw_message: Raw JSON message string

        Returns:
            Validated Pydantic model instance

        Raises:
            ValueError: If message is invalid
            ValidationError: If Pydantic validation fails
        """
        try:
            # Parse JSON
            message_data = json.loads(raw_message)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {e}") from e

        # Get message type
        message_type = message_data.get("type")
        if not message_type:
            raise ValueError("Message must have a 'type' field")

        # Map message types to validation models
        type_models = {
            WebSocketMessageType.AUTH: WebSocketAuthMessage,
            WebSocketMessageType.AUTHENTICATION: WebSocketAuthMessage,
            WebSocketMessageType.HEARTBEAT: WebSocketHeartbeatMessage,
            WebSocketMessageType.PING: WebSocketHeartbeatMessage,
            WebSocketMessageType.PONG: WebSocketHeartbeatMessage,
            WebSocketMessageType.CHAT_MESSAGE: WebSocketChatMessage,
            WebSocketMessageType.SUBSCRIBE: WebSocketSubscribeMessage,
            WebSocketMessageType.UNSUBSCRIBE: WebSocketSubscribeMessage,
            WebSocketMessageType.ERROR: WebSocketErrorMessage,
        }

        # Get appropriate validation model
        if message_type in type_models:
            model_class = type_models[message_type]
        else:
            # Use generic validation for unknown message types
            model_class = WebSocketGenericMessage

        # Validate using appropriate model
        try:
            return model_class(**message_data)
        except Exception as e:
            raise ValueError(f"Message validation failed: {e}") from e

    @staticmethod
    def validate_message_size(raw_message: str, max_size: int = 65536) -> bool:
        """Validate message size.

        Args:
            raw_message: Raw message string
            max_size: Maximum allowed size in bytes

        Returns:
            True if message size is valid
        """
        message_size = len(raw_message.encode("utf-8"))
        return message_size <= max_size

    @staticmethod
    def sanitize_message_content(content: str) -> str:
        """Sanitize message content to prevent XSS and injection attacks.

        Args:
            content: Raw content string

        Returns:
            Sanitized content string
        """
        # Basic HTML escaping
        content = content.replace("&", "&amp;")
        content = content.replace("<", "&lt;")
        content = content.replace(">", "&gt;")
        content = content.replace('"', "&quot;")
        content = content.replace("'", "&#x27;")

        # Remove potential script content
        dangerous_patterns = [
            "javascript:",
            "vbscript:",
            "data:text/html",
            "data:application",
        ]

        content_lower = content.lower()
        for pattern in dangerous_patterns:
            if pattern in content_lower:
                # Replace dangerous content with safe placeholder
                content = content.replace(pattern, "[FILTERED]")

        return content.strip()
