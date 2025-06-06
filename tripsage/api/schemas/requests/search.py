"""Search request schemas using Pydantic V2.

This module defines Pydantic models for search-related API requests.
"""

from datetime import date
from typing import Dict, List, Optional, Union

from pydantic import BaseModel, Field


class SearchFilters(BaseModel):
    """Common search filters across all types."""
    
    price_min: Optional[float] = Field(None, ge=0, description="Minimum price")
    price_max: Optional[float] = Field(None, ge=0, description="Maximum price")
    rating_min: Optional[float] = Field(None, ge=0, le=5, description="Minimum rating")
    
    # Location filters
    latitude: Optional[float] = Field(None, ge=-90, le=90, description="Center latitude")
    longitude: Optional[float] = Field(None, ge=-180, le=180, description="Center longitude")
    radius_km: Optional[float] = Field(None, ge=0, le=100, description="Search radius in kilometers")
    
    # Additional filters as key-value pairs
    custom_filters: Optional[Dict[str, Union[str, int, float, bool, List[str]]]] = Field(
        None, description="Additional type-specific filters"
    )


class UnifiedSearchRequest(BaseModel):
    """Unified search request across multiple resource types."""
    
    query: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Search query string",
    )
    
    types: Optional[List[str]] = Field(
        None,
        description="Resource types to search (destination, flight, accommodation, activity)",
    )
    
    # Common parameters
    destination: Optional[str] = Field(
        None,
        description="Destination for location-based searches",
    )
    start_date: Optional[date] = Field(
        None,
        description="Start date for date-based searches",
    )
    end_date: Optional[date] = Field(
        None,
        description="End date for date-based searches",
    )
    
    # Flight-specific (optional)
    origin: Optional[str] = Field(
        None,
        description="Origin location for flight searches",
    )
    
    # Traveler counts
    adults: Optional[int] = Field(1, ge=1, le=20, description="Number of adults")
    children: Optional[int] = Field(0, ge=0, le=20, description="Number of children")
    infants: Optional[int] = Field(0, ge=0, le=10, description="Number of infants")
    
    # Filters
    filters: Optional[SearchFilters] = Field(
        None,
        description="Search filters to apply",
    )
    
    # Search preferences
    sort_by: Optional[str] = Field(
        None,
        description="Sort field (relevance, price, rating, distance)",
    )
    sort_order: Optional[str] = Field(
        "desc",
        pattern="^(asc|desc)$",
        description="Sort order",
    )
    
    # User context (for personalization)
    user_preferences: Optional[Dict[str, Union[str, int, float, bool]]] = Field(
        None,
        description="User preferences for result personalization",
    )