# Pydantic v2 Usage Guide for TripSage

This document provides canonical examples and best practices for using Pydantic v2 within the TripSage project. Pydantic is extensively used for data validation, schema definition for API requests/responses, MCP tool parameters, and settings management.

## 1. Basic Model Definition

Pydantic models define the structure and types of data.

```python
from typing import Annotated, Optional, Literal, List, Dict, Any
from datetime import date, datetime
import uuid # For generating unique IDs if needed

from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator, ValidationInfo

class TravelRequest(BaseModel):
    """
    Model for validating travel request data.
    Demonstrates common Pydantic v2 features.
    """

    # model_config replaces the old `class Config:` for Pydantic v2
    model_config = ConfigDict(
        extra="forbid",       # Do not allow fields not defined in the model
        frozen=True,          # Makes model instances immutable after creation
        validate_assignment=True, # Validate fields on assignment after instantiation (if not frozen)
        validate_default=True # Ensure default values are also validated
    )

    request_id: uuid.UUID = Field(default_factory=uuid.uuid4, description="Unique identifier for the request.")
    destination: str = Field(..., min_length=2, description="Travel destination location (e.g., city, country).")
    start_date: date = Field(..., description="Trip start date in YYYY-MM-DD format.")
    end_date: date = Field(..., description="Trip end date in YYYY-MM-DD format.")
    
    # Using Annotated for more complex field definitions
    budget: Annotated[float, Field(gt=0, description="Total trip budget in USD.")]
    travelers: Annotated[int, Field(gt=0, le=20, description="Number of travelers (1-19).")]

    accommodation_type: Literal["hotel", "hostel", "airbnb", "resort", "any"] = Field(
        default="any", 
        description="Preferred type of accommodation."
    )
    notes: Optional[str] = Field(None, max_length=1000, description="Additional notes or preferences for the trip.")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Timestamp of request creation.")

    # Field-level validator (Pydantic v2 syntax)
    @field_validator("end_date")
    @classmethod
    def validate_end_date_after_start_date(cls, v: date, info: ValidationInfo) -> date:
        """Ensures the end_date is after or the same as the start_date."""
        # info.data contains the already validated fields
        if 'start_date' in info.data and v < info.data['start_date']:
            raise ValueError("End date must be on or after start date.")
        return v

    # Model-level validator (Pydantic v2 syntax)
    @model_validator(mode="after") # mode="after" runs after individual field validators
    def check_budget_per_traveler(self) -> 'TravelRequest':
        """Ensures a minimum budget per traveler if budget and travelers are specified."""
        if self.budget is not None and self.travelers > 0:
            min_budget_per_person = 50.0 # Example minimum
            if (self.budget / self.travelers) < min_budget_per_person:
                raise ValueError(f"Budget per traveler must be at least ${min_budget_per_person:.2f}.")
        return self

# Example Usage:
# try:
#     request_data = {
#         "destination": "Paris",
#         "start_date": "2025-12-20",
#         "end_date": "2025-12-26",
#         "budget": 1500.00,
#         "travelers": 2
#     }
#     travel_req = TravelRequest(**request_data)
#     print(travel_req.model_dump_json(indent=2))
# except ValidationError as e:
#     print(e.errors())
```

## 2. Function Tool Parameter Validation (OpenAI Agents SDK)

Pydantic models are ideal for defining the input schema for tools used by AI agents. The OpenAI Agents SDK can leverage these for validation.

