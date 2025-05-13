"""
Database models for TripSage.

This module provides database models for the TripSage application.
"""

from datetime import date, datetime
from enum import Enum
from typing import Any, ClassVar, Dict, List, Optional, Type, TypeVar

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)

# Define a type variable for the model
T = TypeVar("T", bound="BaseDBModel")


class BaseDBModel(BaseModel):
    """
    Base class for all database models.

    This class provides common fields and functionality for all database models.
    """

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        validate_assignment=True,
        extra="ignore",
    )

    # Table name in the database - to be overridden by subclasses
    __tablename__: ClassVar[str] = ""

    # Primary key field name - to be overridden by subclasses if different
    __primary_key__: ClassVar[str] = "id"

    id: Optional[int] = Field(None, description="Unique identifier")
    created_at: Optional[datetime] = Field(
        None, description="Timestamp when the record was created"
    )
    updated_at: Optional[datetime] = Field(
        None, description="Timestamp when the record was last updated"
    )

    @property
    def is_new(self) -> bool:
        """Check if this is a new record (no ID assigned yet)."""
        return self.id is None

    @property
    def pk_value(self) -> Optional[Any]:
        """Get the value of the primary key field."""
        return getattr(self, self.__class__.__primary_key__)

    def to_dict(self, exclude_none: bool = True) -> Dict[str, Any]:
        """
        Convert the model to a dictionary suitable for database operations.

        Args:
            exclude_none: Whether to exclude None values from the dictionary.

        Returns:
            Dictionary representation of the model.
        """
        # Convert to dict using model_dump
        model_dict = self.model_dump(exclude_none=exclude_none)

        # Handle nested models
        for key, value in model_dict.items():
            if isinstance(value, BaseDBModel):
                model_dict[key] = value.to_dict(exclude_none=exclude_none)
            elif (
                isinstance(value, list) and value and isinstance(value[0], BaseDBModel)
            ):
                model_dict[key] = [
                    item.to_dict(exclude_none=exclude_none) for item in value
                ]

        return model_dict

    @classmethod
    def from_dict(cls: Type[T], data: Dict[str, Any]) -> T:
        """
        Create a model instance from a dictionary.

        Args:
            data: Dictionary containing model data.

        Returns:
            Instance of the model.
        """
        return cls(**data)

    @classmethod
    def from_row(cls: Type[T], row: Dict[str, Any]) -> T:
        """
        Create a model instance from a database row.

        Args:
            row: Dictionary containing database row data.

        Returns:
            Instance of the model.
        """
        return cls.from_dict(row)

    @classmethod
    def from_rows(cls: Type[T], rows: List[Dict[str, Any]]) -> List[T]:
        """
        Create model instances from a list of database rows.

        Args:
            rows: List of dictionaries containing database row data.

        Returns:
            List of model instances.
        """
        return [cls.from_row(row) for row in rows]

    def __str__(self) -> str:
        """String representation of the model."""
        return f"{self.__class__.__name__}(id={self.id})"

    def __repr__(self) -> str:
        """Detailed representation of the model."""
        items = ", ".join([f"{k}={v}" for k, v in self.to_dict().items()])
        return f"{self.__class__.__name__}({items})"


class User(BaseDBModel):
    """
    User model for TripSage.

    Attributes:
        id: Unique identifier for the user
        name: User's display name
        email: User's email address
        password_hash: Hashed password for the user
        is_admin: Whether the user is an admin
        is_disabled: Whether the user is disabled
        preferences_json: User preferences stored as a dictionary
        created_at: Timestamp when the user record was created
        updated_at: Timestamp when the user record was last updated
    """

    __tablename__: ClassVar[str] = "users"

    name: Optional[str] = Field(None, description="User's display name")
    email: Optional[EmailStr] = Field(None, description="User's email address")
    password_hash: Optional[str] = Field(
        None, description="Hashed password for the user"
    )
    is_admin: bool = Field(False, description="Whether the user is an admin")
    is_disabled: bool = Field(False, description="Whether the user is disabled")
    preferences_json: Optional[Dict[str, Any]] = Field(
        None, description="User preferences"
    )

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        """Validate the email address."""
        if v is None:
            return None
        # Email is already validated by EmailStr, just ensure lowercase
        return v.lower()

    @property
    def full_preferences(self) -> Dict[str, Any]:
        """Get the full preferences dictionary with defaults."""
        defaults = {
            "theme": "light",
            "currency": "USD",
            "notifications_enabled": True,
            "language": "en",
            "travel_preferences": {
                "preferred_airlines": [],
                "preferred_accommodation_types": ["hotel"],
                "preferred_seat_type": "economy",
                "dietary_restrictions": [],
            },
        }

        if not self.preferences_json:
            return defaults

        # Deep merge preferences with defaults
        result = defaults.copy()
        for key, value in self.preferences_json.items():
            if (
                isinstance(value, dict)
                and key in result
                and isinstance(result[key], dict)
            ):
                # Merge nested dictionaries
                result[key] = {**result[key], **value}
            else:
                # Override at top level
                result[key] = value

        return result


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


