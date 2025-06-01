"""
LangGraph-MCP Bridge Layer for Airbnb Integration

This module provides integration between LangGraph and the Airbnb MCP,
allowing LangGraph agents to use Airbnb accommodation tools while
maintaining compatibility with the simplified MCPManager architecture.
"""

import logging
from typing import Any, Dict, List, Optional

from langchain_core.tools import Tool, tool
from pydantic import BaseModel, Field

from tripsage.mcp_abstraction.exceptions import TripSageMCPError
from tripsage.mcp_abstraction.manager import (
    MCPManager,
)
from tripsage.mcp_abstraction.manager import (
    mcp_manager as global_mcp_manager,
)

logger = logging.getLogger(__name__)


class AirbnbToolWrapper(BaseModel):
    """Wrapper for Airbnb tool metadata with LangGraph compatibility."""

    name: str = Field(description="Tool name")
    description: str = Field(description="Tool description")
    parameters: Dict[str, Any] = Field(description="Tool parameters schema")
    mcp_method: str = Field(description="Airbnb MCP method name")


class LangGraphMCPBridge:
    """
    Bridge between LangGraph and Airbnb MCP.

    This class converts Airbnb MCP tools to LangGraph-compatible format while preserving
    all existing error handling, caching, and monitoring capabilities from MCPManager.
    """

    def __init__(self, mcp_manager: Optional[MCPManager] = None):
        """Initialize the bridge with an MCPManager instance."""
        self.mcp_manager = mcp_manager or global_mcp_manager
        self._tool_cache: Dict[str, Tool] = {}
        self._tool_metadata: Dict[str, AirbnbToolWrapper] = {}
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the bridge and load available Airbnb tools."""
        if self._initialized:
            return

        logger.info("Initializing LangGraph-Airbnb MCP bridge")

        try:
            # Initialize the Airbnb MCP wrapper
            await self.mcp_manager.initialize()

            # Load Airbnb tool metadata
            await self._load_airbnb_tools()
            self._initialized = True
            logger.info(
                f"Bridge initialized with {len(self._tool_metadata)} Airbnb tools"
            )
        except Exception as e:
            logger.error(f"Failed to initialize Airbnb MCP bridge: {e}")
            raise

    async def _load_airbnb_tools(self) -> None:
        """Load tool metadata from Airbnb MCP wrapper."""
        # Get available methods from the manager
        methods = self.mcp_manager.get_available_methods()

        # Define metadata for each Airbnb method
        tool_metadata = {
            "search_listings": {
                "description": (
                    "Search for Airbnb accommodations in a specific location"
                ),
                "parameters": {
                    "location": {
                        "type": "string",
                        "description": "Location to search (e.g., 'Paris, France')",
                        "required": True,
                    },
                    "check_in": {
                        "type": "string",
                        "description": "Check-in date (YYYY-MM-DD)",
                        "required": False,
                    },
                    "check_out": {
                        "type": "string",
                        "description": "Check-out date (YYYY-MM-DD)",
                        "required": False,
                    },
                    "adults": {
                        "type": "integer",
                        "description": "Number of adult guests",
                        "required": False,
                    },
                    "children": {
                        "type": "integer",
                        "description": "Number of child guests",
                        "required": False,
                    },
                    "price_min": {
                        "type": "number",
                        "description": "Minimum price per night",
                        "required": False,
                    },
                    "price_max": {
                        "type": "number",
                        "description": "Maximum price per night",
                        "required": False,
                    },
                },
            },
            "get_listing_details": {
                "description": (
                    "Get detailed information about a specific Airbnb listing"
                ),
                "parameters": {
                    "listing_id": {
                        "type": "string",
                        "description": "The Airbnb listing ID",
                        "required": True,
                    },
                    "check_in": {
                        "type": "string",
                        "description": "Check-in date for availability check",
                        "required": False,
                    },
                    "check_out": {
                        "type": "string",
                        "description": "Check-out date for availability check",
                        "required": False,
                    },
                },
            },
        }

        # Create tool wrappers for available methods
        for method in methods:
            # Map method aliases to primary methods
            if method in ["search_listings", "search_accommodations", "search"]:
                primary_method = "search_listings"
            elif method in [
                "get_listing_details",
                "get_listing",
                "get_details",
                "get_accommodation_details",
                "check_availability",
                "check_listing_availability",
            ]:
                primary_method = "get_listing_details"
            else:
                continue  # Skip unknown methods

            if primary_method in tool_metadata:
                tool_name = f"airbnb_{method}"
                self._tool_metadata[tool_name] = AirbnbToolWrapper(
                    name=tool_name,
                    description=tool_metadata[primary_method]["description"],
                    parameters=tool_metadata[primary_method]["parameters"],
                    mcp_method=method,
                )

    async def get_tools(self) -> List[Tool]:
        """
        Get all available Airbnb tools in LangGraph-compatible format.

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

    def _create_langgraph_tool(self, metadata: AirbnbToolWrapper) -> Tool:
        """
        Create a LangGraph Tool from Airbnb tool metadata.

        Args:
            metadata: Airbnb tool metadata

        Returns:
            LangGraph Tool instance
        """

        async def tool_function(**kwargs) -> str:
            """Execute Airbnb tool via MCPManager."""
            try:
                logger.debug(
                    f"Executing Airbnb tool: {metadata.name} with params: {kwargs}"
                )

                # Use existing MCPManager for tool execution
                result = await self.mcp_manager.invoke(
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

            except TripSageMCPError as e:
                logger.error(f"Airbnb tool {metadata.name} failed: {e}")
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

        # Create annotations and fields for dynamic Pydantic model
        annotations = {}
        field_defaults = {}

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

                # Set up type annotations and field defaults
                if required:
                    annotations[param_name] = field_type
                    field_defaults[param_name] = Field(description=param_desc)
                else:
                    annotations[param_name] = Optional[field_type]
                    field_defaults[param_name] = Field(
                        default=None, description=param_desc
                    )

        if not annotations:
            return None

        # Create dynamic model class with proper annotations
        namespace = {"__annotations__": annotations, **field_defaults}
        return type("AirbnbToolArgsSchema", (BaseModel,), namespace)

    async def invoke_tool_direct(self, tool_name: str, params: Dict[str, Any]) -> Any:
        """
        Directly invoke an Airbnb tool by name.

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
            method_name=metadata.mcp_method, params=params
        )

    def get_tool_metadata(self, tool_name: str) -> Optional[AirbnbToolWrapper]:
        """Get metadata for a specific tool."""
        return self._tool_metadata.get(tool_name)

    def list_available_tools(self) -> List[str]:
        """List all available tool names."""
        return list(self._tool_metadata.keys())

    async def refresh_tools(self) -> None:
        """Refresh tool metadata and clear cache."""
        logger.info("Refreshing Airbnb tools")
        self._tool_cache.clear()
        self._tool_metadata.clear()
        self._initialized = False
        await self.initialize()


# Global bridge instance for easy access
_global_bridge: Optional[LangGraphMCPBridge] = None


async def get_mcp_bridge() -> LangGraphMCPBridge:
    """Get the global Airbnb MCP bridge instance."""
    global _global_bridge
    if _global_bridge is None:
        _global_bridge = LangGraphMCPBridge()
        await _global_bridge.initialize()
    return _global_bridge


async def get_airbnb_tools() -> List[Tool]:
    """Get all available Airbnb tools for LangGraph."""
    bridge = await get_mcp_bridge()
    return await bridge.get_tools()


# Convenience function for creating Airbnb tools
def create_airbnb_tool(name: str, description: str, mcp_method: str):
    """
    Decorator to create Airbnb-backed LangGraph tools.

    Usage:
        @create_airbnb_tool(
            "search_airbnb",
            "Search Airbnb accommodations",
            "search_listings"
        )
        async def search_airbnb_tool(
            location: str,
            check_in: str = None,
            check_out: str = None
        ) -> str:
            # Tool implementation handled automatically
            pass
    """

    def decorator(func):
        @tool(description=description)
        async def wrapper(**kwargs) -> str:
            bridge = await get_mcp_bridge()
            return await bridge.invoke_tool_direct(f"airbnb_{mcp_method}", kwargs)

        # Set the name manually after creation
        wrapper.name = name
        return wrapper

    return decorator
