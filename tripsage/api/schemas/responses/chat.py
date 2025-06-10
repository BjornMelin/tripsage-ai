"""Chat response models for TripSage API.

This module defines the response models for chat functionality.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from tripsage_core.models.schemas_common.chat import ChatMessage, ToolCall


class ChatResponse(BaseModel):
    """Chat API response for non-streaming requests."""

    id: UUID = Field(default_factory=uuid4, description="Response ID")
    session_id: Optional[UUID] = Field(None, description="Session ID")
    content: str = Field(..., description="Response content")
    tool_calls: Optional[List[ToolCall]] = Field(None, description="Tool calls made")
    finish_reason: str = Field("stop", description="Finish reason")
    usage: Optional[Dict[str, int]] = Field(None, description="Token usage information")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Response timestamp"
    )


class ChatStreamChunk(BaseModel):
    """Individual chunk in a streaming response."""

    type: str = Field(..., description="Chunk type")
    content: str = Field(..., description="Chunk content")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Chunk metadata")


class SessionHistoryResponse(BaseModel):
    """Response for session history request."""

    session_id: UUID = Field(..., description="Session ID")
    messages: List[ChatMessage] = Field(..., description="Session messages")
    created_at: Optional[datetime] = Field(None, description="Session creation time")
    updated_at: Optional[datetime] = Field(None, description="Last update time")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Session metadata")
