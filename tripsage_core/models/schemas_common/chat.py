"""Common chat models for TripSage.

This module provides shared chat models used across API layers,
services, and core business logic.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, BeforeValidator, Field
from typing_extensions import Annotated


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
def ensure_dict(v: Any) -> Dict[str, Any]:
    """Ensure value is a dictionary."""
    if v is None:
        return {}
    if isinstance(v, dict):
        return v
    return {}


DictOrEmpty = Annotated[Dict[str, Any], BeforeValidator(ensure_dict)]


class ToolCall(BaseModel):
    """Common model for tool calls in chat messages."""

    id: str = Field(..., description="Unique identifier for the tool call")
    name: str = Field(..., description="Name of the tool")
    arguments: DictOrEmpty = Field(default_factory=dict, description="Tool arguments")
    result: Optional[DictOrEmpty] = Field(None, description="Tool result")
    status: ToolCallStatus = Field(
        ToolCallStatus.PENDING, description="Tool call status"
    )
    error: Optional[str] = Field(None, description="Error message if failed")


class ChatMessage(BaseModel):
    """Common model for chat messages."""

    role: MessageRole = Field(..., description="Message role (user/assistant/system)")
    content: str = Field(..., description="Message content", max_length=32768)
    tool_calls: Optional[List[ToolCall]] = Field(None, description="Tool calls made")
    timestamp: Optional[datetime] = Field(None, description="Message timestamp")
    metadata: Optional[DictOrEmpty] = Field(None, description="Message metadata")


class ChatSession(BaseModel):
    """Common model for chat sessions."""

    id: str = Field(..., description="Session ID")
    user_id: Optional[int] = Field(None, description="User ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    metadata: DictOrEmpty = Field(default_factory=dict, description="Session metadata")


class ChatContext(BaseModel):
    """Common model for chat context and memory."""

    session_id: str = Field(..., description="Session ID")
    messages: List[ChatMessage] = Field(
        default_factory=list, description="Conversation messages"
    )
    system_prompt: Optional[str] = Field(None, description="System prompt")
    temperature: Optional[float] = Field(
        None, description="Model temperature", ge=0, le=2
    )
    max_tokens: Optional[int] = Field(None, description="Maximum tokens", gt=0)
    tools: Optional[List[str]] = Field(None, description="Available tools")
