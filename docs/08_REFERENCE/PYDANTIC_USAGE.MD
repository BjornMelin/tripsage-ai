# Pydantic v2 Usage Guide for TripSage

This document provides canonical examples and best practices for using Pydantic v2 within the TripSage project. Pydantic is extensively used for data validation, schema definition for API requests/responses, MCP tool parameters, and settings management.

## 1. Basic Model Definition

```python
from typing import Annotated, Optional, Literal, List, Dict, Any
from datetime import date, datetime
import uuid

from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator, ValidationInfo

class TravelRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        validate_assignment=True,
        validate_default=True
    )

    request_id: uuid.UUID = Field(default_factory=uuid.uuid4, description="Unique identifier for the request.")
    destination: str = Field(..., min_length=2, description="Travel destination location.")
    start_date: date = Field(..., description="Trip start date.")
    end_date: date = Field(..., description="Trip end date.")
    budget: Annotated[float, Field(gt=0)]
    travelers: Annotated[int, Field(gt=0, le=20)]
    accommodation_type: Literal["hotel", "hostel", "airbnb", "resort", "any"] = "any"
    notes: Optional[str] = Field(None, max_length=1000)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("end_date")
    @classmethod
    def validate_end_date_after_start_date(cls, v: date, info: ValidationInfo) -> date:
        if 'start_date' in info.data and v < info.data['start_date']:
            raise ValueError("End date must be on or after start date.")
        return v

    @model_validator(mode="after")
    def check_budget_per_traveler(self) -> 'TravelRequest':
        if self.budget is not None and self.travelers > 0:
            min_budget_per_person = 50.0
            if (self.budget / self.travelers) < min_budget_per_person:
                raise ValueError(f"Budget per traveler must be at least ${min_budget_per_person:.2f}.")
        return self
```

## 2. Function Tool Parameter Validation (OpenAI Agents SDK)

```python
from agents import function_tool
from typing import Dict, Any, Union
from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator, ValidationError
from datetime import date
import uuid
import logging

logger = logging.getLogger(__name__)

class FlightSearchParams(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    origin: str = Field(..., min_length=3, max_length=3, description="IATA code")
    destination: str = Field(..., min_length=3, max_length=3, description="IATA code")
    departure_date: date
    return_date: Optional[date] = None
    passengers: int = Field(1, ge=1, le=9)
    cabin_class: Literal["economy", "premium_economy", "business", "first"] = "economy"
    max_price: Optional[float] = None

    @field_validator("origin", "destination", mode="before")
    @classmethod
    def uppercase_codes(cls, v: str) -> str:
        return v.upper()

    @field_validator('return_date')
    @classmethod
    def validate_return_date(cls, v: Optional[date], info: ValidationInfo) -> Optional[date]:
        if v and 'departure_date' in info.data and info.data['departure_date'] and v < info.data['departure_date']:
            raise ValueError('Return date must be after departure date.')
        return v

@function_tool
async def search_flights(params: FlightSearchParams) -> Dict[str, Any]:
    logger.info(f"Searching flights with parameters: {params.model_dump()}")
    
    # Mocked response:
    flight_results = {
        "search_id": str(uuid.uuid4()),
        "search_params_received": params.model_dump(mode="json"),
        "offers": [
            {"airline": "AA", "flight_no": "100", "price": 350.0},
            {"airline": "DL", "flight_no": "200", "price": 370.0},
        ],
        "timestamp": date.today().isoformat()
    }
    return flight_results
```

## 3. Error Handling with Pydantic `ValidationError`

```python
try:
    invalid_data = {
      "origin": "SanFrancisco",
      "destination": "NY",
      "departure_date": "2023-01-01",
      "passengers": 0
    }
    FlightSearchParams(**invalid_data)
except ValidationError as e:
    for error in e.errors():
        print(error["loc"], error["msg"])
```

## 4. Nested Models

```python
class Passenger(BaseModel):
    model_config = ConfigDict(extra="forbid")
    first_name: str
    last_name: str
    age: Optional[int] = None
    passenger_type: Literal["adult", "child", "infant"] = "adult"

    @model_validator(mode="after")
    def set_passenger_type_from_age(self):
        if self.age is not None:
            if self.age < 2:
                self.passenger_type = "infant"
            elif self.age < 12:
                self.passenger_type = "child"
            else:
                self.passenger_type = "adult"
        return self

class FlightBookingRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    offer_id: str
    passengers: List[Passenger]
    contact_email: str
    payment_token: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

## 5. Settings Management

Refer to [Centralized_Settings.md](./Centralized_Settings.md).

## 6. Tips for Pydantic v2 in TripSage

* Use `model_config = ConfigDict(...)` for each model.
* `extra="forbid"` to disallow unknown fields.
* `@field_validator` vs. `@model_validator(mode="after")`.
* `model_dump(mode="json")` for serialization.
* `model_validate(...)` for deserialization.

Pydantic ensures robust data validation and clear data models throughout TripSage.
