"""Destination response models using Pydantic V2.

This module defines Pydantic models for destination-related responses.
"""

from datetime import date
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from ..common.destinations import Destination, DestinationVisitSchedule


class DestinationSearchResponse(BaseModel):
    """Response model for destination search results."""

    destinations: List[Destination] = Field(description="List of destinations")
    count: int = Field(description="Number of destinations found")
    query: str = Field(description="Original search query")


class DestinationDetailsResponse(BaseModel):
    """Response model for destination details."""

    destination: Destination = Field(description="Destination details")


class SavedDestinationResponse(BaseModel):
    """Response model for a saved destination."""

    id: UUID = Field(description="Saved destination ID")
    user_id: str = Field(description="User ID")
    trip_id: UUID = Field(description="Trip ID")
    destination: Destination = Field(description="Destination details")
    saved_at: date = Field(description="Date when the destination was saved")
    notes: Optional[str] = Field(
        default=None, description="Notes about this destination"
    )
    visit_schedule: Optional[DestinationVisitSchedule] = Field(
        default=None, description="Visit schedule details"
    )
    priority: int = Field(description="Priority (1=highest, 5=lowest)")


class DestinationSuggestionResponse(BaseModel):
    """Response model for destination suggestions."""

    suggestions: List[Destination] = Field(description="Destination suggestions")
    count: int = Field(description="Number of suggestions")
    reasoning: Optional[Dict[str, str]] = Field(
        default=None,
        description="Reasoning for each suggestion (destination_id -> explanation)",
    )


# Aliases for backward compatibility with existing service imports
DestinationDetails = DestinationDetailsResponse
DestinationRecommendation = DestinationSuggestionResponse
PointOfInterestSearchResponse = DestinationSearchResponse
SavedDestination = SavedDestinationResponse
