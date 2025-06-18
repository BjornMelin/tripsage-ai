"""SearchParameters model for TripSage.

This module provides the SearchParameters model to store search criteria
used for finding flights, accommodations, and other travel options.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import Field

from tripsage_core.models.base_core_model import TripSageModel

class SearchParameters(TripSageModel):
    """SearchParameters model for TripSage.

    Attributes:
        id: Unique identifier for the search parameters
        trip_id: Reference to the associated trip
        timestamp: When the search was performed
        parameter_json: The search parameters in JSON format
    """

    id: int | None = Field(None, description="Unique identifier")
    trip_id: int = Field(..., description="Reference to the associated trip")
    timestamp: datetime = Field(..., description="When the search was performed")
    parameter_json: dict[str, Any] = Field(
        ..., description="The search parameters in JSON format"
    )

    @property
    def is_flight_search(self) -> bool:
        """Check if this is a flight search."""
        # Prioritize explicit type field
        if "type" in self.parameter_json:
            return self.parameter_json.get("type") == "flight"
        # Fallback to field-based detection (stricter logic)
        return (
            "origin" in self.parameter_json
            and "destination" in self.parameter_json
            and "check_in" not in self.parameter_json
        )

    @property
    def is_accommodation_search(self) -> bool:
        """Check if this is an accommodation search."""
        # Prioritize explicit type field
        if "type" in self.parameter_json:
            return self.parameter_json.get("type") == "accommodation"
        # Fallback to field-based detection
        return "check_in" in self.parameter_json or "check_out" in self.parameter_json

    @property
    def is_activity_search(self) -> bool:
        """Check if this is an activity search."""
        # Prioritize explicit type field
        if "type" in self.parameter_json:
            return self.parameter_json.get("type") == "activity"
        # Fallback to field-based detection
        return "activity_type" in self.parameter_json or (
            "date" in self.parameter_json and "location" in self.parameter_json
        )

    @property
    def is_transportation_search(self) -> bool:
        """Check if this is a transportation search."""
        # Prioritize explicit type field
        if "type" in self.parameter_json:
            return self.parameter_json.get("type") == "transportation"
        # Fallback to field-based detection
        return "pickup" in self.parameter_json or "dropoff" in self.parameter_json

    @property
    def search_summary(self) -> str:
        """Get a summary of the search parameters."""
        if self.is_flight_search:
            origin = self.parameter_json.get("origin", "Unknown")
            destination = self.parameter_json.get("destination", "Unknown")
            cabin_class = self.parameter_json.get("cabin_class", "Economy").title()
            adults = self.parameter_json.get("adults", 1)
            children = self.parameter_json.get("children", 0)
            return (
                f"Flight from {origin} to {destination} "
                f"({cabin_class}, {adults} adults, {children} children)"
            )

        elif self.is_accommodation_search:
            location = self.parameter_json.get("location", "Unknown")
            check_in = self.parameter_json.get("check_in", "Any")
            check_out = self.parameter_json.get("check_out", "Any")
            adults = self.parameter_json.get("adults", 2)
            accommodation_type = self.parameter_json.get(
                "accommodation_type", "Hotel"
            ).title()
            return (
                f"{accommodation_type} in {location} "
                f"({check_in} to {check_out}, {adults} adults)"
            )

        elif self.is_activity_search:
            location = self.parameter_json.get("location", "Unknown")
            activity_type = self.parameter_json.get(
                "activity_type", "Sightseeing"
            ).title()
            date = self.parameter_json.get("date", "Any")
            return f"{activity_type} activity in {location} ({date})"

        elif self.is_transportation_search:
            # Transportation uses origin/destination OR pickup/dropoff
            pickup = self.parameter_json.get("pickup") or self.parameter_json.get(
                "origin", "Unknown"
            )
            dropoff = self.parameter_json.get("dropoff") or self.parameter_json.get(
                "destination", "Unknown"
            )
            transportation_type = self.parameter_json.get(
                "transportation_type", "Train"
            ).title()
            pickup_date = self.parameter_json.get(
                "pickup_date"
            ) or self.parameter_json.get("date", "Any")
            return f"{transportation_type} from {pickup} to {dropoff} ({pickup_date})"

        else:
            # Fallback for unknown search types
            search_type = self.parameter_json.get("type", "unknown")
            if search_type == "unknown":
                # Format the dictionary properly with quotes
                dict_repr = repr(self.parameter_json)
                return f"Search for {search_type} with parameters: {dict_repr}"
            return f"Search at {self.timestamp.strftime('%Y-%m-%d %H:%M')}"

    @property
    def has_price_filter(self) -> bool:
        """Check if the search includes price filters."""
        return (
            "max_price" in self.parameter_json
            or "min_price" in self.parameter_json
            or "price_range" in self.parameter_json
        )

    @property
    def price_filter_summary(self) -> str:
        """Get a summary of the price filters."""
        if not self.has_price_filter:
            return "No price filter"

        min_price = self.parameter_json.get("min_price")
        max_price = self.parameter_json.get("max_price")

        if min_price is not None and max_price is not None:
            return f"Price: ${min_price} - ${max_price}"
        elif min_price is not None:
            return f"Price: Min ${min_price}"
        elif max_price is not None:
            return f"Price: Max ${max_price}"

        # If price_range is used
        price_range = self.parameter_json.get("price_range")
        if price_range:
            return f"Price range: {price_range}"

        return "Price filter applied"
