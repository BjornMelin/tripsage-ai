"""
MCP Integration for LangGraph orchestration.

This module provides MCP tool registry and wrapper classes for LangGraph-based agents.
"""

import asyncio
import json
from typing import Any, Dict, List, Optional

from langchain_core.tools import Tool
from langchain_core.tools.base import ToolException

from tripsage_core.mcp_abstraction.manager import mcp_manager
from tripsage_core.utils.logging_utils import get_logger

logger = get_logger(__name__)


class MCPToolWrapper:
    """
    Wrapper for MCP tools to make them compatible with LangGraph.

    This class wraps MCP service methods as LangGraph tools with proper
    async/await support and error handling.
    """

    def __init__(
        self,
        service_name: str,
        method_name: str,
        description: str,
        parameters: Optional[Dict[str, Any]] = None,
        **kwargs,
    ):
        """
        Initialize MCP tool wrapper.

        Args:
            service_name: Name of the MCP service
            method_name: Name of the method to call
            description: Tool description
            parameters: Parameter schema for the tool
            **kwargs: Additional Tool arguments
        """
        self.name = f"{service_name}_{method_name}"
        self.description = description
        self.service_name = service_name
        self.method_name = method_name
        self.parameters = parameters or {}
        self.mcp_manager = mcp_manager

        # Create the actual Tool instance
        self._tool = Tool(
            name=self.name,
            description=self.description,
            func=self._run,
            coroutine=self._arun,
            **kwargs,
        )

    @property
    def func(self):
        """Get the function property for compatibility."""
        return self._tool.func

    @property
    def coroutine(self):
        """Get the coroutine property for compatibility."""
        return self._tool.coroutine

    def run(self, *args, **kwargs):
        """Run the tool synchronously."""
        return self._tool.run(*args, **kwargs)

    async def arun(self, *args, **kwargs):
        """Run the tool asynchronously."""
        return await self._tool.arun(*args, **kwargs)

    def __call__(self, *args, **kwargs):
        """Make the wrapper callable."""
        return self._tool(*args, **kwargs)

    def _run(self, **kwargs) -> str:
        """
        Synchronous execution wrapper for async MCP calls.

        Args:
            **kwargs: Tool parameters

        Returns:
            JSON string result
        """
        try:
            # Run async method in sync context
            return asyncio.run(self._arun(**kwargs))
        except Exception as e:
            logger.error(f"Error in sync execution of {self.name}: {e}")
            raise ToolException(f"Error executing {self.name}: {str(e)}") from e

    async def _arun(self, **kwargs) -> str:
        """
        Asynchronous execution of MCP tool.

        Args:
            **kwargs: Tool parameters

        Returns:
            JSON string result

        Raises:
            ToolException: If tool execution fails
        """
        try:
            logger.debug(f"Executing MCP tool {self.name} with params: {kwargs}")

            # Call MCP manager with service method
            result = await self.mcp_manager.invoke(
                method_name=self.method_name, params=kwargs
            )

            # Convert result to JSON string for LangGraph compatibility
            return json.dumps(result, ensure_ascii=False)

        except Exception as e:
            logger.error(f"Error executing {self.name}: {e}")
            raise ToolException(f"Error executing {self.name}: {str(e)}") from e


