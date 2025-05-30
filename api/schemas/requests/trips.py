"""
Request schemas for trip endpoints.

This module defines Pydantic models for validating incoming trip-related requests
from the Next.js frontend. Uses shared travel models from tripsage_core.
"""

from datetime import date
from typing import List, Optional

from pydantic import BaseModel, Field, model_validator

from tripsage_core.models.schemas_common.travel import (
    TripDestination,
    TripPreferences,
)


class CreateTripRequest(BaseModel):
    """Request schema for creating a trip."""

    title: str = Field(
        ...,
        description="Trip title",
        min_length=1,
        max_length=100,
    )
    description: Optional[str] = Field(
        None,
        description="Trip description",
        max_length=500,
    )
    start_date: date = Field(..., description="Trip start date")
    end_date: date = Field(..., description="Trip end date")
    destinations: List[TripDestination] = Field(
        ...,
        description="Trip destinations",
        min_length=1,
    )
    preferences: Optional[TripPreferences] = Field(
        None,
        description="Trip preferences",
    )

    @model_validator(mode="after")
    def validate_dates(self) -> "CreateTripRequest":
        """Validate that end_date is after start_date."""
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("End date must be after start date")
        return self


class UpdateTripRequest(BaseModel):
    """Request schema for updating a trip."""

    title: Optional[str] = Field(
        None,
        description="Trip title",
        min_length=1,
        max_length=100,
    )
    description: Optional[str] = Field(
        None,
        description="Trip description",
        max_length=500,
    )
    start_date: Optional[date] = Field(None, description="Trip start date")
    end_date: Optional[date] = Field(None, description="Trip end date")
    destinations: Optional[List[TripDestination]] = Field(
        None,
        description="Trip destinations",
    )

    @model_validator(mode="after")
    def validate_dates(self) -> "UpdateTripRequest":
        """Validate that end_date is after start_date if both are provided."""
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("End date must be after start date")
        return self


class TripPreferencesRequest(TripPreferences):
    """Request schema for updating trip preferences."""

    pass


class TripSearchRequest(BaseModel):
    """Request schema for searching trips."""

    query: Optional[str] = Field(None, description="Search query")
    destination: Optional[str] = Field(None, description="Destination filter")
    start_date_from: Optional[date] = Field(None, description="Earliest start date")
    start_date_to: Optional[date] = Field(None, description="Latest start date")
    min_duration: Optional[int] = Field(
        None, description="Minimum duration in days", ge=1
    )
    max_duration: Optional[int] = Field(
        None, description="Maximum duration in days", ge=1
    )
    status: Optional[str] = Field(None, description="Trip status filter")

    @model_validator(mode="after")
    def validate_duration_range(self) -> "TripSearchRequest":
        """Validate duration range is logical."""
        if (
            self.min_duration is not None
            and self.max_duration is not None
            and self.min_duration > self.max_duration
        ):
            raise ValueError("Minimum duration cannot be greater than maximum duration")
        return self

    @model_validator(mode="after")
    def validate_date_range(self) -> "TripSearchRequest":
        """Validate start date range is logical."""
        if (
            self.start_date_from is not None
            and self.start_date_to is not None
            and self.start_date_from > self.start_date_to
        ):
            raise ValueError("Start date from cannot be after start date to")
        return self
