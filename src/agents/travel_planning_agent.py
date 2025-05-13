"""
Travel Planning Agent implementation for TripSage.

This module provides the TravelPlanningAgent implementation, which serves as the main
orchestrator for specialized travel agents, integrating various travel-specific
MCP tools and coordinating with specialized sub-agents.
"""

from agents import WebSearchTool
from agents.extensions.allowed_domains import AllowedDomains
from src.utils.config import get_config
from src.utils.logging import get_module_logger

from .base_agent import BaseAgent

logger = get_module_logger(__name__)
config = get_config()


class TravelPlanningAgent(BaseAgent):
    """Main travel planning orchestrator agent for TripSage."""

    def __init__(
        self,
        name: str = "TripSage Travel Planner",
        model: str = "gpt-4",
        temperature: float = 0.2,
    ):
        """Initialize the travel planning agent.

        Args:
            name: Agent name
            model: Model name to use
            temperature: Temperature for model sampling
        """
        # Define comprehensive instructions for the main orchestrator
        instructions = """
        You are the main travel planning orchestrator for TripSage. Your primary role
        is to coordinate travel planning across multiple specialized agents and tools
        to create comprehensive, personalized travel plans.

        As the main orchestrator, you:
        1. Understand high-level user requests and break them down into tasks
        2. Delegate specific tasks to specialized agents when appropriate
        3. Integrate information from various sources into coherent travel plans
        4. Maintain context and personalization across the planning process
        5. Ensure all aspects of travel planning are addressed

        HIERARCHICAL AGENT STRUCTURE:
        You can hand off specific tasks to specialized agents:
        - FlightAgent: For detailed flight search, comparison, and booking
        - AccommodationAgent: For finding and booking hotels, vacation rentals, etc.
        - DestinationResearchAgent: For in-depth research on destinations
        - ItineraryAgent: For creating and managing detailed travel itineraries
        - BudgetAgent: For budget optimization and cost monitoring

        WHEN TO DELEGATE:
        - Hand off to FlightAgent for complex flight searches with multiple criteria
        - Hand off to AccommodationAgent for detailed accommodation searches
        - Hand off to DestinationResearchAgent for thorough destination information
        - Hand off to ItineraryAgent for detailed day-by-day planning
        - Hand off to BudgetAgent for budget optimization and allocation

        WHEN TO HANDLE DIRECTLY:
        - Initial user requirement gathering
        - Simple queries that don't require specialized knowledge
        - Integration of information from multiple domains
        - High-level planning and recommendations
        - Follow-up questions about previous recommendations

        TOOL SELECTION GUIDELINES:
        - Use WebSearchTool for general travel information
        - Use specialized MCP tools for specific data (flights, weather, etc.)
        - Use memory operations to maintain context between planning sessions

        MEMORY MANAGEMENT:
        Always use the knowledge graph to:
        - Store user preferences for personalization
        - Record trip details for future reference
        - Create relationships between travel entities
        - Build a comprehensive view of the user's travel history and preferences

        IMPORTANT COORDINATION GUIDELINES:
        - Clearly summarize information received from specialized agents
        - Integrate specialized agent outputs into cohesive travel plans
        - Maintain consistent tone and style across the planning experience
        - Ensure handoffs to specialized agents include relevant context
        - Verify information from multiple sources when appropriate
        """

        super().__init__(
            name=name,
            instructions=instructions,
            model=model,
            temperature=temperature,
            metadata={"agent_type": "travel_planning_orchestrator", "version": "1.0.0"},
        )

        # Initialize handoffs to specialized agents
        self._register_agent_handoffs()

        # Add WebSearchTool with travel-specific domain focus
        self._add_websearch_tool()

        # Register travel planning tools
        self._register_planning_tools()

        # Register MCP client tools
        self._register_mcp_clients()

    def _register_agent_handoffs(self) -> None:
        """Register handoffs to specialized agents."""
        # Import specialized agents
        from .accommodation_agent import create_accommodation_agent_handoff
        from .budget_agent import create_budget_agent_handoff
        from .destination_research_agent import (
            create_destination_research_agent_handoff,
        )
        from .flight_agent import create_flight_agent_handoff
        from .itinerary_agent import create_itinerary_agent_handoff

        # Register handoffs
        self._handoffs.append(create_flight_agent_handoff())
        self._handoffs.append(create_accommodation_agent_handoff())
        self._handoffs.append(create_destination_research_agent_handoff())
        self._handoffs.append(create_budget_agent_handoff())
        self._handoffs.append(create_itinerary_agent_handoff())

        # Update agent instance with handoffs
        self.agent.handoffs = self._handoffs

        logger.info("Registered specialized agent handoffs")

    def _add_websearch_tool(self) -> None:
        """Add WebSearchTool with travel-specific domain focus."""
        # Configure WebSearchTool with travel-focused domains
        self.web_search_tool = WebSearchTool(
            allowed_domains=AllowedDomains(
                domains=[
                    # Travel information and guides
                    "tripadvisor.com",
                    "lonelyplanet.com",
                    "wikitravel.org",
                    "travel.state.gov",
                    "wikivoyage.org",
                    "frommers.com",
                    "roughguides.com",
                    "fodors.com",
                    # Flight and transportation
                    "kayak.com",
                    "skyscanner.com",
                    "expedia.com",
                    "booking.com",
                    "hotels.com",
                    "airbnb.com",
                    "vrbo.com",
                    "orbitz.com",
                    # Airlines
                    "united.com",
                    "aa.com",
                    "delta.com",
                    "southwest.com",
                    "britishairways.com",
                    "lufthansa.com",
                    "emirates.com",
                    "cathaypacific.com",
                    "qantas.com",
                    # Weather and climate
                    "weather.com",
                    "accuweather.com",
                    "weatherspark.com",
                    "climate.gov",
                    # Government travel advisories
                    "travel.state.gov",
                    "smartraveller.gov.au",
                    "gov.uk/foreign-travel-advice",
                    # Social and review sites
                    "tripadvisor.com",
                    "yelp.com",
                ]
            ),
            # Block content farms and untrustworthy sources
            blocked_domains=["pinterest.com", "quora.com"],
        )
        self.agent.tools.append(self.web_search_tool)
        logger.info(
            "Added WebSearchTool to TravelPlanningAgent with travel-specific "
            "domain configuration"
        )

    def _register_planning_tools(self) -> None:
        """Register travel planning specific tools."""
        # Import planning tools
        try:
            from .planning_tools import (
                combine_search_results,
                create_travel_plan,
                generate_travel_summary,
                save_travel_plan,
                update_travel_plan,
            )

            # Register planning tools
            self._register_tool(create_travel_plan)
            self._register_tool(update_travel_plan)
            self._register_tool(combine_search_results)
            self._register_tool(generate_travel_summary)
            self._register_tool(save_travel_plan)

            logger.info("Registered travel planning tools")
        except ImportError as e:
            logger.warning(f"Could not register planning tools: {str(e)}")

    def _register_mcp_clients(self) -> None:
        """Register all available MCP clients with the agent."""
        # Weather MCP Client
        try:
            from ..mcp.weather import get_client as get_weather_client

            weather_client = get_weather_client()
            self._register_mcp_client_tools(weather_client, prefix="weather_")
            logger.info("Registered Weather MCP client tools")
        except Exception as e:
            logger.warning("Failed to register Weather MCP client: %s", str(e))

        # Time MCP Client
        try:
            from ..mcp.time import get_client as get_time_client

            time_client = get_time_client()
            self._register_mcp_client_tools(time_client, prefix="time_")
            logger.info("Registered Time MCP client tools")
        except Exception as e:
            logger.warning("Failed to register Time MCP client: %s", str(e))

        # Google Maps MCP Client
        try:
            from ..mcp.googlemaps import get_client as get_maps_client

            maps_client = get_maps_client()
            self._register_mcp_client_tools(maps_client, prefix="maps_")
            logger.info("Registered Google Maps MCP client tools")
        except Exception as e:
            logger.warning("Failed to register Google Maps MCP client: %s", str(e))

        # Memory MCP Client (for knowledge graph)
        try:
            from ..mcp.memory import get_client as get_memory_client

            memory_client = get_memory_client()
            self._register_mcp_client_tools(memory_client, prefix="memory_")
            logger.info("Registered Memory MCP client tools")
        except Exception as e:
            logger.warning("Failed to register Memory MCP client: %s", str(e))

        # WebCrawl MCP Client
        try:
            from ..mcp.webcrawl import get_client as get_webcrawl_client

            webcrawl_client = get_webcrawl_client()
            self._register_mcp_client_tools(webcrawl_client, prefix="webcrawl_")
            logger.info("Registered WebCrawl MCP client tools")
        except Exception as e:
            logger.warning("Failed to register WebCrawl MCP client: %s", str(e))


def create_agent() -> TravelPlanningAgent:
    """Create and return a fully initialized TravelPlanningAgent instance.

    Creates a new TravelPlanningAgent with all tools registered and ready for use.

    Returns:
        An initialized TravelPlanningAgent
    """
    agent = TravelPlanningAgent()
    logger.info(
        "Created TripSage Travel Planning Agent instance with all tools registered"
    )
    return agent
