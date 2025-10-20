"""Base models and response schemas for TripSage AI.

This module contains common base models, response patterns, and shared
schemas used across API endpoints and services.
"""

from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import Field

from tripsage_core.models.base_core_model import TripSageModel


# Type variable for generic responses
T = TypeVar("T")


class BaseResponse(TripSageModel):
    """Base response model for all API responses."""

    success: bool = Field(description="Whether the request was successful")
    message: str | None = Field(None, description="Human-readable message")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Response timestamp"
    )


class SuccessResponse(BaseResponse):
    """Standard success response."""

    success: bool = Field(True, description="Always true for success responses")
    data: dict[str, Any] | None = Field(None, description="Response data")


class ErrorResponse(BaseResponse):
    """Standard error response."""

    success: bool = Field(False, description="Always false for error responses")
    error_code: str | None = Field(None, description="Machine-readable error code")
    details: dict[str, Any] | None = Field(None, description="Additional error details")


class PaginationMeta(TripSageModel):
    """Pagination metadata."""

    page: int = Field(ge=1, description="Current page number")
    per_page: int = Field(ge=1, le=100, description="Items per page")
    total_items: int = Field(ge=0, description="Total number of items")
    total_pages: int = Field(ge=0, description="Total number of pages")
    has_next: bool = Field(description="Whether there are more pages")
    has_prev: bool = Field(description="Whether there are previous pages")


class PaginatedResponse(BaseResponse, Generic[T]):
    """Paginated response with metadata."""

    data: list[T] = Field(description="List of items")
    pagination: PaginationMeta = Field(description="Pagination metadata")


class HealthCheckResponse(TripSageModel):
    """Health check response."""

    status: str = Field(description="Service status")
    version: str | None = Field(None, description="Service version")
    uptime: float | None = Field(None, description="Uptime in seconds")
    checks: dict[str, Any] | None = Field(None, description="Individual health checks")


class ValidationErrorDetail(TripSageModel):
    """Validation error detail."""

    field: str = Field(description="Field that failed validation")
    message: str = Field(description="Validation error message")
    value: Any | None = Field(None, description="Invalid value")


class ValidationErrorResponse(ErrorResponse):
    """Validation error response with field details."""

    error_code: str = Field("VALIDATION_ERROR", description="Always VALIDATION_ERROR")
    validation_errors: list[ValidationErrorDetail] = Field(
        description="Field validation errors"
    )


class SearchFilters(TripSageModel):
    """Base search filters."""

    query: str | None = Field(None, description="Search query string")
    limit: int = Field(10, ge=1, le=100, description="Maximum number of results")
    offset: int = Field(0, ge=0, description="Number of results to skip")


class SortOptions(TripSageModel):
    """Sort options for search results."""

    sort_by: str = Field(description="Field to sort by")
    sort_order: str = Field("asc", pattern="^(asc|desc)$", description="Sort order")


class DateFilter(TripSageModel):
    """Date range filter."""

    start_date: datetime | None = Field(None, description="Start date filter")
    end_date: datetime | None = Field(None, description="End date filter")


class PriceFilter(TripSageModel):
    """Price range filter."""

    min_price: float | None = Field(None, ge=0, description="Minimum price")
    max_price: float | None = Field(None, ge=0, description="Maximum price")
    currency: str | None = Field(None, description="Currency code")


class LocationFilter(TripSageModel):
    """Location-based filter."""

    latitude: float | None = Field(None, ge=-90, le=90, description="Latitude")
    longitude: float | None = Field(None, ge=-180, le=180, description="Longitude")
    radius: float | None = Field(None, gt=0, description="Search radius in kilometers")
    city: str | None = Field(None, description="City name")
    country: str | None = Field(None, description="Country name")


class RatingFilter(TripSageModel):
    """Rating filter."""

    min_rating: float | None = Field(None, ge=0, le=5, description="Minimum rating")
    max_rating: float | None = Field(None, ge=0, le=5, description="Maximum rating")


class BulkOperationResponse(BaseResponse):
    """Response for bulk operations."""

    total_processed: int = Field(ge=0, description="Total items processed")
    successful: int = Field(ge=0, description="Successfully processed items")
    failed: int = Field(ge=0, description="Failed items")
    errors: list[dict[str, Any]] | None = Field(
        None, description="List of errors for failed items"
    )


class FileUploadResponse(BaseResponse):
    """Response for file upload operations."""

    file_id: str = Field(description="Unique file identifier")
    filename: str = Field(description="Original filename")
    size: int = Field(ge=0, description="File size in bytes")
    content_type: str = Field(description="MIME content type")
    url: str | None = Field(None, description="File access URL")


class TaskResponse(BaseResponse):
    """Response for asynchronous task operations."""

    task_id: str = Field(description="Unique task identifier")
    status: str = Field(description="Task status")
    progress: float | None = Field(
        None, ge=0, le=100, description="Task progress percentage"
    )
    result: dict[str, Any] | None = Field(None, description="Task result if completed")
    error: str | None = Field(None, description="Error message if failed")
