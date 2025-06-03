"""
Centralized LangGraph Tool Registry for TripSage.

This module provides a comprehensive, centralized tool registry that manages all tools
available to LangGraph agents, including both MCP-based tools and direct SDK tools.
Refactored based on LangGraph best practices for tool management and async patterns.
"""

import asyncio
import json
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from langchain_core.tools import BaseTool, Tool
from langchain_core.tools.base import ToolException
from pydantic import BaseModel, Field

from tripsage.agents.service_registry import ServiceRegistry
from tripsage_core.mcp_abstraction.manager import mcp_manager
from tripsage_core.utils.error_handling_utils import log_exception
from tripsage_core.utils.logging_utils import get_logger

logger = get_logger(__name__)


class ToolMetadata(BaseModel):
    """Metadata for a tool in the registry."""

    name: str
    description: str
    tool_type: str = Field(..., description="MCP, SDK, or custom")
    agent_types: List[str] = Field(
        default_factory=list, description="Agent types that can use this tool"
    )
    capabilities: List[str] = Field(
        default_factory=list, description="Tool capabilities/categories"
    )
    parameters: Dict[str, Any] = Field(
        default_factory=dict, description="Tool parameter schema"
    )
    dependencies: List[str] = Field(
        default_factory=list, description="Required services or dependencies"
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now())
    last_used: Optional[datetime] = None
    usage_count: int = 0
    error_count: int = 0


class BaseToolWrapper(ABC):
    """Abstract base class for tool wrappers."""

    def __init__(self, metadata: ToolMetadata):
        """Initialize the tool wrapper with metadata."""
        self.metadata = metadata
        self.logger = get_logger(f"tool.{metadata.name}")

    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        """Execute the tool with given parameters."""
        pass

    @abstractmethod
    def get_langchain_tool(self) -> BaseTool:
        """Get the LangChain-compatible tool instance."""
        pass

    async def _update_usage_stats(self, success: bool = True) -> None:
        """Update usage statistics for the tool."""
        self.metadata.last_used = datetime.now()
        self.metadata.usage_count += 1
        if not success:
            self.metadata.error_count += 1


class MCPToolWrapper(BaseToolWrapper):
    """Wrapper for MCP tools with enhanced error handling and async support."""

    def __init__(
        self,
        service_name: str,
        method_name: str,
        description: str,
        parameters: Optional[Dict[str, Any]] = None,
        agent_types: Optional[List[str]] = None,
        capabilities: Optional[List[str]] = None,
    ):
        """Initialize MCP tool wrapper."""
        metadata = ToolMetadata(
            name=f"{service_name}_{method_name}",
            description=description,
            tool_type="MCP",
            agent_types=agent_types or [],
            capabilities=capabilities or [],
            parameters=parameters or {},
            dependencies=[service_name],
        )
        super().__init__(metadata)

        self.service_name = service_name
        self.method_name = method_name
        self.mcp_manager = mcp_manager

        # Create the LangChain tool
        self._tool = Tool(
            name=metadata.name,
            description=description,
            func=self._run,
            coroutine=self._arun,
        )

    async def execute(self, **kwargs) -> Any:
        """Execute the MCP tool asynchronously."""
        try:
            self.logger.debug(
                f"Executing MCP tool {self.metadata.name} with params: {kwargs}"
            )

            # Call MCP manager with service method
            result = await self.mcp_manager.invoke(
                method_name=self.method_name, params=kwargs
            )

            await self._update_usage_stats(success=True)
            return result

        except Exception as e:
            await self._update_usage_stats(success=False)
            self.logger.error(f"Error executing MCP tool {self.metadata.name}: {e}")
            log_exception(e, logger_name=f"tool.{self.metadata.name}")
            raise ToolException(
                f"Error executing {self.metadata.name}: {str(e)}"
            ) from e

    def get_langchain_tool(self) -> BaseTool:
        """Get the LangChain-compatible tool instance."""
        return self._tool

    def _run(self, **kwargs) -> str:
        """Synchronous execution wrapper for async MCP calls."""
        try:
            return asyncio.run(self._arun(**kwargs))
        except Exception as e:
            self.logger.error(f"Error in sync execution of {self.metadata.name}: {e}")
            raise ToolException(
                f"Error executing {self.metadata.name}: {str(e)}"
            ) from e

    async def _arun(self, **kwargs) -> str:
        """Asynchronous execution of MCP tool."""
        result = await self.execute(**kwargs)
        # Convert result to JSON string for LangGraph compatibility
        return json.dumps(result, ensure_ascii=False)


