"""Accommodation agent node implementation for LangGraph orchestration.

This module implements the accommodation search and booking agent as a LangGraph node,
using modern LangGraph @tool patterns for simplicity and maintainability.
"""

from datetime import UTC, date, datetime
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, ConfigDict, Field

from tripsage.orchestration.nodes.base import BaseAgentNode
from tripsage.orchestration.state import TravelPlanningState
from tripsage.orchestration.tools.simple_tools import get_tools_for_agent
from tripsage.orchestration.utils.structured import (
    StructuredExtractor,
    model_to_dict,
)
from tripsage_core.config import get_settings
from tripsage_core.services.business.accommodation_service import (
    AccommodationSearchRequest,
    AccommodationSearchResponse,
    AccommodationService,
)
from tripsage_core.utils.logging_utils import get_logger


logger = get_logger(__name__)


class AccommodationSearchParameters(BaseModel):
    """Structured accommodation extraction payload."""

    model_config = ConfigDict(extra="forbid")

    location: str | None = None
    check_in_date: date | None = None
    check_out_date: date | None = None
    guests: int | None = Field(default=None, ge=1)
    rooms: int | None = Field(default=None, ge=1)
    property_type: str | None = None
    min_price: float | None = Field(default=None, ge=0)
    max_price: float | None = Field(default=None, ge=0)
    amenities: list[str] | None = None
    rating_min: float | None = Field(default=None, ge=0, le=5)


