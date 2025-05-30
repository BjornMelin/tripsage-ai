"""
MCP tool integration for LangGraph orchestration.

This module provides wrappers to integrate existing MCP tools with LangGraph's
tool calling system, enabling seamless use of the existing tool ecosystem.
"""

import json
from typing import Any, Dict, List, Optional, Union

from langchain_core.tools import BaseTool
from langchain_core.tools.base import ToolException
from pydantic import Field

from tripsage.mcp_abstraction.manager import MCPManager
from tripsage_core.utils.logging_utils import get_logger

logger = get_logger(__name__)


class MCPToolWrapper(BaseTool):
    """
    Wrapper to integrate MCP tools with LangGraph.

    This class adapts MCP tools to work with LangGraph's tool calling system,
    providing a bridge between the existing MCP ecosystem and the new LangGraph agents.
    """

    # Declare fields for Pydantic model
    service_name: str = Field(description="Name of the MCP service")
    method_name: str = Field(description="Name of the method to call")
    parameters: Dict = Field(default_factory=dict, description="Parameter schema")
    mcp_manager: Any = Field(
        default_factory=MCPManager, description="MCP manager instance"
    )

    def __init__(
        self,
        service_name: str,
        method_name: str,
        description: str,
        parameters: Optional[Dict] = None,
        **kwargs,
    ):
        """
        Initialize the MCP tool wrapper.

        Args:
            service_name: Name of the MCP service (e.g., 'flights', 'accommodations')
            method_name: Name of the method to call on the service
            description: Human-readable description of what this tool does
            parameters: Optional parameter schema for the tool
        """
        # Initialize parent with all required fields
        super().__init__(
            name=f"{service_name}_{method_name}",
            description=description,
            service_name=service_name,
            method_name=method_name,
            parameters=parameters or {},
            mcp_manager=MCPManager(),
            **kwargs,
        )

    def _run(self, **kwargs) -> str:
        """
        Execute MCP tool call synchronously.

        Args:
            **kwargs: Parameters to pass to the MCP tool

        Returns:
            JSON string containing the tool result

        Raises:
            ToolException: If the MCP call fails
        """
        try:
            logger.info(f"Executing MCP tool: {self.service_name}.{self.method_name}")

            result = self.mcp_manager.invoke(
                self.service_name, self.method_name, kwargs
            )

            logger.info(f"MCP tool {self.name} executed successfully")
            return json.dumps(result, ensure_ascii=False)

        except Exception as e:
            logger.error(f"MCP tool {self.name} failed: {str(e)}")
            raise ToolException(f"Error executing {self.name}: {str(e)}") from e

    async def _arun(self, **kwargs) -> str:
        """
        Execute MCP tool call asynchronously.

        Args:
            **kwargs: Parameters to pass to the MCP tool

        Returns:
            JSON string containing the tool result
        """
        # For now, use synchronous implementation
        # TODO: Implement async MCP calls if needed
        return self._run(**kwargs)


