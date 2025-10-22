"""Destination research agent node implementation for LangGraph orchestration.

This module implements the destination research agent as a LangGraph node,
using modern LangGraph @tool patterns for simplicity and maintainability.
"""

from typing import Any, Literal, cast

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import Tool
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, ConfigDict, Field

from tripsage.orchestration.config import get_default_config
from tripsage.orchestration.nodes.base import BaseAgentNode
from tripsage.orchestration.state import TravelPlanningState
from tripsage.orchestration.utils.structured import StructuredExtractor, model_to_dict
from tripsage_core.config import get_settings
from tripsage_core.services import configuration_service as configuration_service_module
from tripsage_core.utils.logging_utils import get_logger


logger = get_logger(__name__)


class DestinationResearchParameters(BaseModel):
    """Structured destination research extraction payload."""

    model_config = ConfigDict(extra="forbid")

    destination: str | None = None
    research_type: (
        Literal[
            "overview", "attractions", "activities", "culture", "practical", "weather"
        ]
        | None
    ) = None
    specific_interests: list[str] | None = None
    travel_dates: str | None = None
    travel_style: str | None = None
    duration: int | None = Field(default=None, ge=1)


class DestinationResearchAgentNode(BaseAgentNode):  # pylint: disable=too-many-instance-attributes
    """Destination research agent node.

    This node handles all destination research requests including destination
    information, attractions, activities, cultural insights, and practical travel
    information using MCP tool integration.
    """

    def __init__(self, service_registry, **config_overrides):
        """Initialize the destination research agent node with dynamic configuration.

        Args:
            service_registry: Service registry for dependency injection
            **config_overrides: Runtime configuration overrides (e.g., temperature=0.8)
        """
        # Get configuration service for database-backed config
        self.config_service = cast(
            Any, configuration_service_module
        ).get_configuration_service()

        # Store overrides for async config loading
        self.config_overrides = config_overrides
        self.agent_config: dict[str, Any] | None = None
        self.llm: ChatOpenAI | None = None
        self.tool_map: dict[str, Tool] = {}
        self._parameter_extractor: (
            StructuredExtractor[DestinationResearchParameters] | None
        ) = None
        self.llm_with_tools = None

        super().__init__("destination_research_agent", service_registry)

    def _initialize_tools(self) -> None:
        """Initialize destination research tools using simple tool catalog."""
        from tripsage.orchestration.tools.tools import get_tools_for_agent

        # Get tools for destination research agent using simple catalog
        self.available_tools = get_tools_for_agent("destination_research_agent")
        self.tool_map = {tool.name: tool for tool in self.available_tools}
        self._alias_tool("webcrawl_search", "web_search")
        self._alias_tool("search_places", "geocode_location")

        # Bind tools to LLM for direct use
        if self.llm:
            self.llm_with_tools = self.llm.bind_tools(self.available_tools)

        logger.info(
            "Initialized destination research agent with %s tools",
            len(self.available_tools),
        )

    def _alias_tool(self, alias: str, canonical: str) -> None:
        """Map a legacy tool alias to a canonical registered tool."""
        tool = self.tool_map.get(canonical)
        if tool:
            self.tool_map[alias] = tool

    def _get_tool(self, name: str) -> Tool | None:
        """Return LangGraph tool by name with logging when missing."""
        tool = self.tool_map.get(name)
        if tool is None:
            logger.warning("Destination research tool %s is not available", name)
        return tool

    async def _load_configuration(self) -> None:
        """Load agent configuration from database with fallback to settings."""
        try:
            self.agent_config = await self.config_service.get_agent_config(
                "destination_research_agent", **self.config_overrides
            )
            if self.agent_config is None:
                raise RuntimeError(
                    "Destination research configuration could not be loaded"
                )
            fallback = get_default_config()
            model_name = str(self.agent_config.get("model", fallback.default_model))
            temperature = float(
                self.agent_config.get("temperature", fallback.temperature)
            )
            # type: ignore # pylint: disable=no-member
            api_key = (
                self.agent_config.get("api_key")
                or get_settings().openai_api_key.get_secret_value()
            )

            self.llm = ChatOpenAI(
                model=model_name,
                temperature=temperature,
                api_key=api_key,  # type: ignore
            )
            self._parameter_extractor = StructuredExtractor(
                self.llm, DestinationResearchParameters, logger=logger
            )
            if hasattr(self, "available_tools"):
                self.llm_with_tools = self.llm.bind_tools(self.available_tools)

            logger.info(
                "Loaded destination research agent config (temp=%s)",
                temperature,
            )

        except Exception:
            logger.exception("Failed to load database configuration, using fallback")

            # Fallback to settings-based configuration
            fallback = get_default_config()
            settings = get_settings()
            # type: ignore # pylint: disable=no-member
            api_key = (
                settings.openai_api_key.get_secret_value()
                if settings.openai_api_key
                else ""
            )
            self.agent_config = {
                "model": fallback.default_model,
                "temperature": fallback.temperature,
                "api_key": api_key,
                "top_p": 1.0,
            }

            self.llm = ChatOpenAI(
                model=fallback.default_model,
                temperature=fallback.temperature,
                api_key=api_key,  # type: ignore
            )
            self._parameter_extractor = StructuredExtractor(
                self.llm, DestinationResearchParameters, logger=logger
            )
            if hasattr(self, "available_tools"):
                self.llm_with_tools = self.llm.bind_tools(self.available_tools)

    async def process(self, state: TravelPlanningState) -> TravelPlanningState:
        """Process destination research requests.

        Args:
            state: Current travel planning state

        Returns:
            Updated state with destination research and response
        """
        # Ensure configuration is loaded before processing
        if self.agent_config is None:
            await self._load_configuration()

        if self.llm is None:
            raise RuntimeError("Destination research LLM is not initialized")

        user_message = state["messages"][-1]["content"] if state["messages"] else ""

        # Extract research parameters from user message and context
        research_params = await self._extract_research_parameters(user_message, state)

        if research_params:
            # Perform destination research using MCP integration
            research_results = await self._research_destination(research_params, state)

            # Store research results in destination_info for other agents
            destination = research_params.get("destination", "")
            if destination:
                destination_info = state.get("destination_info") or {}
                state["destination_info"] = destination_info
                destination_info[destination] = research_results

            # Generate user-friendly response
            response_message = await self._generate_research_response(
                research_results, research_params, state
            )
        else:
            # Handle general destination inquiries
            response_message = await self._handle_general_research_inquiry(
                user_message, state
            )

        # Add response to conversation
        state["messages"].append(response_message)

        return state

    async def _extract_research_parameters(
        self, message: str, state: TravelPlanningState
    ) -> dict[str, Any] | None:
        """Extract destination research parameters from conversation context."""
        if self.llm is None:
            raise RuntimeError("Destination research LLM is not initialized")

        prior_destinations = list((state.get("destination_info") or {}).keys())

        # Use LLM to extract parameters and determine research type
        extraction_prompt = f"""
        Extract destination research parameters from this message and context.

        User message: "{message}"

        Context from conversation:
        - Flight searches: {len(state.get("flight_searches", []))}
        - Accommodation searches: {len(state.get("accommodation_searches", []))}
        - User preferences: {state.get("user_preferences", "None")}
        - Known destinations: {prior_destinations}

        Determine the research type from these options:
        - "overview": General destination information and overview
        - "attractions": Specific attractions and landmarks
        - "activities": Activities and experiences
        - "culture": Cultural information, customs, and etiquette
        - "practical": Practical travel information (transport, currency, etc.)
        - "weather": Climate and seasonal information

        Extract these parameters if mentioned:
        - destination: The destination to research (required)
        - research_type: One of the research types above
        - specific_interests: Specific topics or interests to focus on
        - travel_dates: Dates of travel for seasonal information
        - travel_style: Type of travel (luxury, budget, adventure, family, etc.)
        - duration: Length of stay

        Respond with JSON only. If this doesn't seem destination-research related,
        return null.

        Example: {{"destination": "Paris", "research_type": "attractions",
                   "specific_interests": ["museums", "architecture"], "duration": 5}}
        """

        try:
            if self._parameter_extractor is None:
                raise RuntimeError("Destination research parameter extractor missing")

            result = await self._parameter_extractor.extract_from_prompts(
                system_prompt=(
                    "You are a destination research parameter extraction assistant."
                ),
                user_prompt=extraction_prompt,
            )
        except Exception:
            logger.exception("Error extracting research parameters")
            return None
        params = model_to_dict(result)

        if params.get("destination"):
            interests = params.get("specific_interests")
            if isinstance(interests, list):
                params["specific_interests"] = [str(item) for item in interests if item]
            return params
        return None

    async def _research_destination(
        self, params: dict[str, Any], state: TravelPlanningState
    ) -> dict[str, Any]:
        """Perform destination research using MCP tools.

        Args:
            params: Research parameters
            state: Current conversation state

        Returns:
            Comprehensive destination research results
        """
        destination = params.get("destination", "")
        research_type = params.get("research_type", "overview")
        specific_interests = params.get("specific_interests", [])

        try:
            research_results = {
                "destination": destination,
                "research_type": research_type,
                "overview": {},
                "attractions": [],
                "activities": [],
                "practical_info": {},
                "cultural_info": {},
                "weather_info": {},
            }

            # Use web crawling for research
            if research_type in ("overview", "all"):
                overview_results = await self._research_overview(destination)
                research_results["overview"] = overview_results

            if research_type in ("attractions", "all"):
                attractions_results = await self._research_attractions(
                    destination, specific_interests
                )
                research_results["attractions"] = attractions_results

            if research_type in ("activities", "all"):
                activities_results = await self._research_activities(
                    destination, specific_interests
                )
                research_results["activities"] = activities_results

            if research_type in ("practical", "all"):
                practical_results = await self._research_practical_info(destination)
                research_results["practical_info"] = practical_results

            if research_type in ("culture", "all"):
                cultural_results = await self._research_cultural_info(destination)
                research_results["cultural_info"] = cultural_results

            if research_type in ("weather", "all"):
                weather_results = await self._research_weather_info(
                    destination, params.get("travel_dates")
                )
                research_results["weather_info"] = weather_results

            # Use Google Maps for location data
            location_data = await self._get_location_data(destination)
            research_results["location_data"] = location_data

            logger.info("Destination research completed for %s", destination)
            return research_results

        except Exception as e:
            logger.exception("Destination research failed for %s", destination)
            return {"error": f"Research failed: {e!s}", "destination": destination}

    async def _research_overview(self, destination: str) -> dict[str, Any]:
        """Research general overview information about a destination."""
        try:
            webcrawl_tool = self._get_tool("webcrawl_search")
            if webcrawl_tool:
                query = f"{destination} travel guide overview tourism information"
                result = await webcrawl_tool.ainvoke({"query": query})
                return {"overview_data": result, "sources": "web_research"}
            return {
                "overview_data": f"Overview research for {destination}",
                "sources": "placeholder",
            }
        except Exception as exc:
            logger.exception("Overview research failed")
            return {"error": str(exc)}

    async def _research_attractions(self, destination: str, interests: list) -> list:
        """Research attractions and landmarks in a destination."""
        try:
            webcrawl_tool = self._get_tool("webcrawl_search")
            if webcrawl_tool:
                interest_str = " ".join(interests) if interests else "top attractions"
                query = f"{destination} {interest_str} landmarks must-see attractions"
                result = await webcrawl_tool.ainvoke({"query": query})

                if isinstance(result, str):
                    return [
                        {
                            "name": f"Attraction in {destination}",
                            "description": "Research result",
                            "type": "landmark",
                        }
                        for _ in range(3)
                    ]

                return result
            return [
                {
                    "name": f"Top attraction in {destination}",
                    "description": "Placeholder",
                    "type": "landmark",
                }
            ]
        except Exception as exc:
            logger.exception("Attractions research failed")
            return [{"error": str(exc)}]

    async def _research_activities(self, destination: str, interests: list) -> list:
        """Research activities and experiences in a destination."""
        try:
            webcrawl_tool = self._get_tool("webcrawl_search")
            if webcrawl_tool:
                interest_str = (
                    " ".join(interests) if interests else "activities experiences"
                )
                query = (
                    f"{destination} {interest_str} things to do activities experiences"
                )
                result = await webcrawl_tool.ainvoke({"query": query})
                if isinstance(result, str):
                    return [
                        {
                            "name": f"Activity in {destination}",
                            "description": "Research result",
                            "category": "experience",
                        }
                        for _ in range(3)
                    ]
                return result
            return [
                {
                    "name": f"Activity in {destination}",
                    "description": "Placeholder",
                    "category": "experience",
                }
            ]
        except Exception as exc:
            logger.exception("Activities research failed")
            return [{"error": str(exc)}]

    async def _research_practical_info(self, destination: str) -> dict[str, Any]:
        """Research practical travel information for a destination."""
        try:
            webcrawl_tool = self._get_tool("webcrawl_search")
            if webcrawl_tool:
                query = (
                    f"{destination} travel practical information currency "
                    f"transportation visa requirements"
                )
                result = await webcrawl_tool.ainvoke({"query": query})
                return {"practical_data": result, "sources": "web_research"}
            return {
                "currency": "Local currency",
                "language": "Local language",
                "transportation": "Local transport info",
                "visa_requirements": "Visa information",
                "sources": "placeholder",
            }
        except Exception as exc:
            logger.exception("Practical info research failed")
            return {"error": str(exc)}

    async def _research_cultural_info(self, destination: str) -> dict[str, Any]:
        """Research cultural information and customs for a destination."""
        try:
            webcrawl_tool = self._get_tool("webcrawl_search")
            if webcrawl_tool:
                query = (
                    f"{destination} culture customs etiquette local traditions "
                    f"social norms"
                )
                result = await webcrawl_tool.ainvoke({"query": query})
                return {"cultural_data": result, "sources": "web_research"}
            return {
                "customs": "Local customs",
                "etiquette": "Social etiquette",
                "traditions": "Cultural traditions",
                "sources": "placeholder",
            }
        except Exception as exc:
            logger.exception("Cultural info research failed")
            return {"error": str(exc)}

    async def _research_weather_info(
        self, destination: str, travel_dates: str | None
    ) -> dict[str, Any]:
        """Research weather and climate information for a destination."""
        try:
            weather_tool = self._get_tool("get_weather")
            if weather_tool:
                result = await weather_tool.ainvoke({"location": destination})
                return {"weather_data": result, "travel_dates": travel_dates}
            return {
                "climate": "Climate information",
                "best_time_to_visit": "Seasonal recommendations",
                "travel_dates": travel_dates,
                "sources": "placeholder",
            }
        except Exception as exc:
            logger.exception("Weather info research failed")
            return {"error": str(exc)}

    async def _get_location_data(self, destination: str) -> dict[str, Any]:
        """Get location data using Google Maps tools."""
        try:
            maps_tool = self._get_tool("search_places")
            if maps_tool:
                result = await maps_tool.ainvoke({"location": destination})
                return {"location_data": result, "sources": "google_maps"}
            return {
                "coordinates": "Location coordinates",
                "region": "Geographic region",
                "sources": "placeholder",
            }
        except Exception as exc:
            logger.exception("Location data retrieval failed")
            return {"error": str(exc)}

    async def _generate_research_response(
        self,
        research_results: dict[str, Any],
        params: dict[str, Any],
        state: TravelPlanningState,
    ) -> dict[str, Any]:
        """Generate user-friendly response from destination research results.

        Args:
            research_results: Raw research results
            params: Parameters used for research
            state: Current conversation state

        Returns:
            Formatted response message
        """
        if research_results.get("error"):
            content = (
                f"I apologize, but I encountered an issue researching "
                f"{params.get('destination', 'the destination')}: "
                f"{research_results['error']}. Let me try a different approach."
            )
            return self._create_response_message(
                content,
                {
                    "research_type": params.get("research_type"),
                    "destination": params.get("destination"),
                    "results_summary": research_results,
                },
            )

        destination = params.get("destination", "the destination")
        research_type = params.get("research_type", "overview")
        sections = [
            self._format_overview_section(destination, research_type, research_results),
            self._format_attractions_section(research_type, research_results),
            self._format_activities_section(research_type, research_results),
            self._format_practical_section(research_type, research_results),
            self._format_cultural_section(research_type, research_results),
            self._format_weather_section(research_type, research_results),
        ]

        body = "\n".join(filter(None, sections)).strip()
        if body:
            body = f"Here's what I found about {destination}:\n\n{body}\n\n"
        else:
            body = (
                f"I reviewed the latest research for {destination} but did not "
                "identify notable highlights yet.\n\n"
            )

        body += (
            "Would you like me to provide more detailed information about "
            "any specific aspect of your trip?"
        )

        return self._create_response_message(
            body,
            {
                "research_type": research_type,
                "destination": destination,
                "results_summary": research_results,
            },
        )

    def _format_overview_section(
        self, destination: str, research_type: str, research_results: dict[str, Any]
    ) -> str:
        """Render overview subsection."""
        if research_type not in ("overview", "all"):
            return ""

        overview = research_results.get("overview", {})
        if not overview:
            return ""

        details = (
            f"Based on my research, {destination} offers a rich travel experience."
            if overview.get("overview_data")
            else ""
        )
        return f"**Overview:**\n{details}"

    def _format_attractions_section(
        self, research_type: str, research_results: dict[str, Any]
    ) -> str:
        """Render attractions subsection."""
        if research_type not in ("attractions", "all"):
            return ""

        attractions = research_results.get("attractions", [])
        if not attractions or attractions[0].get("error"):
            return ""

        lines = ["**Top Attractions:**"]
        for index, attraction in enumerate(attractions[:5], 1):
            name = attraction.get("name", "Unnamed attraction")
            description = attraction.get("description", "")
            snippet = f"{index}. {name}"
            if description:
                snippet += f"\n   {description[:100]}..."
            lines.append(snippet)
        return "\n".join(lines)

    def _format_activities_section(
        self, research_type: str, research_results: dict[str, Any]
    ) -> str:
        """Render activities subsection."""
        if research_type not in ("activities", "all"):
            return ""

        activities = research_results.get("activities", [])
        if not activities or activities[0].get("error"):
            return ""

        lines = ["**Recommended Activities:**"]
        for index, activity in enumerate(activities[:5], 1):
            name = activity.get("name", "Unnamed activity")
            category = activity.get("category")
            label = f"{index}. {name}"
            if category:
                label += f" ({category})"
            lines.append(label)
        return "\n".join(lines)

    def _format_practical_section(
        self, research_type: str, research_results: dict[str, Any]
    ) -> str:
        """Render practical information subsection."""
        if research_type not in ("practical", "all"):
            return ""

        practical = research_results.get("practical_info", {})
        if not practical or practical.get("error"):
            return ""

        lines = ["**Practical Information:**"]
        if practical.get("currency"):
            lines.append(f"• Currency: {practical['currency']}")
        if practical.get("language"):
            lines.append(f"• Language: {practical['language']}")
        return "\n".join(lines)

    def _format_cultural_section(
        self, research_type: str, research_results: dict[str, Any]
    ) -> str:
        """Render cultural tips subsection."""
        if research_type not in ("culture", "all"):
            return ""

        cultural = research_results.get("cultural_info", {})
        if not cultural or cultural.get("error"):
            return ""

        return "**Cultural Tips:**\nImportant cultural considerations for your visit."

    def _format_weather_section(
        self, research_type: str, research_results: dict[str, Any]
    ) -> str:
        """Render weather insights subsection."""
        if research_type not in ("weather", "all"):
            return ""

        weather = research_results.get("weather_info", {})
        if not weather or weather.get("error"):
            return ""

        lines = ["**Weather Information:**"]
        travel_dates = weather.get("travel_dates")
        if travel_dates:
            lines.append(f"For your travel dates: {travel_dates}")
        lines.append("Weather and seasonal recommendations.")
        return "\n".join(lines)

    async def _handle_general_research_inquiry(
        self, message: str, state: TravelPlanningState
    ) -> dict[str, Any]:
        """Handle general destination research inquiries.

        Args:
            message: User message
            state: Current conversation state

        Returns:
            Response message
        """
        # Use LLM to generate helpful response for general research questions
        response_prompt = f"""
        The user is asking about destination research but hasn't provided enough
        specific information for targeted research.

        User message: "{message}"

        Provide a helpful response that:
        1. Acknowledges their interest in destination information
        2. Asks for the specific destination they want to research
        3. Mentions the types of information you can provide (attractions, activities,
           culture, practical info)
        4. Offers to help once they specify a destination

        Keep the response friendly and concise.
        """

        try:
            if self.llm is None:
                raise RuntimeError("Destination research LLM is not initialized")

            messages = [
                SystemMessage(
                    content="You are a helpful destination research assistant."
                ),
                HumanMessage(content=response_prompt),
            ]

            response = await self.llm.ainvoke(messages)
            raw_content = response.content
            content = raw_content if isinstance(raw_content, str) else str(raw_content)

        except Exception:
            logger.exception("Error generating research response")
            content = (
                "I'd be happy to help you research destinations! Please let me know "
                "which destination you're interested in, and I can provide information "
                "about attractions, activities, cultural insights, practical travel "
                "tips, weather, and much more. What destination would you like to "
                "explore?"
            )

        return self._create_response_message(content)
