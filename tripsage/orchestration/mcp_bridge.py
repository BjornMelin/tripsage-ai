"""LangGraph-MCP bridge layer for Airbnb integration."""

# pylint: disable=import-error

import logging
from typing import Any

from langchain_core.tools import Tool
from pydantic import BaseModel, Field

from tripsage_core.services.airbnb_mcp import AirbnbMCP, default_airbnb_mcp


logger = logging.getLogger(__name__)


class AirbnbToolWrapper(BaseModel):
    """Wrapper for Airbnb tool metadata with LangGraph compatibility."""

    name: str = Field(description="Tool name")
    description: str = Field(description="Tool description")
    parameters: dict[str, Any] = Field(description="Tool parameters schema")
    mcp_method: str = Field(description="Airbnb MCP method name")


class AirbnbMCPBridge:
    """Bridge between LangGraph and Airbnb MCP.

    This class converts Airbnb MCP tools to LangGraph-compatible format while preserving
    error handling, caching, and monitoring capabilities from the prior MCP abstraction.
    """

    def __init__(self, mcp_service: AirbnbMCP | None = None):
        """Initialize the bridge with an MCP service instance."""
        self.mcp_service = mcp_service or default_airbnb_mcp
        self._tool_cache: dict[str, Tool] = {}
        self._tool_metadata: dict[str, AirbnbToolWrapper] = {}
        self._initialized = False

    @property
    def is_initialized(self) -> bool:
        """Return whether the bridge has completed initialization."""
        return self._initialized

    async def initialize(self) -> None:
        """Initialize the bridge and load available Airbnb tools."""
        if self._initialized:
            return

        logger.info("Initializing LangGraph-Airbnb MCP bridge")

        try:
            # Initialize the Airbnb MCP wrapper
            await self.mcp_service.initialize()

            # Load Airbnb tool metadata
            await self._load_airbnb_tools()
            self._initialized = True
            logger.info(
                "Bridge initialized with %s Airbnb tools", len(self._tool_metadata)
            )
        except Exception:
            logger.exception("Failed to initialize Airbnb MCP bridge")
            raise

    async def _load_airbnb_tools(self) -> None:
        """Load tool metadata from Airbnb MCP wrapper."""
        # Get available methods from the manager
        methods = self.mcp_service.get_available_methods()

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
            if method == "search_listings":
                primary_method = "search_listings"
            elif method == "get_listing_details":
                primary_method = "get_listing_details"
            else:
                continue

            if primary_method in tool_metadata:
                tool_name = f"airbnb_{method}"
                self._tool_metadata[tool_name] = AirbnbToolWrapper(
                    name=tool_name,
                    description=tool_metadata[primary_method]["description"],
                    parameters=tool_metadata[primary_method]["parameters"],
                    mcp_method=method,
                )

    async def get_tools(self) -> list[Tool]:
        """Get all available Airbnb tools in LangGraph-compatible format.

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
        """Create a LangGraph Tool from Airbnb tool metadata.

        Args:
            metadata: Airbnb tool metadata

        Returns:
            LangGraph Tool instance
        """

        async def tool_function(**kwargs) -> str:
            """Execute Airbnb tool via MCPBridge."""
            try:
                logger.debug(
                    "Executing Airbnb tool: %s with params: %s", metadata.name, kwargs
                )

                # Use existing MCPBridge for tool execution
                result = await self.mcp_service.invoke(
                    method_name=metadata.mcp_method,
                    params=kwargs,
                )

                # Convert result to string for LangGraph compatibility
                return str(result)

            except Exception as e:
                logger.exception("Airbnb tool %s failed", metadata.name)
                return f"Tool execution failed: {e!s}"

        # Create LangGraph tool with proper metadata
        return Tool(
            name=metadata.name,
            description=metadata.description,
            func=tool_function,
            args_schema=self._create_args_schema(metadata.parameters),
        )

    def _create_args_schema(self, parameters: dict[str, Any]) -> type | None:
        """Create a Pydantic schema for tool arguments.

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
                    annotations[param_name] = field_type | None
                    field_defaults[param_name] = Field(
                        default=None, description=param_desc
                    )

        if not annotations:
            return None

        # Create dynamic model class with proper annotations
        namespace = {"__annotations__": annotations, **field_defaults}
        return type("AirbnbToolArgsSchema", (BaseModel,), namespace)

    async def invoke_tool_direct(self, tool_name: str, params: dict[str, Any]) -> Any:
        """Directly invoke an Airbnb tool by name.

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

        return await self.mcp_service.invoke(
            method_name=metadata.mcp_method, params=params
        )

    def get_tool_metadata(self, tool_name: str) -> AirbnbToolWrapper | None:
        """Get metadata for a specific tool."""
        return self._tool_metadata.get(tool_name)

    def list_available_tools(self) -> list[str]:
        """List all available tool names."""
        return list(self._tool_metadata.keys())

    async def refresh_tools(self) -> None:
        """Refresh tool metadata and clear cache."""
        logger.info("Refreshing Airbnb tools")
        self._tool_cache.clear()
        self._tool_metadata.clear()
        self._initialized = False
        await self.initialize()
