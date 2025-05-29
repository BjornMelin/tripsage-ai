"""
MCP model classes for TripSage.

This module provides the MCP-related model classes used for communication with
MCP (Model Context Protocol) servers and validation of requests and responses.
"""

from datetime import datetime
from typing import Any, Dict, Generic, Optional, TypeVar

from pydantic import (
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from tripsage_core.models.base_core_model import TripSageModel


class MCPRequestBase(TripSageModel):
    """Base model for all MCP requests."""

    model_config = ConfigDict(
        extra="ignore",  # Allow extra fields in requests for forward compatibility
        validate_assignment=True,  # Validate on attribute assignment
    )

    # Add common request tracing/logging fields
    request_id: Optional[str] = Field(
        None, description="Optional unique request ID for tracing"
    )
    timestamp: Optional[datetime] = Field(None, description="Request timestamp")


class MCPResponseBase(TripSageModel):
    """Base model for all MCP responses."""

    model_config = ConfigDict(
        extra="ignore",  # Allow extra fields in responses for forward compatibility
    )

    # Common response fields
    success: bool = Field(True, description="Whether the request was successful")
    error: Optional[str] = Field(
        None, description="Error message if the request failed"
    )
    request_id: Optional[str] = Field(None, description="The request ID for tracing")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Response timestamp"
    )


class ErrorResponse(MCPResponseBase):
    """Standard error response model."""

    success: bool = Field(False, description="Always false for error responses")
    error: str = Field(..., description="Error message")
    error_type: Optional[str] = Field(None, description="Type of error")
    error_details: Optional[Dict[str, Any]] = Field(
        None, description="Additional error details"
    )


class PaginatedResponseBase(MCPResponseBase):
    """Base model for paginated responses."""

    page: int = Field(1, description="Current page number")
    page_size: int = Field(..., description="Number of items per page")
    total_items: Optional[int] = Field(None, description="Total number of items")
    total_pages: Optional[int] = Field(None, description="Total number of pages")
    has_next: bool = Field(False, description="Whether there is a next page")
    has_previous: bool = Field(False, description="Whether there is a previous page")


class PaginatedRequest(MCPRequestBase):
    """Base model for paginated requests."""

    page: int = Field(1, ge=1, description="Page number to retrieve")
    page_size: int = Field(20, ge=1, le=100, description="Number of items per page")

    @field_validator("page")
    @classmethod
    def validate_page(cls, value: int) -> int:
        """Validate page number is positive."""
        if value < 1:
            raise ValueError("Page number must be at least 1")
        return value

    @field_validator("page_size")
    @classmethod
    def validate_page_size(cls, value: int) -> int:
        """Validate page size within acceptable range."""
        if value < 1:
            raise ValueError("Page size must be at least 1")
        if value > 100:
            raise ValueError("Page size must be at most 100")
        return value


class DateRangeRequest(MCPRequestBase):
    """Base model for date range requests."""

    start_date: datetime = Field(..., description="Start date")
    end_date: datetime = Field(..., description="End date")

    @model_validator(mode="after")
    def validate_date_range(self) -> "DateRangeRequest":
        """Validate start date is before end date."""
        if self.start_date > self.end_date:
            raise ValueError("Start date must be before end date")
        return self


class SearchRequest(MCPRequestBase):
    """Base model for search requests."""

    query: str = Field(..., min_length=1, description="Search query")
    limit: int = Field(
        10, ge=1, le=100, description="Maximum number of results to return"
    )
    offset: Optional[int] = Field(None, ge=0, description="Offset for pagination")


class LocationRequest(MCPRequestBase):
    """Base model for location-based requests."""

    latitude: float = Field(..., ge=-90, le=90, description="Latitude")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude")

    @field_validator("latitude")
    @classmethod
    def validate_latitude(cls, value: float) -> float:
        """Validate latitude is within valid range."""
        if value < -90 or value > 90:
            raise ValueError("Latitude must be between -90 and 90")
        return value

    @field_validator("longitude")
    @classmethod
    def validate_longitude(cls, value: float) -> float:
        """Validate longitude is within valid range."""
        if value < -180 or value > 180:
            raise ValueError("Longitude must be between -180 and 180")
        return value


class CacheConfig(TripSageModel):
    """Configuration model for caching behavior."""

    use_cache: bool = Field(True, description="Whether to use cache")
    ttl_seconds: int = Field(
        3600, ge=0, description="Time-to-live in seconds (0 = indefinite)"
    )
    cache_key_prefix: Optional[str] = Field(None, description="Prefix for cache keys")


class TimeZoneRequest(MCPRequestBase):
    """Base model for timezone-related requests."""

    timezone: str = Field(
        ..., min_length=1, description="IANA timezone name (e.g. 'America/New_York')"
    )


T = TypeVar("T")


class GenericResponse(MCPResponseBase, Generic[T]):
    """Generic response model for any data type."""

    data: T = Field(..., description="Response data")
