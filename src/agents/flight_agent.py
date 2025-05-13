"""
Flight Agent implementation for TripSage.

This module provides a specialized FlightAgent for flight search and booking,
leveraging the flight MCP tools and integrating with the OpenAI Agents SDK.
"""

from typing import Any, Dict

from agents import RunContextWrapper, function_tool, handoff
from src.utils.config import get_config
from src.utils.logging import get_module_logger

from .base_agent import BaseAgent
from .flight_booking import TripSageFlightBooking
from .flight_search import TripSageFlightSearch

logger = get_module_logger(__name__)
config = get_config()


class FlightAgent(BaseAgent):
    """Specialized agent for flight search and booking."""

    def __init__(
        self,
        name: str = "TripSage Flight Specialist",
        model: str = "gpt-4",
        temperature: float = 0.2,
    ):
        """Initialize the flight agent.

        Args:
            name: Agent name
            model: Model name to use
            temperature: Temperature for model sampling
        """
        # Define specialized instructions
        instructions = """
        You are a specialized flight search and booking agent for TripSage. Your goal is
        to help users find and book the optimal flights for their travel needs,
        taking into account their preferences, constraints, and budget.

        Key responsibilities:
        1. Search for flights using detailed criteria
        2. Compare flight options across multiple dimensions
        3. Provide insights on pricing trends and booking timing
        4. Help with flight booking and reservation management
        5. Save flight details in the knowledge graph for future reference

        IMPORTANT GUIDELINES:

        - Ask clarifying questions when user flight requirements are ambiguous
        - Present flight options in a clear, tabular format with key information
        - Highlight important factors like layovers, timing, and price
        - Explain why certain flights are recommended (price, duration, airline, etc.)
        - When presenting prices, include all taxes and fees for transparency
        - For complex itineraries, suggest multi-city search options
        - Provide flexible date options when users are open to different travel dates
        - Look for price history trends to advise on booking timing
        - Save selected flight details in the knowledge graph for future reference

        FLIGHT DATA ANALYSIS:
        - Explain price differences between similar flights
        - Compare direct flights vs. routes with connections
        - Highlight options with significant savings
        - Analyze overnight vs. daytime flights based on user preference
        - Consider airline alliance benefits for frequent flyers

        TOOL USAGE:
        - Use Flights MCP for detailed flight search
        - Use Price History to analyze booking timing
        - Use Memory MCP to store flight preferences and selections
        - Use Flexible Dates search for users with date flexibility
        
        When returning results to the main TravelPlanningAgent, always:
        1. Summarize the top options clearly
        2. Include the reasoning behind your recommendations
        3. Provide the exact flight details that can be used for booking
        4. Return information about price trends if available
        """

        super().__init__(
            name=name,
            instructions=instructions,
            model=model,
            temperature=temperature,
            metadata={"agent_type": "flight_specialist", "version": "1.0.0"},
        )

        # Initialize components
        self.flight_search = TripSageFlightSearch()
        self.flight_booking = TripSageFlightBooking()

        # Register flight-specific tools
        self._register_flight_tools()

        # Register MCP client tools
        self._register_flight_mcp_client()

    def _register_flight_tools(self) -> None:
        """Register flight-specific tools."""
        # Register essential flight tools
        self._register_tool(self.search_flights)
        self._register_tool(self.enhanced_flight_search)
        self._register_tool(self.search_multi_city_flights)
        self._register_tool(self.get_flight_price_history)
        self._register_tool(self.get_flexible_dates_search)
        self._register_tool(self.book_flight)
        self._register_tool(self.get_booking_status)
        self._register_tool(self.cancel_flight_booking)
        self._register_tool(self.compare_flight_options)
        self._register_tool(self.store_flight_details)

    def _register_flight_mcp_client(self) -> None:
        """Register flight MCP client tools."""
        try:
            from ..mcp.flights import get_client as get_flights_client

            flights_client = get_flights_client()
            self._register_mcp_client_tools(flights_client, prefix="flights_")
            logger.info("Registered Flights MCP client tools")
        except Exception as e:
            logger.warning("Failed to register Flights MCP client: %s", str(e))

    @function_tool
    async def search_flights(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Search for available flights.

        Args:
            params: Flight search parameters including:
                origin: Origin airport or city code
                destination: Destination airport or city code
                departure_date: Departure date (YYYY-MM-DD)
                return_date: Return date for round trips (YYYY-MM-DD)
                adults: Number of adult passengers
                children: Number of child passengers
                infants: Number of infant passengers
                cabin_class: Desired cabin class
                    (economy, premium_economy, business, first)
                max_price: Maximum price willing to pay
                max_stops: Maximum number of stops
                preferred_airlines: List of preferred airlines

        Returns:
            Dictionary with flight search results
        """
        try:
            # Delegate to flight search component
            return await self.flight_search.search_flights(params)
        except Exception as e:
            logger.error("Error searching flights: %s", str(e))
            return {"error": f"Flight search error: {str(e)}"}

    @function_tool
    async def enhanced_flight_search(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced search for flights with advanced filtering and recommendations.

        Uses the TripSageFlightSearch component to provide comprehensive search
        results with intelligent filtering, price analysis, and personalized
        recommendations based on user preferences.

        Args:
            params: Enhanced flight search parameters including:
                origin: Origin airport or city code
                destination: Destination airport or city code
                departure_date: Departure date (YYYY-MM-DD)
                return_date: Return date for round trips (YYYY-MM-DD)
                adults: Number of adult passengers
                children: Number of child passengers
                infants: Number of infant passengers
                cabin_class: Desired cabin class
                    (economy, premium_economy, business, first)
                max_price: Maximum price willing to pay
                preferred_airlines: List of preferred airline codes
                max_stops: Maximum number of stops (0 for non-stop only)
                sort_by: How to sort results (price, duration, best)
                flexible_dates: Whether to include nearby dates in search

        Returns:
            Dictionary with enhanced flight search results
        """
        try:
            # Delegate to flight search component
            return await self.flight_search.search_flights(params)
        except Exception as e:
            logger.error("Error in enhanced flight search: %s", str(e))
            return {"error": f"Enhanced flight search error: {str(e)}"}

    @function_tool
    async def search_multi_city_flights(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Search for multi-city flight itineraries.

        Allows searching for complex itineraries with multiple segments between
        different city pairs on different dates.

        Args:
            params: Multi-city flight search parameters including:
                segments: List of flight segments, each containing:
                    origin: Origin airport or city code
                    destination: Destination airport or city code
                    date: Departure date (YYYY-MM-DD)
                adults: Number of adult passengers
                children: Number of child passengers
                infants: Number of infant passengers
                cabin_class: Desired cabin class
                max_price: Maximum total price for all segments

        Returns:
            Dictionary with multi-city flight search results
        """
        try:
            # Validate that segments are provided
            segments = params.get("segments", [])
            if not segments or not isinstance(segments, list) or len(segments) < 2:
                return {
                    "error": (
                        "At least two valid segments are required for multi-city search"
                    )
                }

            # Delegate to flight search component
            return await self.flight_search.search_multi_city(params)
        except Exception as e:
            logger.error("Error in multi-city flight search: %s", str(e))
            return {"error": f"Multi-city flight search error: {str(e)}"}

    @function_tool
    async def get_flight_price_history(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get price history for a specific flight route.

        Retrieves historical pricing data for a given route to help users
        determine if current prices are favorable and whether to book now or wait.

        Args:
            params: Flight route parameters:
                origin: Origin airport or city code
                destination: Destination airport or city code
                cabin_class: Optional cabin class to filter by
                days_back: How many days of history to include (default: 90)

        Returns:
            Dictionary with price history data and trend analysis
        """
        try:
            # Delegate to flight search component
            return await self.flight_search.get_price_history(params)
        except Exception as e:
            logger.error("Error getting flight price history: %s", str(e))
            return {"error": f"Price history error: {str(e)}"}

    @function_tool
    async def get_flexible_dates_search(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Search for flights with flexible dates to find the best prices.

        Searches for flights across a range of dates to help users find the
        optimal travel dates with the best prices.

        Args:
            params: Flexible date search parameters:
                origin: Origin airport or city code
                destination: Destination airport or city code
                date_range_start: Start of date range (YYYY-MM-DD)
                date_range_end: End of date range (YYYY-MM-DD)
                trip_length: Desired trip length in days for round trips
                cabin_class: Desired cabin class
                adults: Number of adult passengers

        Returns:
            Dictionary with flexible date search results
        """
        try:
            # Delegate to flight search component
            return await self.flight_search.search_flexible_dates(params)
        except Exception as e:
            logger.error("Error in flexible date flight search: %s", str(e))
            return {"error": f"Flexible date search error: {str(e)}"}

    @function_tool
    async def book_flight(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Book a flight based on selected search results.

        Creates a flight booking based on the selected flight offer from search results
        and passenger information. Stores booking details in dual storage architecture.

        Args:
            params: Flight booking parameters:
                flight_id: ID of selected flight from search results
                passengers: List of passenger information including:
                    first_name: Passenger's first name
                    last_name: Passenger's last name
                    dob: Date of birth (YYYY-MM-DD)
                    email: Contact email
                    phone: Contact phone number
                payment: Payment information object
                trip_id: Optional ID of associated trip

        Returns:
            Dictionary with booking confirmation details
        """
        try:
            # Delegate to flight booking component
            return await self.flight_booking.book_flight(params)
        except Exception as e:
            logger.error("Error booking flight: %s", str(e))
            return {"error": f"Flight booking error: {str(e)}"}

    @function_tool
    async def get_booking_status(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get the current status of a flight booking.

        Retrieves the latest status of a flight booking, including any updates
        to flight times, gate information, or booking status.

        Args:
            params: Booking status request parameters:
                booking_id: ID of the booking to check
                email: Email associated with the booking

        Returns:
            Dictionary with current booking status information
        """
        try:
            # Delegate to flight booking component
            return await self.flight_booking.get_booking_status(params)
        except Exception as e:
            logger.error("Error getting booking status: %s", str(e))
            return {"error": f"Booking status error: {str(e)}"}

    @function_tool
    async def cancel_flight_booking(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Cancel an existing flight booking.

        Attempts to cancel a flight booking and provides refund information
        according to the airline's cancellation policy.

        Args:
            params: Cancellation request parameters:
                booking_id: ID of the booking to cancel
                email: Email associated with the booking
                reason: Optional reason for cancellation

        Returns:
            Dictionary with cancellation confirmation and refund information
        """
        try:
            # Delegate to flight booking component
            return await self.flight_booking.cancel_booking(params)
        except Exception as e:
            logger.error("Error cancelling flight booking: %s", str(e))
            return {"error": f"Cancellation error: {str(e)}"}

    @function_tool
    async def compare_flight_options(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Compare multiple flight options across different criteria.

        Analyzes and compares flight options based on specified criteria to help
        users make an informed decision.

        Args:
            params: Comparison parameters:
                flight_ids: List of flight IDs to compare
                criteria: List of criteria to compare
                    (price, duration, stops, airline, etc.)
                weighting: Optional dictionary with weights for each criterion

        Returns:
            Dictionary with comparison results and recommendations
        """
        try:
            # Get the flight options to compare
            flight_ids = params.get("flight_ids", [])
            if not flight_ids:
                return {"error": "No flight IDs provided for comparison"}

            # This would be implemented to compare the flight options
            # For now, we just return a placeholder response
            return {
                "comparison": "This functionality will be implemented",
                "flight_ids": flight_ids,
                "criteria": params.get("criteria", []),
                "recommendation": "Placeholder for flight comparison recommendation",
            }
        except Exception as e:
            logger.error("Error comparing flight options: %s", str(e))
            return {"error": f"Flight comparison error: {str(e)}"}

    @function_tool
    async def store_flight_details(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Store flight details in the knowledge graph for future reference.

        Creates entities and relationships in the knowledge graph for the
        selected flights, connecting them to relevant trips, destinations, etc.

        Args:
            params: Storage parameters:
                flight_id: ID of the flight to store
                trip_id: ID of the associated trip
                user_id: ID of the user
                notes: Optional notes about the flight

        Returns:
            Dictionary with storage confirmation
        """
        try:
            from ..mcp.memory import get_client as get_memory_client

            # Get the memory client
            memory_client = get_memory_client()

            # Extract flight details
            flight_id = params.get("flight_id")
            trip_id = params.get("trip_id")
            user_id = params.get("user_id")
            notes = params.get("notes", "")

            if not flight_id or not trip_id:
                return {"error": "Flight ID and trip ID are required"}

            # Get the flight details from cache or search results
            # This would be implemented to retrieve the flight details
            # For now, we just use placeholder data
            flight_details = {
                "id": flight_id,
                "origin": "LAX",
                "destination": "JFK",
                "departure_time": "2023-06-15T08:00:00",
                "arrival_time": "2023-06-15T16:30:00",
                "airline": "United Airlines",
                "flight_number": "UA123",
                "price": 350.00,
            }

            # Create flight entity in knowledge graph
            flight_entity = {
                "name": f"Flight_{flight_id}",
                "entityType": "Flight",
                "observations": [
                    f"Origin: {flight_details.get('origin')}",
                    f"Destination: {flight_details.get('destination')}",
                    f"Departure: {flight_details.get('departure_time')}",
                    f"Arrival: {flight_details.get('arrival_time')}",
                    f"Airline: {flight_details.get('airline')}",
                    f"Flight Number: {flight_details.get('flight_number')}",
                    f"Price: ${flight_details.get('price')}",
                ],
            }

            if notes:
                flight_entity["observations"].append(f"Notes: {notes}")

            # Create the entity
            await memory_client.create_entities([flight_entity])

            # Create relationships
            relations = [
                {
                    "from": f"Flight_{flight_id}",
                    "relationType": "partOf",
                    "to": f"Trip_{trip_id}",
                },
                {
                    "from": f"User_{user_id}",
                    "relationType": "books",
                    "to": f"Flight_{flight_id}",
                },
            ]

            # Create the relations
            await memory_client.create_relations(relations)

            return {
                "success": True,
                "message": "Flight details stored in knowledge graph",
                "flight_id": flight_id,
                "entity_name": flight_entity["name"],
            }
        except Exception as e:
            logger.error("Error storing flight details: %s", str(e))
            return {"error": f"Flight storage error: {str(e)}"}


def create_flight_agent() -> FlightAgent:
    """Create and return a fully initialized FlightAgent instance.

    Returns:
        An initialized FlightAgent
    """
    agent = FlightAgent()
    logger.info("Created Flight Agent instance with all tools registered")
    return agent


def create_flight_agent_handoff():
    """Create a handoff to the Flight Agent.

    Returns:
        A handoff function to be used by the TravelPlanningAgent
    """
    flight_agent = create_flight_agent()

    async def on_flight_handoff(ctx: RunContextWrapper[None], input_data: str):
        """Handle flight agent handoff.

        Args:
            ctx: Context wrapper
            input_data: Input data
        """
        logger.info("Handing off to Flight Agent")
        # Pass any context data needed by the Flight Agent
        if hasattr(ctx, "session_data"):
            ctx.session_data["source_agent"] = "TravelPlanningAgent"

    return handoff(agent=flight_agent, on_handoff=on_flight_handoff)
