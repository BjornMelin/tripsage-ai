"""
Destination Research Agent implementation for TripSage.

This module provides a specialized DestinationResearchAgent for researching travel
destinations, leveraging webcrawl and maps MCP tools and integrating with the
OpenAI Agents SDK.
"""

from agents import RunContextWrapper, WebSearchTool, handoff
from src.utils.config import get_config
from src.utils.logging import get_module_logger

from .base_agent import BaseAgent

logger = get_module_logger(__name__)
config = get_config()


class DestinationResearchAgent(BaseAgent):
    """Specialized agent for destination research."""

    def __init__(
        self,
        name: str = "TripSage Destination Research Specialist",
        model: str = "gpt-4",
        temperature: float = 0.2,
    ):
        """Initialize the destination research agent.

        Args:
            name: Agent name
            model: Model name to use
            temperature: Temperature for model sampling
        """
        # Define specialized instructions
        instructions = """
        You are a specialized destination research agent for TripSage. Your goal is
        to provide comprehensive, accurate, and up-to-date information about travel
        destinations to help users make informed travel decisions.

        Key responsibilities:
        1. Research destinations in depth using web search and specialized tools
        2. Provide information on attractions, culture, local customs,
            and practical details
        3. Find destination-specific events and seasonal information
        4. Research safety, health, and entry requirements for destinations
        5. Save destination information in the knowledge graph for future reference

        IMPORTANT GUIDELINES:

        - Provide well-structured, comprehensive information about destinations
        - Prioritize official sources and reputable travel sites for information
        - Include practical information (currency, language, transportation) 
        - Research both popular attractions and hidden gems
        - Include seasonal information and best times to visit
        - Check for current travel advisories, visa requirements, and health concerns
        - Save researched destination information in the knowledge graph

        RESEARCH APPROACH:
        - Use web search as the primary research tool
        - Use webcrawl for more in-depth information from specialized sites
        - Use maps for location-specific data and spatial relationships
        - Look for information from multiple sources to ensure accuracy
        - Focus on recent information for time-sensitive details

        TOOL USAGE:
        - Use WebSearchTool for general destination information
        - Use WebCrawl MCP for deep research on specific topics
        - Use Google Maps MCP for location analysis and spatial information
        - Use Memory MCP to store destination information for future reference
        
        When returning results to the main TravelPlanningAgent, always:
        1. Organize information in clear categories (attractions, practical info, etc.)
        2. Highlight the most important or distinctive aspects of the destination
        3. Include any time-sensitive information that might affect travel plans
        4. Provide source references for key information
        """

        super().__init__(
            name=name,
            instructions=instructions,
            model=model,
            temperature=temperature,
            metadata={
                "agent_type": "destination_research_specialist",
                "version": "1.0.0",
            },
        )

        # Add WebSearchTool specialized for destination research
        self._add_websearch_tool()

        # Register destination research-specific tools
        self._register_research_tools()

        # Register MCP client tools
        self._register_research_mcp_clients()

    def _add_websearch_tool(self) -> None:
        """Add WebSearchTool with destination research focus."""
        # Configure WebSearchTool with travel guide domains
        self.web_search_tool = WebSearchTool(
            allowed_domains=[
                # Travel guides
                "lonelyplanet.com",
                "wikitravel.org",
                "wikivoyage.org",
                "frommers.com",
                "roughguides.com",
                "fodors.com",
                "tripadvisor.com",
                # Government travel sites
                "travel.state.gov",
                "gov.uk/foreign-travel-advice",
                "smartraveller.gov.au",
                # Weather and climate
                "weatherspark.com",
                "accuweather.com",
                "weather.com",
                # Local tourism boards
                "visitcalifornia.com",
                "visitlondon.com",
                "australia.com",
                "france.fr",
                "germany.travel",
                "visitjapan.jp",
                # Travel blogs
                "nomadicmatt.com",
                "thepointsguy.com",
                "worldnomads.com",
            ],
            # Block unhelpful content
            blocked_domains=["pinterest.com", "quora.com"],
        )
        self.agent.tools.append(self.web_search_tool)
        logger.info("Added WebSearchTool to DestinationResearchAgent")

    def _register_research_tools(self) -> None:
        """Register destination research-specific tools."""
        # This would be implemented to register research tools
        pass

    def _register_research_mcp_clients(self) -> None:
        """Register MCP client tools for destination research."""
        # WebCrawl MCP Client
        try:
            from ..mcp.webcrawl import get_client as get_webcrawl_client

            webcrawl_client = get_webcrawl_client()
            self._register_mcp_client_tools(webcrawl_client, prefix="webcrawl_")
            logger.info("Registered WebCrawl MCP client tools")
        except Exception as e:
            logger.warning("Failed to register WebCrawl MCP client: %s", str(e))

        # Google Maps MCP Client
        try:
            from ..mcp.googlemaps import get_client as get_maps_client

            maps_client = get_maps_client()
            self._register_mcp_client_tools(maps_client, prefix="maps_")
            logger.info("Registered Google Maps MCP client tools")
        except Exception as e:
            logger.warning("Failed to register Google Maps MCP client: %s", str(e))

        # Memory MCP Client
        try:
            from ..mcp.memory import get_client as get_memory_client

            memory_client = get_memory_client()
            self._register_mcp_client_tools(memory_client, prefix="memory_")
            logger.info("Registered Memory MCP client tools")
        except Exception as e:
            logger.warning("Failed to register Memory MCP client: %s", str(e))


def create_destination_research_agent() -> DestinationResearchAgent:
    """Create and return a fully initialized DestinationResearchAgent instance.

    Returns:
        An initialized DestinationResearchAgent
    """
    agent = DestinationResearchAgent()
    logger.info("Created Destination Research Agent instance")
    return agent


def create_destination_research_agent_handoff():
    """Create a handoff to the Destination Research Agent.

    Returns:
        A handoff function to be used by the TravelPlanningAgent
    """
    research_agent = create_destination_research_agent()

    async def on_research_handoff(ctx: RunContextWrapper[None], input_data: str):
        """Handle destination research agent handoff.

        Args:
            ctx: Context wrapper
            input_data: Input data
        """
        logger.info("Handing off to Destination Research Agent")
        # Pass any context data needed by the Research Agent
        if hasattr(ctx, "session_data"):
            ctx.session_data["source_agent"] = "TravelPlanningAgent"

    return handoff(agent=research_agent, on_handoff=on_research_handoff)
