# MCP Service Patterns

This document outlines standardized service patterns for MCP (Model Context Protocol) implementations in the TripSage project.

## Overview

MCP services provide a standardized approach to implementing external service integrations through the Model Context Protocol. The service patterns described here ensure consistency, maintainability, and adherence to SOLID principles across different MCP implementations.

## Base Service Classes

The TripSage MCP implementation includes the following base service classes:

1. `MCPServiceBase` - The foundational abstract base class for all MCP services
2. `CRUDServiceBase` - Generic implementation for Create, Read, Update, Delete operations
3. `SearchServiceBase` - Base implementation for search operations

These classes are located in `src/mcp/service_base.py`.

## Service Pattern Design

### Key Features

- **Automatic Tool Registration:** Tools are automatically discovered and registered based on method naming conventions (`*_tool`) or explicit decoration with `@mcp_tool`.
- **Type Safety:** Generic typing ensures that service implementations adhere to the expected request and response models.
- **Standardized Error Handling:** Common error handling patterns are implemented consistently across services.
- **Extensibility:** The pattern allows for easy extension with custom operations beyond CRUD.

### Implementation Example

Here's a simplified example of implementing a service using the base classes:

```python
from typing import Dict, List, Optional, Any
from pydantic import BaseModel

from src.mcp.models import MCPRequestBase, MCPResponseBase
from src.mcp.service_base import CRUDServiceBase, mcp_tool

# Define models
class WeatherRequest(MCPRequestBase):
    location: str
    units: str = "metric"

class WeatherResponse(MCPResponseBase):
    temperature: float
    humidity: float
    description: str

# Implement service
class WeatherService(CRUDServiceBase[WeatherResponse, WeatherRequest, WeatherResponse]):
    def __init__(self, api_key: str):
        super().__init__(
            service_name="weather",
            entity_type=WeatherResponse,
            request_type=WeatherRequest,
            response_type=WeatherResponse,
        )
        self.api_key = api_key

    async def create(self, data: WeatherRequest) -> WeatherResponse:
        # Implementation for creating a weather record
        ...

    async def read(self, entity_id: str) -> WeatherResponse:
        # Implementation for reading a weather record
        ...

    async def update(self, entity_id: str, data: WeatherRequest) -> WeatherResponse:
        # Implementation for updating a weather record
        ...

    async def delete(self, entity_id: str) -> bool:
        # Implementation for deleting a weather record
        ...

    async def list(
        self, page: int = 1, page_size: int = 20, filters: Optional[Dict[str, Any]] = None
    ) -> List[WeatherResponse]:
        # Implementation for listing weather records
        ...

    @mcp_tool  # Explicitly mark as a tool
    async def forecast_tool(self, location: str, days: int = 5) -> Dict[str, Any]:
        # Custom tool implementation
        ...
```

## Tool Registration and Discovery

Tools are registered through two mechanisms:

1. **Naming Convention:** Methods ending with `_tool` are automatically registered
2. **Explicit Decoration:** Methods decorated with `@mcp_tool` are registered

The tool name used in the MCP protocol is derived from the method name. For methods ending in `_tool`, the suffix is removed unless the method is explicitly decorated.

## Parameter Validation

Parameter validation is centralized in Pydantic models defined in `src/mcp/models.py`. These models provide:

1. Standard base classes for requests and responses
2. Common validation patterns for dates, coordinates, pagination, etc.
3. Consistent error messages and formatting

## Best Practices

When implementing new MCP services:

1. **Extend the appropriate base class** based on the service's operations
2. **Define clear request and response models** using Pydantic
3. **Use the `@mcp_tool` decorator** for methods that don't follow the naming convention
4. **Implement proper error handling** with specific error types
5. **Document the service interface** with detailed docstrings
6. **Follow the single responsibility principle** when designing service methods

## Example Service Operations

The base service classes provide these standard operations:

### CRUD Operations

- `create`: Create a new entity
- `read`: Read an entity by ID
- `update`: Update an existing entity
- `delete`: Delete an entity
- `list`: List entities with optional filtering and pagination

### Search Operations

- `search`: Search for entities based on a query and options

### Custom Operations

Services can implement custom operations in addition to the standard ones by:

1. Creating methods with the `_tool` suffix
2. Using the `@mcp_tool` decorator on custom methods
3. Implementing specialized business logic as needed

## Error Handling

The service pattern includes standardized error handling:

1. All service exceptions are wrapped as `MCPError` instances
2. Errors include specific error types for client handling
3. Validation errors are handled consistently
4. Request/response conversion errors are properly reported

## Integration with MCP Client

The service patterns are designed to work seamlessly with the MCP client infrastructure:

1. Services register their tools with the MCP client
2. The client routes tool requests to the appropriate service
3. Tools can be registered with prefixes for disambiguation
4. Error responses are standardized across services