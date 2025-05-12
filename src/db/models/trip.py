"""
Trip model for TripSage.

This module provides the Trip model for the TripSage database.
"""

from datetime import date
from enum import Enum
from typing import Any, ClassVar, Dict, Optional

from pydantic import Field, field_validator, model_validator

from src.db.models.base import BaseDBModel


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


class Trip(BaseDBModel):
    """
    Trip model for TripSage.

    Attributes:
        id: Unique identifier for the trip
        name: Name or title of the trip
        start_date: Trip start date
        end_date: Trip end date
        destination: Primary destination of the trip
        budget: Total budget allocated for the trip
        travelers: Number of travelers for the trip
        status: Current status of the trip (planning, booked, completed, canceled)
        trip_type: Type of trip (leisure, business, family, solo, other)
        flexibility: JSON containing flexibility parameters for dates, budget, etc.
        created_at: Timestamp when the trip was created
        updated_at: Timestamp when the trip was last updated
    """

    __tablename__: ClassVar[str] = "trips"

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
        # such as country lookup or geocoding
        domestic_indicators = ["USA", "United States", "U.S.", "U.S.A."]
        return not any(
            indicator in self.destination for indicator in domestic_indicators
        )

    def to_dict(self, exclude_none: bool = True) -> Dict[str, Any]:
        """Convert the trip to a dictionary for database operations."""
        data = super().to_dict(exclude_none=exclude_none)

        # Convert enum values to strings for the database
        if "status" in data and isinstance(data["status"], TripStatus):
            data["status"] = data["status"].value
        if "trip_type" in data and isinstance(data["trip_type"], TripType):
            data["trip_type"] = data["trip_type"].value

        return data

    @classmethod
    def from_row(cls, row: Dict[str, Any]) -> "Trip":
        """Create a Trip instance from a database row."""
        # Convert string status and trip_type to enum values
        if "status" in row and isinstance(row["status"], str):
            try:
                row["status"] = TripStatus(row["status"])
            except ValueError:
                # Handle invalid status values
                row["status"] = TripStatus.PLANNING

        if "trip_type" in row and isinstance(row["trip_type"], str):
            try:
                row["trip_type"] = TripType(row["trip_type"])
            except ValueError:
                # Handle invalid trip_type values
                row["trip_type"] = TripType.OTHER

        return super().from_row(row)
