"""Common chat models for TripSage.

This module provides shared chat models used across API layers,
services, and core business logic.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, BeforeValidator, Field
from typing import Annotated

class ToolCallStatus(str, Enum):
    """Valid tool call statuses."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class MessageRole(str, Enum):
    """Valid message roles."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"

# Custom validators for chat models
def ensure_dict(v: Any) -> dict[str, Any]:
    """Ensure value is a dictionary."""
    if v is None:
        return {}
    if isinstance(v, dict):
        return v
    return {}

DictOrEmpty = Annotated[dict[str, Any], BeforeValidator(ensure_dict)]

class ToolCall(BaseModel):
    """Common model for tool calls in chat messages."""

    id: str = Field(..., description="Unique identifier for the tool call")
    name: str = Field(..., description="Name of the tool")
    arguments: DictOrEmpty = Field(default_factory=dict, description="Tool arguments")
    result: DictOrEmpty | None = Field(None, description="Tool result")
    status: ToolCallStatus = Field(
        ToolCallStatus.PENDING, description="Tool call status"
    )
    error: str | None = Field(None, description="Error message if failed")

class ChatMessage(BaseModel):
    """Common model for chat messages."""

    role: MessageRole = Field(..., description="Message role (user/assistant/system)")
    content: str = Field(..., description="Message content", max_length=32768)
    tool_calls: list[ToolCall] | None = Field(None, description="Tool calls made")
    timestamp: datetime | None = Field(None, description="Message timestamp")
    metadata: DictOrEmpty | None = Field(None, description="Message metadata")

class ChatSession(BaseModel):
    """Common model for chat sessions."""

    id: str = Field(..., description="Session ID")
    user_id: int | None = Field(None, description="User ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    metadata: DictOrEmpty = Field(default_factory=dict, description="Session metadata")

class ChatContext(BaseModel):
    """Common model for chat context and memory."""

    session_id: str = Field(..., description="Session ID")
    messages: list[ChatMessage] = Field(
        default_factory=list, description="Conversation messages"
    )
    system_prompt: str | None = Field(None, description="System prompt")
    temperature: float | None = Field(
        None, description="Model temperature", ge=0, le=2
    )
    max_tokens: int | None = Field(None, description="Maximum tokens", gt=0)
    tools: list[str] | None = Field(None, description="Available tools")