class MCPToolRegistry:
    """
    Registry for MCP tools used by LangGraph agents.

    This class manages the available MCP tools and provides them to different
    agent types based on their capabilities and requirements.
    """

    def __init__(self):
        """Initialize the tool registry with available MCP tools."""
        self.tools: Dict[str, MCPToolWrapper] = {}
        self._agent_tool_mappings: Dict[str, List[str]] = {}
        self._initialize_tools()
        self._setup_agent_mappings()

    def _initialize_tools(self) -> None:
        """Initialize all available MCP tools."""
        # Flight tools
        self.tools["search_flights"] = MCPToolWrapper(
            service_name="flights",
            method_name="search_flights",
            description=(
                "Search for flights between two locations with optional filters "
                "for dates, passengers, and preferences"
            ),
            parameters={
                "origin": {
                    "type": "string",
                    "description": "Origin airport code or city",
                },
                "destination": {
                    "type": "string",
                    "description": "Destination airport code or city",
                },
                "departure_date": {
                    "type": "string",
                    "description": "Departure date (YYYY-MM-DD)",
                },
                "return_date": {
                    "type": "string",
                    "description": "Return date (YYYY-MM-DD)",
                    "required": False,
                },
                "passengers": {
                    "type": "integer",
                    "description": "Number of passengers",
                    "required": False,
                },
                "class": {
                    "type": "string",
                    "description": "Flight class (economy, business, first)",
                    "required": False,
                },
            },
        )

        # Accommodation tools
        self.tools["search_accommodations"] = MCPToolWrapper(
            service_name="accommodations",
            method_name="search_listings",
            description=(
                "Search for accommodations in a specific location with "
                "check-in/out dates and guest requirements"
            ),
            parameters={
                "location": {
                    "type": "string",
                    "description": "Location to search for accommodations",
                },
                "check_in": {
                    "type": "string",
                    "description": "Check-in date (YYYY-MM-DD)",
                },
                "check_out": {
                    "type": "string",
                    "description": "Check-out date (YYYY-MM-DD)",
                },
                "guests": {
                    "type": "integer",
                    "description": "Number of guests",
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
        )

        # Location and weather tools
        self.tools["geocode_location"] = MCPToolWrapper(
            service_name="maps",
            method_name="geocode",
            description="Get geographic coordinates and details for a location",
            parameters={
                "location": {"type": "string", "description": "Location to geocode"}
            },
        )

        self.tools["get_weather"] = MCPToolWrapper(
            service_name="weather",
            method_name="get_current_weather",
            description="Get current weather information for a location",
            parameters={
                "location": {
                    "type": "string",
                    "description": "Location for weather information",
                }
            },
        )

        # Web search and research tools
        self.tools["web_search"] = MCPToolWrapper(
            service_name="web",
            method_name="search",
            description="Search the web for travel-related information",
            parameters={
                "query": {"type": "string", "description": "Search query"},
                "location": {
                    "type": "string",
                    "description": "Location context for search",
                    "required": False,
                },
            },
        )

        # Memory and planning tools
        self.tools["save_memory"] = MCPToolWrapper(
            service_name="memory",
            method_name="add_memory",
            description=(
                "Save important information to user memory for future reference"
            ),
            parameters={
                "content": {"type": "string", "description": "Information to save"},
                "category": {
                    "type": "string",
                    "description": "Memory category",
                    "required": False,
                },
            },
        )

        self.tools["search_memory"] = MCPToolWrapper(
            service_name="memory",
            method_name="search_memories",
            description="Search user memories for relevant information",
            parameters={
                "query": {"type": "string", "description": "Search query for memories"}
            },
        )

    def _setup_agent_mappings(self) -> None:
        """Setup tool mappings for different agent types."""
        self._agent_tool_mappings = {
            "flight_agent": [
                "search_flights",
                "geocode_location",
                "get_weather",
                "web_search",
                "save_memory",
                "search_memory",
            ],
            "accommodation_agent": [
                "search_accommodations",
                "geocode_location",
                "get_weather",
                "web_search",
                "save_memory",
                "search_memory",
            ],
            "destination_research_agent": [
                "geocode_location",
                "get_weather",
                "web_search",
                "save_memory",
                "search_memory",
            ],
            "budget_agent": [
                "search_flights",
                "search_accommodations",
                "web_search",
                "save_memory",
                "search_memory",
            ],
            "itinerary_agent": [
                "search_flights",
                "search_accommodations",
                "geocode_location",
                "get_weather",
                "web_search",
                "save_memory",
                "search_memory",
            ],
            "memory_update": ["save_memory", "search_memory"],
        }

    def get_tool(self, tool_name: str) -> Optional[MCPToolWrapper]:
        """
        Get a specific tool by name.

        Args:
            tool_name: Name of the tool to retrieve

        Returns:
            Tool instance or None if not found
        """
        return self.tools.get(tool_name)

    def get_tools_for_agent(self, agent_type: str) -> List[MCPToolWrapper]:
        """
        Get tools available for a specific agent type.

        Args:
            agent_type: Type of agent (e.g., 'flight_agent', 'accommodation_agent')

        Returns:
            List of tools available for the agent
        """
        tool_names = self._agent_tool_mappings.get(agent_type, [])
        return [self.tools[name] for name in tool_names if name in self.tools]

    def register_custom_tool(self, tool: MCPToolWrapper) -> None:
        """
        Register a custom MCP tool.

        Args:
            tool: Custom tool to register
        """
        self.tools[tool.name] = tool
        logger.info(f"Registered custom tool: {tool.name}")

    def list_available_tools(self) -> Dict[str, str]:
        """
        List all available tools with their descriptions.

        Returns:
            Dictionary mapping tool names to descriptions
        """
        return {name: tool.description for name, tool in self.tools.items()}

    def get_all_tools(self) -> List[MCPToolWrapper]:
        """
        Get all available tools.

        Returns:
            List of all tools in the registry
        """
        return list(self.tools.values())
