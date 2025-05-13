"""
Travel Agent implementation for TripSage.

This module provides the travel agent implementation which specializes in
travel planning, flight booking, accommodation search, and destination research.
"""

from tripsage.agents.base_agent import BaseAgent
from tripsage.utils.logging import get_module_logger

logger = get_module_logger(__name__)


class TravelAgent(BaseAgent):
    """Travel planning agent that integrates with travel-specific MCP tools."""

    def __init__(
        self,
        name: str = "TripSage Travel Planner",
        model: str = "gpt-4o",
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
        # Register all travel tool groups
        tool_modules = [
            "calendar",
            "time",
            "webcrawl",
        ]

        for module in tool_modules:
            self.register_tool_group(module)
