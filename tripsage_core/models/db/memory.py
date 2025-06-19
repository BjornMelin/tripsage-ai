"""Database models for memory functionality using Mem0 + pgvector.

These models represent the database schema for memory storage and retrieval,
implementing Mem0's memory system with pgvector for semantic search.
"""

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Memory(BaseModel):
    """Database model for memories using Mem0 + pgvector."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "user_id": "123e4567-e89b-12d3-a456-426614174000",
                    "memory": "User prefers window seats on flights",
                    "metadata": {"preference_type": "flight", "category": "seating"},
                    "categories": ["travel_preferences", "flights"],
                    "created_at": "2025-01-22T10:00:00Z",
                    "updated_at": "2025-01-22T10:00:00Z",
                    "is_deleted": False,
                    "version": 1,
                    "relevance_score": 1.0,
                }
            ]
        },
    )

    id: UUID = Field(description="Unique identifier for the memory")
    user_id: UUID = Field(description="ID of the user this memory belongs to")
    memory: str = Field(description="The actual memory content")
    embedding: list[float] | None = Field(
        None,
        description="Vector embedding (1536 dims for OpenAI text-embedding-3-small)",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata for the memory"
    )
    categories: list[str] = Field(
        default_factory=list, description="Categories for organizing memories"
    )
    created_at: datetime = Field(description="Timestamp when the memory was created")
    updated_at: datetime = Field(
        description="Timestamp when the memory was last updated"
    )
    is_deleted: bool = Field(False, description="Whether the memory is soft deleted")
    version: int = Field(1, description="Version number for tracking changes")
    hash: str | None = Field(None, description="Content hash for deduplication")
    relevance_score: float = Field(
        1.0, description="Relevance score for the memory (0.0 to 1.0)"
    )

    @field_validator("memory")
    @classmethod
    def validate_memory_content(cls, v: str) -> str:
        """Validate memory content is not empty."""
        if not v or not v.strip():
            raise ValueError("Memory content cannot be empty")
        return v.strip()

    @field_validator("user_id")
    @classmethod
    def validate_user_id(cls, v: UUID) -> UUID:
        """Validate user ID format."""
        if not v:
            raise ValueError("User ID cannot be empty")
        return v

    @field_validator("categories")
    @classmethod
    def validate_categories(cls, v: list[str]) -> list[str]:
        """Validate and clean categories."""
        if not v:
            return []
        # Remove empty strings and duplicates while preserving order
        seen = set()
        cleaned = []
        for category in v:
            if category and category.strip():
                cleaned_category = category.strip().lower()
                if cleaned_category not in seen:
                    cleaned.append(cleaned_category)
                    seen.add(cleaned_category)
        return cleaned

    @field_validator("relevance_score")
    @classmethod
    def validate_relevance_score(cls, v: float) -> float:
        """Validate relevance score is between 0.0 and 1.0."""
        if not (0.0 <= v <= 1.0):
            raise ValueError("Relevance score must be between 0.0 and 1.0")
        return v

    @field_validator("metadata", mode="before")
    @classmethod
    def ensure_dict(cls, v: Any) -> dict[str, Any]:
        """Ensure metadata is a dictionary."""
        if v is None:
            return {}
        if isinstance(v, dict):
            return v
        return {}

    @property
    def is_active(self) -> bool:
        """Check if the memory is active (not deleted)."""
        return not self.is_deleted

    def add_category(self, category: str) -> None:
        """Add a category to the memory."""
        category = category.strip().lower()
        if category and category not in self.categories:
            self.categories.append(category)

    def remove_category(self, category: str) -> None:
        """Remove a category from the memory."""
        category = category.strip().lower()
        if category in self.categories:
            self.categories.remove(category)

    def update_metadata(self, updates: dict[str, Any]) -> None:
        """Update memory metadata."""
        self.metadata.update(updates)


class SessionMemory(BaseModel):
    """Database model for session-specific memories."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "session_id": "chat_session_123",
                    "user_id": "123e4567-e89b-12d3-a456-426614174000",
                    "message_index": 5,
                    "role": "user",
                    "content": "I want to book a flight to Paris",
                    "metadata": {"intent": "flight_booking", "destination": "Paris"},
                    "created_at": "2025-01-22T10:00:00Z",
                    "expires_at": "2025-01-23T10:00:00Z",
                }
            ]
        },
    )

    id: UUID = Field(description="Unique identifier for the session memory")
    session_id: UUID = Field(description="ID of the session this memory belongs to")
    user_id: UUID = Field(description="ID of the user this memory belongs to")
    message_index: int = Field(description="Index of the message within the session")
    role: str = Field(description="Role of the message (user, assistant, system)")
    content: str = Field(description="Content of the message")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata for the session memory"
    )
    created_at: datetime = Field(
        description="Timestamp when the session memory was created"
    )
    expires_at: datetime = Field(
        description="Timestamp when the session memory should expire"
    )

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        """Validate message role."""
        valid_roles = {"user", "assistant", "system"}
        if v not in valid_roles:
            raise ValueError(f"Role must be one of {valid_roles}")
        return v

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        """Validate content is not empty."""
        if not v or not v.strip():
            raise ValueError("Content cannot be empty")
        return v.strip()

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, v: UUID) -> UUID:
        """Validate session ID format."""
        if not v:
            raise ValueError("Session ID cannot be empty")
        return v

    @field_validator("user_id")
    @classmethod
    def validate_user_id(cls, v: UUID) -> UUID:
        """Validate user ID format."""
        if not v:
            raise ValueError("User ID cannot be empty")
        return v

    @field_validator("message_index")
    @classmethod
    def validate_message_index(cls, v: int) -> int:
        """Validate message index is non-negative."""
        if v < 0:
            raise ValueError("Message index must be non-negative")
        return v

    @field_validator("metadata", mode="before")
    @classmethod
    def ensure_dict(cls, v: Any) -> dict[str, Any]:
        """Ensure metadata is a dictionary."""
        if v is None:
            return {}
        if isinstance(v, dict):
            return v
        return {}

    @property
    def is_expired(self) -> bool:
        """Check if the session memory has expired."""
        expires_at = self.expires_at
        if expires_at.tzinfo is None:
            # If expires_at is naive, compare with naive now
            return datetime.now() > expires_at
        else:
            # If expires_at is timezone-aware, compare with timezone-aware now
            return datetime.now(timezone.utc) > expires_at

    def extend_expiry(self, hours: int = 24) -> None:
        """Extend the expiry time by the specified number of hours."""
        from datetime import timedelta

        # Ensure timezone-aware comparison
        new_expiry = datetime.now(timezone.utc) + timedelta(hours=hours)
        # Keep the same timezone format as original
        if self.expires_at.tzinfo is None:
            self.expires_at = new_expiry.replace(tzinfo=None)
        else:
            self.expires_at = new_expiry