class SDKToolWrapper(BaseToolWrapper):
    """Wrapper for direct SDK tools (Google Maps, Playwright, etc.)."""

    def __init__(
        self,
        name: str,
        description: str,
        func: callable,
        parameters: Optional[Dict[str, Any]] = None,
        agent_types: Optional[List[str]] = None,
        capabilities: Optional[List[str]] = None,
        dependencies: Optional[List[str]] = None,
    ):
        """Initialize SDK tool wrapper."""
        metadata = ToolMetadata(
            name=name,
            description=description,
            tool_type="SDK",
            agent_types=agent_types or [],
            capabilities=capabilities or [],
            parameters=parameters or {},
            dependencies=dependencies or [],
        )
        super().__init__(metadata)

        self.func = func

        # Create the LangChain tool
        if asyncio.iscoroutinefunction(func):
            self._tool = Tool(
                name=name,
                description=description,
                func=self._run,
                coroutine=self._arun,
            )
        else:
            self._tool = Tool(
                name=name,
                description=description,
                func=func,
            )

    async def execute(self, **kwargs) -> Any:
        """Execute the SDK tool."""
        try:
            self.logger.debug(
                f"Executing SDK tool {self.metadata.name} with params: {kwargs}"
            )

            if asyncio.iscoroutinefunction(self.func):
                result = await self.func(**kwargs)
            else:
                result = self.func(**kwargs)

            await self._update_usage_stats(success=True)
            return result

        except Exception as e:
            await self._update_usage_stats(success=False)
            self.logger.error(f"Error executing SDK tool {self.metadata.name}: {e}")
            log_exception(e, logger_name=f"tool.{self.metadata.name}")
            raise ToolException(
                f"Error executing {self.metadata.name}: {str(e)}"
            ) from e

    def get_langchain_tool(self) -> BaseTool:
        """Get the LangChain-compatible tool instance."""
        return self._tool

    def _run(self, **kwargs) -> str:
        """Synchronous execution wrapper."""
        try:
            result = asyncio.run(self.execute(**kwargs))
            return (
                json.dumps(result, ensure_ascii=False)
                if not isinstance(result, str)
                else result
            )
        except Exception as e:
            self.logger.error(f"Error in sync execution of {self.metadata.name}: {e}")
            raise ToolException(
                f"Error executing {self.metadata.name}: {str(e)}"
            ) from e

    async def _arun(self, **kwargs) -> str:
        """Asynchronous execution wrapper."""
        result = await self.execute(**kwargs)
        return (
            json.dumps(result, ensure_ascii=False)
            if not isinstance(result, str)
            else result
        )


