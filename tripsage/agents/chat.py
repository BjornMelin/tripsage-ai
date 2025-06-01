"""
Chat Agent implementation for TripSage.

This module provides the central chat agent that coordinates with specialized
agents and manages tool calling for travel planning tasks.
Refactored to use dependency injection and service-based architecture.
"""

import re
import time
from typing import Any, Dict, List, Optional

from tripsage.agents.accommodation import AccommodationAgent
from tripsage.agents.base import BaseAgent
from tripsage.agents.budget import Budget as BudgetAgent
from tripsage.agents.destination_research import DestinationResearchAgent
from tripsage.agents.flight import FlightAgent
from tripsage.agents.itinerary import Itinerary as ItineraryAgent
from tripsage.agents.service_registry import ServiceRegistry
from tripsage.agents.travel import TravelAgent
from tripsage_core.config.base_app_settings import get_settings
from tripsage_core.exceptions import CoreTripSageError
from tripsage_core.utils.decorator_utils import with_error_handling
from tripsage_core.utils.error_handling_utils import log_exception
from tripsage_core.utils.logging_utils import get_logger

logger = get_logger(__name__)
settings = get_settings()


class ChatAgentError(CoreTripSageError):
    """Error raised when chat agent operations fail."""

    pass


class ChatAgent(BaseAgent):
    """
    Central chat agent that coordinates with specialized agents and manages tool calling
    """

    def __init__(
        self,
        service_registry: ServiceRegistry,
        name: str = "TripSage Chat Assistant",
        model: str = None,
        temperature: float = None,
    ):
        """Initialize the chat agent with dependency injection.

        Args:
            service_registry: Service registry for dependency injection
            name: Agent name
            model: Model name to use (defaults to settings if None)
            temperature: Temperature for model sampling (defaults to settings if None)
        """
        # Define comprehensive chat instructions
        instructions = """
        You are TripSage's central chat assistant, specializing in intelligent travel
        planning coordination. Your role is to understand user intent and route requests
        to the most appropriate specialized agent while managing tool calling for travel
        operations.
        
        CORE RESPONSIBILITIES:
        1. Analyze user messages to detect travel intent and requirements
        2. Route complex requests to specialized agents (flights, hotels, itineraries,
        etc.)
        3. Execute travel tools directly for simple queries (weather, maps, time)
        4. Coordinate multi-step travel planning workflows
        5. Maintain conversation context and user preferences
        6. Provide personalized recommendations based on user's travel history and
        preferences
        
        AGENT ROUTING STRATEGY:
        - Flight-focused queries → FlightAgent
        - Hotel/accommodation queries → AccommodationAgent  
        - Budget planning → BudgetAgent
        - Destination research → DestinationResearchAgent
        - Itinerary creation → ItineraryAgent
        - General travel planning → TravelAgent
        - Simple tool calls → Handle directly
        
        INTENT DETECTION KEYWORDS:
        Flight: "flight", "fly", "airline", "airport", "departure", "arrival", "booking"
        Hotel: "hotel", "accommodation", "stay", "room", "lodge", "resort", "airbnb"
        Budget: "budget", "cost", "price", "money", "expense", "afford", "cheap"
        Destination: "destination", "place", "city", "country", "attractions", "culture"
        Itinerary: "itinerary", "schedule", "plan", "day-by-day", "timeline", "agenda"
        
        TOOL CALLING GUIDELINES:
        - Use MCP tools for real-time data: weather, maps, flights, accommodations
        - Always validate tool parameters before execution
        - Format tool results for user-friendly display
        - Handle tool failures gracefully with clear error messages
        - Respect rate limits (5 tool calls per minute per user)
        
        PERSONALIZATION:
        - If user context is available in the session, use it to personalize responses
        - Reference previous trips, preferences, and travel style when relevant
        - Suggest options that align with the user's budget patterns and preferences
        - Adapt communication style based on user's travel experience level
        - Remember dietary restrictions, accessibility needs, and special requirements
        
        RESPONSE FORMAT:
        - Be conversational but informative
        - Use structured data when presenting options
        - Include relevant details without overwhelming
        - Ask clarifying questions when intent is unclear
        - Provide next steps or actionable recommendations
        - When available, reference user's previous preferences and travel history
        
        TOOL EXECUTION:
        When executing tools, always:
        1. Explain what you're doing ("Let me search for flights...")
        2. Show progress for long-running operations
        3. Present results in digestible format
        4. Offer to perform related actions
        
        Remember: You're the central coordinator. Route complex domain-specific
        tasks to specialists, but handle simple tool calls and general coordination
        yourself.
        """

        model = model or settings.agent.model_name
        temperature = temperature or settings.agent.temperature

        super().__init__(
            name=name,
            instructions=instructions,
            service_registry=service_registry,
            model=model,
            temperature=temperature,
            metadata={"agent_type": "chat_coordinator", "version": "2.0.0"},
        )

        # Track tool call rate limiting
        self._tool_call_history: Dict[str, List[float]] = {}
        self._max_tool_calls_per_minute = 5

        # Initialize specialized agents
        self._initialize_specialized_agents()

        # Register travel tools
        self._register_travel_tools()

        logger.info("ChatAgent initialized with service-based architecture")

    def _initialize_specialized_agents(self) -> None:
        """Initialize specialized agents for routing with service injection."""
        try:
            # All specialized agents now use the same service registry
            self.flight_agent = FlightAgent(service_registry=self.service_registry)
            self.accommodation_agent = AccommodationAgent(
                service_registry=self.service_registry
            )
            self.budget_agent = BudgetAgent(service_registry=self.service_registry)
            self.destination_agent = DestinationResearchAgent(
                service_registry=self.service_registry
            )
            self.itinerary_agent = ItineraryAgent(
                service_registry=self.service_registry
            )
            self.travel_agent = TravelAgent(service_registry=self.service_registry)

            logger.info("Initialized specialized agents with service injection")
        except Exception as e:
            logger.error(f"Failed to initialize specialized agents: {str(e)}")
            log_exception(e)
            # Continue without specialized agents

    def _register_travel_tools(self) -> None:
        """Register travel-specific tools for direct execution."""
        # Register core travel tool groups with service injection
        tool_modules = [
            "time_tools",
            "weather_tools",
            "googlemaps_tools",
            "webcrawl_tools",
            "memory_tools",
        ]

        for module in tool_modules:
            try:
                self.register_tool_group(module, service_registry=self.service_registry)
            except Exception as e:
                logger.warning(f"Could not register tool module {module}: {str(e)}")

    async def _get_user_context(self, user_id: str) -> Dict[str, Any]:
        """Get user context from memory for personalization.

        Args:
            user_id: User identifier

        Returns:
            User context including preferences and history
        """
        try:
            if self.service_registry.memory_service:
                context = await self.service_registry.memory_service.get_user_context(
                    user_id
                )

                # Extract key personalization data
                user_context = {
                    "preferences": context.get("preferences", []),
                    "past_trips": context.get("past_trips", []),
                    "budget_patterns": context.get("budget_patterns", []),
                    "travel_style": context.get("travel_style", []),
                    "insights": context.get("insights", {}),
                    "summary": context.get("summary", ""),
                }

                logger.debug(
                    f"Retrieved user context for {user_id}: "
                    f"{len(context.get('preferences', []))} preferences"
                )
                return user_context
            else:
                logger.warning("Memory service not available for user context")
                return {}

        except Exception as e:
            logger.warning(f"Failed to get user context for {user_id}: {e}")
            return {}

    async def _store_conversation_memory(
        self,
        user_message: str,
        assistant_response: str,
        user_id: str,
        session_id: Optional[str] = None,
    ) -> None:
        """Store conversation in memory for future personalization.

        Args:
            user_message: User's message
            assistant_response: Assistant's response
            user_id: User identifier
            session_id: Optional session identifier
        """
        try:
            if self.service_registry.memory_service:
                # Create conversation messages
                messages = [
                    {"role": "user", "content": user_message},
                    {"role": "assistant", "content": assistant_response},
                ]

                # Store in memory with travel context
                await self.service_registry.memory_service.add_conversation_memory(
                    messages=messages,
                    user_id=user_id,
                    session_id=session_id,
                    metadata={
                        "source": "chat_agent",
                        "agent_type": "travel_coordinator",
                    },
                )

                logger.debug(f"Stored conversation memory for user {user_id}")
            else:
                logger.warning("Memory service not available for storing conversation")

        except Exception as e:
            logger.warning(f"Failed to store conversation memory for {user_id}: {e}")

    async def detect_intent(self, message: str) -> Dict[str, Any]:
        """Detect user intent from message content.

        Args:
            message: User message to analyze

        Returns:
            Dictionary with intent information
        """
        message_lower = message.lower()

        # Define intent keywords with weights
        intent_patterns = {
            "flight": {
                "keywords": [
                    "flight",
                    "fly",
                    "airline",
                    "airport",
                    "departure",
                    "arrival",
                    "book",
                    "ticket",
                ],
                "patterns": [
                    r"\bfly\s+to\b",
                    r"\bflight\s+from\b",
                    r"\bbook.*flight\b",
                ],
                "weight": 0,
            },
            "accommodation": {
                "keywords": [
                    "hotel",
                    "accommodation",
                    "stay",
                    "room",
                    "lodge",
                    "resort",
                    "airbnb",
                    "booking",
                    "check in",
                    "check out",
                ],
                "patterns": [
                    r"\bstay\s+in\b",
                    r"\bbook.*hotel\b",
                    r"\bfind.*accommodation\b",
                ],
                "weight": 0,
            },
            "budget": {
                "keywords": [
                    "budget",
                    "cost",
                    "price",
                    "money",
                    "expense",
                    "afford",
                    "cheap",
                    "expensive",
                    "deal",
                    "$",
                ],
                "patterns": [r"\bhow\s+much\b", r"\bbudget\s+for\b", r"\bcost\s+of\b"],
                "weight": 0,
            },
            "destination": {
                "keywords": [
                    "destination",
                    "place",
                    "city",
                    "country",
                    "attractions",
                    "culture",
                    "visit",
                    "explore",
                    "sights",
                    "tourist",
                ],
                "patterns": [
                    r"\bwhere.*go\b",
                    r"\bplaces\s+to\s+visit\b",
                    r"\bthings\s+to\s+do\b",
                ],
                "weight": 0,
            },
            "itinerary": {
                "keywords": [
                    "itinerary",
                    "schedule",
                    "plan",
                    "day-by-day",
                    "timeline",
                    "agenda",
                    "trip plan",
                    "organize",
                ],
                "patterns": [
                    r"\bplan.*trip\b",
                    r"\bcreate.*itinerary\b",
                    r"\bday\s+by\s+day\b",
                ],
                "weight": 0,
            },
            "general": {
                "keywords": [
                    "travel",
                    "trip",
                    "vacation",
                    "journey",
                    "tour",
                    "holiday",
                ],
                "patterns": [r"\bplan.*travel\b", r"\bhelp.*trip\b"],
                "weight": 0,
            },
        }

        # Calculate weights for each intent
        for _intent, config in intent_patterns.items():
            # Check keywords
            for keyword in config["keywords"]:
                if keyword in message_lower:
                    config["weight"] += 1

            # Check patterns
            for pattern in config["patterns"]:
                if re.search(pattern, message_lower):
                    config["weight"] += 2  # Patterns get higher weight

        # Find the intent with highest weight
        primary_intent = max(intent_patterns.items(), key=lambda x: x[1]["weight"])

        # Check if multiple intents have high weights (multi-intent query)
        multi_intent = []
        for intent, config in intent_patterns.items():
            if config["weight"] > 0 and intent != primary_intent[0]:
                multi_intent.append(intent)

        return {
            "primary": primary_intent[0]
            if primary_intent[1]["weight"] > 0
            else "general",
            "confidence": min(
                primary_intent[1]["weight"] / 5.0, 1.0
            ),  # Normalize to 0-1
            "multi_intent": multi_intent,
            "requires_clarification": primary_intent[1]["weight"] == 0,
        }

    @with_error_handling
    async def route_to_specialist(
        self, intent: Dict[str, Any], user_input: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Route request to appropriate specialist agent.

        Args:
            intent: Detected intent information
            user_input: Original user input
            context: Request context

        Returns:
            Specialist agent response
        """
        primary_intent = intent["primary"]

        # Map intents to specialist agents
        agent_map = {
            "flight": self.flight_agent,
            "accommodation": self.accommodation_agent,
            "budget": self.budget_agent,
            "destination": self.destination_agent,
            "itinerary": self.itinerary_agent,
            "general": self.travel_agent,
        }

        specialist = agent_map.get(primary_intent, self.travel_agent)

        logger.info(
            f"Routing to {specialist.__class__.__name__} for {primary_intent} intent"
        )

        # Add routing metadata to context
        context["routed_from"] = "ChatAgent"
        context["detected_intent"] = intent

        # Execute specialist agent
        result = await specialist.run(user_input, context)

        return result

    async def run(
        self, user_input: str, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Run the chat agent with user input.

        This method overrides the base agent's run method to add intent detection
        and routing logic before executing the standard agent flow.

        Args:
            user_input: User input text
            context: Optional context data

        Returns:
            Dictionary with the agent's response and other information
        """
        try:
            # Detect intent first
            intent = await self.detect_intent(user_input)
            logger.info(
                f"Detected intent: {intent['primary']} with confidence "
                f"{intent['confidence']}"
            )

            # Add intent to context
            if context is None:
                context = {}
            context["detected_intent"] = intent

            # Get user context for personalization if user_id is provided
            user_id = context.get("user_id")
            if user_id:
                user_context = await self._get_user_context(user_id)
                context["user_context"] = user_context

            # Route to specialist if high confidence and not a simple tool query
            if intent["confidence"] > 0.6 and intent["primary"] != "general":
                # Check if this is a simple tool query that we can handle directly
                tool_keywords = ["weather", "time", "map", "direction", "temperature"]
                is_tool_query = any(kw in user_input.lower() for kw in tool_keywords)

                if not is_tool_query:
                    # Route to specialist
                    result = await self.route_to_specialist(intent, user_input, context)

                    # Store conversation memory if user_id provided
                    if user_id and "content" in result:
                        await self._store_conversation_memory(
                            user_input,
                            result["content"],
                            user_id,
                            context.get("session_id"),
                        )

                    return result

            # Otherwise, handle with base agent (tool calling or general chat)
            result = await super().run(user_input, context)

            # Store conversation memory if user_id provided
            if user_id and "content" in result:
                await self._store_conversation_memory(
                    user_input, result["content"], user_id, context.get("session_id")
                )

            return result

        except Exception as e:
            logger.error(f"Error in ChatAgent run: {str(e)}")
            log_exception(e)
            return {
                "content": (
                    "I apologize, but I encountered an issue processing your request. "
                    "Could you please try rephrasing or let me know how I can help you "
                    "with your travel planning?"
                ),
                "status": "error",
                "error_type": type(e).__name__,
                "error_message": str(e),
            }

    def check_rate_limit(self, user_id: str) -> bool:
        """Check if user is within rate limit for tool calls.

        Args:
            user_id: User identifier

        Returns:
            True if within rate limit, False otherwise
        """
        current_time = time.time()

        # Clean up old entries
        if user_id in self._tool_call_history:
            self._tool_call_history[user_id] = [
                t
                for t in self._tool_call_history[user_id]
                if current_time - t < 60  # Keep only last minute
            ]
        else:
            self._tool_call_history[user_id] = []

        # Check rate limit
        return len(self._tool_call_history[user_id]) < self._max_tool_calls_per_minute

    def record_tool_call(self, user_id: str) -> None:
        """Record a tool call for rate limiting.

        Args:
            user_id: User identifier
        """
        current_time = time.time()

        if user_id not in self._tool_call_history:
            self._tool_call_history[user_id] = []

        self._tool_call_history[user_id].append(current_time)
