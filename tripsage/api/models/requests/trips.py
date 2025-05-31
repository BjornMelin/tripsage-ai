"""
Request models for trip endpoints.

This module defines Pydantic models for validating incoming trip-related requests.
"""

from datetime import date
from typing import List, Optional

from pydantic import BaseModel, Field, model_validator

from tripsage_core.models.schemas_common.travel import TripDestination, TripPreferences


class CreateTripRequest(BaseModel):
    """Request model for creating a trip."""

    title: str = Field(
        description="Trip title",
        min_length=1,
        max_length=100,
    )
    description: Optional[str] = Field(
        default=None,
        description="Trip description",
        max_length=500,
    )
    start_date: date = Field(description="Trip start date")
    end_date: date = Field(description="Trip end date")
    destinations: List[TripDestination] = Field(
        description="Trip destinations",
        min_length=1,
    )
    preferences: Optional[TripPreferences] = Field(
        default=None,
        description="Trip preferences",
    )

    @model_validator(mode="after")
    def validate_dates(self) -> "CreateTripRequest":
        """Validate that end_date is after start_date."""
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("End date must be after start date")
        return self


class UpdateTripRequest(BaseModel):
    """Request model for updating a trip."""

    title: Optional[str] = Field(
        default=None,
        description="Trip title",
        min_length=1,
        max_length=100,
    )
    description: Optional[str] = Field(
        default=None,
        description="Trip description",
        max_length=500,
    )
    start_date: Optional[date] = Field(default=None, description="Trip start date")
    end_date: Optional[date] = Field(default=None, description="Trip end date")
    destinations: Optional[List[TripDestination]] = Field(
        default=None,
        description="Trip destinations",
    )

    @model_validator(mode="after")
    def validate_dates(self) -> "UpdateTripRequest":
        """Validate that end_date is after start_date if both are provided."""
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("End date must be after start date")
        return self


class TripPreferencesRequest(TripPreferences):
    """Request model for updating trip preferences."""

    pass