class MemorySearchResult(BaseModel):
    """Model for memory search results."""

    model_config = ConfigDict(from_attributes=True)

    memory: Memory = Field(description="The memory that matched the search")
    similarity: float = Field(description="Similarity score (0.0 to 1.0)")
    rank: int = Field(description="Rank in the search results")

    @field_validator("similarity")
    @classmethod
    def validate_similarity(cls, v: float) -> float:
        """Validate similarity score is between 0.0 and 1.0."""
        if not (0.0 <= v <= 1.0):
            raise ValueError("Similarity score must be between 0.0 and 1.0")
        return v

    @field_validator("rank")
    @classmethod
    def validate_rank(cls, v: int) -> int:
        """Validate rank is positive."""
        if v < 1:
            raise ValueError("Rank must be positive")
        return v


class MemoryCreate(BaseModel):
    """Model for creating a new memory."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "user_id": "user_123",
                    "memory": "User prefers window seats on flights",
                    "metadata": {"preference_type": "flight", "category": "seating"},
                    "categories": ["travel_preferences", "flights"],
                    "relevance_score": 1.0,
                }
            ]
        }
    )

    user_id: UUID = Field(description="ID of the user this memory belongs to")
    memory: str = Field(description="The actual memory content")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata for the memory"
    )
    categories: list[str] = Field(
        default_factory=list, description="Categories for organizing memories"
    )
    relevance_score: float = Field(
        1.0, description="Relevance score for the memory (0.0 to 1.0)"
    )

    @field_validator("memory")
    @classmethod
    def validate_memory_content(cls, v: str) -> str:
        """Validate memory content is not empty."""
        if not v or not v.strip():
            raise ValueError("Memory content cannot be empty")
        return v.strip()

    @field_validator("user_id")
    @classmethod
    def validate_user_id(cls, v: UUID) -> UUID:
        """Validate user ID format."""
        if not v:
            raise ValueError("User ID cannot be empty")
        return v

    @field_validator("categories")
    @classmethod
    def validate_categories(cls, v: list[str]) -> list[str]:
        """Validate and clean categories."""
        if not v:
            return []
        # Remove empty strings and duplicates while preserving order
        seen = set()
        cleaned = []
        for category in v:
            if category and category.strip() and category not in seen:
                cleaned_category = category.strip().lower()
                cleaned.append(cleaned_category)
                seen.add(cleaned_category)
        return cleaned

    @field_validator("relevance_score")
    @classmethod
    def validate_relevance_score(cls, v: float) -> float:
        """Validate relevance score is between 0.0 and 1.0."""
        if not (0.0 <= v <= 1.0):
            raise ValueError("Relevance score must be between 0.0 and 1.0")
        return v

    @field_validator("metadata", mode="before")
    @classmethod
    def ensure_dict(cls, v: Any) -> dict[str, Any]:
        """Ensure metadata is a dictionary."""
        if v is None:
            return {}
        if isinstance(v, dict):
            return v
        return {}


class MemoryUpdate(BaseModel):
    """Model for updating an existing memory."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "memory": "User strongly prefers window seats on all flights",
                    "metadata": {
                        "preference_type": "flight",
                        "category": "seating",
                        "strength": "strong",
                    },
                    "categories": [
                        "travel_preferences",
                        "flights",
                        "strong_preferences",
                    ],
                    "relevance_score": 1.0,
                }
            ]
        }
    )

    memory: str | None = Field(None, description="Updated memory content")
    metadata: dict[str, Any] | None = Field(
        None, description="Updated metadata for the memory"
    )
    categories: list[str] | None = Field(
        None, description="Updated categories for organizing memories"
    )
    relevance_score: float | None = Field(
        None, description="Updated relevance score for the memory (0.0 to 1.0)"
    )

    @field_validator("memory")
    @classmethod
    def validate_memory_content(cls, v: str | None) -> str | None:
        """Validate memory content is not empty if provided."""
        if v is not None:
            if not v or not v.strip():
                raise ValueError("Memory content cannot be empty")
            return v.strip()
        return v

    @field_validator("categories")
    @classmethod
    def validate_categories(cls, v: list[str] | None) -> list[str] | None:
        """Validate and clean categories if provided."""
        if v is not None:
            if not v:
                return []
            # Remove empty strings and duplicates while preserving order
            seen = set()
            cleaned = []
            for category in v:
                if category and category.strip() and category not in seen:
                    cleaned_category = category.strip().lower()
                    cleaned.append(cleaned_category)
                    seen.add(cleaned_category)
            return cleaned
        return v

    @field_validator("relevance_score")
    @classmethod
    def validate_relevance_score(cls, v: float | None) -> float | None:
        """Validate relevance score is between 0.0 and 1.0 if provided."""
        if v is not None:
            if not (0.0 <= v <= 1.0):
                raise ValueError("Relevance score must be between 0.0 and 1.0")
        return v

    @field_validator("metadata", mode="before")
    @classmethod
    def ensure_dict(cls, v: Any) -> dict[str, Any] | None:
        """Ensure metadata is a dictionary if provided."""
        if v is not None:
            if isinstance(v, dict):
                return v
            return {}
        return v
