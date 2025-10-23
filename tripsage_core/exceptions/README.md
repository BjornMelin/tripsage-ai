# Exception System

This module defines exceptions and error handling utilities for the TripSage application.

## Core Components

### Base Exception

All exceptions inherit from `CoreTripSageError`:

```python
from tripsage_core.exceptions import CoreTripSageError

exc = CoreTripSageError(
    message="Error message",
    code="ERROR_CODE",
    status_code=500,
    details={"service": "example-service"}
)
```

### Exception Hierarchy

```text
CoreTripSageError (base)
├── CoreAuthenticationError (401)
├── CoreAuthorizationError (403) 
├── CoreResourceNotFoundError (404)
├── CoreValidationError (422)
├── CoreServiceError (502)
│   ├── CoreMCPError (502)
│   └── CoreAgentError (502)
├── CoreRateLimitError (429)
├── CoreKeyValidationError (400)
├── CoreDatabaseError (500)
└── CoreExternalAPIError (502)
```

### Error Details

Use `ErrorDetails` for structured error context:

```python
from tripsage_core.exceptions import ErrorDetails

details = ErrorDetails(
    service="flight-service",
    operation="search_flights",
    user_id="user123",
    request_id="req456",
    additional_context={
        "query_params": {"origin": "NYC", "destination": "LAX"},
        "external_api_status": 429
    }
)
```

## Usage

### Exception Creation

```python
from tripsage_core.exceptions import CoreValidationError

# Simple error
exc = CoreValidationError("Invalid email format")

# Detailed error
exc = CoreValidationError(
    message="Email validation failed",
    field="email",
    value="invalid-email",
    constraint="must be valid email address"
)
```

### Factory Functions

```python
from tripsage_core.utils.error_handling_utils import (
    create_mcp_error,
    create_api_error,
    create_validation_error
)

# MCP error
error = create_mcp_error(
    message="Flight search timeout",
    server="duffel-mcp",
    tool="search_flights",
    category="timeout"
)

# API error
error = create_api_error(
    message="OpenAI rate limit exceeded",
    service="openai",
    status_code=429,
    response={"error": "rate_limit_exceeded"}
)

# Validation error
error = create_validation_error(
    message="Invalid input data",
    field="departure_date",
    value="invalid-date",
    constraint="must be valid ISO date"
)
```

### Error Context

```python
from tripsage_core.utils.error_handling_utils import TripSageErrorContext

with TripSageErrorContext(
    operation="search_flights",
    service="flight_service",
    user_id="user123",
    request_id="req456"
):
    raise CoreMCPError("Flight search failed")
```

### API Responses

```python
from tripsage_core.exceptions import create_error_response
from fastapi import HTTPException

try:
    # operation
    pass
except CoreTripSageError as e:
    error_response = create_error_response(e)
    raise HTTPException(
        status_code=e.status_code,
        detail=error_response
    )
```

## Available Exceptions

```python
from tripsage_core.exceptions import (
    CoreTripSageError,
    CoreMCPError,
    CoreExternalAPIError,
    CoreValidationError,
    CoreDatabaseError
)
```

## Utility Functions

### Error Formatting

```python
from tripsage_core.exceptions import format_exception

try:
    raise CoreValidationError("Test error")
except Exception as e:
    formatted = format_exception(e)
    # Returns dict with error details
```

### Safe Execution

```python
from tripsage_core.exceptions import safe_execute

result = safe_execute(
    risky_operation,
    fallback="default_value",
    logger=logger
)
# Returns fallback value and logs exception
```

### Error Decorator

```python
from tripsage_core.exceptions import with_error_handling

@with_error_handling(fallback=[], logger=logger)
def get_flight_data():
    raise CoreExternalAPIError("API failed")

result = get_flight_data()  # Returns fallback and logs error
```

## Testing

Test files:

- `tests/unit/tripsage_core/test_exceptions.py`
- `tests/unit/utils/test_error_handling_integration.py`

Run tests:

```bash
python tests/unit/tripsage_core/test_exceptions_simple.py
```

## Notes

- Use specific exception types for different error categories
- Include context in error details for debugging
- Use factory functions for consistent error creation
- Use `TripSageErrorContext` for operation tracking
- Use `safe_execute` and `with_error_handling` for robust error handling

## Integrations

- FastAPI: HTTP status code mapping
- Pydantic: Error detail validation
- Logging: Structured error logging
