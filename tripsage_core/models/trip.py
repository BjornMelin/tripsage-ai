"""Unified Trip model for TripSage.

This module provides the single, modern Trip model used across the entire application.
It uses UUID as the primary key and includes all enhanced features like visibility,
tags, preferences, and detailed budget breakdown.
"""

from datetime import date, datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import Field, field_validator, model_validator

from tripsage_core.models.base_core_model import TripSageModel
from tripsage_core.models.schemas_common.enums import TripStatus, TripType, TripVisibility


class BudgetBreakdown(TripSageModel):
    """Detailed budget breakdown by category."""

    accommodation: float = Field(default=0.0, ge=0, description="Accommodation budget")
    transportation: float = Field(default=0.0, ge=0, description="Transportation budget")
    food: float = Field(default=0.0, ge=0, description="Food budget")
    activities: float = Field(default=0.0, ge=0, description="Activities budget")
    miscellaneous: float = Field(default=0.0, ge=0, description="Miscellaneous budget")


class EnhancedBudget(TripSageModel):
    """Enhanced budget structure with breakdown."""

    total: float = Field(..., ge=0, description="Total budget amount")
    currency: str = Field(default="USD", description="Currency code")
    spent: float = Field(default=0.0, ge=0, description="Amount spent")
    breakdown: BudgetBreakdown = Field(
        default_factory=BudgetBreakdown, description="Budget breakdown by category"
    )


class TripPreferences(TripSageModel):
    """Extended trip preferences and requirements."""

    budget_flexibility: float = Field(
        0.1, ge=0, le=1, description="Budget flexibility as percentage (0.0-1.0)"
    )
    date_flexibility: int = Field(0, ge=0, description="Date flexibility in days")
    destination_flexibility: bool = Field(
        False, description="Whether destination is flexible"
    )
    accommodation_preferences: Dict[str, Any] = Field(
        default_factory=dict, description="Accommodation preferences"
    )
    transportation_preferences: Dict[str, Any] = Field(
        default_factory=dict, description="Transportation preferences"
    )
    activity_preferences: List[str] = Field(
        default_factory=list, description="Activity preferences"
    )
    dietary_restrictions: List[str] = Field(
        default_factory=list, description="Dietary restrictions"
    )
    accessibility_needs: List[str] = Field(
        default_factory=list, description="Accessibility requirements"
    )


