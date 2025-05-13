"""
Itinerary Agent implementation for TripSage.

This module provides a specialized ItineraryAgent for creating and managing detailed
travel itineraries, integrating with the OpenAI Agents SDK.
"""

from typing import Any, Dict

from agents import RunContextWrapper, function_tool, handoff
from src.utils.config import get_config
from src.utils.logging import get_module_logger

from .base_agent import BaseAgent

logger = get_module_logger(__name__)
config = get_config()


class ItineraryAgent(BaseAgent):
    """Specialized agent for creating and managing travel itineraries."""

    def __init__(
        self,
        name: str = "TripSage Itinerary Specialist",
        model: str = "gpt-4",
        temperature: float = 0.2,
    ):
        """Initialize the itinerary agent.

        Args:
            name: Agent name
            model: Model name to use
            temperature: Temperature for model sampling
        """
        # Define specialized instructions
        instructions = """
        You are a specialized itinerary planning agent for TripSage. Your goal is
        to create detailed, personalized travel itineraries that maximize travelers'
        experiences while respecting their constraints and preferences.

        Key responsibilities:
        1. Create day-by-day itineraries for travel plans
        2. Optimize timing and logistics between activities and locations
        3. Balance sightseeing, activities, and relaxation time
        4. Consider travel time, opening hours, and logical visit sequences
        5. Save itinerary details in the knowledge graph for future reference

        IMPORTANT GUIDELINES:

        - Create realistic itineraries that account for travel time between locations
        - Consider opening hours, crowds, and optimal visit times for attractions
        - Allow sufficient meal and rest breaks in the schedule
        - Group nearby attractions and activities efficiently
        - Adapt plans to weather conditions and seasonal factors
        - Include specific timing for each activity to help with planning
        - Provide logical transportation modes between locations
        - Save itinerary details in the knowledge graph with time information

        ITINERARY PLANNING APPROACH:
        - Start with major attractions and must-see sights
        - Group activities by geographical proximity
        - Consider the nature of activities (e.g., museums in morning, relaxation in afternoon)
        - Build in flexibility for weather changes or unexpected events
        - Include recommended meal locations or options
        - Consider local transportation options and travel times

        TOOL USAGE:
        - Use Google Maps MCP for location analysis and travel times
        - Use Calendar MCP for scheduling and time management
        - Use Memory MCP to store itinerary details for future reference
        - Use Time MCP for timezone management and local time information
        
        When returning results to the main TravelPlanningAgent, always:
        1. Present the itinerary in a clear day-by-day, time-specific format
        2. Include transportation information between locations
        3. Provide estimated durations for activities and visits
        4. Include notes about opening hours, reservations, or special considerations
        """

        super().__init__(
            name=name,
            instructions=instructions,
            model=model,
            temperature=temperature,
            metadata={"agent_type": "itinerary_specialist", "version": "1.0.0"},
        )

        # Register itinerary-specific tools
        self._register_itinerary_tools()

        # Register MCP client tools
        self._register_itinerary_mcp_clients()

    def _register_itinerary_tools(self) -> None:
        """Register itinerary-specific tools."""
        # Register core itinerary tools
        self._register_tool(self.create_daily_itinerary)
        self._register_tool(self.optimize_itinerary)
        self._register_tool(self.add_activity_to_itinerary)
        self._register_tool(self.remove_activity_from_itinerary)
        self._register_tool(self.calculate_travel_times)
        self._register_tool(self.create_calendar_events)

    def _register_itinerary_mcp_clients(self) -> None:
        """Register MCP client tools for itinerary management."""
        # Google Maps MCP Client
        try:
            from ..mcp.googlemaps import get_client as get_maps_client

            maps_client = get_maps_client()
            self._register_mcp_client_tools(maps_client, prefix="maps_")
            logger.info("Registered Google Maps MCP client tools")
        except Exception as e:
            logger.warning("Failed to register Google Maps MCP client: %s", str(e))

        # Calendar MCP Client
        try:
            from ..mcp.calendar import get_client as get_calendar_client

            calendar_client = get_calendar_client()
            self._register_mcp_client_tools(calendar_client, prefix="calendar_")
            logger.info("Registered Calendar MCP client tools")
        except Exception as e:
            logger.warning("Failed to register Calendar MCP client: %s", str(e))

        # Time MCP Client
        try:
            from ..mcp.time import get_client as get_time_client

            time_client = get_time_client()
            self._register_mcp_client_tools(time_client, prefix="time_")
            logger.info("Registered Time MCP client tools")
        except Exception as e:
            logger.warning("Failed to register Time MCP client: %s", str(e))

        # Memory MCP Client
        try:
            from ..mcp.memory import get_client as get_memory_client

            memory_client = get_memory_client()
            self._register_mcp_client_tools(memory_client, prefix="memory_")
            logger.info("Registered Memory MCP client tools")
        except Exception as e:
            logger.warning("Failed to register Memory MCP client: %s", str(e))

    @function_tool
    async def create_daily_itinerary(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create a detailed day-by-day itinerary for a trip.

        Plans a detailed itinerary with specific times, locations, and activities,
        optimized for an efficient and enjoyable experience.

        Args:
            params: Itinerary creation parameters including:
                trip_id: Trip ID
                start_date: Start date of the trip (YYYY-MM-DD)
                end_date: End date of the trip (YYYY-MM-DD)
                destination: Destination name or list of destinations
                activities: List of preferred activities or attractions
                pace: Preferred pace (relaxed, moderate, busy)
                preferences: Dictionary of traveler preferences
                transportation: Preferred transportation modes

        Returns:
            Dictionary with the created itinerary
        """
        # This would be implemented with actual itinerary creation logic
        # For now, we just return a placeholder response
        trip_id = params.get("trip_id", "")
        start_date = params.get("start_date", "")
        end_date = params.get("end_date", "")
        destination = params.get("destination", "")

        # Simple placeholder response
        return {
            "trip_id": trip_id,
            "destination": destination,
            "dates": f"{start_date} to {end_date}",
            "message": "Daily itinerary creation functionality will be implemented",
        }

    @function_tool
    async def optimize_itinerary(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize an existing itinerary for efficiency and enjoyment.

        Analyzes and reorganizes an existing itinerary to improve flow, reduce
        transit time, and enhance the overall experience.

        Args:
            params: Optimization parameters including:
                itinerary_id: ID of the itinerary to optimize
                optimization_goals: List of optimization priorities
                constraints: Any specific constraints to respect

        Returns:
            Dictionary with the optimized itinerary
        """
        # This would be implemented with actual itinerary optimization logic
        # For now, we just return a placeholder response
        itinerary_id = params.get("itinerary_id", "")

        # Simple placeholder response
        return {
            "itinerary_id": itinerary_id,
            "message": "Itinerary optimization functionality will be implemented",
        }

    @function_tool
    async def add_activity_to_itinerary(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Add a new activity to an existing itinerary.

        Intelligently adds a new activity to an itinerary, adjusting times and
        other activities as needed to maintain a logical flow.

        Args:
            params: Activity addition parameters including:
                itinerary_id: ID of the itinerary
                activity: Activity details to add
                day: Day to add the activity (date or day number)
                time: Preferred time for the activity
                duration: Expected duration of the activity

        Returns:
            Dictionary with the updated itinerary
        """
        # This would be implemented with actual activity addition logic
        # For now, we just return a placeholder response
        itinerary_id = params.get("itinerary_id", "")
        activity = params.get("activity", {})

        # Simple placeholder response
        return {
            "itinerary_id": itinerary_id,
            "activity": activity,
            "message": "Activity addition functionality will be implemented",
        }

    @function_tool
    async def remove_activity_from_itinerary(
        self, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Remove an activity from an existing itinerary.

        Removes an activity and rebalances the itinerary to maintain a logical flow.

        Args:
            params: Activity removal parameters including:
                itinerary_id: ID of the itinerary
                activity_id: ID of the activity to remove
                rebalance: Whether to rebalance the remaining activities

        Returns:
            Dictionary with the updated itinerary
        """
        # This would be implemented with actual activity removal logic
        # For now, we just return a placeholder response
        itinerary_id = params.get("itinerary_id", "")
        activity_id = params.get("activity_id", "")

        # Simple placeholder response
        return {
            "itinerary_id": itinerary_id,
            "activity_id": activity_id,
            "message": "Activity removal functionality will be implemented",
        }

    @function_tool
    async def calculate_travel_times(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate travel times between locations in an itinerary.

        Determines realistic travel times between locations in an itinerary using
        various transportation modes.

        Args:
            params: Travel time calculation parameters including:
                origin: Origin location
                destination: Destination location
                transportation_mode: Transportation mode (walking, driving, transit, etc.)
                departure_time: Optional departure time

        Returns:
            Dictionary with calculated travel times
        """
        # This would be implemented with actual travel time calculation logic
        # For now, we just return a placeholder response
        origin = params.get("origin", "")
        destination = params.get("destination", "")
        transportation_mode = params.get("transportation_mode", "driving")

        # Simple placeholder response
        return {
            "origin": origin,
            "destination": destination,
            "transportation_mode": transportation_mode,
            "estimated_time_minutes": 30,  # Placeholder value
            "message": "Travel time calculation functionality will be implemented",
        }

    @function_tool
    async def create_calendar_events(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create calendar events from an itinerary.

        Converts an itinerary into calendar events that can be added to a user's
        calendar for easy reference during the trip.

        Args:
            params: Calendar creation parameters including:
                itinerary_id: ID of the itinerary
                calendar_id: ID of the target calendar
                user_id: User ID
                include_details: Whether to include detailed descriptions

        Returns:
            Dictionary with created calendar events
        """
        # This would be implemented with actual calendar event creation logic
        # For now, we just return a placeholder response
        itinerary_id = params.get("itinerary_id", "")
        calendar_id = params.get("calendar_id", "")

        # Simple placeholder response
        return {
            "itinerary_id": itinerary_id,
            "calendar_id": calendar_id,
            "message": "Calendar event creation functionality will be implemented",
        }


def create_itinerary_agent() -> ItineraryAgent:
    """Create and return a fully initialized ItineraryAgent instance.

    Returns:
        An initialized ItineraryAgent
    """
    agent = ItineraryAgent()
    logger.info("Created Itinerary Agent instance with all tools registered")
    return agent


def create_itinerary_agent_handoff():
    """Create a handoff to the Itinerary Agent.

    Returns:
        A handoff function to be used by the TravelPlanningAgent
    """
    itinerary_agent = create_itinerary_agent()

    async def on_itinerary_handoff(ctx: RunContextWrapper[None], input_data: str):
        """Handle itinerary agent handoff.

        Args:
            ctx: Context wrapper
            input_data: Input data
        """
        logger.info("Handing off to Itinerary Agent")
        # Pass any context data needed by the Itinerary Agent
        if hasattr(ctx, "session_data"):
            ctx.session_data["source_agent"] = "TravelPlanningAgent"

    return handoff(agent=itinerary_agent, on_handoff=on_itinerary_handoff)
