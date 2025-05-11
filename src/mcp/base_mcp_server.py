"""
Base MCP Server implementation for TripSage.

This module provides the base class for all MCP servers in the TripSage system,
with common functionality for tool registration, request handling, and error reporting.
"""

import inspect
from typing import (
    Any,
    Dict,
    Optional,
    Protocol,
    runtime_checkable,
)

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from ..utils.error_handling import MCPError, log_exception
from ..utils.logging import get_module_logger

logger = get_module_logger(__name__)


@runtime_checkable
class MCPTool(Protocol):
    """Protocol defining the standard interface for all MCP tools."""

    name: str
    description: str

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the tool with the given parameters."""
        ...


class ToolMetadata(BaseModel):
    """Metadata for an MCP tool."""

    name: str
    description: str
    parameters_schema: Dict[str, Any]
    return_schema: Dict[str, Any]


class ToolCallRequest(BaseModel):
    """Request to call an MCP tool."""

    params: Dict[str, Any]


class BaseMCPServer:
    """Base class for all MCP servers in TripSage."""

    def __init__(
        self,
        name: str,
        description: str = "",
        version: str = "1.0.0",
        host: str = "0.0.0.0",
        port: int = 3000,
    ):
        """Initialize the MCP server.

        Args:
            name: Server name
            description: Server description
            version: Server version
            host: Host to bind to
            port: Port to listen on
        """
        self.name = name
        self.description = description
        self.version = version
        self.host = host
        self.port = port

        # Create FastAPI app
        self.app = FastAPI(
            title=f"{name} MCP Server",
            description=description,
            version=version,
        )

        # Dictionary of registered tools
        self.tools: Dict[str, MCPTool] = {}

        # Configure routes
        self._setup_routes()

        logger.info("Initialized %s MCP Server v%s", name, version)

    def _setup_routes(self) -> None:
        """Set up the API routes."""

        @self.app.get("/")
        async def root():
            """Root endpoint returning server information."""
            return {
                "name": self.name,
                "description": self.description,
                "version": self.version,
                "tools": list(self.tools.keys()),
            }

        @self.app.get("/tools")
        async def list_tools():
            """List all available tools."""
            return {
                "tools": [
                    {"name": tool.name, "description": tool.description}
                    for tool in self.tools.values()
                ]
            }

        @self.app.get("/tools/{tool_name}")
        async def get_tool_metadata(tool_name: str):
            """Get metadata for a specific tool."""
            if tool_name not in self.tools:
                raise HTTPException(
                    status_code=404, detail=f"Tool '{tool_name}' not found"
                )

            tool = self.tools[tool_name]
            return self._get_tool_metadata(tool)

        @self.app.post("/api/v1/tools/{tool_name}/call")
        async def call_tool(tool_name: str, request: ToolCallRequest):
            """Call a specific tool."""
            if tool_name not in self.tools:
                raise HTTPException(
                    status_code=404, detail=f"Tool '{tool_name}' not found"
                )

            tool = self.tools[tool_name]

            try:
                result = await tool.execute(request.params)
                return result
            except Exception as e:
                log_exception(e)
                if isinstance(e, MCPError):
                    raise HTTPException(status_code=400, detail=str(e))
                else:
                    raise HTTPException(status_code=500, detail="Internal server error")

    def _get_tool_metadata(self, tool: MCPTool) -> ToolMetadata:
        """Get metadata for a tool.

        Args:
            tool: The tool to get metadata for

        Returns:
            Tool metadata
        """
        # Get parameter schema from tool's execute method signature
        signature = inspect.signature(tool.execute)
        params_param = signature.parameters.get("params")

        # Get return type annotation
        return_type = signature.return_annotation

        # Create parameter schema
        parameters_schema = {"type": "object", "properties": {}}

        # Create return schema
        return_schema = {"type": "object"}

        return ToolMetadata(
            name=tool.name,
            description=tool.description,
            parameters_schema=parameters_schema,
            return_schema=return_schema,
        )

    def register_tool(self, tool: MCPTool) -> None:
        """Register a tool with the MCP server.

        Args:
            tool: The tool to register
        """
        if not hasattr(tool, "name") or not hasattr(tool, "description"):
            raise ValueError("Tool must have 'name' and 'description' attributes")

        if not callable(getattr(tool, "execute", None)):
            raise ValueError("Tool must have an 'execute' method")

        self.tools[tool.name] = tool
        logger.info("Registered tool: %s", tool.name)

    def run(self) -> None:
        """Run the MCP server."""
        import uvicorn

        logger.info("Starting %s MCP Server on %s:%d", self.name, self.host, self.port)
        uvicorn.run(self.app, host=self.host, port=self.port)

    def tool(self, name: Optional[str] = None, description: Optional[str] = None):
        """Decorator to register a function as a tool.

        Args:
            name: Tool name (defaults to function name)
            description: Tool description (defaults to function docstring)

        Returns:
            Decorator function
        """

        def decorator(func):
            # Create a class that wraps the function
            class FunctionTool:
                def __init__(self):
                    self.name = name or func.__name__
                    self.description = description or func.__doc__ or ""

                async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
                    return await func(params)

            # Register the tool
            tool_instance = FunctionTool()
            self.register_tool(tool_instance)

            return func

        return decorator
