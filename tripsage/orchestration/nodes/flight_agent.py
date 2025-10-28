"""Flight agent node implementation for LangGraph orchestration.

This module implements the flight search and booking agent as a LangGraph node,
using modern LangGraph @tool patterns for simplicity and maintainability.
"""

# pylint: disable=duplicate-code

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, cast

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, ConfigDict, Field, SecretStr

from tripsage.app_state import AppServiceContainer
from tripsage.orchestration.nodes.base import BaseAgentNode
from tripsage.orchestration.state import TravelPlanningState
from tripsage.orchestration.tools.tools import get_tools_for_agent
from tripsage.orchestration.utils.structured import StructuredExtractor, model_to_dict
from tripsage_core.config import get_settings
from tripsage_core.models.schemas_common.enums import CabinClass
from tripsage_core.models.schemas_common.flight_schemas import FlightSearchRequest
from tripsage_core.services.business.flight_service import FlightService
from tripsage_core.utils.logging_utils import get_logger


logger = get_logger(__name__)


class FlightSearchParameters(BaseModel):
    """Structured flight search payload."""

    model_config = ConfigDict(extra="forbid")

    origin: str | None = None
    destination: str | None = None
    departure_date: str | None = None
    return_date: str | None = None
    passengers: int | None = Field(default=None, ge=1)
    class_preference: str | None = None
    airline_preference: str | None = None


def _empty_tool_list() -> list[BaseTool]:
    """Return a typed empty tool list."""
    return []


@dataclass(slots=True)
class _RuntimeState:
    llm: ChatOpenAI | None = None
    llm_with_tools: ChatOpenAI | None = None
    parameter_extractor: StructuredExtractor[FlightSearchParameters] | None = None
    tools: list[BaseTool] = field(default_factory=_empty_tool_list)


