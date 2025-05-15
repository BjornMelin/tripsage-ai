# TripSage MCP Abstraction Layer

This document describes the unified abstraction layer for interacting with various external MCP clients in TripSage. The abstraction layer provides a consistent interface, standardized error handling, and dependency injection support for all MCP interactions.

## Architecture Overview

The MCP abstraction layer consists of four main components:

1. **Manager (MCPManager)**: Central orchestrator for all MCP operations
2. **Registry (MCPClientRegistry)**: Maintains mapping of MCP names to wrapper classes
3. **Base Wrapper (BaseMCPWrapper)**: Abstract interface that all wrappers implement
4. **Specific Wrappers**: Concrete implementations for each MCP type

```
┌─────────────────────────────────────────┐
│           Agent/Tool/Service            │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│            MCP Manager                  │
│  - Configuration loading                │
│  - Client initialization                │
│  - Method invocation routing            │
│  - Error handling & logging             │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│          MCP Registry                   │
│  - Wrapper registration                 │
│  - Instance management                  │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│         MCP Wrappers                    │
│  ┌──────────────┐  ┌───────────────┐   │
│  │ Playwright   │  │ Google Maps   │   │
│  │   Wrapper    │  │   Wrapper     │   │
│  └──────────────┘  └───────────────┘   │
│  ┌──────────────┐  ┌───────────────┐   │
│  │   Weather    │  │   [Future]    │   │
│  │   Wrapper    │  │   Wrappers    │   │
│  └──────────────┘  └───────────────┘   │
└─────────────────────────────────────────┘
```

## Design Pattern

The abstraction layer implements a **Manager/Registry pattern** with **type-safe wrapper interfaces**:

- **Manager Pattern**: Centralizes lifecycle management and routing
- **Registry Pattern**: Enables dynamic registration of MCP wrappers
- **Wrapper Pattern**: Provides consistent interface across different MCPs
- **Singleton Pattern**: Ensures single instances of manager and registry

## Key Features

### 1. Consistent Interface

All MCP interactions go through the same interface:

```python
# Using the manager
result = await mcp_manager.invoke(
    mcp_name="weather",
    method_name="get_current_weather",
    params={"city": "New York"}
)

# Direct wrapper access
wrapper = await mcp_manager.initialize_mcp("weather")
result = await wrapper.invoke_method("get_current_weather", params={...})
```

### 2. Type Safety

The abstraction layer maintains type safety through:

- Pydantic models for configuration
- Generic type parameters in base classes
- Strong typing in method signatures

### 3. Configuration Management

MCP configurations are loaded from `mcp_settings.py`:

- Automatic configuration validation
- Environment variable support
- Sensible defaults

### 4. Error Handling

Standardized error handling across all MCPs:

- Custom exception hierarchy
- Error categorization
- Consistent error messages
- Proper error propagation

### 5. Dependency Injection

Easy integration with FastAPI and other frameworks:

```python
# FastAPI dependency
async def get_mcp_manager_dep() -> MCPManager:
    return get_mcp_manager()

@router.get("/weather/{city}")
async def get_weather(
    city: str,
    mcp_manager: MCPManager = Depends(get_mcp_manager_dep)
):
    result = await mcp_manager.invoke("weather", "get_current_weather", {"city": city})
    return result
```

## Implementation Guide

### Creating a New MCP Wrapper

1. Create a new wrapper class inheriting from `BaseMCPWrapper`:

```python
from tripsage.mcp_abstraction.base_wrapper import BaseMCPWrapper

class NewMCPWrapper(BaseMCPWrapper[NewMCPClient]):
    def __init__(self, client=None, mcp_name="new_mcp"):
        if client is None:
            # Create client from configuration
            config = mcp_settings.new_mcp
            client = NewMCPClient(config)
        super().__init__(client, mcp_name)

    def _build_method_map(self) -> Dict[str, str]:
        return {
            "standard_method": "client_specific_method",
            # Map all methods
        }

    def get_available_methods(self) -> List[str]:
        return list(self._method_map.keys())
```

2. Register the wrapper in `registration.py`:

```python
mcp_registry.register(
    mcp_name="new_mcp",
    wrapper_class=NewMCPWrapper,
    replace=True
)
```

### Using the Abstraction Layer in Tools

```python
from agents import function_tool
from tripsage.mcp_abstraction import mcp_manager

@function_tool
async def my_tool(param: str) -> dict:
    """Tool using MCP abstraction layer."""
    result = await mcp_manager.invoke(
        mcp_name="my_mcp",
        method_name="my_method",
        params={"param": param}
    )
    return result
```

### Advanced Usage

```python
# Initialize all enabled MCPs
await mcp_manager.initialize_all_enabled()

# Check available MCPs
available = mcp_manager.get_available_mcps()

# Get specific wrapper for advanced operations
wrapper = await mcp_manager.initialize_mcp("weather")
methods = wrapper.get_available_methods()

# Direct client access (when needed)
client = wrapper.get_client()
```

## Benefits

1. **Consistency**: All MCPs accessed through same patterns
2. **Extensibility**: Easy to add new MCP integrations
3. **Maintainability**: Centralized configuration and error handling
4. **Testability**: Easy to mock and test MCP interactions
5. **Type Safety**: Full type checking throughout the system
6. **Flexibility**: Multiple levels of access (manager, wrapper, client)

## Migration Path

To migrate existing tools to use the abstraction layer:

1. Replace direct client instantiation with `mcp_manager.invoke()`
2. Update error handling to use abstraction layer exceptions
3. Remove client-specific configuration code
4. Update tests to mock the abstraction layer

## Future Enhancements

1. **Caching Layer**: Add caching at the abstraction level
2. **Metrics Collection**: Track MCP usage and performance
3. **Circuit Breakers**: Add resilience patterns
4. **Batch Operations**: Support batch method invocations
5. **Async Event System**: Publish events for MCP operations

## Example Integration

### Weather Tools Example

Original implementation:

```python
from tripsage.clients.weather import WeatherMCPClient

async def get_weather(city: str):
    client = WeatherMCPClient.get_client()
    return await client.get_current_weather(city)
```

Using abstraction layer:

```python
from tripsage.mcp_abstraction import mcp_manager

async def get_weather(city: str):
    return await mcp_manager.invoke(
        "weather",
        "get_current_weather",
        {"city": city}
    )
```

This abstraction layer provides a robust foundation for all MCP interactions in TripSage, ensuring consistency, maintainability, and extensibility.
