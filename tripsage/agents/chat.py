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
from tripsage.agents.budget import Budget as BudgetAgent
from tripsage.agents.destination_research import DestinationResearchAgent
from tripsage.agents.flight import FlightAgent
from tripsage.agents.itinerary import Itinerary as ItineraryAgent
from tripsage.agents.travel import TravelAgent
from tripsage.mcp_abstraction.manager import MCPManager
from tripsage.services.core.chat_orchestration import ChatOrchestrationService
from tripsage.services.core.memory_service import TripSageMemoryService
from tripsage.tools.memory_tools import ConversationMessage
from tripsage_core.config.base_app_settings import get_settings
from tripsage_core.exceptions import CoreTripSageError, with_error_handling
from tripsage_core.utils.error_handling_utils import (
    log_exception,
)
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
        name: str = "TripSage Chat Assistant",
        model: str = None,
        temperature: float = None,
        mcp_manager: Optional[MCPManager] = None,
    ):
        """Initialize the chat agent.

        Args:
            name: Agent name
            model: Model name to use (defaults to settings if None)
            temperature: Temperature for model sampling (defaults to settings if None)
            mcp_manager: Optional MCP manager instance. If None, uses global instance.
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
            model=model,
            temperature=temperature,
            metadata={"agent_type": "chat_coordinator", "version": "1.0.0"},
        )

        # Initialize MCP integration (only needed for Airbnb accommodations)
        self.mcp_manager = mcp_manager or MCPManager()
        self.chat_service = ChatOrchestrationService()

        # Initialize memory service for personalization
        self.memory_service = TripSageMemoryService()
        self._memory_initialized = False

        # Initialize specialized agents
        self._initialize_specialized_agents()

        # Register travel tools
        self._register_travel_tools()

        # Track tool call rate limiting
        self._tool_call_history: Dict[str, List[float]] = {}
        self._max_tool_calls_per_minute = 5

        logger.info("ChatAgent initialized with Phase 5 MCP integration")

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

    async def _ensure_memory_initialized(self) -> None:
        """Ensure memory service is connected and ready."""
        if not self._memory_initialized:
            try:
                await self.memory_service.connect()
                self._memory_initialized = True
                logger.info("Memory service initialized for ChatAgent")
            except Exception as e:
                logger.warning(f"Failed to initialize memory service: {e}")

    async def _get_user_context(self, user_id: str) -> Dict[str, Any]:
        """Get user context from memory for personalization.

        Args:
            user_id: User identifier

        Returns:
            User context including preferences and history
        """
        try:
            await self._ensure_memory_initialized()
            context = await self.memory_service.get_user_context(user_id)

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
            await self._ensure_memory_initialized()

            # Create conversation messages
            messages = [
                ConversationMessage(role="user", content=user_message),
                ConversationMessage(role="assistant", content=assistant_response),
            ]

            # Store in memory with travel context
            await self.memory_service.add_conversation_memory(
                messages=messages,
                user_id=user_id,
                session_id=session_id,
                metadata={"source": "chat_agent", "agent_type": "travel_coordinator"},
            )

            logger.debug(f"Stored conversation memory for user {user_id}")

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
        for _intent, config in intent_patterns.items():
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
                "content": (
                    f"I encountered an issue with the {primary_intent} "
                    "specialist. Let me help you directly."
                ),
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
                "error_message": (
                    f"Tool call limit exceeded. Maximum "
                    f"{self._max_tool_calls_per_minute} calls per minute."
                ),
                "retry_after": 60,
            }

        # Log the tool call
        await self.log_tool_call(user_id)

        try:
            # Execute via MCP manager
            result = await self.mcp_manager.invoke(tool_name, **parameters)

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
        session_id = context.get("session_id")

        # Create session if not exists
        if not session_id and user_id != "anonymous":
            try:
                session_data = await self.create_chat_session_mcp(
                    user_id=int(user_id) if user_id.isdigit() else 1,
                    metadata={"agent": "chat", "created_from": "process_message"},
                )
                session_id = session_data.get("session_id")
                context["session_id"] = session_id
            except Exception as e:
                logger.warning(f"Failed to create session: {e}")

        # Save user message if session exists
        if session_id:
            try:
                await self.save_message_mcp(
                    session_id=session_id,
                    role="user",
                    content=message,
                    metadata={"timestamp": context.get("timestamp")},
                )
            except Exception as e:
                logger.warning(f"Failed to save user message: {e}")

        # Get user context from memory for personalization
        user_context = {}
        if user_id != "anonymous":
            user_context = await self._get_user_context(user_id)
            context["user_memory"] = user_context

            # Enhance instructions with user context if available
            if user_context.get("summary"):
                context["user_summary"] = user_context["summary"]
                logger.debug(
                    f"Added user context summary for personalization: {user_id}"
                )

        # Detect intent
        intent = await self.detect_intent(message)

        # Add intent to context
        context["detected_intent"] = intent
        context["chat_agent_processed"] = True

        # Route to specialized agent if high confidence
        if intent["requires_routing"]:
            logger.info(
                f"High confidence ({intent['confidence']:.2f}) "
                f"for {intent['primary_intent']}, routing to specialist"
            )
            response = await self.route_to_agent(intent, message, context)

            # Add routing metadata
            response["routed_to"] = intent["primary_intent"]
            response["routing_confidence"] = intent["confidence"]

        else:
            # Handle directly for general queries or low confidence
            logger.info(
                f"Handling directly - intent: {intent['primary_intent']} "
                f"(confidence: {intent['confidence']:.2f})"
            )

            # Use parent run method for direct handling
            response = await super().run(message, context)

            # Add intent metadata
            response["intent_detected"] = intent
            response["handled_by"] = "chat_agent"

        # Save assistant response if session exists
        if session_id and response.get("content"):
            try:
                await self.save_message_mcp(
                    session_id=session_id,
                    role="assistant",
                    content=response.get("content", ""),
                    metadata={
                        "intent": intent,
                        "routed_to": response.get("routed_to"),
                        "handled_by": response.get("handled_by"),
                    },
                )
            except Exception as e:
                logger.warning(f"Failed to save assistant message: {e}")

        # Store conversation in memory for future personalization
        if user_id != "anonymous" and response.get("content"):
            try:
                await self._store_conversation_memory(
                    user_message=message,
                    assistant_response=response.get("content", ""),
                    user_id=user_id,
                    session_id=session_id,
                )
            except Exception as e:
                logger.warning(f"Failed to store conversation memory: {e}")

        # Add session_id to response
        response["session_id"] = session_id

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

    # Phase 5: MCP Tool Integration Methods

    @with_error_handling(logger=logger, re_raise=True)
    async def route_request(
        self, message: str, session_id: str, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Route chat request to appropriate specialized agent or handle directly.

        This method implements Phase 5 routing patterns using MCP tools.

        Args:
            message: User message content
            session_id: Chat session ID
            context: Optional context data

        Returns:
            Dictionary with response and routing information

        Raises:
            ChatAgentError: If request routing fails
        """
        try:
            self.logger.info(f"Routing Phase 5 request for session {session_id}")

            # Use existing intent detection
            intent = await self.detect_intent(message)

            # Add session context
            routing_context = context or {}
            routing_context["session_id"] = session_id
            routing_context["detected_intent"] = intent

            # For high-confidence intents, use MCP-based services
            if intent["confidence"] > 0.7:
                return await self._handle_mcp_routing(intent, message, routing_context)
            else:
                return await self._handle_direct_conversation(message, routing_context)

        except Exception as e:
            self.logger.error(f"Phase 5 request routing failed: {e}")
            raise ChatAgentError(f"Request routing failed: {str(e)}") from e

    async def _handle_mcp_routing(
        self, intent: Dict[str, Any], message: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle routing using MCP services.

        Args:
            intent: Intent detection results
            message: User message
            context: Routing context

        Returns:
            Response dictionary
        """
        primary_intent = intent["primary_intent"]

        if primary_intent == "flight":
            return await self._handle_flight_request_mcp(message, context)
        elif primary_intent == "accommodation":
            return await self._handle_accommodation_request_mcp(message, context)
        elif primary_intent == "weather":
            return await self._handle_weather_request_mcp(message, context)
        elif primary_intent == "maps":
            return await self._handle_maps_request_mcp(message, context)
        else:
            # Route to existing specialized agents
            return await self.route_to_agent(intent, message, context)

    async def _handle_flight_request_mcp(
        self, message: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle flight requests using MCP services."""
        try:
            # For demonstration, extract basic flight parameters
            # In production, this would use more sophisticated NLP
            return {
                "content": (
                    "I'll help you search for flights using our MCP-integrated "
                    "flight service. Let me find the best options for you."
                ),
                "intent": "flight_search",
                "action": "mcp_flight_search",
                "session_id": context.get("session_id"),
                "mcp_service": "duffel_flights",
                "status": "ready_for_tool_call",
            }
        except Exception as e:
            return {"content": f"Flight search error: {str(e)}", "status": "error"}

    async def _handle_accommodation_request_mcp(
        self, message: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle accommodation requests using MCP services."""
        try:
            return {
                "content": (
                    "I'll search for accommodations using our integrated booking "
                    "services. What location and dates are you considering?"
                ),
                "intent": "accommodation_search",
                "action": "mcp_accommodation_search",
                "session_id": context.get("session_id"),
                "mcp_service": "airbnb",
                "status": "ready_for_tool_call",
            }
        except Exception as e:
            return {
                "content": f"Accommodation search error: {str(e)}",
                "status": "error",
            }

    async def _handle_weather_request_mcp(
        self, message: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle weather requests using MCP services."""
        try:
            return {
                "content": "Let me check the weather information for your destination.",
                "intent": "weather_check",
                "action": "mcp_weather_check",
                "session_id": context.get("session_id"),
                "mcp_service": "weather",
                "status": "ready_for_tool_call",
            }
        except Exception as e:
            return {"content": f"Weather check error: {str(e)}", "status": "error"}

    async def _handle_maps_request_mcp(
        self, message: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle maps/location requests using MCP services."""
        try:
            return {
                "content": (
                    "I'll help you with location information using our maps service."
                ),
                "intent": "location_info",
                "action": "mcp_location_lookup",
                "session_id": context.get("session_id"),
                "mcp_service": "google_maps",
                "status": "ready_for_tool_call",
            }
        except Exception as e:
            return {"content": f"Location lookup error: {str(e)}", "status": "error"}

    async def _handle_direct_conversation(
        self, message: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle general conversation directly."""
        # Use existing direct handling
        return await super().run(message, context)

    @with_error_handling(logger=logger, re_raise=True)
    async def call_mcp_tools(self, tool_calls: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Execute tool calls via MCP manager (Phase 5 pattern).

        Args:
            tool_calls: List of tool call dictionaries

        Returns:
            Dictionary with tool call results

        Raises:
            ChatAgentError: If tool calling fails
        """
        try:
            self.logger.info(f"Executing {len(tool_calls)} MCP tool calls")

            # Use chat orchestration service for parallel execution
            results = await self.chat_service.execute_parallel_tools(tool_calls)

            return {
                "tool_call_results": results,
                "execution_count": len(tool_calls),
                "status": "success",
                "timestamp": time.time(),
            }

        except Exception as e:
            self.logger.error(f"MCP tool calling failed: {e}")
            raise ChatAgentError(f"MCP tool calling failed: {str(e)}") from e

    @with_error_handling(logger=logger, re_raise=True)
    async def create_chat_session_mcp(
        self, user_id: int, metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a new chat session using MCP database operations.

        Args:
            user_id: User ID for the session
            metadata: Optional session metadata

        Returns:
            Dictionary with session information

        Raises:
            ChatAgentError: If session creation fails
        """
        try:
            return await self.chat_service.create_chat_session(user_id, metadata)
        except Exception as e:
            self.logger.error(f"MCP session creation failed: {e}")
            raise ChatAgentError(f"Session creation failed: {str(e)}") from e

    @with_error_handling(logger=logger, re_raise=True)
    async def save_message_mcp(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Save a chat message using MCP database operations.

        Args:
            session_id: Chat session ID
            role: Message role (user, assistant, system)
            content: Message content
            metadata: Optional message metadata

        Returns:
            Dictionary with saved message information

        Raises:
            ChatAgentError: If message saving fails
        """
        try:
            return await self.chat_service.save_message(
                session_id, role, content, metadata
            )
        except Exception as e:
            self.logger.error(f"MCP message saving failed: {e}")
            raise ChatAgentError(f"Message saving failed: {str(e)}") from e

    @with_error_handling(logger=logger, re_raise=True)
    async def get_chat_history_mcp(
        self, session_id: str, limit: int = 10, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get chat history using MCP database operations.

        Args:
            session_id: Chat session ID
            limit: Maximum number of messages to return
            offset: Number of messages to skip

        Returns:
            List of message dictionaries

        Raises:
            ChatAgentError: If history retrieval fails
        """
        try:
            return await self.chat_service.get_chat_history(session_id, limit, offset)
        except Exception as e:
            self.logger.error(f"MCP history retrieval failed: {e}")
            raise ChatAgentError(f"History retrieval failed: {str(e)}") from e

    @with_error_handling(logger=logger, re_raise=True)
    async def end_chat_session_mcp(self, session_id: str) -> bool:
        """End a chat session using MCP database operations.

        Args:
            session_id: Chat session ID to end

        Returns:
            True if session was ended successfully

        Raises:
            ChatAgentError: If session ending fails
        """
        try:
            return await self.chat_service.end_chat_session(session_id)
        except Exception as e:
            self.logger.error(f"MCP session ending failed: {e}")
            raise ChatAgentError(f"Session ending failed: {str(e)}") from e
