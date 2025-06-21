"""Chat API schemas using Pydantic V2.

This module defines Pydantic models for chat-related API requests and responses.
Consolidates both request and response schemas for chat operations.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from tripsage_core.models.schemas_common.chat import ChatMessage, ToolCall

# ===== Request Schemas =====


class ChatRequest(BaseModel):
    """Chat API request."""

    messages: list[ChatMessage] = Field(..., description="Chat messages")
    session_id: Optional[UUID] = Field(None, description="Session ID for context")
    stream: bool = Field(True, description="Whether to stream the response")
    save_history: bool = Field(True, description="Whether to save chat history")
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0, description="Model temperature")
    max_tokens: Optional[int] = Field(None, ge=1, le=4096, description="Maximum tokens to generate")
    tools: Optional[list[str]] = Field(None, description="Specific tools to enable for this request")


class SessionCreateRequest(BaseModel):
    """Request model for creating a new chat session."""

    title: str = Field(..., description="Session title")
    metadata: Optional[dict] = Field(None, description="Session metadata")


class CreateMessageRequest(BaseModel):
    """Request model for creating a message in a session."""

    content: str = Field(..., description="Message content")
    role: str = Field(default="user", description="Message role")


# ===== Response Schemas =====


class ChatResponse(BaseModel):
    """Chat API response for non-streaming requests."""

    id: UUID = Field(default_factory=uuid4, description="Response ID")
    session_id: Optional[UUID] = Field(None, description="Session ID")
    content: str = Field(..., description="Response content")
    tool_calls: Optional[List[ToolCall]] = Field(None, description="Tool calls made")
    finish_reason: str = Field("stop", description="Finish reason")
    usage: Optional[Dict[str, int]] = Field(None, description="Token usage information")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")


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
