"""
Travel Agent implementation for TripSage.

This module provides the travel agent implementation using the OpenAI Agents SDK
and specializes in travel planning with various MCP tools.
"""

import time
from typing import Any, Dict, Optional

from tripsage.agents.accommodation import AccommodationAgent
from tripsage.agents.base import BaseAgent
from tripsage.agents.budget import Budget as BudgetAgent
from tripsage.agents.destination_research import DestinationResearchAgent

# Import specialized agents for handoffs
from tripsage.agents.flight import FlightAgent
from tripsage.agents.itinerary import Itinerary as ItineraryAgent
from tripsage.config.app_settings import settings
from tripsage.utils.logging import get_logger

logger = get_logger(__name__)


class TravelAgent(BaseAgent):
    """Travel planning agent that integrates with travel-specific MCP tools."""

    def __init__(
        self,
        name: str = "TripSage Travel Planner",
        model: str = None,
        temperature: float = None,
    ):
        """Initialize the travel agent.

        Args:
            name: Agent name
            model: Model name to use (defaults to settings if None)
            temperature: Temperature for model sampling (defaults to settings if None)
        """
        # Define comprehensive instructions
        instructions = """
        You are an expert travel planning assistant for TripSage. Your goal is
        to help users plan optimal travel experiences by leveraging multiple data
        sources and adapting to their preferences and constraints.
        
        Key responsibilities:
        1. Help users discover, research, and plan trips to destinations worldwide
        2. Find flights, accommodations, and activities that match user budget 
           and preferences
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
        For specialized travel data (flights, weather, etc.), use the appropriate
        domain-specific MCP tool.
        Use the most specific and appropriate tool for each task.
        
        SPECIALIZED AGENT HANDOFFS:
        You can also hand off specific tasks to specialized agents:
        
        - hand_off_to_flight_agent: For complex flight search and booking questions
          Use when the user is focused on flight details, comparing flight options,
          or needs to book flights.
        
        - hand_off_to_accommodation_agent: For hotel, Airbnb, and lodging inquiries
          Use when the user is primarily interested in accommodation details, 
          comparing options, or needs to book stays.
          
        - hand_off_to_budget_agent: For calculating and optimizing travel budgets
          Use when the user wants to create a trip budget, compare costs, or optimize
          spending across different aspects of their trip.
          
        - hand_off_to_destination_agent: For in-depth destination research
          Use when the user wants detailed information about specific destinations,
          including attractions, local tips, and cultural information.
          
        - hand_off_to_itinerary_agent: For creating and managing detailed itineraries
          Use when the user wants to build a day-by-day itinerary, optimize their
          schedule, or balance activities across their trip.
        
        When to hand off:
        - When the user's request is very focused on one specific domain
        - When complex or detailed information is needed in a specific area
        - When dealing with multi-step processes in a specific domain
        
        Before handing off:
        - Gather relevant context information
        - Make sure you've collected the user's preferences
        - Be explicit with the user about the handoff
        
        MEMORY OPERATIONS:
        - initialize_agent_memory: Retrieve user preferences and recent trips
        - search_knowledge_graph: Find relevant entities like destinations
        - get_entity_details: Get detailed information about specific entities
        - create_knowledge_entities: Create new entities for destinations, hotels, etc.
        - create_knowledge_relations: Create relationships between entities
        - add_entity_observations: Add new information to existing entities
        
        Always use memory operations to provide personalized recommendations
        and to learn from user interactions over time.
        """

        model = model or settings.agent.model_name
        temperature = temperature or settings.agent.temperature

        super().__init__(
            name=name,
            instructions=instructions,
            model=model,
            temperature=temperature,
            metadata={"agent_type": "travel_planner", "version": "1.0.0"},
        )

        # Register travel-specific tools
        self._register_travel_tools()

        # Register handoff and delegation tools for specialized agents
        self._register_specialized_agent_tools()

    def _register_travel_tools(self) -> None:
        """Register travel-specific tools."""
        # Register all travel tool groups
        tool_modules = [
            "calendar_tools",
            "time_tools",
            "webcrawl_tools",
            "flight_tools",
            "accommodations_tools",
            "weather_tools",
            "googlemaps_tools",
            "memory_tools",
        ]

        for module in tool_modules:
            self.register_tool_group(module)

    def _register_specialized_agent_tools(self) -> None:
        """Register specialized agent handoff and delegation tools."""
        # Configure handoff tools
        handoff_configs = {
            "hand_off_to_flight_agent": {
                "agent_class": FlightAgent,
                "description": (
                    "Hand off the conversation to a flight specialist agent for "
                    "detailed flight search, comparison and booking assistance. "
                    "Use this for complex flight queries."
                ),
                "context_filter": [
                    "user_id",
                    "session_id",
                    "session_data",
                    "handoff_data",
                ],
            },
            "hand_off_to_accommodation_agent": {
                "agent_class": AccommodationAgent,
                "description": (
                    "Hand off the conversation to an accommodation specialist agent "
                    "for detailed hotel and lodging search, comparison and booking. "
                    "Use this for complex accommodation queries."
                ),
                "context_filter": [
                    "user_id",
                    "session_id",
                    "session_data",
                    "handoff_data",
                ],
            },
            "hand_off_to_budget_agent": {
                "agent_class": BudgetAgent,
                "description": (
                    "Hand off the conversation to a budget specialist agent for "
                    "creating and optimizing travel budgets. Use this for detailed "
                    "budget planning."
                ),
                "context_filter": [
                    "user_id",
                    "session_id",
                    "session_data",
                    "handoff_data",
                ],
            },
            "hand_off_to_destination_agent": {
                "agent_class": DestinationResearchAgent,
                "description": (
                    "Hand off the conversation to a destination research specialist "
                    "for detailed destination information, attractions, and local "
                    "insights."
                ),
                "context_filter": [
                    "user_id",
                    "session_id",
                    "session_data",
                    "handoff_data",
                ],
            },
            "hand_off_to_itinerary_agent": {
                "agent_class": ItineraryAgent,
                "description": (
                    "Hand off the conversation to an itinerary specialist agent for "
                    "creating and managing detailed day-by-day travel itineraries."
                ),
                "context_filter": [
                    "user_id",
                    "session_id",
                    "session_data",
                    "handoff_data",
                ],
            },
        }

        # Configure delegation tools (used for specific tasks without
        # transferring control)
        delegation_configs = {
            "get_flight_options": {
                "agent_class": FlightAgent,
                "description": (
                    "Get flight options between locations without transferring the "
                    "conversation. The flight agent will return detailed flight "
                    "search results."
                ),
                "return_key": "content",
                "context_filter": ["user_id", "session_id", "session_data"],
            },
            "get_accommodation_options": {
                "agent_class": AccommodationAgent,
                "description": (
                    "Get accommodation options for a location without transferring "
                    "the conversation. The accommodation agent will return detailed "
                    "lodging search results."
                ),
                "return_key": "content",
                "context_filter": ["user_id", "session_id", "session_data"],
            },
            "calculate_trip_budget": {
                "agent_class": BudgetAgent,
                "description": (
                    "Calculate a trip budget without transferring the conversation. "
                    "The budget agent will analyze costs and return a budget "
                    "breakdown."
                ),
                "return_key": "content",
                "context_filter": ["user_id", "session_id", "session_data"],
            },
            "research_destination": {
                "agent_class": DestinationResearchAgent,
                "description": (
                    "Research a destination without transferring the conversation. "
                    "The destination agent will provide detailed information about "
                    "attractions, culture, and local tips."
                ),
                "return_key": "content",
                "context_filter": ["user_id", "session_id", "session_data"],
            },
            "create_trip_itinerary": {
                "agent_class": ItineraryAgent,
                "description": (
                    "Create a trip itinerary without transferring the conversation. "
                    "The itinerary agent will generate a structured day-by-day plan."
                ),
                "return_key": "content",
                "context_filter": ["user_id", "session_id", "session_data"],
            },
        }

        # Register both types of tools
        self.register_multiple_handoffs(handoff_configs)
        self.register_multiple_delegations(delegation_configs)

        logger.info("Registered specialized agent tools with Travel Agent")

    async def process_handoff_result(
        self, result: Dict[str, Any], context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process a result that contains a handoff to another agent.

        Args:
            result: Result from the agent run that contains a handoff
            context: Optional context to pass to the target agent

        Returns:
            Response from the target agent
        """
        if result.get("status") != "handoff":
            logger.warning("Called process_handoff_result on non-handoff result")
            return result

        # Extract handoff information
        handoff_target = result.get("handoff_target")
        handoff_tool = result.get("handoff_tool")

        if not handoff_target or not handoff_tool:
            logger.error("Missing handoff target or tool")
            return {
                "content": (
                    "There was an error processing your request. The handoff could "
                    "not be completed."
                ),
                "status": "error",
                "error_type": "HandoffError",
                "error_message": "Missing handoff target or tool information",
            }

        # Find the appropriate tool in handoff tools
        tool_info = self._handoff_tools.get(handoff_tool)
        if not tool_info:
            logger.error(f"Handoff tool {handoff_tool} not found")
            return {
                "content": (
                    "There was an error processing your request. The handoff could "
                    "not be completed."
                ),
                "status": "error",
                "error_type": "HandoffError",
                "error_message": f"Handoff tool {handoff_tool} not found",
            }

        # Extract the tool callable
        tool = tool_info.get("tool")
        if not callable(tool):
            logger.error(f"Handoff tool {handoff_tool} is not callable")
            return {
                "content": (
                    "There was an error processing your request. The handoff could "
                    "not be completed."
                ),
                "status": "error",
                "error_type": "HandoffError",
                "error_message": f"Handoff tool {handoff_tool} is not callable",
            }

        # Set up context for handoff
        handoff_context = context or {}
        handoff_context["is_handoff"] = True
        handoff_context["handoff_source"] = self.name

        # Add original content and tool calls to handoff data
        handoff_context["handoff_data"] = {
            "original_content": result.get("content", ""),
            "original_tool_calls": result.get("tool_calls", []),
            "source_agent": self.name,
            "handoff_tool": handoff_tool,
            "timestamp": time.time(),
        }

        # Set up query from tool calls if present
        if "tool_calls" in result and result["tool_calls"]:
            # Find the handoff tool call
            for tool_call in result["tool_calls"]:
                if tool_call.get("name") == handoff_tool:
                    # Use the arguments as the query base
                    query_components = []
                    for arg_name, arg_value in tool_call.get("arguments", {}).items():
                        if arg_name != "context":
                            query_components.append(f"{arg_name}: {arg_value}")

                    query = "\n".join(query_components)
                    if not query:
                        # If no arguments, use the original content
                        query = result.get("content", "")

                    # Call the handoff tool with the extracted query and context
                    try:
                        logger.info(
                            f"Executing handoff to {handoff_target} via {handoff_tool}"
                        )
                        handoff_result = await tool(
                            query=query, context=handoff_context
                        )
                        return handoff_result
                    except Exception as e:
                        logger.error(f"Error executing handoff: {str(e)}")
                        return {
                            "content": (
                                f"There was an error handling your request: {str(e)}"
                            ),
                            "status": "error",
                            "error_type": type(e).__name__,
                            "error_message": str(e),
                        }

        # If we couldn't extract a query from tool calls, use original content
        query = result.get("content", "")
        try:
            logger.info(
                f"Executing handoff to {handoff_target} via {handoff_tool} "
                f"with original content: {query}"
            )
            handoff_result = await tool(query=query, context=handoff_context)
            return handoff_result
        except Exception as e:
            logger.error(f"Error executing handoff: {str(e)}")
            return {
                "content": (f"There was an error handling your request: {str(e)}"),
                "status": "error",
                "error_type": type(e).__name__,
                "error_message": str(e),
            }
