"""Schemas for user-related endpoints.

Includes request and response models for user preferences.
"""

from typing import Any

from pydantic import BaseModel, Field


class UserPreferencesRequest(BaseModel):
    """Request model for updating user preferences."""

    preferences: dict[str, Any] = Field(
        ...,
        description="User preferences as a flexible JSON object",
        example={
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
        },
    )


class UserPreferencesResponse(BaseModel):
    """Response model for user preferences."""

    preferences: dict[str, Any] = Field(
        ...,
        description="Current user preferences",
    )

    class Config:
        json_schema_extra = {
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
