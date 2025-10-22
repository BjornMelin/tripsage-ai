"""Schemas for user-related endpoints.

Includes request and response models for user preferences.
"""

from typing import Any, ClassVar

from pydantic import BaseModel, Field


class UserPreferencesRequest(BaseModel):
    """Request model for updating user preferences."""

    preferences: dict[str, Any] = Field(
        ...,
        description="User preferences as a flexible JSON object",
    )


class UserPreferencesResponse(BaseModel):
    """Response model for user preferences."""

    preferences: dict[str, Any] = Field(
        ...,
        description="Current user preferences",
    )

    class Config:
        """Config for UserPreferencesResponse."""

        json_schema_extra: ClassVar = {
            "example": {
                "preferences": {
                    "theme": "dark",
                    "currency": "USD",
                    "language": "en",
                    "notifications": {
                        "email": True,
                        "push": False,
                        "marketing": False,
                    },
                    "travel_preferences": {
                        "budget_level": "moderate",
                        "accommodation_type": ["hotel", "resort"],
                        "travel_style": ["adventure", "cultural"],
                        "dietary_restrictions": ["vegetarian"],
                    },
                }
            }
        }
