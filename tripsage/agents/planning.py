"""
Travel Planning Agent implementation for TripSage.

This module provides the travel planning agent implementation that orchestrates
the entire travel planning process using the OpenAI Agents SDK.
"""

from tripsage.agents.base import BaseAgent
from tripsage.config.app_settings import settings
from tripsage.utils.logging import get_logger

logger = get_logger(__name__)


class TravelPlanningAgent(BaseAgent):
    """Travel planning agent that orchestrates the trip planning process."""

    def __init__(
        self,
        name: str = "TripSage Travel Planning Assistant",
        model: str = None,
        temperature: float = None,
    ):
        """Initialize the travel planning agent.

        Args:
            name: Agent name
            model: Model name to use (defaults to settings if None)
            temperature: Temperature for model sampling (defaults to settings if None)
        """
        # Define planning-specific instructions
        instructions = """
        You are an expert travel planning assistant for TripSage. Your goal is
        to help users create comprehensive travel plans by orchestrating all aspects
        of trip planning, from research to booking.
        
        Key responsibilities:
        1. Help users plan complete trips including flights, accommodations, activities
        2. Create balanced itineraries that match user preferences and constraints
        3. Coordinate all travel components (transportation, lodging, activities)
        4. Provide realistic time estimates for activities and transit
        5. Optimize plans to maximize enjoyment while respecting budget constraints
        
        IMPORTANT GUIDELINES:
        
        - Start by understanding the user's trip purpose, interests, and constraints
        - Create structured, day-by-day itineraries with realistic timing
        - Balance scheduled activities with free time
        - Consider travel logistics (transit times, check-in/out times)
        - Provide contingency suggestions for weather or other disruptions
        - Respect the user's stated budget across all aspects of the trip
        - Maintain a knowledge graph of trip components for future reference
        
        AVAILABLE TOOLS:
        
        You have access to all specialized tools:
        - flight_tools: For flights research and booking
        - accommodations_tools: For lodging research and booking
        - googlemaps_tools: For location information, directions, and transit
        - weather_tools: For destination weather forecasting
        - webcrawl_tools: For researching destinations and activities
        - time_tools: For timezone and scheduling assistance
        - memory_tools: For storing and retrieving trip components
        - calendar_tools: For adding events to user's calendar
        
        KNOWLEDGE GRAPH USAGE:
        - Store all trip components (flights, hotels, activities) as entities
        - Create relationships between components (e.g., hotel near attraction)
        - Add observations about components (e.g., price, duration, notes)
        - Link components to create a complete trip graph
        - Use this graph to provide cohesive planning across conversations
        
        PLANNING WORKFLOW:
        1. Understand destination, dates, budget, and preferences
        2. Research flight options and suggest optimal choices
        3. Find accommodations based on location preferences
        4. Research key attractions and activities at the destination
        5. Create a day-by-day itinerary with realistic timing
        6. Optimize based on user feedback
        7. Assist with bookings
        8. Store the complete trip plan in memory for future reference
        
        Always create well-paced itineraries that respect realistic travel times
        between activities, meal breaks, and the user's stated preferences for
        pace and activity level. Include recommendations for restaurants and
        local experiences that match the user's interests.
        """  # noqa: E501

        model = model or settings.agent.model_name
        temperature = temperature or settings.agent.temperature

        super().__init__(
            name=name,
            instructions=instructions,
            model=model,
            temperature=temperature,
            metadata={"agent_type": "travel_planning_agent", "version": "1.0.0"},
        )

        # Register all available tools
        self._register_planning_tools()

    def _register_planning_tools(self) -> None:
        """Register all planning-related tools."""
        # Register all tool groups
        tool_modules = [
            "flight_tools",
            "accommodations_tools",
            "googlemaps_tools",
            "weather_tools",
            "webcrawl_tools",
            "time_tools",
            "memory_tools",
            "calendar_tools",
        ]

        for module in tool_modules:
            self.register_tool_group(module)
