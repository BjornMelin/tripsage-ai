"""
Accommodation agent node implementation for LangGraph orchestration.

This module implements the accommodation search and booking agent as a LangGraph node,
using modern LangGraph @tool patterns for simplicity and maintainability.
"""

import json
from datetime import datetime, timezone
from typing import Any, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from tripsage.orchestration.nodes.base import BaseAgentNode
from tripsage.orchestration.state import TravelPlanningState
from tripsage.orchestration.tools import get_tools_for_agent
from tripsage_core.config import get_settings
from tripsage_core.utils.logging_utils import get_logger

logger = get_logger(__name__)

class AccommodationAgentNode(BaseAgentNode):
    """
    Accommodation search and booking agent node.

    This node handles all accommodation-related requests including search, booking,
    and accommodation information using service-based integration.
    """

    def __init__(self, service_registry):
        """Initialize the accommodation agent node."""
        super().__init__("accommodation_agent", service_registry)

        # Initialize LLM for accommodation-specific tasks
        settings = get_settings()
        self.llm = ChatOpenAI(
            model=settings.openai_model,
            temperature=settings.model_temperature,
            api_key=settings.openai_api_key.get_secret_value(),
        )

    def _initialize_tools(self) -> None:
        """Initialize accommodation-specific tools using simple tool catalog."""
        # Get tools for accommodation agent using simple catalog
        self.available_tools = get_tools_for_agent("accommodation_agent")

        # Bind tools to LLM for direct use
        self.llm_with_tools = self.llm.bind_tools(self.available_tools)

        logger.info(
            f"Initialized accommodation agent with {len(self.available_tools)} tools"
        )

        logger.info("Initialized accommodation agent with service-based architecture")

    async def process(self, state: TravelPlanningState) -> TravelPlanningState:
        """
        Process accommodation-related requests.

        Args:
            state: Current travel planning state

        Returns:
            Updated state with accommodation search results and response
        """
        user_message = state["messages"][-1]["content"] if state["messages"] else ""

        # Extract accommodation search parameters from user message and context
        search_params = await self._extract_accommodation_parameters(
            user_message, state
        )

        if search_params:
            # Perform accommodation search using service
            search_results = await self._search_accommodations(search_params)

            # Update state with results
            accommodation_search_record = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "parameters": search_params,
                "results": search_results,
                "agent": "accommodation_agent",
            }

            if "accommodation_searches" not in state:
                state["accommodation_searches"] = []
            state["accommodation_searches"].append(accommodation_search_record)

            # Generate user-friendly response
            response_message = await self._generate_accommodation_response(
                search_results, search_params, state
            )
        else:
            # Handle general accommodation inquiries
            response_message = await self._handle_general_accommodation_inquiry(
                user_message, state
            )

        # Add response to conversation
        state["messages"].append(response_message)

        return state

    async def _extract_accommodation_parameters(
        self, message: str, state: TravelPlanningState
    ) -> dict[str, Any] | None:
        """
        Extract accommodation search parameters from user message and context.

        Args:
            message: User message to analyze
            state: Current conversation state for context

        Returns:
            Dictionary of accommodation search parameters or None if insufficient info
        """
        # Use LLM to extract parameters
        extraction_prompt = f"""
        Extract accommodation search parameters from this message and context.
        
        User message: "{message}"
        
        Context from conversation:
        - Previous searches: {len(state.get("accommodation_searches", []))}
        - User preferences: {state.get("user_preferences", "None")}
        - Travel dates mentioned: {state.get("travel_dates", "None")}
        - Destination info: {state.get("destination_info", "None")}
        - Flight searches: {len(state.get("flight_searches", []))}
        
        Extract these parameters if mentioned:
        - location (city, neighborhood, or specific address)
        - check_in_date (YYYY-MM-DD format)
        - check_out_date (YYYY-MM-DD format)
        - guests (number of guests)
        - rooms (number of rooms needed)
        - property_type (hotel, apartment, house, etc.)
        - min_price (minimum price per night)
        - max_price (maximum price per night)
        - amenities (list of required amenities like wifi, pool, kitchen)
        - rating_min (minimum guest rating)
        
        Respond with JSON only. If insufficient information for an accommodation 
        search, return null.
        
        Example: {{"location": "Paris", "check_in_date": "2024-03-15", 
                   "check_out_date": "2024-03-20", "guests": 2}}
        """

        try:
            messages = [
                SystemMessage(
                    content="You are an accommodation parameter extraction assistant."
                ),
                HumanMessage(content=extraction_prompt),
            ]

            response = await self.llm.ainvoke(messages)

            # Parse the response
            if response.content.strip().lower() in ["null", "none", "{}"]:
                return None

            params = json.loads(response.content)

            # Validate required fields
            if params and params.get("location"):
                return params
            else:
                return None

        except Exception as e:
            logger.error(f"Error extracting accommodation parameters: {str(e)}")
            return None

    async def _search_accommodations(
        self, search_params: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Perform accommodation search using service layer.

        Args:
            search_params: Accommodation search parameters

        Returns:
            Accommodation search results
        """
        try:
            # Use accommodation service to search
            result = await self.accommodation_service.search_accommodations(
                **search_params
            )

            if result.get("status") == "success":
                properties_found = len(result.get("listings", []))
                logger.info(f"Search completed: {properties_found} properties found")
            else:
                logger.warning(f"Accommodation search failed: {result.get('error')}")

            return result

        except Exception as e:
            logger.error(f"Accommodation search failed: {str(e)}")
            return {"error": f"Accommodation search failed: {str(e)}"}

    async def _generate_accommodation_response(
        self,
        search_results: dict[str, Any],
        search_params: dict[str, Any],
        state: TravelPlanningState,
    ) -> dict[str, Any]:
        """
        Generate user-friendly response from accommodation search results.

        Args:
            search_results: Raw accommodation search results
            search_params: Parameters used for search
            state: Current conversation state

        Returns:
            Formatted response message
        """
        if search_results.get("error"):
            content = (
                f"I apologize, but I encountered an issue searching: "
                f"{search_results['error']}. Let me help you try a different approach."
            )
        else:
            accommodations = search_results.get("listings", [])

            if accommodations:
                # Format accommodation results
                location = search_params.get("location", "your destination")
                check_in = search_params.get("check_in_date", "")
                check_out = search_params.get("check_out_date", "")

                content = f"I found {len(accommodations)} accommodations in {location}"

                if check_in and check_out:
                    content += f" for {check_in} to {check_out}"

                content += ":\n\n"

                for i, property in enumerate(
                    accommodations[:3], 1
                ):  # Show top 3 results
                    name = property.get("name", "Unknown Property")
                    property_type = property.get("property_type", "Property")
                    price = property.get("price", {}).get(
                        "per_night", "Price not available"
                    )
                    rating = property.get("rating", "No rating")

                    content += (
                        f"{i}. {name} ({property_type})\n"
                        f"   Rating: {rating} | Price: {price}/night\n"
                    )

                    amenities = property.get("amenities", [])
                    if amenities:
                        amenities_str = ", ".join(amenities[:3])
                        content += f"   Amenities: {amenities_str}\n"

                    content += "\n"

                if len(accommodations) > 3:
                    content += (
                        f"... and {len(accommodations) - 3} more options available.\n\n"
                    )

                content += (
                    "Would you like details about any properties "
                    "or search with different criteria?"
                )
            else:
                location = search_params.get("location", "the specified location")
                content = (
                    f"I couldn't find any accommodations in {location} "
                    f"for the specified dates. "
                    f"Would you like to try different dates or adjust preferences?"
                )

        return self._create_response_message(
            content,
            {
                "search_params": search_params,
                "results_count": len(search_results.get("listings", [])),
            },
        )

    async def _handle_general_accommodation_inquiry(
        self, message: str, state: TravelPlanningState
    ) -> dict[str, Any]:
        """
        Handle general accommodation inquiries that don't require a specific search.

        Args:
            message: User message
            state: Current conversation state

        Returns:
            Response message
        """
        # Use LLM to generate helpful response for general accommodation questions
        response_prompt = f"""
        The user is asking about accommodations but hasn't provided enough specific 
        information for a search.
        
        User message: "{message}"
        
        Provide a helpful response that:
        1. Acknowledges their accommodation interest
        2. Asks for the specific information needed (location, dates, preferences)
        3. Offers to help with the search once they provide details
        4. Mentions accommodation types we can help find (hotels, apartments, houses)
        
        Keep the response friendly and concise.
        """

        try:
            messages = [
                SystemMessage(
                    content="You are a helpful accommodation booking assistant."
                ),
                HumanMessage(content=response_prompt),
            ]

            response = await self.llm.ainvoke(messages)
            content = response.content

        except Exception as e:
            logger.error(f"Error generating accommodation response: {str(e)}")
            content = (
                "I'd be happy to help you find accommodations! I'll need "
                "your destination, check-in/check-out dates, and preferences "
                "for property type or amenities. What are you looking for?"
            )

        return self._create_response_message(content)
