"""TripComparison model for TripSage.

This module provides the TripComparison model for storing
comparison data between different trip options.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import Field

from tripsage_core.models.base_core_model import TripSageModel


class TripComparison(TripSageModel):
    """TripComparison model for TripSage.

    Attributes:
        id: Unique identifier for the comparison
        trip_id: Reference to the associated trip
        comparison_json: The comparison data in JSON format
    """

    id: Optional[int] = Field(None, description="Unique identifier")
    trip_id: int = Field(..., description="Reference to the associated trip")
    timestamp: datetime = Field(..., description="When the comparison was created")
    comparison_json: Dict[str, Any] = Field(
        ..., description="The comparison data in JSON format"
    )

    @property
    def is_recent(self) -> bool:
        """Check if the comparison was created recently (within 24 hours)."""
        from datetime import datetime as datetime_type
        from datetime import timedelta

        return datetime_type.now() - self.timestamp < timedelta(hours=24)

    @property
    def formatted_timestamp(self) -> str:
        """Get the formatted timestamp for display."""
        return self.timestamp.strftime("%Y-%m-%d %H:%M")

    @property
    def options_count(self) -> int:
        """Get the number of options being compared."""
        options = self.comparison_json.get("options", [])
        if isinstance(options, list):
            return len(options)
        return 0


    @property
    def has_selected_option(self) -> bool:
        """Check if a selected option is present."""
        return "selected_option_id" in self.comparison_json

    @property
    def selected_option_id(self) -> Optional[int]:
        """Get the ID of the selected option."""
        return self.comparison_json.get("selected_option_id")

    @property
    def comparison_type(self) -> Optional[str]:
        """Get the type of comparison (flight, accommodation, etc.)."""
        # Try to infer from options
        options = self.comparison_json.get("options", [])
        if options and isinstance(options, list) and len(options) > 0:
            first_option = options[0]
            if isinstance(first_option, dict):
                return first_option.get("type")
        # Fallback to explicit type field
        return self.comparison_json.get("type")

    @property
    def has_criteria(self) -> bool:
        """Check if comparison criteria are defined."""
        criteria = self.comparison_json.get("criteria", [])
        return isinstance(criteria, list) and len(criteria) > 0

    @property
    def criteria_list(self) -> List[str]:
        """Get the list of comparison criteria."""
        criteria = self.comparison_json.get("criteria", [])
        if isinstance(criteria, list):
            return criteria
        return []

    @property
    def has_flights(self) -> bool:
        """Check if the comparison includes flight options."""
        return "flights" in self.comparison_json or any(
            "flight" in option for option in self.comparison_json.get("options", [])
        )

    @property
    def has_accommodations(self) -> bool:
        """Check if the comparison includes accommodation options."""
        return "accommodations" in self.comparison_json or any(
            "accommodation" in option
            for option in self.comparison_json.get("options", [])
        )

    @property
    def has_transportation(self) -> bool:
        """Check if the comparison includes transportation options."""
        return "transportation" in self.comparison_json or any(
            "transportation" in option
            for option in self.comparison_json.get("options", [])
        )

    @property
    def has_complete_options(self) -> bool:
        """Check if comparison includes complete trip options with all components."""
        options = self.comparison_json.get("options", [])
        if not options or not isinstance(options, list):
            return False

        # Check if each option has flight, accommodation, and transportation
        for option in options:
            if not all(
                key in option for key in ["flight", "accommodation", "transportation"]
            ):
                return False

        return True

    @property
    def comparison_summary(self) -> str:
        """Get a summary of the comparison."""
        options_count = self.options_count

        components = []
        if self.has_flights:
            components.append("flights")
        if self.has_accommodations:
            components.append("accommodations")
        if self.has_transportation:
            components.append("transportation")

        components_str = ", ".join(components) if components else "no components"

        return f"Comparison of {options_count} options with {components_str}"

    def get_option_by_id(self, option_id: int) -> Optional[Dict[str, Any]]:
        """Get an option by its ID."""
        options = self.comparison_json.get("options", [])
        if isinstance(options, list):
            for option in options:
                if isinstance(option, dict) and option.get("id") == option_id:
                    return option
        return None

    def get_selected_option(self) -> Optional[Dict[str, Any]]:
        """Get the currently selected option."""
        selected_id = self.selected_option_id
        if selected_id is not None:
            return self.get_option_by_id(selected_id)
        return None
