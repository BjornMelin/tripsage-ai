"""
Chat Agent implementation for TripSage.

This module provides the central chat agent that coordinates with specialized
agents and manages tool calling for travel planning tasks.
"""

import re
import time
from typing import Any, Dict, List, Optional

from tripsage.agents.accommodation import AccommodationAgent
from tripsage.agents.base import BaseAgent
from tripsage.agents.budget import BudgetAgent
from tripsage.agents.destination_research import DestinationResearchAgent
from tripsage.agents.flight import FlightAgent
from tripsage.agents.itinerary import ItineraryAgent
from tripsage.agents.travel import TravelAgent
from tripsage.config.app_settings import settings
from tripsage.mcp_abstraction.manager import mcp_manager
from tripsage.utils.error_handling import log_exception
from tripsage.utils.logging import get_module_logger

logger = get_module_logger(__name__)


class ChatAgent(BaseAgent):
    """Central chat agent that coordinates with specialized agents and manages tool calling."""

    def __init__(
        self,
        name: str = "TripSage Chat Assistant",
        model: str = None,
        temperature: float = None,
    ):
        """Initialize the chat agent.

        Args:
            name: Agent name
            model: Model name to use (defaults to settings if None)
            temperature: Temperature for model sampling (defaults to settings if None)
        """
        # Define comprehensive chat instructions
        instructions = """
        You are TripSage's central chat assistant, specializing in intelligent travel planning
        coordination. Your role is to understand user intent and route requests to the most
        appropriate specialized agent while managing tool calling for travel operations.
        
        CORE RESPONSIBILITIES:
        1. Analyze user messages to detect travel intent and requirements
        2. Route complex requests to specialized agents (flights, hotels, itineraries, etc.)
        3. Execute travel tools directly for simple queries (weather, maps, time)
        4. Coordinate multi-step travel planning workflows
        5. Maintain conversation context and user preferences
        
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
        
        RESPONSE FORMAT:
        - Be conversational but informative
        - Use structured data when presenting options
        - Include relevant details without overwhelming
        - Ask clarifying questions when intent is unclear
        - Provide next steps or actionable recommendations
        
        TOOL EXECUTION:
        When executing tools, always:
        1. Explain what you're doing ("Let me search for flights...")
        2. Show progress for long-running operations
        3. Present results in digestible format
        4. Offer to perform related actions
        
        Remember: You're the central coordinator. Route complex domain-specific
        tasks to specialists, but handle simple tool calls and general coordination yourself.
        """

        model = model or settings.agent.model_name
        temperature = temperature or settings.agent.temperature

        super().__init__(
            name=name,
            instructions=instructions,
            model=model,
            temperature=temperature,
            metadata={"agent_type": "chat_coordinator", "version": "1.0.0"},
        )

        # Initialize specialized agents
        self._initialize_specialized_agents()

        # Register travel tools
        self._register_travel_tools()

        # Track tool call rate limiting
        self._tool_call_history: Dict[str, List[float]] = {}
        self._max_tool_calls_per_minute = 5

    def _initialize_specialized_agents(self) -> None:
        """Initialize specialized agents for routing."""
        try:
            self.flight_agent = FlightAgent()
            self.accommodation_agent = AccommodationAgent()
            self.budget_agent = BudgetAgent()
            self.destination_agent = DestinationResearchAgent()
            self.itinerary_agent = ItineraryAgent()
            self.travel_agent = TravelAgent()

            logger.info("Initialized specialized agents for chat coordination")
        except Exception as e:
            logger.error(f"Failed to initialize specialized agents: {str(e)}")
            log_exception(e)
            # Continue without specialized agents - will fallback to tools

    def _register_travel_tools(self) -> None:
        """Register travel-specific tools for direct execution."""
        # Register core travel tool groups
        tool_modules = [
            "time_tools",
            "weather_tools",
            "googlemaps_tools",
            "webcrawl_tools",
            "memory_tools",
        ]

        for module in tool_modules:
            try:
                self.register_tool_group(module)
            except Exception as e:
                logger.warning(f"Could not register tool module {module}: {str(e)}")

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
                "weight": 0.0,
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
                ],
                "patterns": [r"\bstay\s+in\b", r"\bhotel\s+in\b", r"\bbook.*hotel\b"],
                "weight": 0.0,
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
                ],
                "patterns": [r"\bhow\s+much\b", r"\bcost\s+of\b", r"\bbudget\s+for\b"],
                "weight": 0.0,
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
                ],
                "patterns": [
                    r"\bwhere\s+to\b",
                    r"\bplaces\s+to\b",
                    r"\battraction.*in\b",
                ],
                "weight": 0.0,
            },
            "itinerary": {
                "keywords": [
                    "itinerary",
                    "schedule",
                    "plan",
                    "day-by-day",
                    "timeline",
                    "agenda",
                ],
                "patterns": [
                    r"\bday\s+\d+\b",
                    r"\bschedule\s+for\b",
                    r"\bplan.*trip\b",
                ],
                "weight": 0.0,
            },
            "weather": {
                "keywords": [
                    "weather",
                    "temperature",
                    "rain",
                    "sunny",
                    "forecast",
                    "climate",
                ],
                "patterns": [r"\bweather\s+in\b", r"\btemperature.*in\b"],
                "weight": 0.0,
            },
            "maps": {
                "keywords": [
                    "direction",
                    "location",
                    "address",
                    "distance",
                    "route",
                    "map",
                ],
                "patterns": [
                    r"\bhow\s+to\s+get\b",
                    r"\bdirection.*to\b",
                    r"\bwhere\s+is\b",
                ],
                "weight": 0.0,
            },
        }

        # Calculate intent scores
        for intent, config in intent_patterns.items():
            # Check keywords
            for keyword in config["keywords"]:
                if keyword in message_lower:
                    config["weight"] += 1

            # Check patterns
            for pattern in config["patterns"]:
                if re.search(pattern, message_lower):
                    config["weight"] += 2

        # Find dominant intent
        max_weight = max(config["weight"] for config in intent_patterns.values())

        if max_weight == 0:
            primary_intent = "general"
            confidence = 0.5
        else:
            primary_intent = max(
                intent_patterns.keys(), key=lambda k: intent_patterns[k]["weight"]
            )
            confidence = min(max_weight / 5.0, 1.0)  # Normalize to 0-1

        return {
            "primary_intent": primary_intent,
            "confidence": confidence,
            "all_scores": {k: v["weight"] for k, v in intent_patterns.items()},
            "requires_routing": confidence > 0.7
            and primary_intent
            in ["flight", "accommodation", "budget", "destination", "itinerary"],
        }

    async def check_tool_rate_limit(self, user_id: str) -> bool:
        """Check if user has exceeded tool call rate limit.

        Args:
            user_id: User identifier

        Returns:
            True if within rate limit, False if exceeded
        """
        now = time.time()
        user_calls = self._tool_call_history.get(user_id, [])

        # Remove calls older than 1 minute
        recent_calls = [call_time for call_time in user_calls if now - call_time < 60]
        self._tool_call_history[user_id] = recent_calls

        return len(recent_calls) < self._max_tool_calls_per_minute

    async def log_tool_call(self, user_id: str) -> None:
        """Log a tool call for rate limiting.

        Args:
            user_id: User identifier
        """
        now = time.time()
        if user_id not in self._tool_call_history:
            self._tool_call_history[user_id] = []
        self._tool_call_history[user_id].append(now)

    async def route_to_agent(
        self, intent: Dict[str, Any], message: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Route message to appropriate specialized agent.

        Args:
            intent: Intent detection results
            message: User message
            context: Conversation context

        Returns:
            Agent response
        """
        primary_intent = intent["primary_intent"]

        try:
            if primary_intent == "flight" and hasattr(self, "flight_agent"):
                logger.info("Routing to FlightAgent")
                return await self.flight_agent.run(message, context)

            elif primary_intent == "accommodation" and hasattr(
                self, "accommodation_agent"
            ):
                logger.info("Routing to AccommodationAgent")
                return await self.accommodation_agent.run(message, context)

            elif primary_intent == "budget" and hasattr(self, "budget_agent"):
                logger.info("Routing to BudgetAgent")
                return await self.budget_agent.run(message, context)

            elif primary_intent == "destination" and hasattr(self, "destination_agent"):
                logger.info("Routing to DestinationResearchAgent")
                return await self.destination_agent.run(message, context)

            elif primary_intent == "itinerary" and hasattr(self, "itinerary_agent"):
                logger.info("Routing to ItineraryAgent")
                return await self.itinerary_agent.run(message, context)

            else:
                # Fallback to general travel agent
                logger.info("Routing to TravelAgent (general)")
                if hasattr(self, "travel_agent"):
                    return await self.travel_agent.run(message, context)
                else:
                    # Handle directly if no travel agent available
                    return await self.run(message, context)

        except Exception as e:
            logger.error(f"Error routing to {primary_intent} agent: {str(e)}")
            log_exception(e)

            # Fallback to direct handling
            return {
                "content": f"I encountered an issue with the {primary_intent} specialist. Let me help you directly.",
                "status": "fallback",
                "original_error": str(e),
            }

    async def execute_tool_call(
        self, tool_name: str, parameters: Dict[str, Any], user_id: str
    ) -> Dict[str, Any]:
        """Execute a tool call with rate limiting and error handling.

        Args:
            tool_name: Name of the tool to execute
            parameters: Tool parameters
            user_id: User identifier for rate limiting

        Returns:
            Tool execution result
        """
        # Check rate limit
        if not await self.check_tool_rate_limit(user_id):
            return {
                "status": "error",
                "error_type": "RateLimitExceeded",
                "error_message": f"Tool call limit exceeded. Maximum {self._max_tool_calls_per_minute} calls per minute.",
                "retry_after": 60,
            }

        # Log the tool call
        await self.log_tool_call(user_id)

        try:
            # Execute via MCP manager
            result = await mcp_manager.invoke(tool_name, **parameters)

            return {
                "status": "success",
                "result": result,
                "tool_name": tool_name,
                "execution_time": time.time(),
            }

        except Exception as e:
            logger.error(f"Tool execution failed for {tool_name}: {str(e)}")
            log_exception(e)

            return {
                "status": "error",
                "error_type": type(e).__name__,
                "error_message": str(e),
                "tool_name": tool_name,
            }

    async def process_message(
        self, message: str, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process user message with intent detection and routing.

        Args:
            message: User message
            context: Optional conversation context

        Returns:
            Processed response with routing and tool call information
        """
        context = context or {}
        user_id = context.get("user_id", "anonymous")

        # Detect intent
        intent = await self.detect_intent(message)

        # Add intent to context
        context["detected_intent"] = intent
        context["chat_agent_processed"] = True

        # Route to specialized agent if high confidence
        if intent["requires_routing"]:
            logger.info(
                f"High confidence ({intent['confidence']:.2f}) for {intent['primary_intent']}, routing to specialist"
            )
            response = await self.route_to_agent(intent, message, context)

            # Add routing metadata
            response["routed_to"] = intent["primary_intent"]
            response["routing_confidence"] = intent["confidence"]

            return response

        # Handle directly for general queries or low confidence
        logger.info(
            f"Handling directly - intent: {intent['primary_intent']} (confidence: {intent['confidence']:.2f})"
        )

        # Use parent run method for direct handling
        response = await super().run(message, context)

        # Add intent metadata
        response["intent_detected"] = intent
        response["handled_by"] = "chat_agent"

        return response

    async def run_with_tools(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        available_tools: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Run the agent with explicit tool calling support.

        Args:
            message: User message
            context: Optional conversation context
            available_tools: Optional list of available tools for this user

        Returns:
            Response with tool call results
        """
        context = context or {}
        context["available_tools"] = available_tools or []
        context["tool_calling_enabled"] = True

        return await self.process_message(message, context)
