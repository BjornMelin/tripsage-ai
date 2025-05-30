"""Database model for API keys using Pydantic V2.

This module defines the database model for API keys used in the BYOK
(Bring Your Own Key) functionality.
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ApiKeyDB(BaseModel):
    """Database model for API keys.

    This model represents the structure of API keys as stored in the database,
    including all fields with proper validation.
    """

    model_config = ConfigDict(
        from_attributes=True,
        str_strip_whitespace=True,
        validate_assignment=True,
        json_schema_extra={
            "examples": [
                {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "user_id": 1,
                    "name": "OpenAI API Key",
                    "service": "openai",
                    "encrypted_key": "gAAAAABh...",
                    "description": "API key for OpenAI GPT models",
                    "created_at": "2025-01-22T10:00:00Z",
                    "updated_at": "2025-01-22T10:00:00Z",
                    "expires_at": None,
                    "last_used": None,
                    "is_active": True,
                }
            ]
        },
    )

    id: UUID = Field(description="Unique identifier for the API key")
    user_id: int = Field(gt=0, description="ID of the user who owns this API key")
    name: str = Field(
        min_length=1,
        max_length=255,
        description="User-friendly name for the API key",
    )
    service: str = Field(
        min_length=1,
        max_length=255,
        description="Service name this key is for",
    )
    encrypted_key: str = Field(description="Encrypted API key value")
    description: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Optional description of the API key",
    )
    created_at: datetime = Field(description="Timestamp when the API key was created")
    updated_at: datetime = Field(
        description="Timestamp when the API key was last updated"
    )
    expires_at: Optional[datetime] = Field(
        default=None,
        description="Optional expiration timestamp for the API key",
    )
    last_used: Optional[datetime] = Field(
        default=None,
        description="Timestamp when the API key was last used",
    )
    is_active: bool = Field(
        default=True,
        description="Whether the API key is active and can be used",
    )

    @field_validator("service")
    @classmethod
    def validate_service(cls, v: str) -> str:
        """Validate service name format.

        Service names should be lowercase alphanumeric with underscores and hyphens.
        """
        import re

        if not re.match(r"^[a-z0-9_-]+$", v):
            raise ValueError(
                "Service name must contain only lowercase letters, "
                "numbers, underscores, and hyphens"
            )
        return v

    @field_validator("expires_at")
    @classmethod
    def validate_expires_at(cls, v: Optional[datetime]) -> Optional[datetime]:
        """Validate expiration date is in the future."""
        if v is not None:
            # Handle timezone-aware and timezone-naive datetime comparison
            now = datetime.now(timezone.utc) if v.tzinfo is not None else datetime.now()
            if v <= now:
                raise ValueError("Expiration date must be in the future")
        return v

    def is_expired(self) -> bool:
        """Check if the API key is expired."""
        if self.expires_at is None:
            return False
        # Handle timezone-aware and timezone-naive datetime comparison
        now = (
            datetime.now(timezone.utc)
            if self.expires_at.tzinfo is not None
            else datetime.now()
        )
        return now > self.expires_at

    def is_usable(self) -> bool:
        """Check if the API key can be used."""
        return self.is_active and not self.is_expired()


class ApiKeyCreate(BaseModel):
    """Model for creating a new API key."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        json_schema_extra={
            "examples": [
                {
                    "user_id": 1,
                    "name": "OpenAI API Key",
                    "service": "openai",
                    "encrypted_key": "gAAAAABh...",
                    "description": "API key for OpenAI GPT models",
                    "expires_at": None,
                }
            ]
        },
    )

    user_id: int = Field(gt=0, description="ID of the user who owns this API key")
    name: str = Field(
        min_length=1,
        max_length=255,
        description="User-friendly name for the API key",
    )
    service: str = Field(
        min_length=1,
        max_length=255,
        description="Service name this key is for",
    )
    encrypted_key: str = Field(description="Encrypted API key value")
    description: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Optional description of the API key",
    )
    expires_at: Optional[datetime] = Field(
        default=None,
        description="Optional expiration timestamp for the API key",
    )


class ApiKeyUpdate(BaseModel):
    """Model for updating an existing API key."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        json_schema_extra={
            "examples": [
                {
                    "name": "Updated OpenAI Key",
                    "description": "Updated description",
                    "is_active": False,
                }
            ]
        },
    )

    name: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="Updated user-friendly name",
    )
    description: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Updated description",
    )
    is_active: Optional[bool] = Field(
        default=None,
        description="Updated active status",
    )
    expires_at: Optional[datetime] = Field(
        default=None,
        description="Updated expiration timestamp",
    )