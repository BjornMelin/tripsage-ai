# General MCP Implementation Patterns and Evaluation

This document outlines standardized patterns, best practices, and evaluation criteria for implementing and integrating Model Context Protocol (MCP) servers within the TripSage project. It serves as a guide for developing consistent, maintainable, and efficient MCP components.

## 1. MCP Strategy and Evaluation Criteria

TripSage adopts a hybrid approach to MCP server integration:

- **External First**: Prioritize using existing, well-maintained external MCPs for standardized functionality (e.g., Time, Neo4j Memory, Google Maps).
- **Custom When Necessary**: Build custom MCPs using Python FastMCP 2.0 when:
  - The functionality is core to TripSage's unique business logic.
  - Direct database integration or complex orchestration of multiple APIs is required.
  - Specific privacy, security, or performance requirements cannot be met by external MCPs.
- **Thin Wrapper Clients**: Create lightweight Python client wrappers around all MCPs (both external and custom). These wrappers add TripSage-specific validation, error handling, logging, and metrics, and integrate with the MCP Abstraction Layer.

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
from fastmcp import FastMCP, Context, Tool
from pydantic import BaseModel, Field
from typing import Annotated, List, Dict, Any, Optional

class ExampleToolParams(BaseModel):
    location: str = Field(..., description="City or location name.")
    days: Annotated[int, Field(gt=0, le=10, description="Number of days.")]

class ExampleToolResponse(BaseModel):
    status: str
    data: List[Dict[str, Any]]
    message: Optional[str] = None

mcp_server = FastMCP(
    name="CustomMCPExample",
    version="1.0.0",
    description="An example custom MCP server for TripSage."
)

@mcp_server.tool(
    name="get_custom_data",
    description="Fetches custom data based on location and days."
)
async def get_custom_data_tool(params: ExampleToolParams, ctx: Context) -> ExampleToolResponse:
    await ctx.info(f"Fetching {params.days}-day custom data for {params.location}")
    try:
        processed_data = [{"day": i+1, "info": f"Data for day {i+1}"} for i in range(params.days)]
        await ctx.report_progress(0.5, f"Retrieved data for {params.location}")
        await ctx.report_progress(1.0, "Processing complete")
        return ExampleToolResponse(status="success", data=processed_data)
    except ValueError as ve:
        await ctx.error(f"Data processing validation error: {ve}")
        raise
    except Exception as e:
        await ctx.error(f"Unexpected error in get_custom_data_tool: {e}", exc_info=True)
        raise
```

### 2.2. Context Object (`ctx`) Usage

The `Context` object passed to tool handlers is crucial for:

- **Logging**
- **Progress Reporting**
- **Resource Access**
- **LLM Assistance (Sampling)**

### 2.3. Error Handling Best Practices

- Use Pydantic for input validation.
- Catch specific exceptions.
- Log detailed errors with `ctx.error`.
- Return structured errors or raise MCP exceptions.
- Employ graceful degradation if possible.

### 2.4. Tool Naming and Registration

- Methods ending with `_tool` are automatically registered unless explicitly decorated.
- For more control, use the `@mcp_server.tool(...)` decorator.

## 3. Standardized Service Patterns (CRUD & Search)

When MCPs manage persistent entities, TripSage uses base service classes to standardize CRUD and Search operations. Examples include:

```python
# Example: CRUDServiceBase usage
# class ItemService(CRUDServiceBase[ItemModel, ItemCreateRequest, ItemUpdateRequest]):
#     ...
```

## 4. Client-Side Integration (Python MCP Clients)

All MCP servers (custom or external) are accessed via Python client classes that inherit from `BaseMCPClient`. Key features:

- Configuration from centralized settings.
- Standardized error handling.
- Tool invocation with `invoke_tool`.
- Pydantic validation for inputs/outputs.
- Optional caching in Redis.
- `@function_tool` decorator for direct agent usage.

## 5. Conclusion

These patterns and guidelines ensure consistency and maintainability across TripSage’s MCP servers. By leveraging FastMCP 2.0 for custom development, along with best practices for error handling and validation, TripSage maintains a robust microservices architecture for its AI-driven travel platform.
