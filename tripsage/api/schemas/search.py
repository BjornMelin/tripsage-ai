"""Search API schemas (feature-first)."""

from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, Field


class SearchFilters(BaseModel):
    """Common filters for unified search."""

    price_min: float | None = Field(None, ge=0)
    price_max: float | None = Field(None, ge=0)
    rating_min: float | None = Field(None, ge=0, le=5)
    latitude: float | None = Field(None, ge=-90, le=90)
    longitude: float | None = Field(None, ge=-180, le=180)
    radius_km: float | None = Field(None, ge=0, le=100)
    custom_filters: dict[str, str | int | float | bool | list[str]] | None = None


class UnifiedSearchRequest(BaseModel):
    """Request for cross-resource unified search."""

    query: str = Field(..., min_length=1, max_length=500)
    types: list[str] | None = None
    destination: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    origin: str | None = None
    adults: int | None = Field(1, ge=1, le=20)
    children: int | None = Field(0, ge=0, le=20)
    infants: int | None = Field(0, ge=0, le=10)
    filters: SearchFilters | None = None
    sort_by: str | None = None
    sort_order: str | None = Field("desc", pattern="^(asc|desc)$")
    user_preferences: dict[str, str | int | float | bool] | None = None
    # Legacy-compatible fields used by core services
    resource_types: list[str] | None = None
    location: str | None = None
    guests: int | None = None


class SearchResultItem(BaseModel):
    """Generic search result item across types."""

    id: str
    type: str
    title: str
    description: str
    image_url: str | None = None
    price: float | None = None
    currency: str | None = None
    location: str | None = None
    rating: float | None = None
    review_count: int | None = None
    relevance_score: float | None = None
    match_reasons: list[str] | None = None
    metadata: dict[str, Any] | None = None
    quick_actions: list[dict[str, str]] | None = None


class SearchFacet(BaseModel):
    """Facet item used for filtering groups."""

    field: str
    label: str
    type: str
    values: list[dict[str, str | int | float]]


class SearchMetadata(BaseModel):
    """Metadata wrapper for a search operation."""

    total_results: int = 0
    returned_results: int = 0
    search_time_ms: int = 0
    cached_results: int = 0
    search_id: str | None = None
    user_id: str | None = None
    personalized: bool | None = None
    providers_queried: list[str] | None = None
    provider_errors: dict[str, str] | None = None


def _empty_results() -> list[SearchResultItem]:
    """Typed default factory for results list."""
    return []


def _empty_facets() -> list[SearchFacet]:
    """Typed default factory for facets list."""
    return []


class UnifiedSearchAggregateResponse(BaseModel):
    """Aggregate response for unified search."""

    results: list[SearchResultItem] = Field(default_factory=_empty_results)
    facets: list[SearchFacet] = Field(default_factory=_empty_facets)
    metadata: SearchMetadata
    results_by_type: dict[str, list[SearchResultItem]] | None = None
    did_you_mean: str | None = None
    related_searches: list[str] | None = None
    errors: dict[str, str] | None = None


# Backward-compatible alias expected by core services
UnifiedSearchResponse = UnifiedSearchAggregateResponse


class SearchAnalyticsResponse(BaseModel):
    """Per-day analytics summary for a user's searches."""

    date: str
    total_searches: int
    cache_hit_rate: float
    cache_hits: int
    cache_misses: int
    popular_queries: list[dict[str, str | int]]
