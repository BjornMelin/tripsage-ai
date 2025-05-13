"""
Accommodation Agent implementation for TripSage.

This module provides a specialized AccommodationAgent for accommodation
search and booking, leveraging accommodation MCP tools and integrating with
the OpenAI Agents SDK.
"""

from agents import RunContextWrapper, handoff
from src.utils.config import get_config
from src.utils.logging import get_module_logger

from .base_agent import BaseAgent

logger = get_module_logger(__name__)
config = get_config()


class AccommodationAgent(BaseAgent):
    """Specialized agent for accommodation search and booking."""

    def __init__(
        self,
        name: str = "TripSage Accommodation Specialist",
        model: str = "gpt-4",
        temperature: float = 0.2,
    ):
        """Initialize the accommodation agent.

        Args:
            name: Agent name
            model: Model name to use
            temperature: Temperature for model sampling
        """
        # Define specialized instructions
        instructions = """
        You are a specialized accommodation search and booking agent for TripSage.
        Your goal is to help users find and book the optimal accommodations for
        their travel needs, taking into account their preferences, constraints,
        and budget.

        Key responsibilities:
        1. Search for accommodations using detailed criteria
        2. Compare accommodation options across multiple dimensions
        3. Provide insights on pricing, location, and amenities
        4. Help with accommodation booking and reservation management
        5. Save accommodation details in the knowledge graph for future reference

        IMPORTANT GUIDELINES:

        - Ask clarifying questions when user accommodation requirements are ambiguous
        - Present accommodation options in a clear, tabular format with key information
        - Highlight important factors like location, amenities, and price
        - Explain why certain accommodations are recommended
        - When presenting prices, include all taxes and fees for transparency
        - Consider location proximity to attractions or transportation
        - Save selected accommodation details in the knowledge graph for future
          reference

        ACCOMMODATION DATA ANALYSIS:
        - Explain price differences between similar accommodations
        - Compare various property types (hotels, vacation rentals, etc.)
        - Highlight options with significant value
        - Consider location and proximity factors
        - Analyze reviews and ratings for quality assessment

        TOOL USAGE:
        - Use Accommodations MCP for detailed accommodation search
        - Use Google Maps MCP for location analysis
        - Use Memory MCP to store accommodation preferences and selections
        
        When returning results to the main TravelPlanningAgent, always:
        1. Summarize the top options clearly
        2. Include the reasoning behind your recommendations
        3. Provide the exact accommodation details that can be used for booking
        4. Include location insights when relevant
        """

        super().__init__(
            name=name,
            instructions=instructions,
            model=model,
            temperature=temperature,
            metadata={"agent_type": "accommodation_specialist", "version": "1.0.0"},
        )

        # Register accommodation-specific tools
        self._register_accommodation_tools()

        # Register MCP client tools
        self._register_accommodation_mcp_client()

    def _register_accommodation_tools(self) -> None:
        """Register accommodation-specific tools."""
        # This would be implemented to register accommodation tools
        pass

    def _register_accommodation_mcp_client(self) -> None:
        """Register accommodation MCP client tools."""
        try:
            from ..mcp.accommodations import get_client as get_accommodations_client

            accommodations_client = get_accommodations_client()
            self._register_mcp_client_tools(
                accommodations_client, prefix="accommodations_"
            )
            logger.info("Registered Accommodations MCP client tools")
        except Exception as e:
            logger.warning("Failed to register Accommodations MCP client: %s", str(e))


def create_accommodation_agent() -> AccommodationAgent:
    """Create and return a fully initialized AccommodationAgent instance.

    Returns:
        An initialized AccommodationAgent
    """
    agent = AccommodationAgent()
    logger.info("Created Accommodation Agent instance with all tools registered")
    return agent


def create_accommodation_agent_handoff():
    """Create a handoff to the Accommodation Agent.

    Returns:
        A handoff function to be used by the TravelPlanningAgent
    """
    accommodation_agent = create_accommodation_agent()

    async def on_accommodation_handoff(ctx: RunContextWrapper[None], input_data: str):
        """Handle accommodation agent handoff.

        Args:
            ctx: Context wrapper
            input_data: Input data
        """
        logger.info("Handing off to Accommodation Agent")
        # Pass any context data needed by the Accommodation Agent
        if hasattr(ctx, "session_data"):
            ctx.session_data["source_agent"] = "TravelPlanningAgent"

    return handoff(agent=accommodation_agent, on_handoff=on_accommodation_handoff)
