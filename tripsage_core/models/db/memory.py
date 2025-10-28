"""Database models for memory functionality using Mem0 + pgvector.

These models represent the database schema for memory storage and retrieval,
implementing Mem0's memory system with pgvector for semantic search.
"""

from datetime import UTC, datetime
from typing import Any, cast
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
        seen: set[str] = set()
        cleaned: list[str] = []
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
        if not 0.0 <= v <= 1.0:
            raise ValueError("Relevance score must be between 0.0 and 1.0")
        return v

    @field_validator("metadata", mode="before")
    @classmethod
    def ensure_dict(cls, v: Any) -> dict[str, Any]:
        """Ensure metadata is a dictionary."""
        if v is None:
            return {}
        if isinstance(v, dict):
            return cast(dict[str, Any], v)
        metadata_default: dict[str, Any] = {}
        return metadata_default

    @property
    def is_active(self) -> bool:
        """Check if the memory is active (not deleted)."""
        return not self.is_deleted

    def add_category(self, category: str) -> None:
        """Add a category to the memory."""
        category_normalized = category.strip().lower()
        categories = self._categories_list()
        if category_normalized and category_normalized not in categories:
            categories.append(category_normalized)

    def remove_category(self, category: str) -> None:
        """Remove a category from the memory."""
        category_normalized = category.strip().lower()
        categories = self._categories_list()
        if category_normalized in categories:
            categories.remove(category_normalized)

    def update_metadata(self, updates: dict[str, Any]) -> None:
        """Update memory metadata."""
        metadata = self._metadata_dict()
        metadata.update(updates)
        self.metadata = metadata

    def _metadata_dict(self) -> dict[str, Any]:
        """Return metadata as a dictionary."""
        metadata_any: Any | None = self.__dict__.get("metadata")
        if metadata_any is None:
            return {}
        if not isinstance(metadata_any, dict):
            raise TypeError("Memory.metadata must be a dictionary")
        return cast(dict[str, Any], metadata_any)

    def _categories_list(self) -> list[str]:
        """Return categories as a list."""
        categories_any: Any | None = self.__dict__.get("categories")
        if categories_any is None:
            return []
        if not isinstance(categories_any, list):
            raise TypeError("Memory.categories must be a list of strings")
        return cast(list[str], categories_any)


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
            empty: dict[str, Any] = {}
            return empty
        if isinstance(v, dict):
            return cast(dict[str, Any], v)
        empty2: dict[str, Any] = {}
        return empty2

    @property
    def is_expired(self) -> bool:
        """Check if the session memory has expired."""
        expires_at = self.expires_at
        if expires_at.tzinfo is None:
            # If expires_at is naive, compare with naive now
            return datetime.now() > expires_at
        # If expires_at is timezone-aware, compare with timezone-aware now
        return datetime.now(UTC) > expires_at

    def extend_expiry(self, hours: int = 24) -> None:
        """Extend the expiry time by the specified number of hours."""
        from datetime import timedelta

        # Ensure timezone-aware comparison
        new_expiry = datetime.now(UTC) + timedelta(hours=hours)
        # Keep the same timezone format as original
        if self.expires_at.tzinfo is None:
            self.expires_at = new_expiry.replace(tzinfo=None)
        else:
            self.expires_at = new_expiry


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
        seen: set[str] = set()
        cleaned: list[str] = []
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
        if not 0.0 <= v <= 1.0:
            raise ValueError("Relevance score must be between 0.0 and 1.0")
        return v

    @field_validator("metadata", mode="before")
    @classmethod
    def ensure_dict(cls, v: Any) -> dict[str, Any]:
        """Ensure metadata is a dictionary."""
        if v is None:
            empty3: dict[str, Any] = {}
            return empty3
        if isinstance(v, dict):
            return cast(dict[str, Any], v)
        return cast(dict[str, Any], {})


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
            seen: set[str] = set()
            cleaned: list[str] = []
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
        if v is not None and not 0.0 <= v <= 1.0:
            raise ValueError("Relevance score must be between 0.0 and 1.0")
        return v

    @field_validator("metadata", mode="before")
    @classmethod
    def ensure_dict(cls, v: Any) -> dict[str, Any] | None:
        """Ensure metadata is a dictionary if provided."""
        if v is not None:
            if isinstance(v, dict):
                return cast(dict[str, Any], v)
            empty4: dict[str, Any] = {}
            return empty4
        return None
