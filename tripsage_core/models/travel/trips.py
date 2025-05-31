"""Trip domain models.

This module consolidates all trip-related models including domain logic
and database representations following Pydantic v2 best practices.
"""

from datetime import date
from typing import Any, Dict, List, Optional

from pydantic import Field, field_validator, model_validator

from tripsage_core.models.base_core_model import TripSageDomainModel, TripSageModel
from tripsage_core.models.schemas_common.enums import (
    TripStatus,
    TripType,
    TripVisibility,
)
from tripsage_core.models.schemas_common.geographic import Coordinates


class TripPlan(TripSageDomainModel):
    """Domain model for trip planning with business logic."""

    name: str = Field(..., description="Name or title of the trip")
    start_date: date = Field(..., description="Trip start date")
    end_date: date = Field(..., description="Trip end date")
    destination: str = Field(..., description="Primary destination of the trip")
    budget: float = Field(..., description="Total budget allocated for the trip")
    travelers: int = Field(..., description="Number of travelers for the trip")
    trip_type: TripType = Field(TripType.LEISURE, description="Type of trip")
    flexibility: Optional[Dict[str, Any]] = Field(
        None, description="Flexibility parameters for dates, budget, etc."
    )
    description: Optional[str] = Field(None, description="Trip description or notes")

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

    @model_validator(mode="after")
    def validate_dates(self) -> "TripPlan":
        """Validate that end_date is not before start_date."""
        if self.end_date < self.start_date:
            raise ValueError("End date must not be before start date")
        return self

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
    def budget_per_person_per_day(self) -> float:
        """Get the budget per person per day for the trip."""
        return self.budget_per_day / self.travelers if self.travelers > 0 else 0


