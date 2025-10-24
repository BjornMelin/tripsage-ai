"""Memory API request schemas.

Defines Pydantic request models used by the memory router.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ConversationMemoryRequest(BaseModel):
    """Request payload for adding conversation memory.

    Attributes:
        messages: Ordered list of role/content message dicts.
        session_id: Optional session identifier for threading.
        context_type: Logical context hint for downstream processors.
    """

    messages: list[dict[str, str]] = Field(..., description="Conversation messages")
    session_id: str | None = Field(default=None, description="Session ID")
    context_type: str = Field(default="travel_planning", description="Context type")


class SearchMemoryRequest(BaseModel):
    """Request model for searching user memories.

    Attributes:
        query: Free-text query string.
        limit: Maximum number of results to return.
    """

    query: str = Field(..., description="Search query")
    limit: int = Field(
        default=10, ge=1, le=100, description="Maximum results to return"
    )


class UpdatePreferencesRequest(BaseModel):
    """Request model for updating user preferences.

    Attributes:
        preferences: Arbitrary preferences map to merge.
    """

    preferences: dict = Field(..., description="User preferences to update")
