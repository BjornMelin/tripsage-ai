"""
Response schemas for itinerary endpoints.

This module defines Pydantic V2 models for API responses related to itineraries.
"""

from datetime import date
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from tripsage_core.models.schemas_common import PaginatedResponse


class ItineraryItemResponse(BaseModel):
    """Response model for itinerary item."""

    id: str = Field(description="Unique identifier for the itinerary item")
    item_type: str = Field(description="Type of itinerary item")
    title: str = Field(description="Title or name of the item")
    description: Optional[str] = Field(None, description="Description of the item")
    item_date: date = Field(description="Date of the itinerary item")
    cost: Optional[float] = Field(None, description="Cost of the item")
    currency: Optional[str] = Field(None, description="Currency code for the cost")
    booking_reference: Optional[str] = Field(None, description="Booking reference")
    notes: Optional[str] = Field(None, description="Additional notes")
    is_flexible: bool = Field(False, description="Whether item time is flexible")


class ItineraryResponse(BaseModel):
    """Response model for itinerary."""

    id: str = Field(description="Itinerary identifier")
    title: str = Field(description="Itinerary title")
    description: Optional[str] = Field(None, description="Itinerary description")
    start_date: date = Field(description="Itinerary start date")
    end_date: date = Field(description="Itinerary end date")
    status: str = Field(description="Current status of the itinerary")
    total_budget: Optional[float] = Field(None, description="Total budget for the trip")
    currency: Optional[str] = Field(None, description="Currency code for budget")
    tags: List[str] = Field(default_factory=list, description="Associated tags")
    items: List[ItineraryItemResponse] = Field(
        default_factory=list, description="Itinerary items"
    )
    created_at: Optional[str] = Field(None, description="Creation timestamp")
    updated_at: Optional[str] = Field(None, description="Last update timestamp")


class ItinerarySearchResponse(PaginatedResponse[ItineraryResponse]):
    """Response model for itinerary search results."""

    pass


class ItineraryConflictCheckResponse(BaseModel):
    """Response model for checking conflicting items in an itinerary."""

    has_conflicts: bool = Field(
        description="Whether there are any conflicts",
    )
    conflicts: List[Dict] = Field(
        default_factory=list,
        description="List of conflicts found",
    )


class ItineraryOptimizeResponse(BaseModel):
    """Response model for optimized itinerary."""

    original_itinerary: ItineraryResponse = Field(
        description="Original itinerary before optimization",
    )
    optimized_itinerary: ItineraryResponse = Field(
        description="Optimized itinerary",
    )
    changes: List[Dict] = Field(
        default_factory=list,
        description="List of changes made during optimization",
    )
    optimization_score: float = Field(
        description="Score representing the optimization improvement (0-1)",
        ge=0,
        le=1,
    )