class BookingStatus(str, Enum):
    """Enum for booking status values."""

    VIEWED = "viewed"
    SAVED = "saved"
    BOOKED = "booked"
    CANCELED = "canceled"


class Flight(BaseDBModel):
    """
    Flight model for TripSage.

    Attributes:
        id: Unique identifier for the flight
        trip_id: Reference to the associated trip
        origin: Origin airport or city
        destination: Destination airport or city
        airline: Name of the airline
        departure_time: Scheduled departure time with timezone
        arrival_time: Scheduled arrival time with timezone
        price: Price of the flight in default currency
        booking_link: URL for booking the flight
        segment_number: Segment number for multi-leg flights
        search_timestamp: When this flight option was found
        booking_status: Status of the flight booking (viewed, saved, booked, canceled)
        data_source: Source of the flight data (API provider)
    """

    __tablename__: ClassVar[str] = "flights"

    trip_id: int = Field(..., description="Reference to the associated trip")
    origin: str = Field(..., description="Origin airport or city")
    destination: str = Field(..., description="Destination airport or city")
    airline: Optional[str] = Field(None, description="Name of the airline")
    departure_time: datetime = Field(
        ..., description="Scheduled departure time with timezone"
    )
    arrival_time: datetime = Field(
        ..., description="Scheduled arrival time with timezone"
    )
    price: float = Field(..., description="Price of the flight in default currency")
    booking_link: Optional[str] = Field(None, description="URL for booking the flight")
    segment_number: Optional[int] = Field(
        None, description="Segment number for multi-leg flights"
    )
    search_timestamp: Optional[datetime] = Field(
        default_factory=datetime.now, description="When this flight option was found"
    )
    booking_status: BookingStatus = Field(
        BookingStatus.VIEWED, description="Status of the flight booking"
    )
    data_source: Optional[str] = Field(
        None, description="Source of the flight data (API provider)"
    )

    @model_validator(mode="after")
    def validate_times(self) -> "Flight":
        """Validate that arrival_time is after departure_time."""
        if self.arrival_time <= self.departure_time:
            raise ValueError("Arrival time must be after departure time")
        return self

    @field_validator("price")
    @classmethod
    def validate_price(cls, v: float) -> float:
        """Validate that price is non-negative."""
        if v < 0:
            raise ValueError("Price must be non-negative")
        return v

    @property
    def duration_minutes(self) -> int:
        """Get the flight duration in minutes."""
        delta = self.arrival_time - self.departure_time
        return int(delta.total_seconds() / 60)

    @property
    def duration_formatted(self) -> str:
        """Get the flight duration formatted as HH:MM."""
        minutes = self.duration_minutes
        hours = minutes // 60
        remaining_minutes = minutes % 60
        return f"{hours}h {remaining_minutes}m"

    @property
    def is_international(self) -> bool:
        """
        Determine if the flight is likely international based on origin/destination.

        This is a simplistic implementation and would need to be improved with
        actual airport code mappings in a production system.
        """
        # Simple check - if origin and destination are 3-letter codes (IATA),
        # and they start with different characters, consider it international
        # This is obviously not accurate but serves as a placeholder
        if (
            len(self.origin) == 3
            and len(self.destination) == 3
            and self.origin[0] != self.destination[0]
        ):
            return True
        return False

    def to_dict(self, exclude_none: bool = True) -> Dict[str, Any]:
        """Convert the flight to a dictionary for database operations."""
        data = super().to_dict(exclude_none=exclude_none)

        # Convert enum values to strings for the database
        if "booking_status" in data and isinstance(
            data["booking_status"], BookingStatus
        ):
            data["booking_status"] = data["booking_status"].value

        return data

    @classmethod
    def from_row(cls, row: Dict[str, Any]) -> "Flight":
        """Create a Flight instance from a database row."""
        # Convert string booking_status to enum value
        if "booking_status" in row and isinstance(row["booking_status"], str):
            try:
                row["booking_status"] = BookingStatus(row["booking_status"])
            except ValueError:
                # Handle invalid booking_status values
                row["booking_status"] = BookingStatus.VIEWED

        return super().from_row(row)
