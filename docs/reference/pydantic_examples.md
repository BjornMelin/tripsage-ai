# Pydantic v2 Examples for TripSage

This document provides examples of Pydantic v2 usage for data validation, settings management, and serialization/deserialization in the TripSage project.

## Basic Model Definition

```python
from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator
from typing import Annotated, Optional, Literal
from datetime import date

class TravelRequest(BaseModel):
    """Model for travel request data validation and schema definition."""

    # Configure model behavior using ConfigDict (v2 approach)
    model_config = ConfigDict(
        extra="forbid",       # Prevent unknown fields
        frozen=True,          # Make instances immutable
        validate_default=True # Validate default values too
    )

    # Fields with validation
    destination: str = Field(..., description="Travel destination location")
    start_date: date = Field(..., description="Trip start date")
    end_date: date = Field(..., description="Trip end date")
    budget: Annotated[float, Field(gt=0, description="Trip budget in USD")]
    travelers: Annotated[int, Field(gt=0, lt=20, description="Number of travelers")]

    # Field with predefined options
    accommodation_type: Literal["hotel", "hostel", "airbnb", "resort"] = "hotel"
    notes: Optional[str] = Field(None, max_length=1000)

    # Field-level validator methods
    @field_validator("end_date")
    @classmethod
    def validate_end_date(cls, value: date, info: ValidationInfo) -> date:
        """Ensure end_date is after start_date."""
        if "start_date" in info.data and value <= info.data["start_date"]:
            raise ValueError("End date must be after start date")
        return value

    # Model-level validator for cross-field validation
    @model_validator(mode="after")
    def validate_budget_per_traveler(self) -> "TravelRequest":
        """Ensure sufficient budget per traveler."""
        min_budget_per_person = 100.0
        if self.budget / self.travelers < min_budget_per_person:
            raise ValueError(f"Budget per traveler must be at least ${min_budget_per_person}")
        return self
```

## Function Tool with Pydantic Model

```python
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import List, Optional, Dict, Any, Annotated
from agents import function_tool
from datetime import date, datetime
import uuid
import logging

logger = logging.getLogger(__name__)

class FlightSearchParams(BaseModel):
    """Model for validating flight search parameters."""

    # Use ConfigDict for model configuration (Pydantic v2)
    model_config = ConfigDict(
        extra="forbid",  # Reject unknown fields
        frozen=True      # Make instances immutable
    )

    # Required parameters with validation
    origin: str = Field(..., min_length=3, max_length=3,
                      description="Origin airport IATA code (e.g., 'SFO')")
    destination: str = Field(..., min_length=3, max_length=3,
                           description="Destination airport IATA code (e.g., 'JFK')")
    departure_date: date = Field(..., description="Departure date (YYYY-MM-DD)")

    # Optional parameters with defaults and validation
    return_date: Optional[date] = Field(None, description="Return date for round trips")
    max_price: Optional[float] = Field(None, gt=0, description="Maximum price in USD")
    passengers: int = Field(1, ge=1, le=9, description="Number of passengers")
    cabin_class: str = Field("economy", description="Cabin class for flight")

    # Field-level validators
    @field_validator("origin", "destination")
    @classmethod
    def validate_airport_code(cls, v: str) -> str:
        """Validate airport code format."""
        return v.upper()  # Ensure IATA codes are uppercase

    @field_validator("return_date")
    @classmethod
    def validate_return_date(cls, v: Optional[date], info: ValidationInfo) -> Optional[date]:
        """Ensure return_date is after departure_date if provided."""
        if v is not None and "departure_date" in info.data:
            if v <= info.data["departure_date"]:
                raise ValueError("Return date must be after departure date")
        return v

@function_tool
async def search_flights(params: FlightSearchParams) -> Dict[str, Any]:
    """Search for available flights based on user criteria.

    Args:
        params: The flight search parameters including origin, destination,
               dates, price constraints, and number of passengers.

    Returns:
        A dictionary containing flight options with prices and details.
    """
    try:
        # Implementation that accesses flight APIs
        # Store results in Supabase and knowledge graph

        # Log the search for analytics
        logger.info(
            "Flight search executed for %s to %s on %s",
            params.origin, params.destination, params.departure_date
        )

        return {
            "search_id": str(uuid.uuid4()),
            "search_params": params.model_dump(),
            "results": [
                # Flight results would be populated here
            ],
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.exception("Error in flight search: %s", str(e))
        return {
            "error": "SEARCH_ERROR",
            "message": f"Failed to fetch flight data: {str(e)}",
            "timestamp": datetime.utcnow().isoformat()
        }
```

## Error Handling with Pydantic

```python
from pydantic import BaseModel, ValidationError

class SearchError(BaseModel):
    error_code: str
    message: str
    timestamp: str

try:
    params = FlightSearchParams(
        origin="SFO",
        destination="NYC",  # Invalid: should be 3 characters
        departure_date="2023-12-01"
    )
except ValidationError as e:
    error_data = {
        "error_code": "VALIDATION_ERROR",
        "message": str(e),
        "timestamp": datetime.utcnow().isoformat()
    }
    error = SearchError(**error_data)
    # Handle the validation error appropriately
```

## Nested Models

```python
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from datetime import datetime

class Passenger(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    age: int = Field(..., ge=0, le=120)
    is_child: bool = Field(default_factory=lambda: age < 12 if 'age' in locals() else False)

class BookingRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    booking_id: str
    passengers: List[Passenger]
    departure_time: datetime
    arrival_time: datetime
    total_price: float
    notes: Optional[str] = None

    @model_validator(mode="after")
    def check_arrival_after_departure(self) -> "BookingRequest":
        if self.arrival_time <= self.departure_time:
            raise ValueError("Arrival time must be after departure time")
        return self
```
