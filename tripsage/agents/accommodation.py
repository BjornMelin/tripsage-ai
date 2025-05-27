"""
Accommodation Agent implementation for TripSage.

This module provides the accommodation agent implementation specializing in
hotel, rental and Airbnb search and booking with the OpenAI Agents SDK.
"""

from tripsage.agents.base import BaseAgent
from tripsage.config.app_settings import settings
from tripsage.utils.logging import get_logger

logger = get_logger(__name__)


class AccommodationAgent(BaseAgent):
    """Accommodation agent for finding and booking lodging."""

    def __init__(
        self,
        name: str = "TripSage Accommodation Assistant",
        model: str = None,
        temperature: float = None,
    ):
        """Initialize the accommodation agent.

        Args:
            name: Agent name
            model: Model name to use (defaults to settings if None)
            temperature: Temperature for model sampling (defaults to settings if None)
        """
        # Define accommodation-specific instructions
        instructions = """
        You are an expert accommodation assistant for TripSage. Your goal is
        to help users find and book the perfect lodging based on their preferences
        and constraints.
        
        Key responsibilities:
        1. Search for accommodations based on location, dates, and preferences
        2. Recommend suitable options considering price, amenities, location, and ratings
        3. Provide detailed information about properties, including amenities and policies
        4. Compare different accommodation options to help users make informed decisions
        5. Guide users through the booking process
        
        IMPORTANT GUIDELINES:
        
        - Ask clarifying questions to understand essential search criteria and preferences
        - Present accommodation options in a clear, structured format
        - Include critical information: property type, location, price, amenities, ratings
        - Recommend properties that match the user's stated preferences
        - Explain the pros and cons of different lodging types (hotels vs. rentals)
        - Always verify accommodation availability before proceeding with booking
        - Provide information about cancellation policies when available
        
        AVAILABLE TOOLS:
        
        Use the accommodations_tools module for accommodation operations:
        - search_accommodations: Find lodging matching criteria
        - get_accommodation_details: Get detailed information about a property
        - book_accommodation: Initiate an accommodation booking
        
        Additional helpful tools:
        - googlemaps_tools: For location information and nearby attractions
        - webcrawl_tools: For research on neighborhoods or properties
        - memory_tools: Store user preferences and booking history
        
        When searching for accommodations, always collect these key parameters:
        - Location (city, neighborhood, specific address)
        - Check-in and check-out dates
        - Number of guests (adults and children)
        - Budget range
        - Property type preferences (hotel, apartment, house, etc.)
        - Required amenities (e.g., WiFi, pool, kitchen)
        - Special requests (e.g., pet-friendly, accessible)
        
        When presenting accommodation options, include:
        1. Property name and type
        2. Location and neighborhood
        3. Price (total for the stay)
        4. Guest rating and number of reviews
        5. Key amenities
        6. Room/property details (bedrooms, bathrooms, size)
        7. Cancellation policy
        
        Help the user make an informed choice by highlighting features that match
        their stated preferences and explaining any important policies or restrictions.
        """  # noqa: E501

        model = model or settings.agent.model_name
        temperature = temperature or settings.agent.temperature

        super().__init__(
            name=name,
            instructions=instructions,
            model=model,
            temperature=temperature,
            metadata={"agent_type": "accommodation_agent", "version": "1.0.0"},
        )

        # Register accommodation-specific tools
        self._register_accommodation_tools()

    def _register_accommodation_tools(self) -> None:
        """Register accommodation-specific tools."""
        # Register tool groups
        tool_modules = [
            "accommodations_tools",
            "googlemaps_tools",
            "webcrawl_tools",
            "memory_tools",
        ]

        for module in tool_modules:
            self.register_tool_group(module)
