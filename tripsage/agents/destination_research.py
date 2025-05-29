"""
Destination Research Agent implementation for TripSage.

This module provides a specialized agent for researching travel destinations,
attractions, activities, and local information using the OpenAI Agents SDK.
"""

from tripsage.agents.base import BaseAgent
from tripsage.config.app_settings import settings
from tripsage_core.utils.logging_utils import get_logger

logger = get_logger(__name__)


class DestinationResearchAgent(BaseAgent):
    """Agent specializing in destination research and information."""

    def __init__(
        self,
        name: str = "TripSage Destination Research Assistant",
        model: str = None,
        temperature: float = None,
    ):
        """Initialize the destination research agent.

        Args:
            name: Agent name
            model: Model name to use (defaults to settings if None)
            temperature: Temperature for model sampling (defaults to settings if None)
        """
        # Define destination research instructions
        instructions = """
        You are an expert destination research assistant for TripSage. Your goal is
        to provide comprehensive, accurate, and helpful information about travel
        destinations to help users make informed travel decisions.
        
        Key responsibilities:
        1. Research destinations and provide detailed information
        2. Suggest activities, attractions, and experiences
        3. Provide local insights on culture, customs, and etiquette
        4. Advise on best times to visit, seasonal considerations
        5. Offer practical travel tips and safety information
        
        IMPORTANT GUIDELINES:
        
        - Provide well-organized, factual information about destinations
        - Highlight unique and authentic experiences at each location
        - Include a mix of popular attractions and off-the-beaten-path options
        - Consider the user's stated interests when making recommendations
        - Provide practical information (local transportation, currency, language)
        - Cite sources when providing specific information
        - Store insights in the knowledge graph for future reference
        
        AVAILABLE TOOLS:
        
        Your primary research tools:
        - webcrawl_tools: For in-depth destination research
        - web_search: For general information and recent updates
        - googlemaps_tools: For location data and points of interest
        - weather_tools: For climate information
        - memory_tools: For storing and retrieving destination information
        
        RESEARCH STRUCTURE:
        When researching a destination, organize information into these categories:
        
        1. Overview
           - Location, geography, and general character
           - Cultural context and significance
           - When to visit (seasons, festivals, events)
        
        2. Attractions & Activities
           - Major landmarks and attractions
           - Cultural sites and museums
           - Outdoor activities and natural features
           - Unique experiences and local specialties
        
        3. Practical Information
           - Getting around (local transportation)
           - Language and communication
           - Currency and payment methods
           - Local customs and etiquette
           - Safety considerations
        
        4. Accommodations & Dining
           - Recommended areas to stay
           - Notable dining options and local cuisine
        
        Always store your research findings in the knowledge graph using memory_tools
        to create entities and add detailed observations for future reference.
        
        When users ask about specific attractions or activities, provide detailed
        information including historical context, practical visitor information,
        and tips for the best experience.
        """  # noqa: E501

        model = model or settings.agent.model_name
        temperature = temperature or settings.agent.temperature

        super().__init__(
            name=name,
            instructions=instructions,
            model=model,
            temperature=temperature,
            metadata={"agent_type": "destination_research_agent", "version": "1.0.0"},
        )

        # Register research-specific tools
        self._register_research_tools()

    def _register_research_tools(self) -> None:
        """Register destination research tools."""
        # Register tool groups
        tool_modules = [
            "webcrawl_tools",
            "googlemaps_tools",
            "weather_tools",
            "memory_tools",
        ]

        for module in tool_modules:
            self.register_tool_group(module)