```python
from agents import function_tool # Assuming this is from your SDK

class FlightSearchParams(BaseModel):
    """Input schema for the flight search tool."""
    model_config = ConfigDict(extra="forbid", frozen=True)

    origin: Annotated[str, Field(..., min_length=3, max_length=3, pattern=r"^[A-Z]{3}$", description="Origin airport IATA code (e.g., 'SFO').")]
    destination: Annotated[str, Field(..., min_length=3, max_length=3, pattern=r"^[A-Z]{3}$", description="Destination airport IATA code (e.g., 'JFK').")]
    departure_date: Annotated[date, Field(..., description="Departure date (YYYY-MM-DD).")]
    return_date: Annotated[Optional[date], Field(None, description="Return date for round trips (YYYY-MM-DD).")]
    passengers: Annotated[int, Field(1, ge=1, le=9, description="Number of passengers.")]
    cabin_class: Annotated[Literal["economy", "premium_economy", "business", "first"], Field("economy", description="Cabin class.")]
    max_price: Annotated[Optional[float], Field(None, gt=0, description="Maximum price in USD.")]

    @field_validator("origin", "destination", mode="before") # mode='before' to modify before other validation
    @classmethod
    def uppercase_airport_codes(cls, v: str) -> str:
        return v.upper()

    @field_validator('return_date')
    @classmethod
    def validate_return_date(cls, v: Optional[date], info: ValidationInfo) -> Optional[date]:
        if v and 'departure_date' in info.data and info.data['departure_date'] and v < info.data['departure_date']:
            raise ValueError('Return date must be after departure date.')
        return v

@function_tool # Decorator from OpenAI Agents SDK
async def search_flights(params: FlightSearchParams) -> Dict[str, Any]:
    """
    Search for available flights based on user criteria.

    Args:
        params: Flight search parameters validated by FlightSearchParams.

    Returns:
        A dictionary containing flight options or an error message.
    """
    # The 'params' argument is already an instance of FlightSearchParams, validated.
    logger.info(f"Searching flights with parameters: {params.model_dump()}")
    
    try:
        # --- Actual flight search logic using an MCP client ---
        # flight_results = await flights_mcp_client.search_flights(
        #     origin=params.origin,
        #     destination=params.destination,
        #     # ... and so on
        # )
        # Mocked response for example:
        flight_results = {
            "search_id": str(uuid.uuid4()),
            "search_params_received": params.model_dump(mode="json"), # mode="json" to serialize date to string
            "offers": [
                {"airline": "AA", "flight_no": "100", "price": 350.00, "currency": "USD"},
                {"airline": "DL", "flight_no": "200", "price": 370.00, "currency": "USD"},
            ],
            "timestamp": datetime.utcnow().isoformat()
        }
        return flight_results
    except Exception as e:
        # logger.error(f"Flight search tool error: {e}", exc_info=True)
        return {"error": "SEARCH_API_ERROR", "message": str(e)}

# Example of how the agent might call this (internally):
# agent_result = await search_flights(
#     FlightSearchParams(origin="SFO", destination="JFK", departure_date="2025-10-10")
# )
```

## 3. Error Handling with Pydantic `ValidationError`

Pydantic's `ValidationError` provides detailed information about validation failures.

```python
from pydantic import ValidationError

# ... (FlightSearchParams model defined above) ...

invalid_data = {
    "origin": "SanFrancisco", # Too long, not uppercase
    "destination": "NY",      # Too short
    "departure_date": "2023-01-01", # Potentially in the past if validator added
    "passengers": 0 # Less than minimum
}

try:
    FlightSearchParams(**invalid_data)
except ValidationError as e:
    print(f"Validation failed for FlightSearchParams with {len(e.errors())} error(s):")
    for error in e.errors():
        print(f"  Field: {'.'.join(str(loc) for loc in error['loc'])}")
        print(f"  Message: {error['msg']}")
        print(f"  Type: {error['type']}")
    # Example output:
    # Validation failed for FlightSearchParams with 3 error(s):
    #   Field: origin
    #   Message: String should have at most 3 characters
    #   Type: string_too_long 
    #   ... (and other errors for destination, passengers)

    # You can return a structured error response:
    # error_response = {
    #     "error_code": "VALIDATION_ERROR",
    #     "message": "Input validation failed.",
    #     "details": e.errors() # Provides a list of error details
    # }
    # return error_response
```

## 4. Nested Models

Pydantic excels at handling nested data structures, which is common in travel data.

```python
class Passenger(BaseModel):
    model_config = ConfigDict(extra="forbid")
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    age: Optional[int] = Field(None, ge=0, le=120)
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

    offer_id: str = Field(..., description="The unique ID of the flight offer to book.")
    passengers: List[Passenger] = Field(..., min_length=1, description="List of passengers for the booking.")
    contact_email: Annotated[str, Field(..., description="Primary contact email for the booking.")] # Pydantic has EmailStr for stricter email validation
    payment_token: str = Field(..., description="A secure token representing payment information.") # Never handle raw CC details
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator('passengers')
    @classmethod
    def ensure_at_least_one_adult(cls, v: List[Passenger]) -> List[Passenger]:
        if not any(p.passenger_type == "adult" for p in v):
            # This validation might be better if passenger_type is set before this validator runs,
            # or if age is always required to derive passenger_type.
            # For simplicity, assuming passenger_type is correctly set.
            raise ValueError("At least one adult passenger is required for a booking.")
        return v

# Example Usage:
# passenger_data = [
#     {"first_name": "John", "last_name": "Doe", "age": 30},
#     {"first_name": "Jane", "last_name": "Doe", "age": 5}
# ]
# booking_req_data = {
#     "offer_id": "offer_123xyz",
#     "passengers": passenger_data,
#     "contact_email": "john.doe@example.com",
#     "payment_token": "tok_abcdef123456"
# }
# try:
#     booking_request = FlightBookingRequest(**booking_req_data)
#     print("Booking Request Validated:", booking_request.model_dump_json(indent=2))
# except ValidationError as e:
#     print("Booking Request Validation Error:", e.errors())
```

## 5. Settings Management

Pydantic's `BaseSettings` is used for centralized application configuration.

(Refer to `docs/08_REFERENCE/Centralized_Settings.md` for the detailed guide on settings management in TripSage.)

## 6. Tips for Pydantic v2 in TripSage

