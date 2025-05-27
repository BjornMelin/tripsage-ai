"""
LangGraph-MCP Bridge Layer

This module provides integration between LangGraph and the TripSage MCP
abstraction layer, allowing LangGraph agents to use MCP tools while
maintaining compatibility with the existing MCPManager architecture.
"""

import logging
from typing import Any, Dict, List, Optional

from langchain_core.tools import Tool, tool
from pydantic import BaseModel, Field

from tripsage.mcp_abstraction.exceptions import MCPError
from tripsage.mcp_abstraction.manager import MCPManager

logger = logging.getLogger(__name__)


class MCPToolWrapper(BaseModel):
    """Wrapper for MCP tool metadata with LangGraph compatibility."""

    name: str = Field(description="Tool name")
    description: str = Field(description="Tool description")
    parameters: Dict[str, Any] = Field(description="Tool parameters schema")
    mcp_server: str = Field(description="MCP server name")
    mcp_method: str = Field(description="MCP method name")


class LangGraphMCPBridge:
    """
    Bridge between LangGraph and TripSage MCP abstraction layer.

    This class converts MCP tools to LangGraph-compatible format while preserving
    all existing error handling, caching, and monitoring capabilities from MCPManager.
    """

    def __init__(self, mcp_manager: Optional[MCPManager] = None):
        """Initialize the bridge with an MCPManager instance."""
        self.mcp_manager = mcp_manager or MCPManager()
        self._tool_cache: Dict[str, Tool] = {}
        self._tool_metadata: Dict[str, MCPToolWrapper] = {}
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the bridge and load available tools."""
        if self._initialized:
            return

        logger.info("Initializing LangGraph-MCP bridge")

        try:
            # Load tool metadata from all registered MCP servers
            await self._load_tool_metadata()
            self._initialized = True
            logger.info(f"Bridge initialized with {len(self._tool_metadata)} tools")
        except Exception as e:
            logger.error(f"Failed to initialize MCP bridge: {e}")
            raise

    async def _load_tool_metadata(self) -> None:
        """Load tool metadata from all registered MCP wrappers."""
        # Get available MCP servers from the registry
        from tripsage.mcp_abstraction.registry import registry as mcp_registry

        for server_name in mcp_registry.get_registered_mcps():
            try:
                # Get wrapper class and instantiate
                wrapper_class = mcp_registry.get_wrapper_class(server_name)
                wrapper = wrapper_class()
                methods = wrapper.get_available_methods()

                for method_name, method_info in methods.items():
                    tool_name = f"{server_name}_{method_name}"

                    # Create tool metadata
                    self._tool_metadata[tool_name] = MCPToolWrapper(
                        name=tool_name,
                        description=method_info.get(
                            "description", f"{method_name} tool"
                        ),
                        parameters=method_info.get("parameters", {}),
                        mcp_server=server_name,
                        mcp_method=method_name,
                    )

                logger.debug(f"Loaded {len(methods)} tools from {server_name}")

            except Exception as e:
                logger.warning(f"Failed to load tools from {server_name}: {e}")

    async def get_tools(self) -> List[Tool]:
        """
        Get all available MCP tools in LangGraph-compatible format.

        Returns:
            List of LangGraph Tool objects
        """
        if not self._initialized:
            await self.initialize()

        tools = []
        for tool_name, metadata in self._tool_metadata.items():
            if tool_name not in self._tool_cache:
                # Create LangGraph tool
                lang_tool = self._create_langgraph_tool(metadata)
                self._tool_cache[tool_name] = lang_tool

            tools.append(self._tool_cache[tool_name])

        return tools

    def _create_langgraph_tool(self, metadata: MCPToolWrapper) -> Tool:
        """
        Create a LangGraph Tool from MCP tool metadata.

        Args:
            metadata: MCP tool metadata

        Returns:
            LangGraph Tool instance
        """

        async def tool_function(**kwargs) -> str:
            """Execute MCP tool via MCPManager."""
            try:
                logger.debug(
                    f"Executing MCP tool: {metadata.name} with params: {kwargs}"
                )

                # Use existing MCPManager for tool execution
                result = await self.mcp_manager.invoke(
                    mcp_name=metadata.mcp_server,
                    method_name=metadata.mcp_method,
                    params=kwargs,
                )

                # Convert result to string for LangGraph compatibility
                if isinstance(result, dict):
                    return str(result)
                elif isinstance(result, list):
                    return str(result)
                else:
                    return str(result)

            except MCPError as e:
                logger.error(f"MCP tool {metadata.name} failed: {e}")
                return f"Tool execution failed: {str(e)}"
            except Exception as e:
                logger.error(f"Unexpected error in tool {metadata.name}: {e}")
                return f"Unexpected error: {str(e)}"

        # Create LangGraph tool with proper metadata
        return Tool(
            name=metadata.name,
            description=metadata.description,
            func=tool_function,
            args_schema=self._create_args_schema(metadata.parameters),
        )

    def _create_args_schema(self, parameters: Dict[str, Any]) -> Optional[type]:
        """
        Create a Pydantic schema for tool arguments.

        Args:
            parameters: Tool parameters schema

        Returns:
            Pydantic model class or None
        """
        if not parameters:
            return None

        # Create dynamic Pydantic model for parameters
        fields = {}
        for param_name, param_info in parameters.items():
            if isinstance(param_info, dict):
                param_type = param_info.get("type", "string")
                param_desc = param_info.get("description", f"{param_name} parameter")
                required = param_info.get("required", False)

                # Map JSON schema types to Python types
                if param_type == "string":
                    field_type = str
                elif param_type == "integer":
                    field_type = int
                elif param_type == "number":
                    field_type = float
                elif param_type == "boolean":
                    field_type = bool
                else:
                    field_type = str  # Default to string

                # Create field with proper type and description
                if required:
                    fields[param_name] = (field_type, Field(description=param_desc))
                else:
                    fields[param_name] = (
                        Optional[field_type],
                        Field(default=None, description=param_desc),
                    )

        if not fields:
            return None

        # Create dynamic model class
        return type("ToolArgsSchema", (BaseModel,), fields)

    async def invoke_tool_direct(self, tool_name: str, params: Dict[str, Any]) -> Any:
        """
        Directly invoke an MCP tool by name.

        Args:
            tool_name: Name of the tool to invoke
            params: Tool parameters

        Returns:
            Tool execution result
        """
        if not self._initialized:
            await self.initialize()

        metadata = self._tool_metadata.get(tool_name)
        if not metadata:
            raise ValueError(f"Tool {tool_name} not found")

        return await self.mcp_manager.invoke(
            mcp_name=metadata.mcp_server, method_name=metadata.mcp_method, params=params
        )

    def get_tool_metadata(self, tool_name: str) -> Optional[MCPToolWrapper]:
        """Get metadata for a specific tool."""
        return self._tool_metadata.get(tool_name)

    def list_available_tools(self) -> List[str]:
        """List all available tool names."""
        return list(self._tool_metadata.keys())

    async def refresh_tools(self) -> None:
        """Refresh tool metadata and clear cache."""
        logger.info("Refreshing MCP tools")
        self._tool_cache.clear()
        self._tool_metadata.clear()
        self._initialized = False
        await self.initialize()


# Global bridge instance for easy access
_global_bridge: Optional[LangGraphMCPBridge] = None


async def get_mcp_bridge() -> LangGraphMCPBridge:
    """Get the global MCP bridge instance."""
    global _global_bridge
    if _global_bridge is None:
        _global_bridge = LangGraphMCPBridge()
        await _global_bridge.initialize()
    return _global_bridge


async def get_mcp_tools() -> List[Tool]:
    """Get all available MCP tools for LangGraph."""
    bridge = await get_mcp_bridge()
    return await bridge.get_tools()


# Convenience function for creating tools with MCP integration
def create_mcp_tool(name: str, description: str, mcp_server: str, mcp_method: str):
    """
    Decorator to create MCP-backed LangGraph tools.

    Usage:
        @create_mcp_tool("search_flights", "Search for flights", "flights", "search")
        async def search_flights_tool(origin: str, destination: str, date: str) -> str:
            # Tool implementation handled automatically
            pass
    """

    def decorator(func):
        @tool(name=name, description=description)
        async def wrapper(**kwargs) -> str:
            bridge = await get_mcp_bridge()
            return await bridge.invoke_tool_direct(f"{mcp_server}_{mcp_method}", kwargs)

        return wrapper

    return decorator
