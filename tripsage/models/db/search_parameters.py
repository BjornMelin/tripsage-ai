"""SearchParameters model for TripSage.

This module provides the SearchParameters model to store search criteria
used for finding flights, accommodations, and other travel options.
"""

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import Field

from tripsage.models.base import TripSageModel


class SearchParameters(TripSageModel):
    """SearchParameters model for TripSage.

    Attributes:
        id: Unique identifier for the search parameters
        trip_id: Reference to the associated trip
        timestamp: When the search was performed
        parameter_json: The search parameters in JSON format
    """

    id: Optional[int] = Field(None, description="Unique identifier")
    trip_id: int = Field(..., description="Reference to the associated trip")
    timestamp: datetime = Field(..., description="When the search was performed")
    parameter_json: Dict[str, Any] = Field(
        ..., description="The search parameters in JSON format"
    )

    @property
    def is_flight_search(self) -> bool:
        """Check if this is a flight search."""
        return (
            self.parameter_json.get("type") == "flight" 
            or "origin" in self.parameter_json 
            or "destination" in self.parameter_json
        )

    @property
    def is_accommodation_search(self) -> bool:
        """Check if this is an accommodation search."""
        return (
            self.parameter_json.get("type") == "accommodation"
            or "check_in" in self.parameter_json
            or "check_out" in self.parameter_json
        )
    
    @property
    def is_transportation_search(self) -> bool:
        """Check if this is a transportation search."""
        return (
            self.parameter_json.get("type") == "transportation"
            or "pickup" in self.parameter_json
            or "dropoff" in self.parameter_json
        )

    @property
    def search_summary(self) -> str:
        """Get a summary of the search parameters."""
        if self.is_flight_search:
            origin = self.parameter_json.get("origin", "Unknown")
            destination = self.parameter_json.get("destination", "Unknown")
            departure_date = self.parameter_json.get("departure_date", "Any")
            return f"Flight from {origin} to {destination} on {departure_date}"
        
        elif self.is_accommodation_search:
            location = self.parameter_json.get("location", "Unknown")
            check_in = self.parameter_json.get("check_in", "Any")
            check_out = self.parameter_json.get("check_out", "Any")
            return f"Accommodation in {location} from {check_in} to {check_out}"
        
        elif self.is_transportation_search:
            pickup = self.parameter_json.get("pickup", "Unknown")
            dropoff = self.parameter_json.get("dropoff", "Unknown")
            pickup_date = self.parameter_json.get("pickup_date", "Any")
            return f"Transportation from {pickup} to {dropoff} on {pickup_date}"
        
        else:
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