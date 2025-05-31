"""
Response models for itinerary endpoints.

This module defines Pydantic models for API responses related to itineraries.
"""

from typing import Dict, List

from pydantic import BaseModel, Field

from ..common.itineraries import Itinerary


class ItinerarySearchResponse(BaseModel):
    """Response model for itinerary search results."""

    results: List[Itinerary] = Field(
        description="List of itineraries matching the search criteria",
    )
    total: int = Field(
        description="Total number of itineraries matching the search criteria",
    )
    page: int = Field(
        description="Current page number",
    )
    page_size: int = Field(
        description="Number of results per page",
    )
    pages: int = Field(
        description="Total number of pages available",
    )


class ItineraryConflictCheckResponse(BaseModel):
    """Response model for checking conflicting items in an itinerary."""

    has_conflicts: bool = Field(
        description="Whether there are any conflicts",
    )
    conflicts: List[Dict] = Field(
        description="List of conflicts found",
        default=[],
    )


class ItineraryOptimizeResponse(BaseModel):
    """Response model for optimized itinerary."""

    original_itinerary: Itinerary = Field(
        description="Original itinerary before optimization",
    )
    optimized_itinerary: Itinerary = Field(
        description="Optimized itinerary",
    )
    changes: List[Dict] = Field(
        description="List of changes made during optimization",
    )
    optimization_score: float = Field(
        description="Score representing the optimization improvement (0-1)",
        ge=0,
        le=1,
    )
