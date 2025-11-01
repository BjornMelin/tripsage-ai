"""SearchParameters model for TripSage.

This module provides the SearchParameters model to store search criteria
used for finding flights, accommodations, and other travel options.
"""

from datetime import datetime
from typing import Any, cast

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
        parameters = self._parameters_dict()
        # Prioritize explicit type field
        if "type" in parameters:
            return parameters.get("type") == "flight"
        # Fallback to field-based detection (stricter logic)
        return (
            "origin" in parameters
            and "destination" in parameters
            and "check_in" not in parameters
        )

    @property
    def is_accommodation_search(self) -> bool:
        """Check if this is an accommodation search."""
        parameters = self._parameters_dict()
        # Prioritize explicit type field
        if "type" in parameters:
            return parameters.get("type") == "accommodation"
        # Fallback to field-based detection
        return "check_in" in parameters or "check_out" in parameters

    @property
    def is_activity_search(self) -> bool:
        """Check if this is an activity search."""
        parameters = self._parameters_dict()
        # Prioritize explicit type field
        if "type" in parameters:
            return parameters.get("type") == "activity"
        # Fallback to field-based detection
        return "activity_type" in parameters or (
            "date" in parameters and "location" in parameters
        )

    @property
    def is_transportation_search(self) -> bool:
        """Check if this is a transportation search."""
        parameters = self._parameters_dict()
        # Prioritize explicit type field
        if "type" in parameters:
            return parameters.get("type") == "transportation"
        # Fallback to field-based detection
        return "pickup" in parameters or "dropoff" in parameters

    @property
    def search_summary(self) -> str:
        """Get a summary of the search parameters."""
        parameters = self._parameters_dict()
        if self.is_flight_search:
            origin = parameters.get("origin", "Unknown")
            destination = parameters.get("destination", "Unknown")
            cabin_class = cast(str, parameters.get("cabin_class", "Economy")).title()
            adults = parameters.get("adults", 1)
            children = parameters.get("children", 0)
            return (
                f"Flight from {origin} to {destination} "
                f"({cabin_class}, {adults} adults, {children} children)"
            )

        if self.is_accommodation_search:
            location = parameters.get("location", "Unknown")
            check_in = parameters.get("check_in", "Any")
            check_out = parameters.get("check_out", "Any")
            adults = parameters.get("adults", 2)
            accommodation_type = cast(
                str, parameters.get("accommodation_type", "Hotel")
            ).title()
            return (
                f"{accommodation_type} in {location} "
                f"({check_in} to {check_out}, {adults} adults)"
            )

        if self.is_activity_search:
            location = parameters.get("location", "Unknown")
            activity_type = cast(
                str, parameters.get("activity_type", "Sightseeing")
            ).title()
            date = parameters.get("date", "Any")
            return f"{activity_type} activity in {location} ({date})"

        if self.is_transportation_search:
            # Transportation uses origin/destination OR pickup/dropoff
            pickup = parameters.get("pickup") or parameters.get("origin", "Unknown")
            dropoff = parameters.get("dropoff") or parameters.get(
                "destination", "Unknown"
            )
            transportation_type = cast(
                str, parameters.get("transportation_type", "Train")
            ).title()
            pickup_date = parameters.get("pickup_date") or parameters.get("date", "Any")
            return f"{transportation_type} from {pickup} to {dropoff} ({pickup_date})"

        # Fallback for unknown search types
        search_type = parameters.get("type", "unknown")
        if search_type == "unknown":
            # Format the dictionary properly with quotes
            dict_repr = repr(parameters)
            return f"Search for {search_type} with parameters: {dict_repr}"
        timestamp_value = self._timestamp_as_datetime()
        return f"Search at {timestamp_value.strftime('%Y-%m-%d %H:%M')}"

    @property
    def has_price_filter(self) -> bool:
        """Check if the search includes price filters."""
        parameters = self._parameters_dict()
        return (
            "max_price" in parameters
            or "min_price" in parameters
            or "price_range" in parameters
        )

    @property
    def price_filter_summary(self) -> str:
        """Get a summary of the price filters."""
        parameters = self._parameters_dict()
        if not self.has_price_filter:
            return "No price filter"

        min_price = parameters.get("min_price")
        max_price = parameters.get("max_price")

        if min_price is not None and max_price is not None:
            return f"Price: ${min_price} - ${max_price}"
        if min_price is not None:
            return f"Price: Min ${min_price}"
        if max_price is not None:
            return f"Price: Max ${max_price}"

        # If price_range is used
        price_range = parameters.get("price_range")
        if price_range:
            return f"Price range: {price_range}"

        return "Price filter applied"

    def _timestamp_as_datetime(self) -> datetime:
        """Return the timestamp as a datetime instance, validating the payload."""
        timestamp_value: datetime = self.timestamp
        return timestamp_value

    def _parameters_dict(self) -> dict[str, Any]:
        """Return the parameter JSON as a dictionary."""
        parameters: dict[str, Any] = self.parameter_json
        return parameters
