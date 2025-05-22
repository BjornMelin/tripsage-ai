"""Chat models for TripSage API.

This module defines the request and response models for chat functionality.
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


class ChatRequest(BaseModel):
    """Chat API request."""

    messages: list[ChatMessage] = Field(..., description="Chat messages")
    session_id: Optional[UUID] = Field(None, description="Session ID for context")
    stream: bool = Field(True, description="Whether to stream the response")
    temperature: Optional[float] = Field(
        None, ge=0.0, le=2.0, description="Model temperature"
    )
    max_tokens: Optional[int] = Field(
        None, ge=1, le=4096, description="Maximum tokens to generate"
    )
    tools: Optional[list[str]] = Field(
        None, description="Specific tools to enable for this request"
    )


class ChatResponse(BaseModel):
    """Chat API response for non-streaming requests."""

    id: UUID = Field(default_factory=uuid4, description="Response ID")
    session_id: Optional[UUID] = Field(None, description="Session ID")
    content: str = Field(..., description="Response content")
    tool_calls: Optional[list[ToolCall]] = Field(None, description="Tool calls made")
    finish_reason: str = Field("stop", description="Finish reason")
    usage: Optional[dict[str, int]] = Field(None, description="Token usage information")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Response timestamp"
    )


class ChatStreamChunk(BaseModel):
    """Individual chunk in a streaming response."""

    type: str = Field(..., description="Chunk type")
    content: str = Field(..., description="Chunk content")
    metadata: Optional[dict[str, Any]] = Field(None, description="Chunk metadata")


class SessionHistoryResponse(BaseModel):
    """Response for session history request."""

    session_id: UUID = Field(..., description="Session ID")
    messages: list[ChatMessage] = Field(..., description="Session messages")
    created_at: Optional[datetime] = Field(None, description="Session creation time")
    updated_at: Optional[datetime] = Field(None, description="Last update time")
    metadata: Optional[dict[str, Any]] = Field(None, description="Session metadata")
