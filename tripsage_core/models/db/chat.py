"""Database models for chat functionality.

These models represent the database schema for chat sessions and messages.
They are separate from the API models to maintain clean separation of concerns.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ChatSessionDB(BaseModel):
    """Database model for chat sessions."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Session ID")
    user_id: UUID = Field(..., description="User ID from auth.users table")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    ended_at: datetime | None = Field(None, description="Session end timestamp")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Session metadata"
    )

    @field_validator("metadata", mode="before")
    @classmethod
    def ensure_dict(cls, v: Any) -> dict[str, Any]:
        """Ensure metadata is a dictionary."""
        if v is None:
            return {}
        if isinstance(v, dict):
            return v
        return {}


class ChatMessageDB(BaseModel):
    """Database model for chat messages."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Message ID")
    session_id: UUID = Field(..., description="Session ID")
    role: str = Field(..., description="Message role (user/assistant/system)")
    content: str = Field(..., description="Message content")
    created_at: datetime = Field(..., description="Creation timestamp")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Message metadata"
    )

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        """Validate message role."""
        valid_roles = {"user", "assistant", "system"}
        if v not in valid_roles:
            raise ValueError(f"Role must be one of {valid_roles}")
        return v

    @field_validator("content")
    @classmethod
    def validate_content_length(cls, v: str) -> str:
        """Validate content length (32KB limit)."""
        if len(v) > 32768:
            raise ValueError("Message content exceeds 32KB limit")
        return v

    @field_validator("metadata", mode="before")
    @classmethod
    def ensure_dict(cls, v: Any) -> dict[str, Any]:
        """Ensure metadata is a dictionary."""
        if v is None:
            return {}
        if isinstance(v, dict):
            return v
        return {}


class ChatToolCallDB(BaseModel):
    """Database model for tool calls within chat messages."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Tool call database ID")
    message_id: int = Field(..., description="Message ID that triggered this tool call")
    tool_id: str = Field(
        ..., description="Unique identifier for this tool call instance"
    )
    tool_name: str = Field(..., description="Name of the tool")
    arguments: dict[str, Any] = Field(
        default_factory=dict, description="Tool arguments"
    )
    result: dict[str, Any] | None = Field(None, description="Tool result")
    status: str = Field("pending", description="Tool call status")
    created_at: datetime = Field(..., description="Creation timestamp")
    completed_at: datetime | None = Field(None, description="Completion timestamp")
    error_message: str | None = Field(None, description="Error message if failed")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        """Validate tool call status."""
        valid_statuses = {"pending", "running", "completed", "failed"}
        if v not in valid_statuses:
            raise ValueError(f"Status must be one of {valid_statuses}")
        return v

    @field_validator("arguments", mode="before")
    @classmethod
    def ensure_dict_args(cls, v: Any) -> dict[str, Any]:
        """Ensure arguments is a dictionary."""
        if v is None:
            return {}
        if isinstance(v, dict):
            return v
        return {}


class ChatSessionWithStats(ChatSessionDB):
    """Chat session with additional statistics."""

    message_count: int = Field(0, description="Total messages in session")
    last_message_at: datetime | None = Field(
        None, description="Timestamp of last message"
    )


class MessageWithTokenEstimate(ChatMessageDB):
    """Chat message with token estimation."""

    estimated_tokens: int = Field(..., description="Estimated token count")


# Response models for queries
class RecentMessagesResponse(BaseModel):
    """Response for recent messages query."""

    messages: list[MessageWithTokenEstimate] = Field(
        ..., description="Recent messages within token limit"
    )
    total_tokens: int = Field(..., description="Total estimated tokens")
    truncated: bool = Field(
        False, description="Whether messages were truncated due to token limit"
    )
