"""User model for TripSage.

This module provides the User model with business logic validation,
used across different storage backends.
"""

from enum import Enum
from typing import Any, Optional

from pydantic import Field

from tripsage_core.models.base_core_model import TripSageModel
from tripsage_core.models.schemas_common.common_validators import EmailLowercase

class UserRole(str, Enum):
    """Enum for user role values."""

    USER = "user"
    ADMIN = "admin"

class User(TripSageModel):
    """User model for TripSage.

    Attributes:
        id: Unique identifier for the user
        name: User's display name
        email: User's email address
        password_hash: Hashed password for the user
        is_admin: Whether the user is an admin
        is_disabled: Whether the user is disabled
        preferences_json: User preferences stored as a dictionary
    """

    id: int | None = Field(None, description="Unique identifier")
    name: str | None = Field(None, description="User's display name")
    email: EmailLowercase = Field(None, description="User's email address")
    password_hash: str | None = Field(None, description="Hashed password")
    role: UserRole = Field(UserRole.USER, description="User's role")
    is_admin: bool = Field(False, description="Whether the user is an admin")
    is_disabled: bool = Field(False, description="Whether the user is disabled")
    preferences_json: dict[str, Any] | None = Field(
        None, description="User preferences", alias="preferences"
    )

    @property
    def full_preferences(self) -> dict[str, Any]:
        """Get the full preferences dictionary with defaults."""
        defaults = {
            "theme": "light",
            "currency": "USD",
            "notifications_enabled": True,
            "language": "en",
            "travel_preferences": {
                "preferred_airlines": [],
                "preferred_accommodation_types": ["hotel"],
                "preferred_seat_type": "economy",
                "dietary_restrictions": [],
            },
        }

        if not self.preferences_json:
            return defaults

        # Deep merge preferences with defaults
        result = defaults.copy()
        for key, value in self.preferences_json.items():
            if (
                isinstance(value, dict)
                and key in result
                and isinstance(result[key], dict)
            ):
                # Merge nested dictionaries
                result[key] = {**result[key], **value}
            else:
                # Override at top level
                result[key] = value

        return result

    @property
    def display_name(self) -> str:
        """Get the display name for the user."""
        return self.name or self.email or "Unknown User"

    @property
    def is_active(self) -> bool:
        """Check if the user account is active."""
        return not self.is_disabled

    def update_preferences(self, updates: dict[str, Any]) -> None:
        """Update user preferences, merging with existing preferences.

        Args:
            updates: Dictionary of preference updates
        """
        if self.preferences_json is None:
            self.preferences_json = {}

        # Deep merge updates
        for key, value in updates.items():
            if (
                isinstance(value, dict)
                and key in self.preferences_json
                and isinstance(self.preferences_json[key], dict)
            ):
                self.preferences_json[key].update(value)
            else:
                self.preferences_json[key] = value