class Trip(TripSageModel):
    """Database model for trip bookings and management."""

    id: Optional[int] = Field(None, description="Unique identifier")
    user_id: Optional[int] = Field(None, description="User who owns the trip")
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
    visibility: TripVisibility = Field(
        TripVisibility.PRIVATE, description="Trip visibility/sharing level"
    )
    flexibility: Optional[Dict[str, Any]] = Field(
        None, description="Flexibility parameters"
    )
    destination_coordinates: Optional[Coordinates] = Field(
        None, description="Coordinates of the primary destination"
    )
    accommodations: Optional[List[int]] = Field(
        None, description="IDs of associated accommodations"
    )
    flights: Optional[List[int]] = Field(None, description="IDs of associated flights")
    activities: Optional[List[int]] = Field(
        None, description="IDs of associated activities"
    )
    transportation: Optional[List[int]] = Field(
        None, description="IDs of associated transportation"
    )
    notes: Optional[str] = Field(None, description="Trip notes and additional info")
    actual_cost: Optional[float] = Field(
        None, description="Actual cost spent on the trip"
    )
    tags: Optional[List[str]] = Field(None, description="Tags for categorization")

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

    @field_validator("actual_cost")
    @classmethod
    def validate_actual_cost(cls, v: Optional[float]) -> Optional[float]:
        """Validate that actual cost is non-negative if provided."""
        if v is not None and v < 0:
            raise ValueError("Actual cost must be non-negative")
        return v

    @model_validator(mode="after")
    def validate_dates(self) -> "Trip":
        """Validate that end_date is not before start_date."""
        if self.end_date < self.start_date:
            raise ValueError("End date must not be before start date")
        return self

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
    def budget_per_person_per_day(self) -> float:
        """Get the budget per person per day for the trip."""
        return self.budget_per_day / self.travelers if self.travelers > 0 else 0

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
        return self.status in [
            TripStatus.PLANNING,
            TripStatus.BOOKED,
            TripStatus.IN_PROGRESS,
        ]

    @property
    def is_completed(self) -> bool:
        """Check if the trip is completed."""
        return self.status == TripStatus.COMPLETED

    @property
    def is_cancelable(self) -> bool:
        """Check if the trip can be canceled."""
        return self.status in [TripStatus.PLANNING, TripStatus.BOOKED]

    @property
    def is_modifiable(self) -> bool:
        """Check if the trip can be modified."""
        # Trips can be modified if they're in planning or booked status
        # and haven't started yet
        if self.status not in [TripStatus.PLANNING, TripStatus.BOOKED]:
            return False
        from datetime import date as date_type

        return date_type.today() < self.start_date

    @property
    def budget_variance(self) -> Optional[float]:
        """Calculate budget variance (actual vs planned)."""
        if self.actual_cost is None:
            return None
        return self.actual_cost - self.budget

    @property
    def budget_variance_percentage(self) -> Optional[float]:
        """Calculate budget variance as percentage."""
        if self.actual_cost is None or self.budget == 0:
            return None
        return (self.budget_variance / self.budget) * 100

    @property
    def is_over_budget(self) -> bool:
        """Check if the trip is over budget."""
        if self.actual_cost is None:
            return False
        return self.actual_cost > self.budget

    @property
    def has_accommodations(self) -> bool:
        """Check if the trip has any accommodations."""
        return bool(self.accommodations)

    @property
    def has_flights(self) -> bool:
        """Check if the trip has any flights."""
        return bool(self.flights)

    @property
    def has_activities(self) -> bool:
        """Check if the trip has any activities."""
        return bool(self.activities)

    @property
    def has_transportation(self) -> bool:
        """Check if the trip has any transportation."""
        return bool(self.transportation)

    @property
    def completion_percentage(self) -> float:
        """Calculate completion percentage based on bookings."""
        # Simple metric based on whether basic components are booked
        components = [
            self.has_accommodations,
            self.has_flights,
            self.has_activities,
            self.has_transportation,
        ]
        booked_components = sum(components)
        total_components = len(components)

        if total_components == 0:
            return 0.0

        return (booked_components / total_components) * 100

    def can_modify(self) -> bool:
        """Check if the trip can be modified."""
        return self.is_modifiable

    def add_accommodation(self, accommodation_id: int) -> None:
        """Add an accommodation to the trip."""
        if self.accommodations is None:
            self.accommodations = []
        if accommodation_id not in self.accommodations:
            self.accommodations.append(accommodation_id)

    def remove_accommodation(self, accommodation_id: int) -> bool:
        """Remove an accommodation from the trip."""
        if self.accommodations and accommodation_id in self.accommodations:
            self.accommodations.remove(accommodation_id)
            return True
        return False

    def add_flight(self, flight_id: int) -> None:
        """Add a flight to the trip."""
        if self.flights is None:
            self.flights = []
        if flight_id not in self.flights:
            self.flights.append(flight_id)

    def remove_flight(self, flight_id: int) -> bool:
        """Remove a flight from the trip."""
        if self.flights and flight_id in self.flights:
            self.flights.remove(flight_id)
            return True
        return False

    def add_tag(self, tag: str) -> None:
        """Add a tag to the trip."""
        if self.tags is None:
            self.tags = []
        if tag not in self.tags:
            self.tags.append(tag)

    def remove_tag(self, tag: str) -> bool:
        """Remove a tag from the trip."""
        if self.tags and tag in self.tags:
            self.tags.remove(tag)
            return True
        return False

    def update_status(self, new_status: TripStatus) -> bool:
        """Update the trip status with validation.

        Args:
            new_status: The new status to set

        Returns:
            True if the status was updated, False if invalid transition
        """
        # Define valid status transitions
        valid_transitions = {
            TripStatus.PLANNING: [
                TripStatus.BOOKED,
                TripStatus.CANCELED,
                TripStatus.CANCELLED,
            ],
            TripStatus.BOOKED: [
                TripStatus.IN_PROGRESS,
                TripStatus.COMPLETED,
                TripStatus.CANCELED,
                TripStatus.CANCELLED,
            ],
            TripStatus.IN_PROGRESS: [
                TripStatus.COMPLETED,
                TripStatus.CANCELED,
                TripStatus.CANCELLED,
            ],
            TripStatus.COMPLETED: [],  # Cannot change from completed
            TripStatus.CANCELED: [],  # Cannot change from canceled
            TripStatus.CANCELLED: [],  # Cannot change from cancelled
        }

        if new_status in valid_transitions.get(self.status, []):
            self.status = new_status
            return True
        return False

    def set_actual_cost(self, cost: float) -> None:
        """Set the actual cost of the trip."""
        if cost < 0:
            raise ValueError("Actual cost must be non-negative")
        self.actual_cost = cost
