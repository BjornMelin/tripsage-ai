"""Search response schemas using Pydantic V2.

This module defines Pydantic models for search-related API responses.
"""

from typing import Any, Optional, Union

from pydantic import BaseModel, Field

class SearchResultItem(BaseModel):
    """Individual search result item that can represent any resource type."""

    id: str = Field(..., description="Unique identifier")
    type: str = Field(
        ...,
        description="Resource type (destination, flight, accommodation, activity)",
    )
    title: str = Field(..., description="Display title")
    description: str = Field(..., description="Brief description")
    image_url: str | None = Field(None, description="Primary image URL")

    # Common fields across types
    price: float | None = Field(None, ge=0, description="Price (if applicable)")
    currency: str | None = Field(None, description="Currency code")
    location: str | None = Field(None, description="Location string")
    rating: float | None = Field(None, ge=0, le=5, description="Average rating")
    review_count: int | None = Field(None, ge=0, description="Number of reviews")

    # Search relevance
    relevance_score: float | None = Field(
        None,
        ge=0,
        le=1,
        description="Search relevance score",
    )
    match_reasons: list[str] | None = Field(
        None,
        description="Reasons why this result matches the search",
    )

    # Type-specific metadata
    metadata: dict[str, Any] | None = Field(
        None,
        description="Additional type-specific data",
    )

    # Quick actions
    quick_actions: list[dict[str, str]] | None = Field(
        None,
        description="Available quick actions (view, book, save, etc.)",
    )

class SearchFacet(BaseModel):
    """Search facet for filtering results."""

    field: str = Field(..., description="Facet field name")
    label: str = Field(..., description="Display label")
    type: str = Field(
        ...,
        description="Facet type (range, terms, boolean)",
    )
    values: list[dict[str, str | int | float]] = Field(
        ...,
        description="Facet values with counts",
    )

class SearchMetadata(BaseModel):
    """Metadata about the search operation."""

    total_results: int = Field(0, ge=0, description="Total results found")
    returned_results: int = Field(0, ge=0, description="Results in this response")
    search_time_ms: int = Field(0, ge=0, description="Search execution time")
    cached_results: int = Field(0, ge=0, description="Number of cached results")

    # Search context
    search_id: str | None = Field(None, description="Unique search session ID")
    user_id: str | None = Field(None, description="User ID if authenticated")
    personalized: bool | None = Field(
        None,
        description="Whether results are personalized",
    )

    # Provider information
    providers_queried: list[str] | None = Field(
        None,
        description="External providers queried",
    )
    provider_errors: dict[str, str] | None = Field(
        None,
        description="Errors from specific providers",
    )

class UnifiedSearchResponse(BaseModel):
    """Unified search response containing results from multiple resource types."""

    results: list[SearchResultItem] = Field(
        default_factory=list,
        description="Search results across all types",
    )
    facets: list[SearchFacet] = Field(
        default_factory=list,
        description="Available facets for filtering",
    )
    metadata: SearchMetadata = Field(
        ...,
        description="Search operation metadata",
    )

    # Grouped results by type (optional view)
    results_by_type: dict[str, list[SearchResultItem]] | None = Field(
        None,
        description="Results grouped by resource type",
    )

    # Search suggestions
    did_you_mean: str | None = Field(
        None,
        description="Spelling correction suggestion",
    )
    related_searches: list[str] | None = Field(
        None,
        description="Related search suggestions",
    )

    # Errors (partial failures allowed)
    errors: dict[str, str] | None = Field(
        None,
        description="Non-fatal errors by provider or type",
    )

class SavedSearchResponse(BaseModel):
    """Response model for saved search operation."""

    id: str = Field(..., description="ID of the saved search")
    message: str = Field(..., description="Success message")

class SearchHistoryEntry(BaseModel):
    """Individual search history entry."""

    id: str = Field(..., description="Unique identifier for the saved search")
    user_id: str = Field(..., description="ID of the user who performed the search")
    query: str = Field(..., description="Search query text")
    resource_types: list[str] | None = Field(
        None, description="Types of resources searched"
    )
    filters: dict[str, Any] | None = Field(
        None, description="Applied search filters"
    )
    destination: str | None = Field(None, description="Search destination")
    created_at: str = Field(..., description="ISO timestamp when search was performed")

class SearchHistoryResponse(BaseModel):
    """Response model for search history."""

    searches: list[dict[str, Any]] = Field(
        default_factory=list,
        description="List of recent searches",
    )
    total_count: int | None = Field(
        None, description="Total number of searches in history"
    )
