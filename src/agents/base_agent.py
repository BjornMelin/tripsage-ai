"""
Base Agent implementation for TripSage.

This module provides the base agent class using the OpenAI Agents SDK
with integration for MCP tools and dual storage architecture.
"""

import asyncio
import json
import time
from typing import Any, Callable, Dict, List, Optional, Type, Union

from pydantic import BaseModel, Field

from agents import Agent, RunContextWrapper, function_tool, handoff
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX

from ..cache.redis_cache import redis_cache
from ..mcp.base_mcp_client import BaseMCPClient
from ..utils.config import get_config
from ..utils.error_handling import MCPError, TripSageError, log_exception
from ..utils.logging import get_module_logger

logger = get_module_logger(__name__)
config = get_config()


class ToolCallInput(BaseModel):
    """Input for a tool call."""

    tool_name: str
    params: Dict[str, Any]


class ToolCallOutput(BaseModel):
    """Output from a tool call."""

    tool_name: str
    result: Dict[str, Any]
    error: Optional[str] = None


class BaseAgent:
    """Base class for all TripSage agents using the OpenAI Agents SDK."""

    def __init__(
        self,
        name: str,
        instructions: str,
        model: str = "gpt-4",
        temperature: float = 0.2,
        tools: Optional[List[Dict[str, Any]]] = None,
        handoffs: Optional[List[Any]] = None,
        metadata: Optional[Dict[str, str]] = None,
    ):
        """Initialize the agent.

        Args:
            name: Agent name
            instructions: Agent instructions
            model: Model name to use
            temperature: Temperature for model sampling
            tools: List of tools to register
            handoffs: List of agents to hand off to
            metadata: Additional metadata
        """
        self.name = name
        self.instructions = instructions
        self.model = model
        self.temperature = temperature
        self.metadata = metadata or {"agent_type": "tripsage"}

        # Initialize tools and handoffs
        self._tools = tools or []
        self._handoffs = handoffs or []

        # Register default tools
        self._register_default_tools()

        # Create OpenAI Agent
        self.agent = Agent(
            name=name,
            instructions=instructions,
            model=model,
            temperature=temperature,
            tools=self._tools,
            handoffs=self._handoffs,
        )

        # Store conversation history
        self.messages_history = []

        logger.info("Initialized agent: %s", name)

    def _register_default_tools(self) -> None:
        """Register default tools for the agent."""
        # Register local tool examples
        pass

    def _register_tool(self, tool: Callable) -> None:
        """Register a tool with the agent.

        Args:
            tool: Tool function to register
        """
        self._tools.append(tool)
        logger.debug("Registered tool: %s", tool.__name__)

    def _register_mcp_client_tools(
        self, mcp_client: BaseMCPClient, prefix: str = ""
    ) -> None:
        """Register tools from an MCP client.

        Args:
            mcp_client: MCP client to register tools from
            prefix: Prefix to add to tool names
        """
        # This would register functions that call the MCP client's methods
        pass

    async def run(
        self, user_input: str, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Run the agent with user input.

        Args:
            user_input: User input text
            context: Optional context data

        Returns:
            Dictionary with the agent's response and other information
        """
        from agents import Runner

        # Add to message history
        self.messages_history.append(
            {"role": "user", "content": user_input, "timestamp": time.time()}
        )

        # Set up context
        run_context = context or {}

        try:
            # Run the agent
            logger.info("Running agent: %s", self.name)
            result = await Runner.run(self.agent, user_input, context=run_context)

            # Extract response
            response = {
                "content": result.final_output,
                "tool_calls": (
                    result.tool_calls if hasattr(result, "tool_calls") else []
                ),
                "handoffs": result.handoffs if hasattr(result, "handoffs") else [],
                "status": "success",
            }

            # Add to message history
            self.messages_history.append(
                {
                    "role": "assistant",
                    "content": response["content"],
                    "timestamp": time.time(),
                }
            )

            return response

        except Exception as e:
            logger.error("Error running agent: %s", str(e))
            log_exception(e)

            error_message = "An error occurred while processing your request."
            if isinstance(e, TripSageError):
                error_message = e.message

            # Add error to message history
            self.messages_history.append(
                {
                    "role": "assistant",
                    "content": error_message,
                    "timestamp": time.time(),
                    "error": True,
                }
            )

            return {
                "content": error_message,
                "status": "error",
                "error_type": type(e).__name__,
                "error_message": str(e),
            }

    def get_last_response(self) -> Optional[str]:
        """Get the last response from the agent.

        Returns:
            The last response text or None if no responses
        """
        assistant_messages = [
            msg for msg in self.messages_history if msg["role"] == "assistant"
        ]
        if not assistant_messages:
            return None
        return assistant_messages[-1]["content"]

    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """Get the conversation history.

        Returns:
            List of message dictionaries
        """
        return self.messages_history

    @function_tool
    async def echo(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Echo the input back to the user.

        Args:
            params: Parameters including the text to echo

        Returns:
            Dictionary with the echoed text
        """
        text = params.get("text", "")
        return {"text": text}


class TravelAgent(BaseAgent):
    """Travel planning agent that integrates with travel-specific MCP tools."""

    def __init__(
        self,
        name: str = "TripSage Travel Planner",
        model: str = "gpt-4",
        temperature: float = 0.2,
    ):
        """Initialize the travel agent.

        Args:
            name: Agent name
            model: Model name to use
            temperature: Temperature for model sampling
        """
        # Define comprehensive instructions
        instructions = """
        You are an expert travel planning assistant for TripSage. Your goal is to help users
        plan optimal travel experiences by leveraging multiple data sources and adapting to 
        their preferences and constraints.
        
        Key responsibilities:
        1. Help users discover, research, and plan trips to destinations worldwide
        2. Find flights, accommodations, and activities that match user budget and preferences
        3. Provide weather and local information to assist with planning
        4. Optimize travel plans to maximize value and enjoyment
        5. Store and retrieve information across sessions
        
        IMPORTANT GUIDELINES:
        
        - Ask questions to understand user preferences before making recommendations
        - Always provide a brief rationale for your recommendations
        - When presenting options, number them clearly for easy reference
        - Present concise, formatted information rather than lengthy text
        - Provide specific prices and options rather than vague ranges
        - Prioritize information from specialized MCP tools over general knowledge
        - For complex, multi-step tasks, create a clear plan with numbered steps
        
        DUAL STORAGE ARCHITECTURE:
        The TripSage system uses two storage systems:
        1. Supabase database (for structured data like bookings, user preferences)
        2. Knowledge graph (for travel concepts, entities, and relationships)
        
        MCP TOOLS:
        You have access to specialized MCP tools that provide real-time information:
        - Weather MCP: Get current and forecast weather data
        - Flights MCP: Search for flights with pricing
        - Accommodations MCP: Find hotels, Airbnb, and other accommodations
        - Google Maps MCP: Get location information and directions
        - Web Crawling MCP: Research destinations and activities
        - Browser MCP: Automated web browsing for information
        - Memory MCP: Store and retrieve knowledge graph information
        - Time MCP: Handle timezone conversions and scheduling
        
        Use the most specific and appropriate tool for each task.
        """

        super().__init__(
            name=name,
            instructions=instructions,
            model=model,
            temperature=temperature,
            metadata={"agent_type": "travel_planner", "version": "1.0.0"},
        )

        # Register travel-specific tools
        self._register_travel_tools()

    def _register_travel_tools(self) -> None:
        """Register travel-specific tools."""
        # This will be implemented to register tools from various MCP clients
        pass

    @function_tool
    async def get_weather(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get current weather for a location.

        Args:
            params: Parameters with location information

        Returns:
            Current weather data
        """
        from ..mcp.weather import get_client

        try:
            # Get weather client
            weather_client = get_client()

            # Extract parameters
            lat = params.get("lat")
            lon = params.get("lon")
            city = params.get("city")
            country = params.get("country")

            # Call weather MCP
            weather_data = await weather_client.get_current_weather(
                lat=lat, lon=lon, city=city, country=country
            )

            return weather_data

        except Exception as e:
            logger.error("Error getting weather: %s", str(e))
            if isinstance(e, MCPError):
                return {"error": e.message}
            return {"error": f"Weather service error: {str(e)}"}


class BudgetAgent(BaseAgent):
    """Budget optimization agent for travel planning."""

    def __init__(
        self,
        name: str = "TripSage Budget Optimizer",
        model: str = "gpt-4",
        temperature: float = 0.2,
    ):
        """Initialize the budget agent.

        Args:
            name: Agent name
            model: Model name to use
            temperature: Temperature for model sampling
        """
        # Define specialized instructions
        instructions = (
            f"{RECOMMENDED_PROMPT_PREFIX}\n\n"
            + """
        You are a specialized travel budget optimization agent. Your goal is to help
        users allocate their travel budget efficiently across different aspects of their
        trip to maximize value.
        
        Key responsibilities:
        1. Analyze budget constraints and trip requirements
        2. Recommend optimal allocation of funds between transportation, accommodation, food, activities
        3. Find cost-saving opportunities without compromising quality
        4. Compare options based on price-to-value ratio
        5. Track price changes for flights and accommodations
        
        IMPORTANT GUIDELINES:
        
        - Prioritize the user's stated preferences when making trade-offs
        - Provide specific, actionable advice rather than general tips
        - Support all recommendations with clear rationales and data
        - When appropriate, suggest alternatives that offer better value
        - Maintain transparency about all costs, including hidden fees
        - Present budget allocations in both amounts and percentages
        
        Treat all budget information with privacy and security.
        """
        )

        super().__init__(
            name=name,
            instructions=instructions,
            model=model,
            temperature=temperature,
            metadata={"agent_type": "budget_optimizer", "version": "1.0.0"},
        )

        # Register budget-specific tools
        self._register_budget_tools()

    def _register_budget_tools(self) -> None:
        """Register budget-specific tools."""
        # This will be implemented to register budget optimization tools
        pass


# Function to create a handoff to the Budget Agent
def budget_agent_handoff():
    """Create a handoff to the Budget Agent."""
    budget_agent = BudgetAgent()

    async def on_budget_handoff(ctx: RunContextWrapper[None], input_data: str):
        """Handle budget agent handoff.

        Args:
            ctx: Context wrapper
            input_data: Input data
        """
        logger.info("Handing off to Budget Agent")
        # Additional handoff logic could be implemented here

    return handoff(agent=budget_agent, on_handoff=on_budget_handoff)
