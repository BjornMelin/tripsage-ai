# TripSage Core Exception System

This directory contains the centralized exception system for the entire TripSage application. It provides a consistent, hierarchical exception framework that can be used across all components including APIs, agents, services, and tools.

## Overview

The TripSage Core Exception System consolidates exception handling from across the application into a single, consistent system. It replaces multiple fragmented exception implementations with a unified approach that provides:

- **Consistent Error Structure**: All exceptions follow the same pattern with message, code, status_code, and structured details
- **HTTP Status Code Integration**: Uses FastAPI status constants for proper API responses
- **Structured Error Details**: Pydantic-based error details for enhanced debugging and logging
- **Backwards Compatibility**: Aliases for existing exception names to ensure smooth migration
- **Utility Functions**: Helper functions for error handling, logging, and response creation

## Core Components

### Base Exception: CoreTripSageError

All TripSage exceptions inherit from `CoreTripSageError`, which provides:

```python
from tripsage_core.exceptions import CoreTripSageError

exc = CoreTripSageError(
    message="Human-readable error message",
    code="MACHINE_READABLE_CODE",
    status_code=500,  # HTTP status code
    details={"service": "example-service"}  # Structured details
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

### Structured Error Details

The `ErrorDetails` class provides structured context for debugging:

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

## Usage Examples

### Basic Exception Creation

```python
from tripsage_core.exceptions import CoreValidationError

# Simple validation error
exc = CoreValidationError("Invalid email format")

# Detailed validation error
exc = CoreValidationError(
    message="Email validation failed",
    field="email",
    value="invalid-email",
    constraint="must be valid email address"
)
```

### Factory Functions

Use factory functions for consistent error creation:

```python
from tripsage.utils.error_handling import (
    create_mcp_error,
    create_api_error,
    create_validation_error
)

# MCP service error
mcp_error = create_mcp_error(
    message="Flight search timeout",
    server="duffel-mcp", 
    tool="search_flights",
    category="timeout"
)

# External API error
api_error = create_api_error(
    message="OpenAI rate limit exceeded",
    service="openai",
    status_code=429,
    response={"error": "rate_limit_exceeded"}
)

# Validation error
validation_error = create_validation_error(
    message="Invalid input data",
    field="departure_date",
    value="invalid-date",
    constraint="must be valid ISO date"
)
```

### Error Context Management

Use the `TripSageErrorContext` for enhanced error tracking:

```python
from tripsage.utils.error_handling import TripSageErrorContext

with TripSageErrorContext(
    operation="search_flights",
    service="flight_service", 
    user_id="user123",
    request_id="req456"
):
    # Any exceptions raised here will be enhanced with context
    raise CoreMCPError("Flight search failed")
```

### API Error Responses

Create standardized API responses:

```python
from tripsage_core.exceptions import create_error_response
from fastapi import HTTPException

try:
    # Some operation that might fail
    pass
except CoreTripSageError as e:
    # Create API response
    error_response = create_error_response(e)
    raise HTTPException(
        status_code=e.status_code,
        detail=error_response
    )
```

## Backwards Compatibility

The system provides aliases for existing exception names:

```python
from tripsage.utils.error_handling import (
    TripSageError,      # -> CoreTripSageError
    MCPError,           # -> CoreMCPError
    APIError,           # -> CoreExternalAPIError
    ValidationError,    # -> CoreValidationError
    DatabaseError       # -> CoreDatabaseError
)

# These work exactly like before
exc = TripSageError("Compatible error")
```

## Utility Functions

### Error Formatting

```python
from tripsage_core.exceptions import format_exception

try:
    raise CoreValidationError("Test error")
except Exception as e:
    formatted = format_exception(e)
    # Returns standardized dict with error, message, code, status_code, details
```

### Safe Execution

```python
from tripsage_core.exceptions import safe_execute

def risky_operation():
    raise ValueError("Something went wrong")

result = safe_execute(
    risky_operation,
    fallback="default_value",
    logger=logger
)
# Returns "default_value" and logs the exception
```

### Error Handling Decorator

```python
from tripsage_core.exceptions import with_error_handling

@with_error_handling(fallback=[], logger=logger)
def get_flight_data():
    # Might raise an exception
    raise CoreExternalAPIError("API failed")

result = get_flight_data()  # Returns [] and logs error
```

## Testing

The exception system includes comprehensive tests demonstrating all functionality:

- `tests/unit/tripsage_core/test_exceptions.py` - Core exception system tests
- `tests/unit/utils/test_error_handling_integration.py` - Integration tests

Run tests directly (due to pytest import issues):

```bash
# Test core functionality
python tests/unit/tripsage_core/test_exceptions_simple.py

# Test integration
python -c "
import sys, os
sys.path.insert(0, '.')
# Run integration test code here
"
```

## Migration Guide

### From Old API Exceptions

Replace imports:

```python
# OLD
from api.core.exceptions import TripSageError, AuthenticationError

# NEW  
from tripsage_core.exceptions import CoreTripSageError, CoreAuthenticationError

# OR use backwards-compatible imports
from tripsage.utils.error_handling import TripSageError, AuthenticationError
```

### From Utility Exceptions

Replace direct exception classes:

```python
# OLD
from tripsage.utils.error_handling import MCPError, APIError

# NEW - use factory functions for consistency
from tripsage.utils.error_handling import create_mcp_error, create_api_error

# Or use aliases (backwards compatible)
from tripsage.utils.error_handling import MCPError, APIError
```

### Exception Creation

Update exception creation patterns:

```python
# OLD
exc = MCPError("Server failed", "flights-mcp", tool="search")

# NEW
exc = create_mcp_error("Server failed", "flights-mcp", tool="search")

# Or direct usage
exc = CoreMCPError(
    message="Server failed",
    server="flights-mcp", 
    tool="search"
)
```

## Best Practices

1. **Use Specific Exception Types**: Choose the most specific exception type for your use case
2. **Include Context**: Always provide relevant details in the `details` parameter
3. **Use Factory Functions**: Prefer factory functions for consistency
4. **Enhance with Context**: Use `TripSageErrorContext` for operation tracking
5. **Log Appropriately**: Use the built-in logging functions for consistent error reporting
6. **Handle Gracefully**: Use `safe_execute` and decorators for robust error handling

## Integration Points

The exception system integrates with:

- **FastAPI**: Direct status code mapping for HTTP responses
- **Pydantic**: Structured error details with validation
- **Logging**: Structured logging with rich context
- **MCP Services**: Specialized MCP error handling
- **External APIs**: Consistent external service error mapping
- **Database Operations**: Database-specific error context

## Architecture Benefits

- **Centralization**: Single source of truth for all application exceptions
- **Consistency**: Uniform error structure across all components  
- **Debuggability**: Rich context and structured details for troubleshooting
- **API Integration**: Direct HTTP status code mapping
- **Backwards Compatibility**: Smooth migration path from existing code
- **Extensibility**: Easy to add new exception types as needed
