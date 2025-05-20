"""Trip model for TripSage.

This module provides the Trip model with business logic validation,
used across different storage backends.
"""

from datetime import date
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import Field, field_validator, model_validator

from tripsage.models.base import TripSageModel


class TripStatus(str, Enum):
    """Enum for trip status values."""

    PLANNING = "planning"
    BOOKED = "booked"
    COMPLETED = "completed"
    CANCELED = "canceled"


class TripType(str, Enum):
    """Enum for trip type values."""

    LEISURE = "leisure"
    BUSINESS = "business"
    FAMILY = "family"
    SOLO = "solo"
    OTHER = "other"


class TripVisibility(str, Enum):
    """Enum for trip visibility values."""

    PRIVATE = "private"
    PUBLIC = "public"
    SHARED = "shared"


class Trip(TripSageModel):
    """Trip model for TripSage.

    Attributes:
        id: Unique identifier for the trip
        name: Name or title of the trip
        start_date: Trip start date
        end_date: Trip end date
        destination: Primary destination of the trip
        budget: Total budget allocated for the trip
        travelers: Number of travelers for the trip
        status: Current status of the trip
        trip_type: Type of trip
        flexibility: JSON containing flexibility parameters
    """

    id: Optional[int] = Field(None, description="Unique identifier")
    name: str = Field(..., description="Name or title of the trip")
    start_date: date = Field(..., description="Trip start date")
    end_date: date = Field(..., description="Trip end date")
    destination: str = Field(..., description="Primary destination of the trip")
    budget: float = Field(..., description="Total budget allocated for the trip")
    travelers: int = Field(..., description="Number of travelers for the trip")
    status: TripStatus = Field(
        TripStatus.PLANNING, description="Current status of the trip"
    )
    trip_type: TripType = Field(TripType.LEISURE, description="Type of trip")
    flexibility: Optional[Dict[str, Any]] = Field(
        None, description="Flexibility parameters"
    )

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
    def validate_budget(cls, v: float) -> float:
        """Validate that budget is a positive number."""
        if v <= 0:
            raise ValueError("Budget must be positive")
        return v

    @property
    def duration_days(self) -> int:
        """Get the duration of the trip in days."""
        return (self.end_date - self.start_date).days + 1

    @property
    def budget_per_day(self) -> float:
        """Get the budget per day for the trip."""
        return self.budget / self.duration_days if self.duration_days > 0 else 0

    @property
    def budget_per_person(self) -> float:
        """Get the budget per person for the trip."""
        return self.budget / self.travelers if self.travelers > 0 else 0

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
            TripStatus.PLANNING: [TripStatus.BOOKED, TripStatus.CANCELED],
            TripStatus.BOOKED: [TripStatus.COMPLETED, TripStatus.CANCELED],
            TripStatus.COMPLETED: [],  # Cannot change from completed
            TripStatus.CANCELED: [],  # Cannot change from canceled
        }

        if new_status in valid_transitions.get(self.status, []):
            self.status = new_status
            return True
        return False
