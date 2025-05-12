"""
FastMCP 2.0 implementation for TripSage.

This module provides enhanced MCP server and client implementations using the
FastMCP 2.0 framework for consistency across all TripSage's MCP implementations.
"""

import asyncio
import json
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Union,
)

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel

from ..utils.error_handling import MCPError, log_exception
from ..utils.logging import get_module_logger
from .base_mcp_client import BaseMCPClient
from .base_mcp_server import BaseMCPServer

logger = get_module_logger(__name__)


class ToolSchema(BaseModel):
    """Schema definition for a FastMCP 2.0 tool."""

    name: str
    description: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    examples: Optional[List[Dict[str, Any]]] = None
    version: str = "1.0.0"


class FastMCPTool:
    """Base class for FastMCP 2.0 tools."""

    def __init__(
        self,
        name: str,
        description: str,
        input_schema: Dict[str, Any],
        output_schema: Optional[Dict[str, Any]] = None,
        examples: Optional[List[Dict[str, Any]]] = None,
        version: str = "1.0.0",
    ):
        """Initialize a FastMCP tool.

        Args:
            name: Tool name
            description: Tool description
            input_schema: JSON schema for input parameters
            output_schema: JSON schema for output (defaults to any object)
            examples: List of example inputs and outputs
            version: Tool version
        """
        self.name = name
        self.description = description
        self.input_schema = input_schema
        self.output_schema = output_schema or {"type": "object"}
        self.examples = examples or []
        self.version = version

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the tool with the given parameters.

        Args:
            params: Tool parameters

        Returns:
            Tool execution result

        Raises:
            NotImplementedError: This method must be implemented by subclasses
        """
        raise NotImplementedError(
            "Tool execute method must be implemented by subclasses"
        )

    def get_schema(self) -> ToolSchema:
        """Get the tool schema.

        Returns:
            Tool schema
        """
        return ToolSchema(
            name=self.name,
            description=self.description,
            input_schema=self.input_schema,
            output_schema=self.output_schema,
            examples=self.examples,
            version=self.version,
        )

    @classmethod
    def create(
        cls,
        name: str,
        description: str,
        input_schema: Dict[str, Any],
        handler: Callable[[Dict[str, Any]], Any],
        output_schema: Optional[Dict[str, Any]] = None,
        examples: Optional[List[Dict[str, Any]]] = None,
        version: str = "1.0.0",
    ) -> "FastMCPTool":
        """Create a FastMCP tool from a handler function.

        Args:
            name: Tool name
            description: Tool description
            input_schema: JSON schema for input parameters
            handler: Function that implements tool logic
            output_schema: JSON schema for output (defaults to any object)
            examples: List of example inputs and outputs
            version: Tool version

        Returns:
            A FastMCP tool instance
        """
        # Create a tool class dynamically
        tool_cls = type(
            f"{name.title().replace('_', '')}Tool",
            (FastMCPTool,),
            {
                "async_handler": (
                    staticmethod(handler)
                    if asyncio.iscoroutinefunction(handler)
                    else None
                ),
                "sync_handler": (
                    staticmethod(handler)
                    if not asyncio.iscoroutinefunction(handler)
                    else None
                ),
                "execute": lambda self, params: (
                    self.async_handler(params)
                    if self.async_handler
                    else asyncio.create_task(self.sync_handler(params))
                ),
            },
        )

        # Create instance
        return tool_cls(
            name=name,
            description=description,
            input_schema=input_schema,
            output_schema=output_schema,
            examples=examples,
            version=version,
        )


def create_tool(
    name: str,
    description: str,
    input_schema: Dict[str, Any],
    handler: Callable[[Dict[str, Any]], Any],
    output_schema: Optional[Dict[str, Any]] = None,
    examples: Optional[List[Dict[str, Any]]] = None,
    version: str = "1.0.0",
) -> FastMCPTool:
    """Create a FastMCP tool from a handler function.

    Args:
        name: Tool name
        description: Tool description
        input_schema: JSON schema for input parameters
        handler: Function that implements tool logic
        output_schema: JSON schema for output (defaults to any object)
        examples: List of example inputs and outputs
        version: Tool version

    Returns:
        A FastMCP tool instance
    """
    return FastMCPTool.create(
        name=name,
        description=description,
        input_schema=input_schema,
        handler=handler,
        output_schema=output_schema,
        examples=examples,
        version=version,
    )


class FastMCPServer(BaseMCPServer):
    """Enhanced MCP server implementation using FastMCP 2.0 framework."""

    def __init__(
        self,
        name: str,
        description: str = "",
        version: str = "1.0.0",
        host: str = "0.0.0.0",
        port: int = 3000,
        openapi_url: str = "/openapi.json",
        docs_url: str = "/docs",
    ):
        """Initialize the FastMCP server.

        Args:
            name: Server name
            description: Server description
            version: Server version
            host: Host to bind to
            port: Port to listen on
            openapi_url: URL for OpenAPI schema
            docs_url: URL for API documentation
        """
        super().__init__(
            name=name,
            description=description,
            version=version,
            host=host,
            port=port,
        )

        # Update FastAPI app configuration
        self.app = FastAPI(
            title=f"{name} MCP Server",
            description=description,
            version=version,
            openapi_url=openapi_url,
            docs_url=docs_url,
        )

        # Configure routes
        self._setup_routes()

        # Add OpenAI compatibility routes
        self._setup_openai_routes()

        # Add Claude compatibility routes
        self._setup_claude_routes()

        logger.info("Initialized FastMCP 2.0 Server: %s v%s", name, version)

    def _setup_openai_routes(self) -> None:
        """Set up routes for OpenAI compatibility."""

        class OpenAICompatRequest(BaseModel):
            model: Optional[str] = None
            messages: Optional[List[Dict[str, Any]]] = None
            tools: Optional[List[Dict[str, Any]]] = None
            tool_choice: Optional[Union[str, Dict[str, Any]]] = None

        class OpenAIToolCallResult(BaseModel):
            id: str
            type: str = "function"
            function: Dict[str, Any]

        class OpenAICompatResponse(BaseModel):
            id: str
            object: str = "chat.completion"
            created: int
            model: str
            choices: List[Dict[str, Any]]
            usage: Dict[str, int]

        @self.app.post("/v1/chat/completions")
        async def openai_compat(request: OpenAICompatRequest):
            """OpenAI compatibility endpoint for tools."""
            # This is just a stub implementation for now
            # In a real implementation, this would process the request and
            # call the appropriate tools

            available_tools = [
                {
                    "id": f"ft_{tool.name}",
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": self._get_tool_metadata(tool).parameters_schema,
                    },
                }
                for tool in self.tools.values()
            ]

            return {
                "id": "fastmcp_response_id",
                "object": "chat.completion",
                "created": int(asyncio.get_event_loop().time()),
                "model": request.model or f"{self.name}-model",
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": available_tools,
                        },
                        "finish_reason": "tool_calls",
                    }
                ],
                "usage": {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                },
            }

    def _setup_claude_routes(self) -> None:
        """Set up routes for Claude compatibility."""

        class ClaudeCompatRequest(BaseModel):
            model: Optional[str] = None
            messages: Optional[List[Dict[str, Any]]] = None
            tools: Optional[List[Dict[str, Any]]] = None
            tool_choice: Optional[Union[str, Dict[str, Any]]] = None

        class ClaudeToolResponse(BaseModel):
            type: str = "tool_use"
            id: str
            name: str
            input: Dict[str, Any]

        @self.app.post("/v1/messages")
        async def claude_compat(request: ClaudeCompatRequest):
            """Claude compatibility endpoint for tools."""
            # This is just a stub implementation for now
            # In a real implementation, this would process the request and
            # call the appropriate tools

            available_tools = [
                {
                    "type": "tool_use",
                    "id": f"tool_{tool.name}",
                    "name": tool.name,
                    "input": {},
                }
                for tool in self.tools.values()
            ]

            return {
                "id": "fastmcp_claude_response_id",
                "type": "message",
                "role": "assistant",
                "model": request.model or f"{self.name}-model",
                "content": [],
                "stop_reason": "tool_use",
                "stop_sequence": None,
                "usage": {"input_tokens": 0, "output_tokens": 0},
                "tool_use": available_tools[0] if available_tools else None,
            }

    def register_fast_tool(self, tool: FastMCPTool) -> None:
        """Register a FastMCP tool with the server.

        Args:
            tool: The FastMCP tool to register
        """
        if not isinstance(tool, FastMCPTool):
            raise TypeError("Tool must be an instance of FastMCPTool")

        # Register with base implementation
        self.register_tool(tool)

        # Add a specific route for this tool
        @self.app.post(f"/tools/{tool.name}/call", response_model=None)
        async def tool_endpoint(request: Request):
            try:
                # Parse request body
                data = await request.json()

                # Execute tool
                result = await tool.execute(data)

                # Return result
                return result
            except Exception as e:
                log_exception(e)
                if isinstance(e, MCPError):
                    raise HTTPException(status_code=400, detail=str(e)) from e
                else:
                    raise HTTPException(
                        status_code=500, detail="Internal server error"
                    ) from e


class FastMCPClient(BaseMCPClient):
    """Enhanced MCP client implementation using FastMCP 2.0 framework."""

    def __init__(
        self,
        server_name: str,
        endpoint: str,
        api_key: Optional[str] = None,
        timeout: float = 60.0,
        use_cache: bool = True,
        cache_ttl: Optional[int] = None,
    ):
        """Initialize the FastMCP client.

        Args:
            server_name: Server name (for logging and caching)
            endpoint: MCP server endpoint URL
            api_key: API key for authentication (if required)
            timeout: Request timeout in seconds
            use_cache: Whether to use caching
            cache_ttl: Cache TTL in seconds (None means default TTL)
        """
        super().__init__(
            endpoint=endpoint,
            api_key=api_key,
            timeout=timeout,
            use_cache=use_cache,
            cache_ttl=cache_ttl,
        )
        self.server_name = server_name

        logger.debug("Initialized FastMCP 2.0 Client for %s: %s", server_name, endpoint)

    async def list_tools_with_schema(self) -> List[ToolSchema]:
        """List all available tools with their full schema.

        Returns:
            List of tool schemas
        """
        tool_list = await self.list_tools()
        schemas = []

        for tool_info in tool_list:
            name = tool_info.get("name")
            if name:
                try:
                    tool_metadata = await self.get_tool_metadata(name)
                    schemas.append(
                        ToolSchema(
                            name=name,
                            description=tool_info.get("description", ""),
                            input_schema=tool_metadata.get("parameters_schema", {}),
                            output_schema=tool_metadata.get("return_schema", {}),
                            examples=tool_metadata.get("examples", []),
                            version=tool_metadata.get("version", "1.0.0"),
                        )
                    )
                except Exception as e:
                    logger.warning("Error getting schema for tool %s: %s", name, str(e))

        return schemas

    async def call_tool_with_json(
        self, tool_name: str, json_input: str
    ) -> Dict[str, Any]:
        """Call a tool with JSON input.

        Args:
            tool_name: Tool name
            json_input: Tool parameters as JSON string

        Returns:
            Tool execution result
        """
        try:
            params = json.loads(json_input)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON input: {str(e)}") from e

        return await self.call_tool(tool_name, params)

    @staticmethod
    def tool_for_openai(tool: ToolSchema) -> Dict[str, Any]:
        """Convert a tool schema to OpenAI tool format.

        Args:
            tool: Tool schema

        Returns:
            OpenAI-compatible tool definition
        """
        return {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.input_schema,
            },
        }

    @staticmethod
    def tool_for_claude(tool: ToolSchema) -> Dict[str, Any]:
        """Convert a tool schema to Claude tool format.

        Args:
            tool: Tool schema

        Returns:
            Claude-compatible tool definition
        """
        return {
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.input_schema,
        }

    async def get_openai_tools(self) -> List[Dict[str, Any]]:
        """Get all tools in OpenAI format.

        Returns:
            List of tools in OpenAI format
        """
        schemas = await self.list_tools_with_schema()
        return [self.tool_for_openai(schema) for schema in schemas]

    async def get_claude_tools(self) -> List[Dict[str, Any]]:
        """Get all tools in Claude format.

        Returns:
            List of tools in Claude format
        """
        schemas = await self.list_tools_with_schema()
        return [self.tool_for_claude(schema) for schema in schemas]

    def list_tools_sync(self) -> List[Dict[str, str]]:
        """Synchronous version of list_tools.

        This method provides a simple way to get available tools during
        initialization without making async HTTP requests.

        Returns:
            List of tool names and descriptions
        """
        # For now, return a small set of common tool names for this MCP type
        # This will be replaced by actual tool discovery in a production implementation
        tool_names = [
            {
                "name": f"{self.server_name.lower()}_status",
                "description": f"Get {self.server_name} MCP status",
            },
            {
                "name": f"{self.server_name.lower()}_version",
                "description": f"Get {self.server_name} MCP version",
            },
        ]

        logger.debug(
            "Using simplified list_tools_sync implementation for %s MCP",
            self.server_name,
        )
        return tool_names

    def get_tool_metadata_sync(self, tool_name: str) -> Dict[str, Any]:
        """Synchronous version of get_tool_metadata.

        This method provides basic metadata for a tool during initialization
        without making async HTTP requests.

        Args:
            tool_name: Tool name

        Returns:
            Tool metadata
        """
        # For now, return generic metadata
        # This will be replaced by actual metadata in a production implementation
        return {
            "name": tool_name,
            "description": f"Call the {tool_name} tool from {self.server_name} MCP.",
            "parameters_schema": {"type": "object", "properties": {}, "required": []},
            "return_schema": {"type": "object", "properties": {}},
        }