class MCPToolRegistry:
    """
    Registry for all MCP tools available to LangGraph.

    This class manages the registration and retrieval of MCP tools,
    providing a centralized way to access tools across different agents.
    """

    def __init__(self):
        """Initialize the tool registry and register all available tools."""
        self.tools: Dict[str, Union[MCPToolWrapper, BaseTool]] = {}
        self._register_all_tools()
        logger.info(f"Initialized MCP tool registry with {len(self.tools)} tools")

    def _register_all_tools(self) -> None:
        """Register all MCP tools for LangGraph use."""

        # Flight tools
        self.tools["search_flights"] = MCPToolWrapper(
            "flights",
            "search_flights",
            "Search for flights between destinations with dates and preferences",
            {
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
                    "description": "Return date (YYYY-MM-DD), optional",
                },
                "passengers": {
                    "type": "integer",
                    "description": "Number of passengers",
                    "default": 1,
                },
            },
        )

        # Accommodation tools
        self.tools["search_accommodations"] = MCPToolWrapper(
            "accommodations",
            "search_stays",
            "Search for hotels, rentals, and accommodations",
            {
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
                    "default": 1,
                },
            },
        )

        # Maps tools - Use unified LocationService supporting both MCP and direct modes
        from tripsage.orchestration.tools.location_tools import (
            DirectionsTool,
            DistanceMatrixTool,
            ElevationTool,
            GeocodeTool,
            PlaceDetailsTool,
            ReverseGeocodeTool,
            SearchPlacesTool,
            TimezoneTool,
        )

        self.tools["geocode_location"] = GeocodeTool()
        self.tools["reverse_geocode_location"] = ReverseGeocodeTool()
        self.tools["search_places"] = SearchPlacesTool()
        self.tools["get_place_details"] = PlaceDetailsTool()
        self.tools["get_directions"] = DirectionsTool()
        self.tools["distance_matrix"] = DistanceMatrixTool()
        self.tools["get_elevation"] = ElevationTool()
        self.tools["get_timezone"] = TimezoneTool()

        # Weather tools
        self.tools["get_weather"] = MCPToolWrapper(
            "weather",
            "get_current_weather",
            "Get current weather conditions for a location",
            {
                "location": {
                    "type": "string",
                    "description": "Location to get weather for",
                }
            },
        )

        # Memory tools
        self.tools["search_memory"] = MCPToolWrapper(
            "memory",
            "search_nodes",
            "Search user's travel history and preferences",
            {"query": {"type": "string", "description": "Search query for memory"}},
        )

        self.tools["add_memory"] = MCPToolWrapper(
            "memory",
            "add_observations",
            "Store new information about user preferences or travel context",
            {
                "entity_name": {
                    "type": "string",
                    "description": "Entity to add observations to",
                },
                "observations": {
                    "type": "array",
                    "description": "List of observations to add",
                },
            },
        )

        # Time tools
        self.tools["get_current_time"] = MCPToolWrapper(
            "time",
            "get_current_time",
            "Get current time in a specific timezone",
            {"timezone": {"type": "string", "description": "IANA timezone name"}},
        )

        # Web crawling tools - Direct SDK integration only
        from tripsage.orchestration.tools.webcrawl_integration import (
            BookingSiteCrawlTool,
            EventListingCrawlTool,
            TravelBlogCrawlTool,
            WebCrawlTool,
        )

        self.tools["crawl_website_content"] = WebCrawlTool()
        self.tools["crawl_travel_blog"] = TravelBlogCrawlTool()
        self.tools["crawl_booking_site"] = BookingSiteCrawlTool()
        self.tools["crawl_event_listing"] = EventListingCrawlTool()

        logger.info("All MCP tools registered successfully")

    def get_tool(self, tool_name: str) -> Optional[Union[MCPToolWrapper, BaseTool]]:
        """
        Get a specific tool by name.

        Args:
            tool_name: Name of the tool to retrieve

        Returns:
            Tool instance or None if not found
        """
        return self.tools.get(tool_name)

    def get_all_tools(self) -> List[Union[MCPToolWrapper, BaseTool]]:
        """
        Get all available tools.

        Returns:
            List of all registered tool instances
        """
        return list(self.tools.values())

    def get_tools_for_agent(
        self, agent_name: str
    ) -> List[Union[MCPToolWrapper, BaseTool]]:
        """
        Get tools relevant to a specific agent.

        Args:
            agent_name: Name of the agent to get tools for

        Returns:
            List of relevant tool instances
        """
        # Define which tools each agent should have access to
        agent_tool_mapping = {
            "flight_agent": [
                "search_flights",
                "geocode_location",
                "reverse_geocode_location",
                "get_directions",
                "distance_matrix",
                "get_weather",
                "get_current_time",
                "search_memory",
            ],
            "accommodation_agent": [
                "search_accommodations",
                "geocode_location",
                "reverse_geocode_location",
                "search_places",
                "get_place_details",
                "get_directions",
                "distance_matrix",
                "get_weather",
                "search_memory",
            ],
            "destination_research_agent": [
                "geocode_location",
                "reverse_geocode_location",
                "search_places",
                "get_place_details",
                "get_directions",
                "get_elevation",
                "get_timezone",
                "get_weather",
                "crawl_website_content",
                "crawl_travel_blog",
                "search_memory",
            ],
            "destination_agent": [
                "geocode_location",
                "reverse_geocode_location",
                "search_places",
                "get_place_details",
                "get_weather",
                "crawl_website_content",
                "crawl_travel_blog",
                "search_memory",
            ],
            "budget_agent": ["search_memory", "get_current_time"],
            "itinerary_agent": [
                "geocode_location",
                "reverse_geocode_location",
                "search_places",
                "get_place_details",
                "get_directions",
                "distance_matrix",
                "get_elevation",
                "get_timezone",
                "get_weather",
                "get_current_time",
                "crawl_website_content",
                "crawl_booking_site",
                "crawl_event_listing",
                "search_memory",
            ],
            "travel_agent": [
                "search_memory",
                "geocode_location",
                "reverse_geocode_location",
                "search_places",
                "get_place_details",
                "get_directions",
                "get_current_time",
                "get_weather",
                "crawl_website_content",
                "crawl_travel_blog",
            ],
        }

        tool_names = agent_tool_mapping.get(agent_name, [])
        return [self.tools[name] for name in tool_names if name in self.tools]

    def register_custom_tool(self, tool: Union[MCPToolWrapper, BaseTool]) -> None:
        """
        Register a custom tool.

        Args:
            tool: Custom tool to register
        """
        self.tools[tool.name] = tool
        logger.info(f"Registered custom tool: {tool.name}")

    def list_available_tools(self) -> Dict[str, str]:
        """
        Get a list of all available tools with their descriptions.

        Returns:
            Dictionary mapping tool names to descriptions
        """
        return {name: tool.description for name, tool in self.tools.items()}