class Trip(TripSageModel):
    """Unified Trip model for TripSage.

    This is the single Trip model used across the entire application.
    It uses UUID as the primary key and includes all modern features.
    """

    # Primary identifier
    id: UUID = Field(default_factory=uuid4, description="Trip UUID identifier")
    user_id: UUID = Field(..., description="Owner user UUID")

    # Core Trip Information
    title: str = Field(..., min_length=1, max_length=200, description="Trip title")
    description: Optional[str] = Field(None, max_length=2000, description="Trip description")
    start_date: date = Field(..., description="Trip start date")
    end_date: date = Field(..., description="Trip end date")
    destination: str = Field(..., description="Primary destination of the trip")

    # Budget Information
    budget_breakdown: EnhancedBudget = Field(
        ..., description="Enhanced budget with breakdown"
    )

    # Trip Details
    travelers: int = Field(default=1, ge=1, description="Number of travelers")
    status: TripStatus = Field(
        default=TripStatus.PLANNING, description="Current status of the trip"
    )
    trip_type: TripType = Field(
        default=TripType.LEISURE, description="Type of trip"
    )

    # Enhanced Features
    visibility: TripVisibility = Field(
        default=TripVisibility.PRIVATE,
        description="Trip visibility (private/shared/public)",
    )
    tags: List[str] = Field(
        default_factory=list, max_items=20, description="Trip tags"
    )
    preferences_extended: TripPreferences = Field(
        default_factory=TripPreferences, description="Extended preferences"
    )

    # Additional metadata
    notes: List[Dict[str, Any]] = Field(
        default_factory=list, description="Trip notes"
    )
    search_metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Search and discovery metadata"
    )

    # Timestamps
    created_at: datetime = Field(
        default_factory=lambda: datetime.utcnow(), description="Creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.utcnow(), description="Last update timestamp"
    )

    @model_validator(mode="after")
    def validate_dates(self) -> "Trip":
        """Validate that end_date is not before start_date."""
        if self.end_date < self.start_date:
            raise ValueError("End date must not be before start date")
        return self

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: List[str]) -> List[str]:
        """Validate and clean trip tags."""
        # Remove duplicates and empty strings
        cleaned = list(set(tag.strip() for tag in v if tag.strip()))
        # max_items constraint already enforces the limit
        return cleaned

    @property
    def duration_days(self) -> int:
        """Get the duration of the trip in days."""
        return (self.end_date - self.start_date).days + 1

    @property
    def budget_per_day(self) -> float:
        """Get the budget per day for the trip."""
        return (
            self.budget_breakdown.total / self.duration_days
            if self.duration_days > 0
            else 0
        )

    @property
    def budget_per_person(self) -> float:
        """Get the budget per person for the trip."""
        return (
            self.budget_breakdown.total / self.travelers
            if self.travelers > 0
            else 0
        )

    @property
    def budget_utilization(self) -> float:
        """Get budget utilization percentage."""
        if self.budget_breakdown.total <= 0:
            return 0.0
        return min(
            (self.budget_breakdown.spent / self.budget_breakdown.total) * 100, 100.0
        )

    @property
    def remaining_budget(self) -> float:
        """Get remaining budget amount."""
        return max(self.budget_breakdown.total - self.budget_breakdown.spent, 0.0)

    @property
    def is_shared(self) -> bool:
        """Check if the trip is shared with others."""
        return self.visibility in [TripVisibility.SHARED, TripVisibility.PUBLIC]

    @property
    def is_active(self) -> bool:
        """Check if the trip is in an active state."""
        return self.status in [TripStatus.PLANNING, TripStatus.BOOKED]

    @property
    def is_completed(self) -> bool:
        """Check if the trip is completed."""
        return self.status == TripStatus.COMPLETED

    @property
    def is_cancelable(self) -> bool:
        """Check if the trip can be canceled."""
        return self.status in [TripStatus.PLANNING, TripStatus.BOOKED]

    def can_modify(self) -> bool:
        """Check if the trip can be modified."""
        # Trips can be modified if they're in planning or booked status
        # and haven't started yet
        if self.status not in [TripStatus.PLANNING, TripStatus.BOOKED]:
            return False
        return date.today() < self.start_date

    def update_status(self, new_status: TripStatus) -> bool:
        """Update the trip status with validation.

        Args:
            new_status: The new status to set

        Returns:
            True if the status was updated, False if invalid transition
        """
        # Define valid status transitions
        valid_transitions = {
            TripStatus.PLANNING: [TripStatus.BOOKED, TripStatus.CANCELLED],
            TripStatus.BOOKED: [TripStatus.COMPLETED, TripStatus.CANCELLED],
            TripStatus.COMPLETED: [],  # Cannot change from completed
            TripStatus.CANCELLED: [],  # Cannot change from cancelled
        }

        if new_status in valid_transitions.get(self.status, []):
            self.status = new_status
            self.updated_at = datetime.utcnow()
            return True
        return False

    def add_tag(self, tag: str) -> bool:
        """Add a tag to the trip.

        Args:
            tag: Tag to add

        Returns:
            True if tag was added, False if already exists or limit reached
        """
        cleaned_tag = tag.strip()
        if not cleaned_tag or cleaned_tag in self.tags:
            return False
        if len(self.tags) >= 20:
            return False
        self.tags.append(cleaned_tag)
        self.updated_at = datetime.utcnow()
        return True

    def remove_tag(self, tag: str) -> bool:
        """Remove a tag from the trip.

        Args:
            tag: Tag to remove

        Returns:
            True if tag was removed, False if not found
        """
        cleaned_tag = tag.strip()
        if cleaned_tag in self.tags:
            self.tags.remove(cleaned_tag)
            self.updated_at = datetime.utcnow()
            return True
        return False


# Export the models
__all__ = [
    "Trip",
    "EnhancedBudget",
    "BudgetBreakdown",
    "TripPreferences",
]