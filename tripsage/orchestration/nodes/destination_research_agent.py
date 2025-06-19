"""
Destination research agent node implementation for LangGraph orchestration.

This module implements the destination research agent as a LangGraph node,
replacing the OpenAI Agents SDK implementation with improved performance and
capabilities.
"""

import json
from datetime import datetime, timezone
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from tripsage.orchestration.nodes.base import BaseAgentNode
from tripsage.orchestration.state import TravelPlanningState
from tripsage_core.config import get_settings
from tripsage_core.services.configuration_service import get_configuration_service
from tripsage_core.utils.logging_utils import get_logger

logger = get_logger(__name__)


class DestinationResearchAgentNode(BaseAgentNode):
    """
    Destination research agent node.

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
        self.config_service = get_configuration_service()

        # Store overrides for async config loading
        self.config_overrides = config_overrides
        self.agent_config = None
        self.llm = None

        super().__init__("destination_research_agent", service_registry)

    async def _initialize_tools(self) -> None:
        """Initialize destination research tools using simple tool catalog."""
        from tripsage.orchestration.tools.tools import get_tools_for_agent

        # Load configuration from database if not already loaded
        if self.agent_config is None:
            await self._load_configuration()

        # Get tools for destination research agent using simple catalog
        self.available_tools = get_tools_for_agent("destination_research_agent")

        # Bind tools to LLM for direct use
        if self.llm:
            self.llm_with_tools = self.llm.bind_tools(self.available_tools)

        logger.info(
            f"Initialized destination research agent with "
            f"{len(self.available_tools)} tools"
        )

    async def _load_configuration(self) -> None:
        """Load agent configuration from database with fallback to settings."""
        try:
            # Get configuration from database with runtime overrides
            self.agent_config = await self.config_service.get_agent_config(
                "destination_research_agent", **self.config_overrides
            )

            # Initialize LLM with loaded configuration
            self.llm = ChatOpenAI(
                model=self.agent_config["model"],
                temperature=self.agent_config["temperature"],
                max_tokens=self.agent_config["max_tokens"],
                top_p=self.agent_config["top_p"],
                api_key=self.agent_config["api_key"],
            )

            logger.info(
                f"Loaded destination research agent configuration from database: "
                f"temp={self.agent_config['temperature']}"
            )

        except Exception as e:
            logger.error(f"Failed to load database configuration, using fallback: {e}")

            # Fallback to settings-based configuration
            settings = get_settings()
            self.agent_config = settings.get_agent_config(
                "destination_research_agent", **self.config_overrides
            )

            self.llm = ChatOpenAI(
                model=self.agent_config["model"],
                temperature=self.agent_config["temperature"],
                max_tokens=self.agent_config["max_tokens"],
                top_p=self.agent_config["top_p"],
                api_key=self.agent_config["api_key"],
            )

    async def process(self, state: TravelPlanningState) -> TravelPlanningState:
        """
        Process destination research requests.

        Args:
            state: Current travel planning state

        Returns:
            Updated state with destination research and response
        """
        # Ensure configuration is loaded before processing
        if self.agent_config is None:
            await self._load_configuration()

        user_message = state["messages"][-1]["content"] if state["messages"] else ""

        # Extract research parameters from user message and context
        research_params = await self._extract_research_parameters(user_message, state)

        if research_params:
            # Perform destination research using MCP integration
            research_results = await self._research_destination(research_params, state)

            # Update state with results
            research_record = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "parameters": research_params,
                "results": research_results,
                "agent": "destination_research_agent",
            }

            if "destination_research" not in state:
                state["destination_research"] = []
            state["destination_research"].append(research_record)

            # Store research results in destination_info for other agents
            if "destination_info" not in state:
                state["destination_info"] = {}

            destination = research_params.get("destination", "")
            if destination:
                state["destination_info"][destination] = research_results

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
        """
        Extract destination research parameters from user message and conversation
        context.

        Args:
            message: User message to analyze
            state: Current conversation state for context

        Returns:
            Dictionary of research parameters or None if insufficient info
        """
        # Use LLM to extract parameters and determine research type
        extraction_prompt = f"""
        Extract destination research parameters from this message and context.
        
        User message: "{message}"
        
        Context from conversation:
        - Previous destination research: {len(state.get("destination_research", []))}
        - Flight searches: {len(state.get("flight_searches", []))}
        - Accommodation searches: {len(state.get("accommodation_searches", []))}
        - User preferences: {state.get("user_preferences", "None")}
        - Current destination info: {list(state.get("destination_info", {}).keys())}
        
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
            messages = [
                SystemMessage(
                    content="You are a destination research parameter extraction "
                    "assistant."
                ),
                HumanMessage(content=extraction_prompt),
            ]

            response = await self.llm.ainvoke(messages)

            # Parse the response
            if response.content.strip().lower() in ["null", "none", "{}"]:
                return None

            params = json.loads(response.content)

            # Validate required fields
            if params and params.get("destination"):
                return params
            else:
                return None

        except Exception as e:
            logger.error(f"Error extracting research parameters: {str(e)}")
            return None

    async def _research_destination(
        self, params: dict[str, Any], state: TravelPlanningState
    ) -> dict[str, Any]:
        """
        Perform comprehensive destination research using MCP tools.

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

            # Use web crawling for comprehensive research
            if research_type in ["overview", "all"]:
                overview_results = await self._research_overview(destination)
                research_results["overview"] = overview_results

            if research_type in ["attractions", "all"]:
                attractions_results = await self._research_attractions(
                    destination, specific_interests
                )
                research_results["attractions"] = attractions_results

            if research_type in ["activities", "all"]:
                activities_results = await self._research_activities(
                    destination, specific_interests
                )
                research_results["activities"] = activities_results

            if research_type in ["practical", "all"]:
                practical_results = await self._research_practical_info(destination)
                research_results["practical_info"] = practical_results

            if research_type in ["culture", "all"]:
                cultural_results = await self._research_cultural_info(destination)
                research_results["cultural_info"] = cultural_results

            if research_type in ["weather", "all"]:
                weather_results = await self._research_weather_info(
                    destination, params.get("travel_dates")
                )
                research_results["weather_info"] = weather_results

            # Use Google Maps for location data
            location_data = await self._get_location_data(destination)
            research_results["location_data"] = location_data

            logger.info(f"Destination research completed for {destination}")
            return research_results

        except Exception as e:
            logger.error(f"Destination research failed for {destination}: {str(e)}")
            return {"error": f"Research failed: {str(e)}", "destination": destination}

    async def _research_overview(self, destination: str) -> dict[str, Any]:
        """Research general overview information about a destination."""
        try:
            # Use web crawling tool for comprehensive overview
            webcrawl_tool = self.tool_registry.get_tool("webcrawl_search")
            if webcrawl_tool:
                query = f"{destination} travel guide overview tourism information"
                result = await webcrawl_tool._arun(query=query, max_results=3)
                return {"overview_data": result, "sources": "web_research"}
            else:
                return {
                    "overview_data": f"Overview research for {destination}",
                    "sources": "placeholder",
                }
        except Exception as e:
            logger.error(f"Overview research failed: {str(e)}")
            return {"error": str(e)}

    async def _research_attractions(self, destination: str, interests: list) -> list:
        """Research attractions and landmarks in a destination."""
        try:
            # Use web crawling and maps tools for attractions
            webcrawl_tool = self.tool_registry.get_tool("webcrawl_search")
            if webcrawl_tool:
                interest_str = " ".join(interests) if interests else "top attractions"
                query = f"{destination} {interest_str} landmarks must-see attractions"
                result = await webcrawl_tool._arun(query=query, max_results=5)

                # Parse attractions from results
                attractions = []
                if isinstance(result, str):
                    # Simple parsing - in real implementation this would be
                    # more sophisticated
                    attractions = [
                        {
                            "name": f"Attraction in {destination}",
                            "description": "Research result",
                            "type": "landmark",
                        }
                        for _ in range(3)  # Placeholder
                    ]

                return attractions
            else:
                return [
                    {
                        "name": f"Top attraction in {destination}",
                        "description": "Placeholder",
                        "type": "landmark",
                    }
                ]
        except Exception as e:
            logger.error(f"Attractions research failed: {str(e)}")
            return [{"error": str(e)}]

    async def _research_activities(self, destination: str, interests: list) -> list:
        """Research activities and experiences in a destination."""
        try:
            # Use web crawling for activities research
            webcrawl_tool = self.tool_registry.get_tool("webcrawl_search")
            if webcrawl_tool:
                interest_str = (
                    " ".join(interests) if interests else "activities experiences"
                )
                query = (
                    f"{destination} {interest_str} things to do activities experiences"
                )
                result = await webcrawl_tool._arun(query=query, max_results=5)

                # Parse activities from results
                activities = []
                if isinstance(result, str):
                    # Simple parsing - in real implementation this would be
                    # more sophisticated
                    activities = [
                        {
                            "name": f"Activity in {destination}",
                            "description": "Research result",
                            "category": "experience",
                        }
                        for _ in range(3)  # Placeholder
                    ]

                return activities
            else:
                return [
                    {
                        "name": f"Activity in {destination}",
                        "description": "Placeholder",
                        "category": "experience",
                    }
                ]
        except Exception as e:
            logger.error(f"Activities research failed: {str(e)}")
            return [{"error": str(e)}]

    async def _research_practical_info(self, destination: str) -> dict[str, Any]:
        """Research practical travel information for a destination."""
        try:
            # Use web crawling for practical information
            webcrawl_tool = self.tool_registry.get_tool("webcrawl_search")
            if webcrawl_tool:
                query = (
                    f"{destination} travel practical information currency "
                    "transportation visa requirements"
                )
                result = await webcrawl_tool._arun(query=query, max_results=3)
                return {"practical_data": result, "sources": "web_research"}
            else:
                return {
                    "currency": "Local currency",
                    "language": "Local language",
                    "transportation": "Local transport info",
                    "visa_requirements": "Visa information",
                    "sources": "placeholder",
                }
        except Exception as e:
            logger.error(f"Practical info research failed: {str(e)}")
            return {"error": str(e)}

    async def _research_cultural_info(self, destination: str) -> dict[str, Any]:
        """Research cultural information and customs for a destination."""
        try:
            # Use web crawling for cultural information
            webcrawl_tool = self.tool_registry.get_tool("webcrawl_search")
            if webcrawl_tool:
                query = (
                    f"{destination} culture customs etiquette local traditions "
                    "social norms"
                )
                result = await webcrawl_tool._arun(query=query, max_results=3)
                return {"cultural_data": result, "sources": "web_research"}
            else:
                return {
                    "customs": "Local customs",
                    "etiquette": "Social etiquette",
                    "traditions": "Cultural traditions",
                    "sources": "placeholder",
                }
        except Exception as e:
            logger.error(f"Cultural info research failed: {str(e)}")
            return {"error": str(e)}

    async def _research_weather_info(
        self, destination: str, travel_dates: str | None
    ) -> dict[str, Any]:
        """Research weather and climate information for a destination."""
        try:
            # Use weather tools for climate information
            weather_tool = self.tool_registry.get_tool("get_weather")
            if weather_tool:
                result = await weather_tool._arun(location=destination)
                return {"weather_data": result, "travel_dates": travel_dates}
            else:
                return {
                    "climate": "Climate information",
                    "best_time_to_visit": "Seasonal recommendations",
                    "travel_dates": travel_dates,
                    "sources": "placeholder",
                }
        except Exception as e:
            logger.error(f"Weather info research failed: {str(e)}")
            return {"error": str(e)}

    async def _get_location_data(self, destination: str) -> dict[str, Any]:
        """Get location data using Google Maps tools."""
        try:
            # Use Google Maps for location information
            maps_tool = self.tool_registry.get_tool("search_places")
            if maps_tool:
                result = await maps_tool._arun(query=destination)
                return {"location_data": result, "sources": "google_maps"}
            else:
                return {
                    "coordinates": "Location coordinates",
                    "region": "Geographic region",
                    "sources": "placeholder",
                }
        except Exception as e:
            logger.error(f"Location data retrieval failed: {str(e)}")
            return {"error": str(e)}

    async def _generate_research_response(
        self,
        research_results: dict[str, Any],
        params: dict[str, Any],
        state: TravelPlanningState,
    ) -> dict[str, Any]:
        """
        Generate user-friendly response from destination research results.

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
        else:
            destination = params.get("destination", "the destination")
            research_type = params.get("research_type", "overview")

            content = f"Here's what I found about {destination}:\n\n"

            if research_type == "overview" or research_type == "all":
                content += "**Overview:**\n"
                overview = research_results.get("overview", {})
                if overview.get("overview_data"):
                    content += (
                        f"Based on my research, {destination} offers a rich travel "
                        "experience. "
                    )
                content += "\n"

            if research_type == "attractions" or research_type == "all":
                attractions = research_results.get("attractions", [])
                if attractions and not attractions[0].get("error"):
                    content += "**Top Attractions:**\n"
                    for i, attraction in enumerate(attractions[:5], 1):
                        name = attraction.get("name", "Unnamed attraction")
                        description = attraction.get("description", "")
                        content += f"{i}. {name}\n"
                        if description:
                            content += f"   {description[:100]}...\n"
                    content += "\n"

            if research_type == "activities" or research_type == "all":
                activities = research_results.get("activities", [])
                if activities and not activities[0].get("error"):
                    content += "**Recommended Activities:**\n"
                    for i, activity in enumerate(activities[:5], 1):
                        name = activity.get("name", "Unnamed activity")
                        category = activity.get("category", "")
                        content += f"{i}. {name}"
                        if category:
                            content += f" ({category})"
                        content += "\n"
                    content += "\n"

            if research_type == "practical" or research_type == "all":
                practical = research_results.get("practical_info", {})
                if practical and not practical.get("error"):
                    content += "**Practical Information:**\n"
                    if practical.get("currency"):
                        content += f"• Currency: {practical['currency']}\n"
                    if practical.get("language"):
                        content += f"• Language: {practical['language']}\n"
                    content += "\n"

            if research_type == "culture" or research_type == "all":
                cultural = research_results.get("cultural_info", {})
                if cultural and not cultural.get("error"):
                    content += "**Cultural Tips:**\n"
                    content += "Important cultural considerations for your visit.\n\n"

            if research_type == "weather" or research_type == "all":
                weather = research_results.get("weather_info", {})
                if weather and not weather.get("error"):
                    content += "**Weather Information:**\n"
                    if weather.get("travel_dates"):
                        content += f"For your travel dates: {weather['travel_dates']}\n"
                    content += "Weather and seasonal recommendations.\n\n"

            content += (
                "Would you like me to provide more detailed information about any "
                "specific aspect of your trip?"
            )

        return self._create_response_message(
            content,
            {
                "research_type": params.get("research_type"),
                "destination": params.get("destination"),
                "results_summary": research_results,
            },
        )

    async def _handle_general_research_inquiry(
        self, message: str, state: TravelPlanningState
    ) -> dict[str, Any]:
        """
        Handle general destination research inquiries.

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
            messages = [
                SystemMessage(
                    content="You are a helpful destination research assistant."
                ),
                HumanMessage(content=response_prompt),
            ]

            response = await self.llm.ainvoke(messages)
            content = response.content

        except Exception as e:
            logger.error(f"Error generating research response: {str(e)}")
            content = (
                "I'd be happy to help you research destinations! Please let me know "
                "which destination you're interested in, and I can provide information "
                "about attractions, activities, cultural insights, practical travel "
                "tips, weather, and much more. What destination would you like to "
                "explore?"
            )

        return self._create_response_message(content)
