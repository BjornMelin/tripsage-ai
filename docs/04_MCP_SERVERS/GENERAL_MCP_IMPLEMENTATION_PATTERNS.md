# General MCP Implementation Patterns and Evaluation

This document outlines standardized patterns, best practices, and evaluation criteria for implementing and integrating Model Context Protocol (MCP) servers within the TripSage project. It serves as a guide for developing consistent, maintainable, and efficient MCP components.

## 1. MCP Strategy and Evaluation Criteria

TripSage adopts a hybrid approach to MCP server integration:

* **External First**: Prioritize using existing, well-maintained external MCPs for standardized functionality (e.g., Time, Neo4j Memory, Google Maps).
* **Custom When Necessary**: Build custom MCPs using Python FastMCP 2.0 when:
  * The functionality is core to TripSage's unique business logic.
  * Direct database integration or complex orchestration of multiple APIs is required.
  * Specific privacy, security, or performance requirements cannot be met by external MCPs.
* **Thin Wrapper Clients**: Create lightweight Python client wrappers around all MCPs (both external and custom). These wrappers add TripSage-specific validation, error handling, logging, and metrics, and integrate with the MCP Abstraction Layer.

### Evaluation Criteria for MCP Solutions

When choosing or building an MCP solution, consider the following:

1. **Functionality & Feature Set**: Does it meet TripSage's requirements?
2. **Maturity & Maintenance**: Is it actively maintained? Is it stable?
3. **Implementation Language & Technology**: Preference for Python (FastMCP 2.0) for custom servers to align with the backend stack.
4. **Ease of Integration**: How well does it fit into the TripSage architecture (MCP Abstraction Layer, OpenAI Agents SDK)?
5. **Performance**: Latency, throughput, resource consumption.
6. **Scalability**: Can it handle increasing load?
7. **Cost**: API fees, hosting costs, development effort.
8. **Security**: Authentication, data protection.
9. **Documentation & Community Support**.
10. **Licensing**.

## 2. Custom MCP Server Implementation with Python FastMCP 2.0

All custom MCP servers in TripSage are developed using Python FastMCP 2.0.

### 2.1. Server Structure Example

```python
# src/mcp/custom_mcp_server_name/server.py
from fastmcp import FastMCP, Context, Tool
from pydantic import BaseModel, Field
from typing import Annotated, List, Dict, Any, Optional

# --- Configuration (Loaded from centralized settings) ---
# from ....utils.config import settings
# mcp_config = settings.mcp_servers.custom_mcp_server_name

# --- Pydantic Models for Tool Inputs/Outputs ---
class ExampleToolParams(BaseModel):
    location: str = Field(..., description="City or location name.")
    days: Annotated[int, Field(gt=0, le=10, description="Number of days.")]

class ExampleToolResponse(BaseModel):
    status: str
    data: List[Dict[str, Any]]
    message: Optional[str] = None

# --- MCP Server Initialization ---
# The server name should match the key in the centralized MCP configuration
mcp_server = FastMCP(
    name="CustomMCPExample",
    version="1.0.0",
    description="An example custom MCP server for TripSage."
)

# --- Tool Implementation ---
@mcp_server.tool(
    name="get_custom_data", # Explicit tool name for clarity
    description="Fetches custom data based on location and days."
    # input_model=ExampleToolParams, # FastMCP can infer from type hints
    # output_model=ExampleToolResponse # FastMCP can infer from return type hints
)
async def get_custom_data_tool(params: ExampleToolParams, ctx: Context) -> ExampleToolResponse:
    """
    Fetches custom data.
    Args:
        params: Validated input parameters (ExampleToolParams).
        ctx: MCP context object for logging, progress, etc.
    Returns:
        Validated output (ExampleToolResponse).
    """
    await ctx.info(f"Fetching {params.days}-day custom data for {params.location}")

    try:
        # --- Main tool logic ---
        # Example: Call an external API or perform business logic
        # external_api_result = await some_api_client.fetch(params.location, params.days)
        # processed_data = _transform_api_result(external_api_result)
        processed_data = [{"day": i+1, "info": f"Data for day {i+1}"} for i in range(params.days)] # Mock data

        await ctx.report_progress(0.5, f"Retrieved data for {params.location}")

        # Example: Using LLM assistance via context if needed
        # summary = await ctx.sample("Summarize this custom data briefly", processed_data)
        
        await ctx.report_progress(1.0, "Processing complete")
        return ExampleToolResponse(status="success", data=processed_data)

    except ValueError as ve: # Example: Pydantic validation error during internal processing
        await ctx.error(f"Data processing validation error: {ve}")
        # Re-raise or return a structured error
        # For FastMCP, raising an exception is often cleaner if it's an unrecoverable tool error.
        # FastMCP will handle turning it into a proper MCP error response.
        raise MCPToolExecutionError(f"Invalid data encountered: {ve}") # Assuming MCPToolExecutionError
    except Exception as e:
        await ctx.error(f"Unexpected error in get_custom_data_tool: {e}", exc_info=True)
        # Return a structured error response for the MCP client
        # This pattern is useful if you want to pass back specific error codes/messages
        # return ExampleToolResponse(
        #     status="error", 
        #     data=[], 
        #     message=f"An unexpected error occurred: {type(e).__name__}"
        # )
        # Alternatively, just raise, and FastMCP handles it:
        raise MCPToolExecutionError(f"Tool execution failed: {e}")


# --- Resource Implementation (Optional) ---
@mcp_server.resource(uri_pattern="custom://data_sources/available")
async def get_available_data_sources(ctx: Context) -> List[str]:
    """Returns a list of available data sources for this MCP."""
    await ctx.info("Fetching available data sources.")
    return ["source_A", "source_B"]

# --- Server Startup (for standalone execution) ---
# if __name__ == "__main__":
#     # Load environment variables if needed (e.g., using python-dotenv)
#     # from dotenv import load_dotenv
#     # load_dotenv()
#     # logger = configure_logging_for_mcp("CustomMCPExample") # Setup logging
#     mcp_server.run(
#         transport="http", # or "sse", "stdio"
#         host=settings.mcp_servers.custom_mcp_server_name.host, # From centralized settings
#         port=settings.mcp_servers.custom_mcp_server_name.port  # From centralized settings
#     )
```