class AccommodationAgentNode(BaseAgentNode):
    """Accommodation search and booking agent node.

    This node handles all accommodation-related requests including search, booking,
    and accommodation information using service-based integration.
    """

    def __init__(self, service_registry):
        """Initialize the accommodation agent node."""
        settings = get_settings()
        # type: ignore # pylint: disable=no-member
        api_key_str = settings.openai_api_key.get_secret_value()
        self.llm = ChatOpenAI(
            model=settings.openai_model,
            temperature=settings.model_temperature,
            api_key=api_key_str,  # type: ignore
        )
        self._parameter_extractor = StructuredExtractor(
            self.llm, AccommodationSearchParameters, logger=logger
        )
        super().__init__("accommodation_agent", service_registry)
        self.accommodation_service: AccommodationService = self.get_service(
            "accommodation_service"
        )
        self.memory_service = self.get_optional_service("memory_service")

    def _initialize_tools(self) -> None:
        """Initialize accommodation-specific tools using simple tool catalog."""
        # Get tools for accommodation agent using simple catalog
        self.available_tools = get_tools_for_agent("accommodation_agent")

        # Bind tools to LLM for direct use
        self.llm_with_tools = self.llm.bind_tools(self.available_tools)

        logger.info(
            "Initialized accommodation agent with %s tools", len(self.available_tools)
        )

        logger.info("Initialized accommodation agent with service-based architecture")

    async def process(self, state: TravelPlanningState) -> TravelPlanningState:
        """Process accommodation-related requests.

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
                "timestamp": datetime.now(UTC).isoformat(),
                "parameters": search_params,
                "results": search_results.model_dump(),
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
        """Extract accommodation search parameters from user message and context.

        Args:
            message: User message to analyze
            state: Current conversation state for context

        Returns:
            Dictionary of accommodation search parameters or None if insufficient info
        """
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
            result = await self._parameter_extractor.extract_from_prompts(
                system_prompt=(
                    "You are an accommodation parameter extraction assistant."
                ),
                user_prompt=extraction_prompt,
            )
        except Exception:
            logger.exception("Error extracting accommodation parameters")
            return None

        params = model_to_dict(result)
        if not params.get("location"):
            return None

        amenities = params.get("amenities")
        if isinstance(amenities, list):
            params["amenities"] = [str(item) for item in amenities if item]

        return params

    async def _search_accommodations(
        self, search_params: dict[str, Any]
    ) -> AccommodationSearchResponse:
        """Perform accommodation search using service layer."""
        try:
            search_request = self._build_search_request(search_params)
            result = await self.accommodation_service.search_accommodations(
                search_request
            )

            logger.info(
                "Accommodation search completed",
                extra={
                    "search_id": result.search_id,
                    "results": result.results_returned,
                    "cached": result.cached,
                },
            )

            return result

        except Exception:
            logger.exception("Accommodation search failed")
            raise

    def _build_search_request(
        self, search_params: dict[str, Any]
    ) -> AccommodationSearchRequest:
        """Convert extracted parameters into a typed search request."""
        normalized = search_params.copy()
        check_in_val = normalized.pop("check_in_date", None)
        check_out_val = normalized.pop("check_out_date", None)

        if check_in_val:
            normalized["check_in"] = (
                date.fromisoformat(check_in_val)
                if isinstance(check_in_val, str)
                else check_in_val
            )
        if check_out_val:
            normalized["check_out"] = (
                date.fromisoformat(check_out_val)
                if isinstance(check_out_val, str)
                else check_out_val
            )

        return AccommodationSearchRequest(**normalized)

    async def _generate_accommodation_response(
        self,
        search_results: AccommodationSearchResponse,
        search_params: dict[str, Any],
        state: TravelPlanningState,
    ) -> dict[str, Any]:
        """Generate user-friendly response from accommodation search results.

        Args:
            search_results: Raw accommodation search results
            search_params: Parameters used for search
            state: Current conversation state

        Returns:
            Formatted response message
        """
        listings = search_results.listings
        location = search_params.get("location", "your destination")
        check_in = search_params.get("check_in_date")
        check_out = search_params.get("check_out_date")

        if not listings:
            content = (
                "I couldn't find accommodations in "
                f"{location} for the specified dates. "
                "Would you like to adjust the dates or preferences?"
            )
            return self._create_response_message(
                content,
                {
                    "search_params": search_params,
                    "results_count": search_results.results_returned,
                },
            )

        content = f"I found {len(listings)} accommodations in {location}"

        if check_in and check_out:
            content += f" for {check_in} to {check_out}"

        content += ":\n\n"

        for index, listing in enumerate(listings[:3], 1):
            price = f"${listing.price_per_night:,.0f}"
            rating = (
                f"{listing.rating:.1f}" if listing.rating is not None else "No rating"
            )
            amenities = (
                ", ".join(amenity.name for amenity in listing.amenities[:3] if amenity)
                or "No amenities listed"
            )
            content += (
                f"{index}. {listing.name} ({listing.property_type})\n"
                f"   Rating: {rating} | Price: {price}/night\n"
                f"   Amenities: {amenities}\n\n"
            )

        remaining = len(listings) - min(len(listings), 3)
        if remaining > 0:
            content += f"... and {remaining} more options available.\n\n"

        content += (
            "Would you like details about any properties or refine your criteria?"
        )

        return self._create_response_message(
            content,
            {
                "search_params": search_params,
                "results_count": search_results.results_returned,
            },
        )

    async def _handle_general_accommodation_inquiry(
        self, message: str, state: TravelPlanningState
    ) -> dict[str, Any]:
        """Handle general accommodation inquiries that don't require a specific search.

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
            if self.llm is None:
                raise RuntimeError("Accommodation LLM is not initialized")

            messages = [
                SystemMessage(
                    content="You are a helpful accommodation booking assistant."
                ),
                HumanMessage(content=response_prompt),
            ]

            response = await self.llm.ainvoke(messages)
            raw_content = response.content
            content = raw_content if isinstance(raw_content, str) else str(raw_content)

        except Exception:
            logger.exception("Error generating accommodation response")
            content = (
                "I'd be happy to help you find accommodations! I'll need "
                "your destination, check-in/check-out dates, and preferences "
                "for property type or amenities. What are you looking for?"
            )

        return self._create_response_message(content)
