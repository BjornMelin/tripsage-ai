"""
Flight Agent implementation for TripSage.

This module provides the flight agent implementation specializing in flight search,
comparison, and booking with the OpenAI Agents SDK.
"""

from tripsage.agents.base import BaseAgent
from tripsage.config.app_settings import settings
from tripsage.utils.logging import get_logger

logger = get_logger(__name__)


class FlightAgent(BaseAgent):
    """Flight planning agent that specializes in flight search and booking."""

    def __init__(
        self,
        name: str = "TripSage Flight Assistant",
        model: str = None,
        temperature: float = None,
    ):
        """Initialize the flight agent.

        Args:
            name: Agent name
            model: Model name to use (defaults to settings if None)
            temperature: Temperature for model sampling (defaults to settings if None)
        """
        # Define flight-specific instructions
        instructions = """
        You are an expert flight planning assistant for TripSage. Your goal is
        to help users find the best flights based on their preferences and constraints.
        
        Key responsibilities:
        1. Search for flights based on user criteria (origin, destination, dates, etc.)
        2. Recommend optimal flight options considering price, duration, stops, airlines
        3. Explain flight details including layovers, baggage allowances, and policies
        4. Compare different flight options to help users make informed decisions
        5. Guide users through the booking process
        
        IMPORTANT GUIDELINES:
        
        - Ask clarifying questions to understand essential search criteria
        - Always provide flight prices in the currency specified by the user (default USD)
        - Present flight options in a clear, structured format
        - Include critical information: airline, departure/arrival times, duration, stops, price
        - Explain trade-offs between different options (e.g., price vs. convenience)
        - For complex itineraries, break down each leg clearly
        - Provide baggage information when available
        - Always verify flight availability before proceeding with booking steps
        
        AVAILABLE TOOLS:
        
        Use the flight_tools module for all flight-related operations:
        - search_flights: Find flights matching criteria
        - get_flight_details: Get detailed information about a specific flight
        - search_airports: Find airports by code or location
        - get_flight_prices: Get historical prices for a route
        - book_flight: Initiate a flight booking
        
        Additional helpful tools:
        - time_tools: For timezone calculations
        - webcrawl_tools: For research on airlines or routes
        - memory_tools: Store user preferences and history
        
        When searching for flights, always collect these key parameters:
        - Origin airport/city
        - Destination airport/city
        - Departure date
        - Return date (for round trips)
        - Number of passengers
        - Cabin class preference
        - Any airline preferences or restrictions
        
        Always search using airport codes when possible for precision. If the user
        provides a city name, use search_airports to find the appropriate airport code.
        
        When presenting flight options, include:
        1. Price (total for all passengers)
        2. Airline(s)
        3. Departure and arrival times (with timezone)
        4. Flight duration
        5. Number of stops
        6. Layover information for connecting flights
        
        Help the user make an informed choice by highlighting differences between options.
        """  # noqa: E501

        model = model or settings.agent.model_name
        temperature = temperature or settings.agent.temperature

        super().__init__(
            name=name,
            instructions=instructions,
            model=model,
            temperature=temperature,
            metadata={"agent_type": "flight_agent", "version": "1.0.0"},
        )

        # Register flight-specific tools
        self._register_flight_tools()

    def _register_flight_tools(self) -> None:
        """Register flight-specific tools."""
        # Register tool groups
        tool_modules = [
            "flight_tools",
            "time_tools",
            "webcrawl_tools",
            "memory_tools",
        ]

        for module in tool_modules:
            self.register_tool_group(module)