class LangGraphToolRegistry:
    """
    Comprehensive centralized tool registry for LangGraph agents.

    This registry manages all tools available to agents, providing:
    - Tool lifecycle management
    - Agent-specific tool filtering
    - Usage analytics and monitoring
    - Dynamic tool discovery and registration
    - Dependency injection support
    """

    def __init__(self, service_registry: Optional[ServiceRegistry] = None):
        """Initialize the tool registry."""
        self.service_registry = service_registry
        self.tools: Dict[str, BaseToolWrapper] = {}
        self.agent_tool_mappings: Dict[str, Set[str]] = {}
        self.capability_mappings: Dict[str, Set[str]] = {}

        # Initialize with core tools
        self._initialize_core_tools()

        logger.info("Initialized LangGraphToolRegistry")

    def _initialize_core_tools(self) -> None:
        """Initialize core tools for the registry."""
        # MCP-based tools
        self._register_mcp_tools()

        # SDK-based tools
        self._register_sdk_tools()

        # Agent-specific tool mappings
        self._setup_agent_mappings()

        logger.info(f"Initialized {len(self.tools)} core tools")

    def _register_mcp_tools(self) -> None:
        """Register MCP-based tools."""
        mcp_tools = [
            # Flight tools
            {
                "service_name": "flights",
                "method_name": "search_flights",
                "description": (
                    "Search for flights between locations with filters for dates, "
                    "passengers, and preferences"
                ),
                "agent_types": ["flight_agent", "budget_agent", "itinerary_agent"],
                "capabilities": ["flight_search", "booking", "travel"],
                "parameters": {
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
            },
            # Accommodation tools
            {
                "service_name": "accommodations",
                "method_name": "search_listings",
                "description": (
                    "Search for accommodations in a location with check-in/out "
                    "dates and guest requirements"
                ),
                "agent_types": [
                    "accommodation_agent",
                    "budget_agent",
                    "itinerary_agent",
                ],
                "capabilities": ["accommodation_search", "booking", "lodging"],
                "parameters": {
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
            },
            # Location and weather tools
            {
                "service_name": "maps",
                "method_name": "geocode",
                "description": "Get geographic coordinates and details for a location",
                "agent_types": [
                    "destination_research_agent",
                    "flight_agent",
                    "accommodation_agent",
                    "itinerary_agent",
                ],
                "capabilities": ["geocoding", "location", "mapping"],
                "parameters": {
                    "location": {"type": "string", "description": "Location to geocode"}
                },
            },
            {
                "service_name": "weather",
                "method_name": "get_current_weather",
                "description": "Get current weather information for a location",
                "agent_types": ["destination_research_agent", "itinerary_agent"],
                "capabilities": ["weather", "information"],
                "parameters": {
                    "location": {
                        "type": "string",
                        "description": "Location for weather information",
                    }
                },
            },
            # Web search tools
            {
                "service_name": "web",
                "method_name": "search",
                "description": "Search the web for travel-related information",
                "agent_types": [
                    "destination_research_agent",
                    "flight_agent",
                    "accommodation_agent",
                    "budget_agent",
                ],
                "capabilities": ["web_search", "research", "information"],
                "parameters": {
                    "query": {"type": "string", "description": "Search query"},
                    "location": {
                        "type": "string",
                        "description": "Location context for search",
                        "required": False,
                    },
                },
            },
            # Memory tools
            {
                "service_name": "memory",
                "method_name": "add_memory",
                "description": (
                    "Save important information to user memory for future reference"
                ),
                "agent_types": [
                    "memory_update",
                    "flight_agent",
                    "accommodation_agent",
                    "destination_research_agent",
                    "budget_agent",
                    "itinerary_agent",
                ],
                "capabilities": ["memory", "persistence", "user_context"],
                "parameters": {
                    "content": {"type": "string", "description": "Information to save"},
                    "category": {
                        "type": "string",
                        "description": "Memory category",
                        "required": False,
                    },
                },
            },
            {
                "service_name": "memory",
                "method_name": "search_memories",
                "description": "Search user memories for relevant information",
                "agent_types": [
                    "memory_update",
                    "flight_agent",
                    "accommodation_agent",
                    "destination_research_agent",
                    "budget_agent",
                    "itinerary_agent",
                ],
                "capabilities": ["memory", "search", "user_context"],
                "parameters": {
                    "query": {
                        "type": "string",
                        "description": "Search query for memories",
                    }
                },
            },
        ]

        for tool_config in mcp_tools:
            tool = MCPToolWrapper(**tool_config)
            self.register_tool(tool)

    def _register_sdk_tools(self) -> None:
        """Register SDK-based tools."""
        # These would be implemented based on available SDK tools
        # Example: Google Maps direct SDK tools, Playwright tools, etc.
        pass

    def _setup_agent_mappings(self) -> None:
        """Setup agent-specific tool mappings."""
        # Build mappings from tool metadata
        for tool_name, tool in self.tools.items():
            for agent_type in tool.metadata.agent_types:
                if agent_type not in self.agent_tool_mappings:
                    self.agent_tool_mappings[agent_type] = set()
                self.agent_tool_mappings[agent_type].add(tool_name)

            for capability in tool.metadata.capabilities:
                if capability not in self.capability_mappings:
                    self.capability_mappings[capability] = set()
                self.capability_mappings[capability].add(tool_name)

    def register_tool(self, tool: BaseToolWrapper) -> None:
        """Register a tool in the registry."""
        self.tools[tool.metadata.name] = tool

        # Update mappings
        for agent_type in tool.metadata.agent_types:
            if agent_type not in self.agent_tool_mappings:
                self.agent_tool_mappings[agent_type] = set()
            self.agent_tool_mappings[agent_type].add(tool.metadata.name)

        for capability in tool.metadata.capabilities:
            if capability not in self.capability_mappings:
                self.capability_mappings[capability] = set()
            self.capability_mappings[capability].add(tool.metadata.name)

        logger.info(
            f"Registered tool: {tool.metadata.name} ({tool.metadata.tool_type})"
        )

    def get_tool(self, tool_name: str) -> Optional[BaseToolWrapper]:
        """Get a specific tool by name."""
        return self.tools.get(tool_name)

    def get_tools_for_agent(
        self,
        agent_type: str,
        capabilities: Optional[List[str]] = None,
        exclude_tools: Optional[List[str]] = None,
    ) -> List[BaseToolWrapper]:
        """
        Get tools available for a specific agent type with optional filtering.

        Args:
            agent_type: Type of agent requesting tools
            capabilities: Optional list of required capabilities
            exclude_tools: Optional list of tool names to exclude

        Returns:
            List of tools available for the agent
        """
        tool_names = self.agent_tool_mappings.get(agent_type, set()).copy()

        # Filter by capabilities if specified
        if capabilities:
            capability_tools = set()
            for capability in capabilities:
                capability_tools.update(self.capability_mappings.get(capability, set()))
            tool_names = tool_names.intersection(capability_tools)

        # Exclude specific tools if specified
        if exclude_tools:
            tool_names = tool_names - set(exclude_tools)

        return [self.tools[name] for name in tool_names if name in self.tools]

    def get_langchain_tools_for_agent(
        self,
        agent_type: str,
        capabilities: Optional[List[str]] = None,
        exclude_tools: Optional[List[str]] = None,
    ) -> List[BaseTool]:
        """Get LangChain-compatible tools for an agent."""
        tools = self.get_tools_for_agent(agent_type, capabilities, exclude_tools)
        return [tool.get_langchain_tool() for tool in tools]

    def get_tools_by_capability(self, capability: str) -> List[BaseToolWrapper]:
        """Get all tools that have a specific capability."""
        tool_names = self.capability_mappings.get(capability, set())
        return [self.tools[name] for name in tool_names if name in self.tools]

    def get_tool_metadata(self, tool_name: str) -> Optional[ToolMetadata]:
        """Get metadata for a specific tool."""
        tool = self.get_tool(tool_name)
        return tool.metadata if tool else None

    def get_usage_statistics(self) -> Dict[str, Any]:
        """Get usage statistics for all tools."""
        stats = {
            "total_tools": len(self.tools),
            "by_type": {},
            "by_agent": {},
            "top_used": [],
            "error_rates": {},
        }

        # Count by type
        for tool in self.tools.values():
            tool_type = tool.metadata.tool_type
            stats["by_type"][tool_type] = stats["by_type"].get(tool_type, 0) + 1

        # Count by agent type
        for agent_type, tool_names in self.agent_tool_mappings.items():
            stats["by_agent"][agent_type] = len(tool_names)

        # Top used tools
        sorted_tools = sorted(
            self.tools.values(), key=lambda t: t.metadata.usage_count, reverse=True
        )
        stats["top_used"] = [
            {
                "name": tool.metadata.name,
                "usage_count": tool.metadata.usage_count,
                "last_used": tool.metadata.last_used.isoformat()
                if tool.metadata.last_used
                else None,
            }
            for tool in sorted_tools[:10]
        ]

        # Error rates
        for tool in self.tools.values():
            if tool.metadata.usage_count > 0:
                error_rate = tool.metadata.error_count / tool.metadata.usage_count
                if error_rate > 0:
                    stats["error_rates"][tool.metadata.name] = {
                        "error_rate": error_rate,
                        "error_count": tool.metadata.error_count,
                        "total_usage": tool.metadata.usage_count,
                    }

        return stats

    def list_available_tools(self) -> Dict[str, Dict[str, Any]]:
        """List all available tools with their metadata."""
        return {
            name: {
                "description": tool.metadata.description,
                "type": tool.metadata.tool_type,
                "agent_types": tool.metadata.agent_types,
                "capabilities": tool.metadata.capabilities,
                "parameters": tool.metadata.parameters,
                "dependencies": tool.metadata.dependencies,
                "usage_count": tool.metadata.usage_count,
                "error_count": tool.metadata.error_count,
                "last_used": tool.metadata.last_used.isoformat()
                if tool.metadata.last_used
                else None,
            }
            for name, tool in self.tools.items()
        }

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on all tools."""
        health_status = {
            "healthy": [],
            "unhealthy": [],
            "total_tools": len(self.tools),
            "timestamp": datetime.now().isoformat(),
        }

        for tool_name, tool in self.tools.items():
            try:
                # For MCP tools, check if the service is available
                if isinstance(tool, MCPToolWrapper):
                    # Basic connectivity check - this could be enhanced
                    await tool.mcp_manager.check_service_health(tool.service_name)

                health_status["healthy"].append(tool_name)

            except Exception as e:
                health_status["unhealthy"].append({"tool": tool_name, "error": str(e)})
                logger.warning(f"Health check failed for tool {tool_name}: {e}")

        return health_status


# Global registry instance
_global_registry: Optional[LangGraphToolRegistry] = None


def get_tool_registry(
    service_registry: Optional[ServiceRegistry] = None,
) -> LangGraphToolRegistry:
    """Get the global tool registry instance."""
    global _global_registry
    if _global_registry is None or service_registry is not None:
        _global_registry = LangGraphToolRegistry(service_registry)
    return _global_registry
