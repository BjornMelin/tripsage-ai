"""SavedOption model for TripSage.

This module provides the SavedOption model for storing saved travel options
such as flights, accommodations, or transportation options.
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from pydantic import Field, field_validator

from tripsage_core.models.base_core_model import TripSageModel


class OptionType(str, Enum):
    """Enum for option type values."""

    FLIGHT = "flight"
    ACCOMMODATION = "accommodation"
    TRANSPORTATION = "transportation"
    ACTIVITY = "activity"


class SavedOption(TripSageModel):
    """SavedOption model for TripSage.

    Attributes:
        id: Unique identifier for the saved option
        trip_id: Reference to the associated trip
        option_type: Type of the saved option
        option_id: ID of the saved option
        timestamp: When the option was saved
        notes: Additional notes or comments about this option
    """

    id: int | None = Field(None, description="Unique identifier")
    trip_id: int = Field(..., description="Reference to the associated trip")
    option_type: OptionType = Field(..., description="Type of the saved option")
    option_id: int = Field(..., description="ID of the saved option")
    timestamp: datetime = Field(..., description="When the option was saved")
    notes: str | None = Field(None, description="Additional notes or comments")

    @field_validator("option_id")
    @classmethod
    def validate_option_id(cls, v: int) -> int:
        """Validate that option_id is a positive number."""
        if v <= 0:
            raise ValueError("Option ID must be positive")
        return v

    @property
    def is_recent(self) -> bool:
        """Check if the option was saved recently (within 24 hours)."""
        saved_timestamp = self._timestamp_as_datetime()
        current_timestamp = (
            datetime.now(tz=saved_timestamp.tzinfo)
            if saved_timestamp.tzinfo is not None
            else datetime.now()
        )
        return current_timestamp - saved_timestamp < timedelta(hours=24)

    @property
    def formatted_timestamp(self) -> str:
        """Get the formatted timestamp for display."""
        return self._timestamp_as_datetime().strftime("%Y-%m-%d %H:%M")

    @property
    def is_flight(self) -> bool:
        """Check if this is a flight option."""
        return self.option_type == OptionType.FLIGHT

    @property
    def is_accommodation(self) -> bool:
        """Check if this is an accommodation option."""
        return self.option_type == OptionType.ACCOMMODATION

    @property
    def is_transportation(self) -> bool:
        """Check if this is a transportation option."""
        return self.option_type == OptionType.TRANSPORTATION

    @property
    def is_activity(self) -> bool:
        """Check if this is an activity option."""
        return self.option_type == OptionType.ACTIVITY

    @property
    def type_display_name(self) -> str:
        """Get a display-friendly name for the option type."""
        option_type = self._option_type()
        return option_type.value.title()

    @property
    def has_notes(self) -> bool:
        """Check if the option has notes."""
        return self.notes is not None and len(self.notes.strip()) > 0

    def update_notes(self, new_notes: str | None) -> None:
        """Update the notes for this saved option.

        Args:
            new_notes: The new notes to set, or None to clear
        """
        self.notes = new_notes

    def _option_type(self) -> OptionType:
        """Return option type, validating it is an OptionType instance."""
        option_type_any: Any | None = self.__dict__.get("option_type")
        if not isinstance(option_type_any, OptionType):
            raise TypeError("SavedOption.option_type must be an OptionType")
        return option_type_any

    def _timestamp_as_datetime(self) -> datetime:
        """Return the timestamp as a datetime instance, validating the payload."""
        timestamp_any: Any | None = self.__dict__.get("timestamp")
        if not isinstance(timestamp_any, datetime):
            raise TypeError("SavedOption.timestamp must be a datetime instance")
        return timestamp_any
