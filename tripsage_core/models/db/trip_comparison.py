"""TripComparison model for TripSage.

This module provides the TripComparison model for storing
comparison data between different trip options.
"""

from datetime import datetime, timedelta
from typing import Any, TypeGuard, cast

from pydantic import Field

from tripsage_core.models.base_core_model import TripSageModel


def _is_option_dict(candidate: Any) -> TypeGuard[dict[str, Any]]:
    """Determine whether a value is a dictionary suitable for option data."""
    return isinstance(candidate, dict)


def _extract_option_dicts(raw_options: Any) -> list[dict[str, Any]]:
    """Normalize arbitrary option payloads into a list of dictionaries."""
    if not isinstance(raw_options, list):
        return []
    typed_options: list[Any] = cast(list[Any], raw_options)
    return [candidate for candidate in typed_options if _is_option_dict(candidate)]


def _extract_list(raw_values: Any) -> list[Any]:
    """Return a shallow list copy when the payload is list-like."""
    if isinstance(raw_values, list):
        typed_values: list[Any] = cast(list[Any], raw_values)
        return typed_values.copy()
    return []


class TripComparison(TripSageModel):
    """TripComparison model for TripSage.

    Attributes:
        id: Unique identifier for the comparison
        trip_id: Reference to the associated trip
        comparison_json: The comparison data in JSON format
    """

    id: int | None = Field(None, description="Unique identifier")
    trip_id: int = Field(..., description="Reference to the associated trip")
    timestamp: datetime = Field(..., description="When the comparison was created")
    comparison_json: dict[str, Any] = Field(
        ..., description="The comparison data in JSON format"
    )

    @property
    def is_recent(self) -> bool:
        """Check if the comparison was created recently (within 24 hours)."""
        comparison_timestamp = self._timestamp_as_datetime()
        current_timestamp = (
            datetime.now(tz=comparison_timestamp.tzinfo)
            if comparison_timestamp.tzinfo is not None
            else datetime.now()
        )
        return current_timestamp - comparison_timestamp < timedelta(hours=24)

    @property
    def formatted_timestamp(self) -> str:
        """Get the formatted timestamp for display."""
        return self._timestamp_as_datetime().strftime("%Y-%m-%d %H:%M")

    @property
    def options_count(self) -> int:
        """Get the number of options being compared."""
        return len(self._option_dicts())

    @property
    def has_selected_option(self) -> bool:
        """Check if a selected option is present."""
        return self.selected_option_id is not None

    @property
    def selected_option_id(self) -> int | None:
        """Get the ID of the selected option."""
        selected_id = self._comparison_data().get("selected_option_id")
        return selected_id if isinstance(selected_id, int) else None

    @property
    def comparison_type(self) -> str | None:
        """Get the type of comparison (flight, accommodation, etc.)."""
        options = self._option_dicts()
        if options:
            option_type = options[0].get("type")
            if isinstance(option_type, str):
                return option_type
        # Fallback to explicit type field
        explicit_type = self._comparison_data().get("type")
        return explicit_type if isinstance(explicit_type, str) else None

    @property
    def has_criteria(self) -> bool:
        """Check if comparison criteria are defined."""
        return bool(self._criteria_values())

    @property
    def criteria_list(self) -> list[str]:
        """Get the list of comparison criteria."""
        return [str(criteria) for criteria in self._criteria_values()]

    @property
    def has_flights(self) -> bool:
        """Check if the comparison includes flight options."""
        options = self._option_dicts()
        comparison_data = self._comparison_data()
        return "flights" in comparison_data or any(
            "flight" in option for option in options
        )

    @property
    def has_accommodations(self) -> bool:
        """Check if the comparison includes accommodation options."""
        options = self._option_dicts()
        comparison_data = self._comparison_data()
        return "accommodations" in comparison_data or any(
            "accommodation" in option for option in options
        )

    @property
    def has_transportation(self) -> bool:
        """Check if the comparison includes transportation options."""
        options = self._option_dicts()
        comparison_data = self._comparison_data()
        return "transportation" in comparison_data or any(
            "transportation" in option for option in options
        )

    @property
    def has_complete_options(self) -> bool:
        """Check if comparison includes complete trip options with all components."""
        options = self._option_dicts()
        if not options:
            return False

        # Check if each option has flight, accommodation, and transportation
        required_keys = ("flight", "accommodation", "transportation")
        return all(all(key in option for key in required_keys) for option in options)

    @property
    def comparison_summary(self) -> str:
        """Get a summary of the comparison."""
        options_count = self.options_count

        components: list[str] = []
        if self.has_flights:
            components.append("flights")
        if self.has_accommodations:
            components.append("accommodations")
        if self.has_transportation:
            components.append("transportation")

        components_str = ", ".join(components) if components else "no components"

        return f"Comparison of {options_count} options with {components_str}"

    def get_option_by_id(self, option_id: int) -> dict[str, Any] | None:
        """Get an option by its ID."""
        for option in self._option_dicts():
            if option.get("id") == option_id:
                return option
        return None

    def get_selected_option(self) -> dict[str, Any] | None:
        """Get the currently selected option."""
        selected_id = self.selected_option_id
        if selected_id is not None:
            return self.get_option_by_id(selected_id)
        return None

    def _option_dicts(self) -> list[dict[str, Any]]:
        """Retrieve sanitized option dictionaries."""
        return _extract_option_dicts(self._comparison_data().get("options"))

    def _criteria_values(self) -> list[Any]:
        """Retrieve criteria entries as a list."""
        return _extract_list(self._comparison_data().get("criteria"))

    def _timestamp_as_datetime(self) -> datetime:
        """Return the timestamp as a datetime instance, validating the payload."""
        timestamp_any: Any | None = self.__dict__.get("timestamp")
        if not isinstance(timestamp_any, datetime):
            raise TypeError("TripComparison.timestamp must be a datetime instance")
        return timestamp_any

    def _comparison_data(self) -> dict[str, Any]:
        """Return the comparison JSON payload as a dictionary."""
        comparison_data_any: Any | None = self.__dict__.get("comparison_json")
        if not isinstance(comparison_data_any, dict):
            raise TypeError("TripComparison.comparison_json must be a dictionary")
        return cast(dict[str, Any], comparison_data_any)
