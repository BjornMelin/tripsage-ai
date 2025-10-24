"""Memory API schemas (feature-first).

Consolidated request and response models for memory endpoints.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from tripsage_core.services.business.memory_service import MemorySearchResult


class ConversationMemoryRequest(BaseModel):
    """Request payload for adding conversation memory."""

    messages: list[dict[str, str]] = Field(..., description="Conversation messages")
    session_id: str | None = Field(default=None, description="Session ID")
    context_type: str = Field(default="travel_planning", description="Context type")


class SearchMemoryRequest(BaseModel):
    """Search query for user memories."""

    query: str = Field(..., description="Search query")
    limit: int = Field(
        default=10, ge=1, le=100, description="Maximum results to return"
    )


class UpdatePreferencesRequest(BaseModel):
    """Partial update of user preferences."""

    preferences: dict = Field(..., description="User preferences to update")


class MemorySearchResponse(BaseModel):
    """Search results wrapper for memory queries."""

    results: list[MemorySearchResult] = Field(description="Search results")
    query: str = Field(description="Original query string")
    total: int = Field(description="Total results returned")