class FlightAgentNode(BaseAgentNode):
    """Flight search and booking agent node.

    This node handles all flight-related requests including search, booking,
    changes, and flight information using the centralized tool registry.

    Responsibilities:
    - Extract flight search parameters from user input and conversation context
    - Execute flight searches using MCP tools
    - Generate user-friendly responses with flight options
    - Handle general flight inquiries and provide guidance
    - Update conversation state with search results and booking progress
    """

    def __init__(self, services: AppServiceContainer, **config_overrides: Any):
        """Initialize the flight agent node with dynamic configuration.

        Args:
            services: Application service container for dependency injection
            **config_overrides: Runtime configuration overrides (e.g., temperature=0.6)
        """
        # Store overrides for async config loading
        self.config_overrides: dict[str, Any] = dict(config_overrides)
        self.agent_config: dict[str, Any] = {}
        self._runtime = _RuntimeState()

        super().__init__("flight_agent", services)

        # Get configuration service for database-backed config
        self.config_service: Any = self.get_service("configuration_service")

    def _initialize_tools(self) -> None:
        """Initialize flight-specific tools using simple tool catalog."""
        # Get tools for flight agent using simple catalog
        self._runtime.tools = list(get_tools_for_agent("flight_agent"))

        # Bind tools to LLM for direct use (if LLM is available)
        if self._runtime.llm:
            runtime_llm = cast(Any, self._runtime.llm)
            self._runtime.llm_with_tools = cast(
                ChatOpenAI, runtime_llm.bind_tools(self._runtime.tools)
            )

        logger.info("Initialized flight agent with %s tools", len(self._runtime.tools))

    async def _load_configuration(self) -> None:
        """Load agent configuration from database with fallback to settings."""
        try:
            # Get configuration from database with runtime overrides
            self.agent_config = await self.config_service.get_agent_config(
                "flight_agent", **self.config_overrides
            )
            if not self.agent_config:
                raise RuntimeError("Flight agent configuration is missing")

            # Initialize LLM with loaded configuration
            self._runtime.llm = self._create_llm_from_config()
            self._runtime.parameter_extractor = StructuredExtractor(
                self._runtime.llm, FlightSearchParameters, logger=logger
            )
            if self._runtime.tools:
                runtime_llm = cast(Any, self._runtime.llm)
                self._runtime.llm_with_tools = cast(
                    ChatOpenAI, runtime_llm.bind_tools(self._runtime.tools)
                )

            logger.info(
                "Loaded flight agent configuration from database: temp=%s",
                self.agent_config["temperature"],
            )

        except Exception:
            logger.exception("Failed to load database configuration, using fallback")

            # Fallback to settings-based configuration
            settings = get_settings()
            # Preserve SecretStr or None as provided by settings
            secret_api_key: SecretStr | None = settings.openai_api_key
            self.agent_config = {
                "model": settings.openai_model,
                "temperature": settings.model_temperature,
                "api_key": secret_api_key,
                "top_p": 1.0,
            }

            self._runtime.llm = self._create_llm_from_config()
            self._runtime.parameter_extractor = StructuredExtractor(
                self._runtime.llm, FlightSearchParameters, logger=logger
            )
            if self._runtime.tools:
                runtime_llm = cast(Any, self._runtime.llm)
                self._runtime.llm_with_tools = cast(
                    ChatOpenAI, runtime_llm.bind_tools(self._runtime.tools)
                )

    async def process(self, state: TravelPlanningState) -> TravelPlanningState:
        """Process flight-related requests.

        Args:
            state: Current travel planning state

        Returns:
            Updated state with flight search results and response
        """
        # Ensure configuration is loaded before processing
        if not self.agent_config:
            await self._load_configuration()

        user_message = state["messages"][-1]["content"] if state["messages"] else ""

        # Extract flight search parameters from user message and context
        search_params = await self._extract_flight_parameters(user_message, state)

        if search_params:
            # Perform flight search using MCP integration
            search_results = await self._search_flights(search_params)

            # Update state with results
            flight_search_record = {
                "timestamp": datetime.now(UTC).isoformat(),
                "parameters": search_params,
                "results": search_results,
                "agent": "flight_agent",
            }
            state["flight_searches"].append(flight_search_record)

            # Generate user-friendly response
            response_message = await self._generate_flight_response(
                search_results, search_params, state
            )
        else:
            # Handle general flight inquiries
            response_message = await self._handle_general_flight_inquiry(
                user_message, state
            )

        # Add response to conversation
        state["messages"].append(response_message)

        return state

    async def _extract_flight_parameters(
        self, message: str, state: TravelPlanningState
    ) -> dict[str, Any] | None:
        """Extract flight search parameters from user message and conversation context.

        Args:
            message: User message to analyze
            state: Current conversation state for context

        Returns:
            Dictionary of flight search parameters or None if insufficient info
        """
        extraction_prompt = f"""
        Extract flight search parameters from this message and context.

        User message: "{message}"

        Context from conversation:
        - Previous flight searches: {len(state.get("flight_searches", []))}
        - User preferences: {state.get("user_preferences", "None")}
        - Travel dates mentioned: {state.get("travel_dates", "None")}
        - Destination info: {state.get("destination_info", "None")}

        Extract these parameters if mentioned:
        - origin (airport code, city, or airport name)
        - destination (airport code, city, or airport name)
        - departure_date (YYYY-MM-DD format)
        - return_date (YYYY-MM-DD format, if round trip)
        - passengers (number of travelers)
        - class_preference (economy, business, first)
        - airline_preference (specific airline)

        Respond with JSON only. If insufficient information for a flight
        search, return null.

        Example: {{"origin": "NYC", "destination": "LAX",
                   "departure_date": "2024-03-15", "passengers": 2}}
        """

        try:
            extractor = self._runtime.parameter_extractor
            if extractor is None:
                raise RuntimeError("Flight parameter extractor is not initialised")

            result = await extractor.extract_from_prompts(
                system_prompt="You are a flight search parameter extraction assistant.",
                user_prompt=extraction_prompt,
            )
        except Exception:
            logger.exception("Error extracting flight parameters")
            return None
        params = model_to_dict(result)

        if params.get("origin") and params.get("destination"):
            return params
        return None

    async def _search_flights(self, search_params: dict[str, Any]) -> dict[str, Any]:
        """Perform flight search via FlightService canonical API.

        Args:
            search_params: Flight search parameters extracted from chat.

        Returns:
            Dict with key "flights" listing offers (serialized), and metadata.
        """
        try:
            service = self.get_service("flight_service")
            if not isinstance(service, FlightService):  # Defensive check
                raise TypeError("flight_service is not initialized correctly")

            # Build typed request from extracted params
            # Map cabin class safely to enum
            cabin_raw = search_params.get("class_preference")
            try:
                cabin = CabinClass(str(cabin_raw)) if cabin_raw else CabinClass.ECONOMY
            except ValueError:
                cabin = CabinClass.ECONOMY

            dep_raw = search_params.get("departure_date")
            dep_value = dep_raw if dep_raw else datetime.now(UTC).date()

            req = FlightSearchRequest(
                origin=str(search_params.get("origin")),
                destination=str(search_params.get("destination")),
                departure_date=dep_value,
                return_date=search_params.get("return_date"),
                adults=max(1, int(search_params.get("passengers", 1) or 1)),
                children=0,
                infants=0,
                passengers=None,
                cabin_class=cabin,
                max_stops=None,
                max_price=None,
                preferred_airlines=(
                    [str(search_params["airline_preference"])]
                    if search_params.get("airline_preference")
                    else None
                ),
                excluded_airlines=None,
                trip_id=None,
            )

            resp = await service.search_flights(req)
            # Serialize offers for agent-friendly output
            offers = [o.model_dump() for o in resp.offers]
            return {
                "flights": offers,
                "search_id": resp.search_id,
                "total_results": resp.total_results,
                "cached": resp.cached,
            }
        except Exception as e:  # pragma: no cover - orchestration surface
            logger.exception("Flight search failed")
            return {"error": f"Flight search failed: {e!s}"}

    async def _generate_flight_response(
        self,
        search_results: dict[str, Any],
        search_params: dict[str, Any],
        state: TravelPlanningState,
    ) -> dict[str, Any]:
        """Generate user-friendly response from flight search results.

        Args:
            search_results: Raw flight search results
            search_params: Parameters used for search
            state: Current conversation state

        Returns:
            Formatted response message
        """
        if search_results.get("error"):
            content = (
                f"I apologize, but I encountered an issue searching for flights: "
                f"{search_results['error']}. Let me help you try a different approach."
            )
        else:
            flights: list[dict[str, Any]] = search_results.get("flights", [])  # type: ignore[assignment]

            if flights:
                # Format canonical FlightOffer dicts
                content = (
                    f"I found {len(flights)} flights from "
                    f"{search_params['origin']} to {search_params['destination']}:\n\n"
                )

                for i, offer_dict in enumerate(flights[:3], 1):  # Show top 3 results
                    # Derive primary airline and departure from canonical structure
                    offer: dict[str, Any] = offer_dict
                    airlines: list[str] = offer.get("airlines") or []
                    airline: str = airlines[0] if airlines else "Unknown"

                    outbound: list[dict[str, Any]] = (
                        offer.get("outbound_segments") or []
                    )
                    first_seg: dict[str, Any] = outbound[0] if outbound else {}
                    departure: str = str(first_seg.get("departure_date", "Unknown"))

                    currency: str = str(offer.get("currency", "USD"))
                    total_price: Any = offer.get("total_price")
                    price_str = (
                        f"{currency} {total_price:.2f}"
                        if isinstance(total_price, (int, float))
                        else str(total_price)
                        if total_price is not None
                        else "Unknown"
                    )

                    content += (
                        f"{i}. {airline} - Departure: {departure} - "
                        f"Price: {price_str}\n"
                    )

                if len(flights) > 3:
                    content += f"\n... and {len(flights) - 3} more options available."

                content += (
                    "\n\nWould you like me to help you book one of these flights "
                    "or search with different criteria?"
                )
            else:
                content = (
                    f"I couldn't find any flights for {search_params['origin']} "
                    f"to {search_params['destination']} on the specified dates. "
                    f"Would you like to try different dates or airports?"
                )

        return self._create_response_message(
            content,
            {
                "search_params": search_params,
                "results_count": len(search_results.get("flights", [])),
            },
        )

    async def _handle_general_flight_inquiry(
        self, message: str, state: TravelPlanningState
    ) -> dict[str, Any]:
        """Handle general flight inquiries that don't require a specific search.

        Args:
            message: User message
            state: Current conversation state

        Returns:
            Response message
        """
        # Use LLM to generate helpful response for general flight questions
        response_prompt = f"""
        The user is asking about flights but hasn't provided enough specific
        information for a search.

        User message: "{message}"

        Provide a helpful response that:
        1. Acknowledges their flight interest
        2. Asks for the specific information needed (origin, destination, dates)
        3. Offers to help with the search once they provide details

        Keep the response friendly and concise.
        """

        try:
            messages = [
                SystemMessage(content="You are a helpful flight booking assistant."),
                HumanMessage(content=response_prompt),
            ]

            llm = self._runtime.llm
            if llm is None:
                raise RuntimeError("Flight LLM is not initialized")

            response = await llm.ainvoke(messages)
            raw_resp: Any = cast(Any, response)
            if hasattr(raw_resp, "content"):
                raw_content: Any = raw_resp.content
            else:
                raw_content = raw_resp
            if isinstance(raw_content, str):
                content: str = raw_content
            else:
                content = str(raw_content)

        except Exception:
            logger.exception("Error generating flight response")
            content = (
                "I'd be happy to help you find flights! To get started, I'll need "
                "to know your departure city, destination, and travel dates. "
                "What trip are you planning?"
            )

        return self._create_response_message(content)
