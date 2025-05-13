# TripSage MCP Client Architecture

This module provides standardized Model Context Protocol (MCP) clients for accessing
various MCP servers in the TripSage application, including time, weather, flights,
accommodations, calendar, and more.

## Architecture

### Client Factory Pattern

All MCP clients follow a standardized factory pattern, which provides:

- Centralized configuration validation with Pydantic
- Consistent initialization patterns
- Global client instance management
- Configuration override capabilities
- Standardized error handling

### Directory Structure

```
src/mcp/
├── __init__.py
├── base_mcp_client.py        # Base client classes
├── client_factory.py         # Base factory classes
├── fastmcp.py                # FastMCP 2.0 implementation
├── [service]/                # Service-specific implementation
    ├── __init__.py
    ├── client.py             # MCP client implementation
    ├── factory.py            # Client factory implementation
    ├── models.py             # Pydantic models for parameters/responses
```

### MCP Client Usage

To use an MCP client:

```python
from src.mcp.time.factory import get_client as get_time_client

# Get default client (configured from settings)
time_client = get_time_client()

# Get client with custom configuration
custom_client = get_time_client(
    endpoint="https://custom-endpoint.example.com",
    timeout=60.0
)

# Make an API call
result = await time_client.get_current_time("America/New_York")
```

### Error Handling

All MCP clients use a standardized error handling approach:

1. Errors are categorized by type (validation, network, authentication, etc.)
2. All errors are wrapped in a consistent MCPError with detailed context
3. Error messages are user-friendly and actionable
4. Logging is detailed and consistent across all clients

## Implementing a New MCP Client

To implement a new MCP client, follow these steps:

1. Create a directory under `src/mcp/` for your service
2. Create `models.py` with Pydantic models for parameters and responses
3. Create `client.py` with client implementation, extending BaseMCPClient or FastMCPClient
4. Create `factory.py` with a client factory implementation, following the pattern

Example factory implementation:

```python
from ..client_factory import BaseClientFactory, ClientConfig
from .client import MyServiceClient

class MyServiceConfig(ClientConfig):
    # Custom configuration fields
    pass

class MyServiceClientFactory(BaseClientFactory[MyServiceClient, MyServiceConfig]):
    def __init__(self):
        super().__init__(
            client_class=MyServiceClient,
            config_class=MyServiceConfig,
            server_name="MyService",
            default_config={...}
        )
    
    def _load_config_from_settings(self):
        # Load from settings
        pass

# Create global factory instance
my_service_factory = MyServiceClientFactory()

def get_client(**override_config):
    return my_service_factory.get_client(**override_config)
```

## Testing MCP Clients

All MCP clients should be tested for:

- Configuration validation
- Client initialization
- Factory functionality 
- Tool methods with mocked responses
- Error handling

See the test files in `tests/mcp/` for examples.