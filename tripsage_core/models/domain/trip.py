"""
Core trip domain models for TripSage.

This module contains the core business domain models for trip-related
entities. These models represent the essential trip data structures
independent of storage implementation or API specifics.
"""

from typing import List, Optional

from pydantic import Field, field_validator

from tripsage_core.models.base_core_model import TripSageDomainModel
from tripsage_core.models.schemas_common.enums import TripType, TripVisibility


class TripPreferences(TripSageDomainModel):
    """Trip preferences and requirements."""

    accommodation_type: Optional[str] = Field(
        None, description="Preferred accommodation type"
    )
    budget_flexibility: float = Field(
        0.1, description="Budget flexibility as percentage (0.0-1.0)"
    )
    date_flexibility: int = Field(0, description="Date flexibility in days")
    transportation_preferences: List[str] = Field(
        [], description="Preferred transportation types"
    )
    dietary_restrictions: List[str] = Field([], description="Dietary restrictions")
    accessibility_needs: List[str] = Field([], description="Accessibility requirements")
    activity_interests: List[str] = Field(
        [], description="Activity interests and preferences"
    )

    @field_validator("budget_flexibility")
    @classmethod
    def validate_budget_flexibility(cls, v: float) -> float:
        """Validate budget flexibility is between 0 and 1."""
        if v < 0 or v > 1:
            raise ValueError("Budget flexibility must be between 0.0 and 1.0")
        return v

    @field_validator("date_flexibility")
    @classmethod
    def validate_date_flexibility(cls, v: int) -> int:
        """Validate date flexibility is non-negative."""
        if v < 0:
            raise ValueError("Date flexibility must be non-negative")
        return v


class TripLocation(TripSageDomainModel):
    """Location information for trips."""

    name: str = Field(..., description="Location name")
    address: Optional[str] = Field(None, description="Full address")
    city: str = Field(..., description="City")
    state: Optional[str] = Field(None, description="State/province")
    country: str = Field(..., description="Country")
    latitude: Optional[float] = Field(None, description="Latitude coordinate")
    longitude: Optional[float] = Field(None, description="Longitude coordinate")
    timezone: Optional[str] = Field(None, description="Timezone")


class TripBudget(TripSageDomainModel):
    """Budget information for trips."""

    total_budget: float = Field(..., description="Total budget amount")
    currency: str = Field(..., description="Currency code")
    accommodation_budget: Optional[float] = Field(
        None, description="Accommodation budget"
    )
    transportation_budget: Optional[float] = Field(
        None, description="Transportation budget"
    )
    food_budget: Optional[float] = Field(None, description="Food and dining budget")
    activity_budget: Optional[float] = Field(
        None, description="Activities and entertainment budget"
    )
    miscellaneous_budget: Optional[float] = Field(
        None, description="Miscellaneous expenses budget"
    )

    @field_validator("total_budget")
    @classmethod
    def validate_total_budget(cls, v: float) -> float:
        """Validate that total budget is positive."""
        if v <= 0:
            raise ValueError("Total budget must be positive")
        return v

    @field_validator(
        "accommodation_budget",
        "transportation_budget",
        "food_budget",
        "activity_budget",
        "miscellaneous_budget",
    )
    @classmethod
    def validate_category_budget(cls, v: Optional[float]) -> Optional[float]:
        """Validate that category budgets are non-negative if provided."""
        if v is not None and v < 0:
            raise ValueError("Category budget must be non-negative")
        return v


class TripItinerary(TripSageDomainModel):
    """Core trip itinerary business entity.

    This represents the canonical trip itinerary model used throughout
    the TripSage system. It contains all essential information about a
    trip plan independent of the source or storage mechanism.
    """

    id: str = Field(..., description="Itinerary ID")
    name: str = Field(..., description="Trip name")
    description: Optional[str] = Field(None, description="Trip description")
    start_date: str = Field(..., description="Trip start date (YYYY-MM-DD)")
    end_date: str = Field(..., description="Trip end date (YYYY-MM-DD)")
    destinations: List[TripLocation] = Field(..., description="Trip destinations")
    travelers: int = Field(..., description="Number of travelers")
    trip_type: TripType = Field(TripType.LEISURE, description="Type of trip")
    visibility: TripVisibility = Field(
        TripVisibility.PRIVATE, description="Trip visibility"
    )
    budget: TripBudget = Field(..., description="Trip budget information")
    preferences: Optional[TripPreferences] = Field(None, description="Trip preferences")

    # Bookings and reservations
    accommodation_ids: List[str] = Field([], description="Associated accommodation IDs")
    flight_ids: List[str] = Field([], description="Associated flight IDs")
    transportation_ids: List[str] = Field(
        [], description="Associated transportation IDs"
    )
    activity_ids: List[str] = Field([], description="Associated activity IDs")

    # Metadata
    tags: List[str] = Field([], description="Trip tags for categorization")
    notes: Optional[str] = Field(None, description="Additional trip notes")
    created_by: Optional[str] = Field(None, description="Creator user ID")
    collaborators: List[str] = Field([], description="Collaborator user IDs")

    # Source and tracking
    source: Optional[str] = Field(None, description="Source of the itinerary")
    last_modified: Optional[str] = Field(
        None, description="Last modification timestamp"
    )

    @field_validator("travelers")
    @classmethod
    def validate_travelers(cls, v: int) -> int:
        """Validate that travelers is a positive number."""
        if v <= 0:
            raise ValueError("Number of travelers must be positive")
        return v

    @property
    def duration_days(self) -> int:
        """Calculate trip duration in days."""
        from datetime import datetime

        start = datetime.fromisoformat(self.start_date)
        end = datetime.fromisoformat(self.end_date)
        return (end - start).days + 1

    @property
    def budget_per_day(self) -> float:
        """Calculate budget per day."""
        return (
            self.budget.total_budget / self.duration_days
            if self.duration_days > 0
            else 0
        )

    @property
    def budget_per_person(self) -> float:
        """Calculate budget per person."""
        return self.budget.total_budget / self.travelers if self.travelers > 0 else 0

    @property
    def budget_per_person_per_day(self) -> float:
        """Calculate budget per person per day."""
        return self.budget_per_day / self.travelers if self.travelers > 0 else 0

    @property
    def primary_destination(self) -> Optional[TripLocation]:
        """Get the primary destination (first in the list)."""
        return self.destinations[0] if self.destinations else None

    @property
    def is_multi_destination(self) -> bool:
        """Check if the trip has multiple destinations."""
        return len(self.destinations) > 1

    @property
    def has_bookings(self) -> bool:
        """Check if the trip has any bookings."""
        return bool(
            self.accommodation_ids
            or self.flight_ids
            or self.transportation_ids
            or self.activity_ids
        )

    @property
    def booking_completion_percentage(self) -> float:
        """Calculate booking completion percentage."""
        total_categories = 4  # accommodations, flights, transportation, activities
        completed_categories = sum(
            [
                bool(self.accommodation_ids),
                bool(self.flight_ids),
                bool(self.transportation_ids),
                bool(self.activity_ids),
            ]
        )
        return (completed_categories / total_categories) * 100
