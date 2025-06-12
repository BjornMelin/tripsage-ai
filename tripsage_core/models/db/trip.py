"""Trip model for TripSage.

This module provides the Trip model with business logic validation,
used across different storage backends. Enhanced with schema alignment
to support visibility, tags, preferences, and dual ID system.
"""

from datetime import date
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from tripsage_core.models.base_core_model import TripSageModel
from tripsage_core.models.schemas_common.enums import (
    TripStatus,
    TripType,
)


class TripVisibility(str):
    """Trip visibility options."""
    PRIVATE = "private"
    SHARED = "shared"
    PUBLIC = "public"


class TripBudget(TripSageModel):
    """Enhanced budget structure for trips."""
    
    total: float = Field(..., ge=0, description="Total budget amount")
    currency: str = Field(default="USD", description="Currency code")
    spent: float = Field(default=0.0, ge=0, description="Amount spent")
    breakdown: Optional[Dict[str, float]] = Field(
        default_factory=dict, description="Budget breakdown by category"
    )


class Trip(TripSageModel):
    """Enhanced Trip model for TripSage with schema alignment.

    Attributes:
        id: Legacy BIGINT identifier for backward compatibility
        uuid_id: New UUID identifier for future use
        title: Trip title (renamed from 'name' for consistency)
        description: Detailed trip description
        start_date: Trip start date
        end_date: Trip end date
        destination: Primary destination of the trip
        budget: Total budget allocated for the trip (legacy)
        enhanced_budget: Detailed budget structure
        travelers: Number of travelers for the trip
        status: Current status of the trip
        trip_type: Type of trip
        visibility: Trip visibility (private/shared/public)
        tags: List of trip tags
        preferences: Enhanced preferences structure
        flexibility: JSON containing flexibility parameters (legacy)
    """

    # ID Fields - Supporting both legacy and new systems
    id: Optional[int] = Field(None, description="Legacy BIGINT identifier")
    uuid_id: Optional[UUID] = Field(None, description="New UUID identifier")
    
    # Core Trip Information
    title: str = Field(..., description="Trip title")
    description: Optional[str] = Field(None, description="Trip description")
    start_date: date = Field(..., description="Trip start date")
    end_date: date = Field(..., description="Trip end date")
    destination: str = Field(..., description="Primary destination of the trip")
    
    # Budget Information - Supporting both legacy and enhanced
    budget: Optional[float] = Field(None, description="Legacy total budget")
    enhanced_budget: Optional[TripBudget] = Field(None, description="Enhanced budget structure")
    currency: str = Field(default="USD", description="Budget currency")
    spent_amount: float = Field(default=0.0, ge=0, description="Amount spent")
    
    # Trip Details
    travelers: int = Field(..., description="Number of travelers for the trip")
    status: TripStatus = Field(
        TripStatus.PLANNING, description="Current status of the trip"
    )
    trip_type: TripType = Field(TripType.LEISURE, description="Type of trip")
    
    # Enhanced Fields
    visibility: str = Field(
        default=TripVisibility.PRIVATE, 
        description="Trip visibility (private/shared/public)"
    )
    tags: List[str] = Field(
        default_factory=list, description="Trip tags"
    )
    preferences: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Enhanced preferences structure"
    )
    
    # Legacy Compatibility
    flexibility: Optional[Dict[str, Any]] = Field(
        None, description="Legacy flexibility parameters"
    )
    
    # Backward Compatibility Properties
    @property
    def name(self) -> str:
        """Legacy name property for backward compatibility."""
        return self.title
    
    @name.setter
    def name(self, value: str) -> None:
        """Allow setting title via legacy name property."""
        self.title = value

    @model_validator(mode="after")
    def validate_dates(self) -> "Trip":
        """Validate that end_date is not before start_date."""
        if self.end_date < self.start_date:
            raise ValueError("End date must not be before start date")
        return self

    @field_validator("travelers")
    @classmethod
    def validate_travelers(cls, v: int) -> int:
        """Validate that travelers is a positive number."""
        if v <= 0:
            raise ValueError("Number of travelers must be positive")
        return v

    @field_validator("budget")
    @classmethod
    def validate_budget(cls, v: Optional[float]) -> Optional[float]:
        """Validate that budget is a positive number if provided."""
        if v is not None and v <= 0:
            raise ValueError("Budget must be positive")
        return v
    
    @field_validator("visibility")
    @classmethod
    def validate_visibility(cls, v: str) -> str:
        """Validate visibility value."""
        valid_values = [TripVisibility.PRIVATE, TripVisibility.SHARED, TripVisibility.PUBLIC]
        if v not in valid_values:
            raise ValueError(f"Visibility must be one of: {valid_values}")
        return v
    
    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: List[str]) -> List[str]:
        """Validate and clean trip tags."""
        # Remove duplicates and empty strings
        return list(set(tag.strip() for tag in v if tag.strip()))

    @property
    def duration_days(self) -> int:
        """Get the duration of the trip in days."""
        return (self.end_date - self.start_date).days + 1

    @property
    def effective_budget(self) -> float:
        """Get the effective budget amount from either source."""
        if self.enhanced_budget:
            return self.enhanced_budget.total
        return self.budget or 0.0
    
    @property
    def budget_per_day(self) -> float:
        """Get the budget per day for the trip."""
        effective_budget = self.effective_budget
        return effective_budget / self.duration_days if self.duration_days > 0 else 0

    @property
    def budget_per_person(self) -> float:
        """Get the budget per person for the trip."""
        effective_budget = self.effective_budget
        return effective_budget / self.travelers if self.travelers > 0 else 0
    
    @property
    def budget_utilization(self) -> float:
        """Get budget utilization percentage."""
        effective_budget = self.effective_budget
        if effective_budget <= 0:
            return 0.0
        return min((self.spent_amount / effective_budget) * 100, 100.0)
    
    @property
    def remaining_budget(self) -> float:
        """Get remaining budget amount."""
        return max(self.effective_budget - self.spent_amount, 0.0)
    
    @property
    def trip_id(self) -> Union[str, int, None]:
        """Get the appropriate trip ID (UUID if available, otherwise BIGINT)."""
        return str(self.uuid_id) if self.uuid_id else self.id
    
    @property
    def is_shared(self) -> bool:
        """Check if the trip is shared with others."""
        return self.visibility in [TripVisibility.SHARED, TripVisibility.PUBLIC]
    
    @property
    def tag_count(self) -> int:
        """Get the number of tags associated with the trip."""
        return len(self.tags)

    @property
    def is_international(self) -> bool:
        """Determine if the trip is likely international based on destination."""
        # This is a simple approximation
        # In a real implementation, this would use more sophisticated checks
        domestic_indicators = ["USA", "United States", "U.S.", "U.S.A."]
        return not any(
            indicator in self.destination for indicator in domestic_indicators
        )

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
        from datetime import date as date_type

        return date_type.today() < self.start_date

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
            return True
        return False
