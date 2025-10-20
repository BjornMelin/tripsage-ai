"""Session memory utilities for TripSage Core using Mem0.

This module provides utilities for initializing and updating session memory
using the new Mem0-based memory system. Complete replacement of the old
Neo4j-based implementation.

Key Features:
- User context initialization from memory
- Preference tracking and updates
- Session summary storage
- Learned facts processing
- Integration with Core memory service
"""

from typing import Any

from pydantic import BaseModel, Field

from tripsage_core.exceptions.exceptions import (
    CoreServiceError,
    CoreValidationError as ValidationError,
)
from tripsage_core.utils.logging_utils import get_logger


logger = get_logger(__name__)


# Session memory models
class ConversationMessage(BaseModel):
    """Model for conversation messages."""

    role: str = Field(..., description="Message role (system/user/assistant)")
    content: str = Field(..., description="Message content")


class SessionSummary(BaseModel):
    """Model for session summary data."""

    user_id: str = Field(..., description="User ID")
    session_id: str = Field(..., description="Session ID")
    summary: str = Field(..., description="Session summary text")
    key_insights: list[str] | None = Field(
        None, description="Key insights from the session"
    )
    decisions_made: list[str] | None = Field(
        None, description="Decisions made during the session"
    )


class UserPreferences(BaseModel):
    """Model for user preferences."""

    budget_range: dict[str, float] | None = None
    preferred_destinations: list[str] | None = None
    travel_style: str | None = None
    accommodation_preferences: dict[str, Any] | None = None
    dietary_restrictions: list[str] | None = None
    accessibility_needs: list[str] | None = None





# Simple SessionMemory utility class for API dependencies
class SessionMemory:
    """Simple session memory utility class for API integration.

    This is a lightweight utility class that provides a simple interface for
    session memory operations while the full domain models handle the data storage.
    """

    def __init__(self, session_id: str, user_id: str | None = None):
        """Initialize session memory utility.

        Args:
            session_id: Session identifier
            user_id: Optional user identifier
        """
        self.session_id = session_id
        self.user_id = user_id
        self._memory_data: dict[str, Any] = {}

    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from session memory.

        Args:
            key: Memory key
            default: Default value if key not found

        Returns:
            Value from memory or default
        """
        return self._memory_data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a value in session memory.

        Args:
            key: Memory key
            value: Value to store
        """
        self._memory_data[key] = value

    def update(self, data: dict[str, Any]) -> None:
        """Update session memory with multiple values.

        Args:
            data: Dictionary of key-value pairs to update
        """
        self._memory_data.update(data)

    def clear(self) -> None:
        """Clear all session memory data."""
        self._memory_data.clear()

    def to_dict(self) -> dict[str, Any]:
        """Convert session memory to dictionary.

        Returns:
            Dictionary representation of session memory
        """
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "data": self._memory_data.copy(),
        }


__all__ = [
    "ConversationMessage",
    "SessionMemory",
    "SessionSummary",
    "UserPreferences",
]