### 2.2. Context Object (`ctx`) Usage

The `Context` object passed to tool handlers is crucial for:

* **Logging**:
  * `await ctx.debug("Detailed debug message")`
  * `await ctx.info("Informational message")`
  * `await ctx.warning("Potential issue encountered")`
  * `await ctx.error("Error occurred", exc_info=True)` (includes traceback)
* **Progress Reporting**:
  * `await ctx.report_progress(0.0, "Starting task...")`
  * `await ctx.report_progress(0.5, "Halfway done.")`
  * `await ctx.report_progress(1.0, "Task completed.")`
* **Resource Access**:
  * `available_sources = await ctx.read_resource("custom://data_sources/available")`
* **LLM Assistance (Sampling)**:
  * `summary = await ctx.sample("Summarize this text:", long_text_data)`

### 2.3. Error Handling Best Practices

* **Use Pydantic for Input Validation**: Define Pydantic models for tool inputs. FastMCP automatically validates incoming parameters against these models.
* **Specific Exception Handling**: Catch specific exceptions from API calls or business logic (e.g., `httpx.HTTPStatusError`, `ValueError`).
* **Log Detailed Errors**: Use `await ctx.error(..., exc_info=True)` for comprehensive server-side logs.
* **Return Structured Errors or Raise MCP Exceptions**:
  * For errors the client might be able to handle or display, return a Pydantic model that includes error details.
  * For unrecoverable tool execution failures, raise an appropriate exception (e.g., `fastmcp.MCPError` or a custom derivative). FastMCP will format this into a standard MCP error response.
* **Graceful Degradation**: If a primary data source fails, attempt to use a fallback if available and inform the context (`ctx.warning`).

### 2.4. Tool Naming and Registration

* **Automatic Discovery**: Methods ending with `_tool` (e.g., `get_weather_data_tool`) are automatically registered. The `_tool` suffix is typically removed to form the MCP tool name unless explicitly decorated.
* **Explicit Decoration**: Use `@mcp_server.tool(name="actual_tool_name", ...)` for:
  * Methods not following the `_tool` suffix convention.
  * Overriding the automatically derived tool name.
  * Providing schema directly if not inferable from type hints or if more complex.

## 3. Standardized Service Patterns (CRUD & Search)

