"""Common chat models for TripSage API.

This module defines the common/domain models for chat functionality.
"""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


class ChatMessage(BaseModel):
    """Individual chat message."""

    role: str = Field(..., description="Message role (user/assistant/system)")
    content: str = Field(..., description="Message content")
    timestamp: Optional[datetime] = Field(None, description="Message timestamp")
    metadata: Optional[dict[str, Any]] = Field(None, description="Additional metadata")

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        """Validate message role."""
        valid_roles = {"user", "assistant", "system"}
        if v not in valid_roles:
            raise ValueError(f"Role must be one of {valid_roles}")
        return v


class ChatSession(BaseModel):
    """Chat session information."""

    id: UUID = Field(default_factory=uuid4, description="Session ID")
    user_id: str = Field(..., description="User ID")
    messages: list[ChatMessage] = Field(default_factory=list, description="Messages")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow, description="Last update timestamp"
    )
    metadata: Optional[dict[str, Any]] = Field(None, description="Session metadata")


class ToolCall(BaseModel):
    """Tool call information."""

    id: str = Field(..., description="Tool call ID")
    name: str = Field(..., description="Tool name")
    args: dict[str, Any] = Field(..., description="Tool arguments")
    result: Optional[Any] = Field(None, description="Tool result")
