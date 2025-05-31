"""Chat request models for TripSage API.

This module defines the request models for chat functionality.
"""

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from ..common.chat import ChatMessage


class ChatRequest(BaseModel):
    """Chat API request."""

    messages: list[ChatMessage] = Field(..., description="Chat messages")
    session_id: Optional[UUID] = Field(None, description="Session ID for context")
    stream: bool = Field(True, description="Whether to stream the response")
    save_history: bool = Field(True, description="Whether to save chat history")
    temperature: Optional[float] = Field(
        None, ge=0.0, le=2.0, description="Model temperature"
    )
    max_tokens: Optional[int] = Field(
        None, ge=1, le=4096, description="Maximum tokens to generate"
    )
    tools: Optional[list[str]] = Field(
        None, description="Specific tools to enable for this request"
    )