For MCPs that manage persistent entities, TripSage uses base service classes to standardize CRUD (Create, Read, Update, Delete) and Search operations. These are typically used when an MCP server directly interacts with a database (like the Supabase/Neon MCPs or a custom MCP managing its own data).

* **`MCPServiceBase`**: Foundational abstract base class.
* **`CRUDServiceBase`**: Generic implementation for CRUD tools.
* **`SearchServiceBase`**: Base for search-focused tools.

These base classes (e.g., in `src/mcp/service_base.py`) promote:

* Automatic registration of standard tools (`create_<entity>`, `read_<entity>`, etc.).
* Type safety using Python generics tied to Pydantic entity models.
* Consistent error handling for common database operations.

**Example of a Service using `CRUDServiceBase`:**

```python
# Conceptual example - actual implementation in specific DB MCPs
# from typing import Dict, List, Optional, Any
# from pydantic import BaseModel
# from src.mcp.service_base import CRUDServiceBase, mcp_tool # Adjust import

# class ItemModel(BaseModel):
#     id: str
#     name: str
#     description: Optional[str] = None

# class ItemCreateRequest(BaseModel):
#     name: str
#     description: Optional[str] = None

# class ItemUpdateRequest(BaseModel):
#     name: Optional[str] = None
#     description: Optional[str] = None

# class ItemService(CRUDServiceBase[ItemModel, ItemCreateRequest, ItemUpdateRequest]):
#     def __init__(self, db_client: Any): # db_client would be specific to the database
#         super().__init__(
#             service_name="item_manager", # Used for tool name prefixing
#             entity_type=ItemModel,
#             request_type=ItemCreateRequest, # For create
#             response_type=ItemModel, # For read/create/update responses
#             update_request_type=ItemUpdateRequest # For update
#         )
#         self.db_client = db_client
#         # Tool names would be like: item_manager_create_item, item_manager_read_item, etc.

    # --- Implement abstract CRUD methods ---
    # async def _create_entity(self, data: ItemCreateRequest) -> ItemModel:
    #     # ... logic to create item in DB using self.db_client ...
    #     pass

    # async def _read_entity(self, entity_id: str) -> Optional[ItemModel]:
    #     # ... logic to read item from DB ...
    #     pass
    
    # async def _update_entity(self, entity_id: str, data: ItemUpdateRequest) -> Optional[ItemModel]:
    #     # ... logic to update item in DB ...
    #     pass

    # async def _delete_entity(self, entity_id: str) -> bool:
    #     # ... logic to delete item from DB ...
    #     pass

    # async def _list_entities(self, page: int = 1, page_size: int = 20, filters: Optional[Dict[str, Any]] = None) -> List[ItemModel]:
    #     # ... logic to list items from DB ...
    #     pass

    # --- Custom tools specific to this service ---
    # @mcp_tool 
    # async def get_item_by_name_custom_tool(self, name: str, ctx: Context) -> Optional[ItemModel]:
    #     await ctx.info(f"Searching for item by name: {name}")
    #     # ... custom logic ...
    #     pass
```

## 4. Client-Side Integration (Python MCP Clients)

All MCP servers (custom or external) are accessed within TripSage via Python client classes that inherit from a `BaseMCPClient`. This `BaseMCPClient` is part of the MCP Abstraction Layer.

Key features of these clients:

* **Configuration**: Loaded from the centralized settings system.
* **Error Handling**: Standardized wrapping of MCP errors.
* **Tool Invocation**: A common method like `invoke_tool(tool_name: str, params: Dict)`.
* **Pydantic Validation**: Input parameters for tool calls are validated against Pydantic models. Response data can also be validated.
* **Caching**: Integration with Redis for caching MCP tool responses where appropriate (see Caching Strategy docs).
* **`@function_tool` Decorator**: Methods on these clients intended for direct use by OpenAI Agents are decorated with `@function_tool` to expose them correctly.

Refer to the documentation for the MCP Abstraction Layer and specific client implementations (e.g., `FlightsMCPClient`, `WeatherMCPClient`) for more details.

## 5. Conclusion

These patterns and guidelines ensure that MCP server development and integration within TripSage are consistent, robust, and maintainable. By leveraging FastMCP 2.0 for custom servers, standardizing client interactions, and adhering to best practices for error handling and validation, TripSage can effectively manage its diverse set of microservices and external API integrations.
