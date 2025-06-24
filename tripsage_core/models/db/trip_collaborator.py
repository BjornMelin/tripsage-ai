"""Database model for trip collaborators using Pydantic V2.

This module defines database models for trip collaboration functionality,
allowing users to share trips with others with different permission levels.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PermissionLevel(str, Enum):
    """Permission levels for trip collaborators.

    - VIEW: Can view trip details but cannot modify
    - EDIT: Can view and edit trip details but cannot manage collaborators
    - ADMIN: Full access including managing other collaborators
    """

    VIEW = "view"
    EDIT = "edit"
    ADMIN = "admin"


class TripCollaboratorDB(BaseModel):
    """Database model for trip collaborators.

    This model represents the structure of trip collaborators as stored
    in the database, including all fields with proper validation.
    """

    model_config = ConfigDict(
        from_attributes=True,
        str_strip_whitespace=True,
        validate_assignment=True,
        json_schema_extra={
            "examples": [
                {
                    "id": 1,
                    "trip_id": 123,
                    "user_id": "123e4567-e89b-12d3-a456-426614174000",
                    "permission_level": "edit",
                    "added_by": "123e4567-e89b-12d3-a456-426614174001",
                    "added_at": "2025-06-11T10:00:00Z",
                    "updated_at": "2025-06-11T10:00:00Z",
                }
            ]
        },
    )

    id: int = Field(description="Unique identifier for the collaboration record")
    trip_id: int = Field(description="ID of the trip being shared")
    user_id: UUID = Field(description="ID of the user who has access to the trip")
    permission_level: PermissionLevel = Field(
        default=PermissionLevel.VIEW,
        description="Permission level for the collaborator",
    )
    added_by: UUID = Field(description="ID of the user who added this collaborator")
    added_at: datetime = Field(
        description="Timestamp when the collaboration was created"
    )
    updated_at: datetime = Field(
        description="Timestamp when the collaboration was last updated"
    )

    @property
    def can_view(self) -> bool:
        """Check if collaborator can view the trip."""
        return True  # All permission levels can view

    @property
    def can_edit(self) -> bool:
        """Check if collaborator can edit the trip."""
        return self.permission_level in [PermissionLevel.EDIT, PermissionLevel.ADMIN]

    @property
    def can_manage_collaborators(self) -> bool:
        """Check if collaborator can manage other collaborators."""
        return self.permission_level == PermissionLevel.ADMIN

    def has_permission(self, required_level: PermissionLevel) -> bool:
        """Check if collaborator has at least the required permission level.

        Args:
            required_level: The minimum permission level required

        Returns:
            True if collaborator has sufficient permissions
        """
        permission_hierarchy = {
            PermissionLevel.VIEW: 1,
            PermissionLevel.EDIT: 2,
            PermissionLevel.ADMIN: 3,
        }

        current_level = permission_hierarchy.get(self.permission_level, 0)
        required_level_value = permission_hierarchy.get(required_level, 0)

        return current_level >= required_level_value


class TripCollaboratorCreate(BaseModel):
    """Model for creating a new trip collaborator."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        json_schema_extra={
            "examples": [
                {
                    "trip_id": 123,
                    "user_id": "123e4567-e89b-12d3-a456-426614174000",
                    "permission_level": "edit",
                    "added_by": "123e4567-e89b-12d3-a456-426614174001",
                }
            ]
        },
    )

    trip_id: int = Field(gt=0, description="ID of the trip to share")
    user_id: UUID = Field(description="ID of the user to grant access to")
    permission_level: PermissionLevel = Field(
        default=PermissionLevel.VIEW,
        description="Permission level to grant to the collaborator",
    )
    added_by: UUID = Field(description="ID of the user adding this collaborator")

    @field_validator("trip_id")
    @classmethod
    def validate_trip_id(cls, v: int) -> int:
        """Validate trip ID is positive."""
        if v <= 0:
            raise ValueError("Trip ID must be positive")
        return v

    @field_validator("user_id")
    @classmethod
    def validate_user_id(cls, v: UUID) -> UUID:
        """Validate user ID format."""
        # UUID validation is handled by pydantic, but we can add custom logic here
        return v

    @field_validator("added_by")
    @classmethod
    def validate_added_by(cls, v: UUID) -> UUID:
        """Validate added_by user ID format."""
        # UUID validation is handled by pydantic, but we can add custom logic here
        return v


class TripCollaboratorUpdate(BaseModel):
    """Model for updating an existing trip collaborator."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        json_schema_extra={
            "examples": [
                {
                    "permission_level": "admin",
                }
            ]
        },
    )

    permission_level: Optional[PermissionLevel] = Field(
        default=None, description="Updated permission level for the collaborator"
    )

    def has_updates(self) -> bool:
        """Check if there are any updates to apply."""
        return self.permission_level is not None

    def get_update_fields(self) -> dict:
        """Get only the fields that have updates.

        Returns:
            Dictionary containing only non-None fields for updating
        """
        updates = {}
        if self.permission_level is not None:
            updates["permission_level"] = self.permission_level
        return updates