* **`model_config = ConfigDict(...)`**: Always use `ConfigDict` for model configurations.
* **Immutability**: Use `frozen=True` in `ConfigDict` for models representing data that shouldn't change after creation (like API request parameters once validated).
* **Strictness**: `extra="forbid"` is good practice for API inputs to catch unexpected fields.
* **Type Hinting**: Be explicit with type hints, including `Optional`, `List`, `Dict`, `Union`, and `Literal`. Use `Annotated` for complex field constraints.
* **Validators**:
  * `@field_validator`: For single field validation or transformation.
  * `@model_validator(mode="after")`: For cross-field validation after individual fields are processed.
  * `@model_validator(mode="before")`: For pre-processing the entire input data dictionary.
* **Serialization/Deserialization**:
  * `model.model_dump()`: Replaces `.dict()`. Use `mode="json"` to get JSON-serializable types (e.g., `date` to string).
  * `model.model_dump_json()`: Replaces `.json()`.
  * `MyModel.model_validate(data_dict)`: Replaces `MyModel.parse_obj(data_dict)`.
  * `MyModel.model_validate_json(json_string)`: Replaces `MyModel.parse_raw(json_string)`.
* **Computed Fields**: Use `@computed_field` decorator for fields derived from other fields.
* **Default Factories**: Use `default_factory` for defaults that require function calls (e.g., `uuid.uuid4`, `datetime.utcnow`).

By consistently applying these Pydantic v2 patterns, TripSage ensures robust data validation, clear data contracts, and improved maintainability across its components.

## 7. Testing Pydantic BaseSettings Classes

**Critical Pattern for TripSage Testing Infrastructure**

When testing code that uses Pydantic BaseSettings classes (like `AppSettings`), special care must be taken because these classes instantiate at module import time. This means environment variables must be set **before** any imports that trigger pydantic validation.

### The Problem

```python
# ❌ WRONG - This will fail with validation errors
import os
from tripsage.config.app_settings import AppSettings  # Settings instantiate here!

# Too late - the settings have already been validated
os.environ["OPENAI_API_KEY"] = "test-key"
```

### The Solution

```python
# ✅ CORRECT - Set environment variables BEFORE imports
import os

# CRITICAL: Set ALL environment variables BEFORE imports
test_env_vars = {
    "OPENAI_API_KEY": "test-openai-key",
    "PASSWORD": "test-password",  # For Neo4j
    "SUPABASE_URL": "https://test-project.supabase.co",
    "SUPABASE_ANON_KEY": "test_anon_key",
    "NEO4J_URI": "bolt://localhost:7687",
    "NEO4J_USER": "test_user",
    "NEO4J_PASSWORD": "test_password",
    # ... all required environment variables
}

for key, value in test_env_vars.items():
    os.environ[key] = value

# Now safe to import pydantic settings classes
from tripsage.config.app_settings import AppSettings
```

### Test Environment Configuration

TripSage provides a comprehensive test environment setup:

1. **Test Environment File**: `tests/.env.test`
   ```env
   # Test-safe environment variables
   OPENAI_API_KEY=test-openai-key
   PASSWORD=test-password
   SUPABASE_URL=https://test-project.supabase.co
   # ... comprehensive test configuration
   ```

2. **TestSettings Class**: `tests/test_settings.py`
   ```python
   from pydantic import BaseSettings
   from typing import Dict
   
   class TestSettings(BaseSettings):
       """Test-safe settings configuration."""
       openai_api_key: str = "test-openai-key"
       password: str = "test-password"
       # ... all test settings
       
       class Config:
           env_file = "tests/.env.test"
   
   def get_test_env_vars() -> Dict[str, str]:
       """Get test environment variables as a dictionary."""
       test_settings = TestSettings()
       return {
           "OPENAI_API_KEY": test_settings.openai_api_key,
           "PASSWORD": test_settings.password,
           # ... map all settings to environment variables
       }
   ```

3. **Test Pattern**: `tests/agents/test_chat_agent_demo.py`
   ```python
   import os
   from tests.test_settings import get_test_env_vars
   
   # CRITICAL: Set environment before ANY imports
   for key, value in get_test_env_vars().items():
       os.environ[key] = value
   
   # Now safe to import application modules
   from tripsage.config.app_settings import AppSettings
   from tripsage.agents.chat import ChatAgent
   
   def test_chat_agent():
       """Test ChatAgent with proper environment isolation."""
       # Test implementation here
   ```

### Key Benefits

- **Environment Isolation**: Tests never use real personal configuration
- **Reproducible Results**: Consistent test environment across all runs  
- **Security**: No risk of exposing real API keys or credentials in tests
- **Reliability**: Tests don't fail due to missing or invalid environment variables

### Documentation

For complete implementation details, see:
- `tests/TESTING_SOLUTION.md` - Comprehensive testing solution documentation
- `tests/.env.test` - Test environment configuration
- `tests/test_settings.py` - TestSettings class and utilities
