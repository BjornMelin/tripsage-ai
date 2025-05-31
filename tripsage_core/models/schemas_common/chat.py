"""Common chat models for TripSage.

This module provides shared chat models used across API layers,
services, and core business logic.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class ToolCall(BaseModel):
    """Common model for tool calls in chat messages."""

    id: str = Field(..., description="Unique identifier for the tool call")
    name: str = Field(..., description="Name of the tool")
    arguments: Dict[str, Any] = Field(
        default_factory=dict, description="Tool arguments"
    )
    result: Optional[Dict[str, Any]] = Field(None, description="Tool result")
    status: str = Field("pending", description="Tool call status")
    error: Optional[str] = Field(None, description="Error message if failed")

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
    def ensure_dict(cls, v: Any) -> Dict[str, Any]:
        """Ensure arguments is a dictionary."""
        if v is None:
            return {}
        if isinstance(v, dict):
            return v
        return {}


class ChatMessage(BaseModel):
    """Common model for chat messages."""

    role: str = Field(..., description="Message role (user/assistant/system)")
    content: str = Field(..., description="Message content")
    tool_calls: Optional[List[ToolCall]] = Field(None, description="Tool calls made")
    timestamp: Optional[datetime] = Field(None, description="Message timestamp")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Message metadata")

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        """Validate message role."""
        valid_roles = {"user", "assistant", "system", "tool"}
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
    def ensure_dict(cls, v: Any) -> Dict[str, Any]:
        """Ensure metadata is a dictionary."""
        if v is None:
            return {}
        if isinstance(v, dict):
            return v
        return {}


class ChatSession(BaseModel):
    """Common model for chat sessions."""

    id: str = Field(..., description="Session ID")
    user_id: Optional[int] = Field(None, description="User ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Session metadata"
    )

    @field_validator("metadata", mode="before")
    @classmethod
    def ensure_dict(cls, v: Any) -> Dict[str, Any]:
        """Ensure metadata is a dictionary."""
        if v is None:
            return {}
        if isinstance(v, dict):
            return v
        return {}


class ChatContext(BaseModel):
    """Common model for chat context and memory."""

    session_id: str = Field(..., description="Session ID")
    messages: List[ChatMessage] = Field(
        default_factory=list, description="Conversation messages"
    )
    system_prompt: Optional[str] = Field(None, description="System prompt")
    temperature: Optional[float] = Field(None, description="Model temperature")
    max_tokens: Optional[int] = Field(None, description="Maximum tokens")
    tools: Optional[List[str]] = Field(None, description="Available tools")

    @field_validator("temperature")
    @classmethod
    def validate_temperature(cls, v: Optional[float]) -> Optional[float]:
        """Validate temperature is between 0 and 2."""
        if v is not None and (v < 0 or v > 2):
            raise ValueError("Temperature must be between 0 and 2")
        return v

    @field_validator("max_tokens")
    @classmethod
    def validate_max_tokens(cls, v: Optional[int]) -> Optional[int]:
        """Validate max_tokens is positive."""
        if v is not None and v <= 0:
            raise ValueError("Max tokens must be positive")
        return v
