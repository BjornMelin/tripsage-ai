"""
User model for TripSage.

This module provides the User model for the TripSage database.
"""

from datetime import datetime
from typing import Any, ClassVar, Dict, Optional

from pydantic import EmailStr, Field, field_validator

from src.db.models.base import BaseDBModel


class User(BaseDBModel):
    """
    User model for TripSage.

    Attributes:
        id: Unique identifier for the user
        name: User's display name
        email: User's email address
        password_hash: Hashed password for the user
        is_admin: Whether the user is an admin
        is_disabled: Whether the user is disabled
        preferences_json: User preferences stored as a dictionary
        created_at: Timestamp when the user record was created
        updated_at: Timestamp when the user record was last updated
    """

    __tablename__: ClassVar[str] = "users"

    name: Optional[str] = Field(None, description="User's display name")
    email: Optional[EmailStr] = Field(None, description="User's email address")
    password_hash: Optional[str] = Field(
        None, description="Hashed password for the user"
    )
    is_admin: bool = Field(False, description="Whether the user is an admin")
    is_disabled: bool = Field(False, description="Whether the user is disabled")
    preferences_json: Optional[Dict[str, Any]] = Field(
        None, description="User preferences"
    )

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        """Validate the email address."""
        if v is None:
            return None
        # Email is already validated by EmailStr, just ensure lowercase
        return v.lower()

    @property
    def full_preferences(self) -> Dict[str, Any]:
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
