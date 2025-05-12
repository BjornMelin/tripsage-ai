"""
Base Agent implementation for TripSage.

This module provides the base agent class using the OpenAI Agents SDK
with integration for MCP tools and dual storage architecture.
"""

import time
import uuid
from typing import Any, Callable, Dict, List, Optional

from pydantic import BaseModel

from agents import Agent, RunContextWrapper, function_tool, handoff
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX
from src.mcp.base_mcp_client import BaseMCPClient
from src.utils.config import get_config
from src.utils.error_handling import MCPError, TripSageError, log_exception
from src.utils.logging import get_module_logger
from src.utils.session_memory import initialize_session_memory, store_session_summary

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
        self.session_id = str(uuid.uuid4())
        self.session_data = {}

        logger.info("Initialized agent: %s", name)

    def _register_default_tools(self) -> None:
        """Register default tools for the agent."""
        # Import memory tools
        from .memory_tools import (
            add_entity_observations,
            create_knowledge_entities,
            create_knowledge_relations,
            delete_entity_observations,
            delete_knowledge_entities,
            delete_knowledge_relations,
            get_entity_details,
            get_knowledge_graph,
            initialize_agent_memory,
            save_session_summary,
            search_knowledge_graph,
            update_agent_memory,
        )

        # Register memory tools
        self._register_tool(get_knowledge_graph)
        self._register_tool(search_knowledge_graph)
        self._register_tool(get_entity_details)
        self._register_tool(create_knowledge_entities)
        self._register_tool(create_knowledge_relations)
        self._register_tool(add_entity_observations)
        self._register_tool(delete_knowledge_entities)
        self._register_tool(delete_knowledge_relations)
        self._register_tool(delete_entity_observations)
        self._register_tool(initialize_agent_memory)
        self._register_tool(update_agent_memory)
        self._register_tool(save_session_summary)

        # Register echo tool
        self._register_tool(self.echo)

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
        try:
            # Get available tools from client
            client_tools = mcp_client.list_tools_sync()

            if not client_tools:
                logger.warning(
                    "No tools found in MCP client: %s", mcp_client.server_name
                )
                return

            for tool_name in client_tools:
                # Create a wrapper function for this tool that will call the client
                @function_tool
                async def mcp_tool_wrapper(
                    params: Dict[str, Any], _tool_name=tool_name
                ):
                    """Wrapper for MCP client tool."""
                    try:
                        result = await mcp_client.call_tool(_tool_name, params)
                        return result
                    except Exception as e:
                        logger.error(
                            "Error calling MCP tool %s: %s", _tool_name, str(e)
                        )
                        if isinstance(e, MCPError):
                            return {"error": e.message}
                        return {"error": f"MCP tool error: {str(e)}"}

                # Set proper name and docstring for the wrapper
                tool_metadata = mcp_client.get_tool_metadata_sync(tool_name)
                wrapper_name = f"{prefix}{tool_name}"
                mcp_tool_wrapper.__name__ = wrapper_name

                if tool_metadata and "description" in tool_metadata:
                    mcp_tool_wrapper.__doc__ = tool_metadata["description"]
                else:
                    mcp_tool_wrapper.__doc__ = (
                        f"Call the {tool_name} tool from {mcp_client.server_name} MCP."
                    )

                # Register the wrapper
                self._register_tool(mcp_tool_wrapper)
                logger.debug(
                    "Registered MCP tool %s as %s from %s",
                    tool_name,
                    wrapper_name,
                    mcp_client.server_name,
                )

            logger.info(
                "Registered %d tools from MCP client: %s",
                len(client_tools),
                mcp_client.server_name,
            )

        except Exception as e:
            logger.error("Error registering MCP client tools: %s", str(e))
            log_exception(e)

    async def _initialize_session(
        self, user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Initialize a new session with knowledge graph data.

        Args:
            user_id: Optional user ID

        Returns:
            Session data
        """
        try:
            # Initialize session memory
            self.session_data = await initialize_session_memory(user_id)
            logger.info("Session initialized with memory data")
            return self.session_data
        except Exception as e:
            logger.error("Error initializing session: %s", str(e))
            log_exception(e)
            return {}

    async def _save_session_summary(self, user_id: str, summary: str) -> None:
        """Save a summary of the current session.

        Args:
            user_id: User ID
            summary: Session summary
        """
        try:
            await store_session_summary(user_id, summary, self.session_id)
            logger.info("Session summary saved")
        except Exception as e:
            logger.error("Error saving session summary: %s", str(e))
            log_exception(e)

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

        # Initialize session data if this is the first message
        if not self.session_data and "user_id" in run_context:
            await self._initialize_session(run_context.get("user_id"))
            run_context["session_data"] = self.session_data
            run_context["session_id"] = self.session_id

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

            # Save session summary if needed
            if len(self.messages_history) >= 10 and "user_id" in run_context:
                # Generate session summary
                summary = (
                    f"Conversation with {self.messages_history[0]['content'][:50]}..."
                )
                await self._save_session_summary(run_context["user_id"], summary)

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
        You are an expert travel planning assistant for TripSage. Your goal is
        to help users plan optimal travel experiences by leveraging multiple data
        sources and adapting to their preferences and constraints.
        
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
        
        KNOWLEDGE GRAPH USAGE:
        - At the start of each session, retrieve relevant knowledge for the user
        - During the session, create entities for new destinations, accommodations, etc.
        - Create relationships between entities (e.g., hotel located in city)
        - Add observations to entities as you learn more about them
        - At the end of the session, save a summary to the knowledge graph
        
        AVAILABLE TOOLS:
        You have access to specialized tools that provide real-time information:
        - Web Search: Search the internet for up-to-date travel information
        - Weather MCP: Get current and forecast weather data
        - Flights MCP: Search for flights with pricing
        - Accommodations MCP: Find hotels, Airbnb, and other accommodations
        - Google Maps MCP: Get location information and directions
        - Web Crawling MCP: Research destinations and activities in depth
        - Browser MCP: Automated web browsing for complex information gathering
        - Memory MCP: Store and retrieve knowledge graph information
        - Time MCP: Handle timezone conversions and scheduling

        For general travel information queries, use the built-in Web Search tool first.
        For more in-depth research or specific data extraction, use Web Crawling MCP.
        For interactive tasks like checking availability, use Browser MCP.
        For specialized travel data (flights, weather, etc.), use the appropriate domain-specific MCP tool.
        Use the most specific and appropriate tool for each task.
        
        MEMORY OPERATIONS:
        - initialize_agent_memory: Retrieve user preferences and recent trips
        - search_knowledge_graph: Find relevant entities like destinations
        - get_entity_details: Get detailed information about specific entities
        - create_knowledge_entities: Create new entities for destinations, hotels, etc.
        - create_knowledge_relations: Create relationships between entities
        - add_entity_observations: Add new information to existing entities
        
        Always use memory operations to provide personalized recommendations
        and to learn from user interactions over time.
        """  # noqa: E501

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
        
        KNOWLEDGE GRAPH USAGE:
        Use memory operations to retrieve and store budget-related knowledge:
        - Retrieve user budget preferences using initialize_agent_memory
        - Record budget allocations and price tracking information
        - Create budget entities and relate them to trips and destinations
        
        Treat all budget information with privacy and security.
        """  # noqa: E501
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
