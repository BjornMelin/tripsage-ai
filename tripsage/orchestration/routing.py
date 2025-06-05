"""
Intelligent routing node for LangGraph orchestration.

This module implements enhanced semantic intent detection and routing logic to determine
which specialized agent should handle each user request, with improved context awareness
and confidence scoring.
"""

import json
from datetime import datetime, timezone
from typing import Any, Dict

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from tripsage.orchestration.nodes.base import BaseAgentNode
from tripsage.orchestration.state import TravelPlanningState
from tripsage_core.config.base_app_settings import settings
from tripsage_core.utils.logging_utils import get_logger

logger = get_logger(__name__)


class RouterNode(BaseAgentNode):
    """
    Intelligent routing node using semantic analysis to determine agent routing.

    This node analyzes user messages and determines which specialized agent
    should handle the request based on intent detection, context analysis,
    and conversation history.

    Responsibilities:
    - Analyze user intent and conversation context
    - Route requests to appropriate specialized agents
    - Maintain confidence scoring for routing decisions
    - Handle routing failures and fallback strategies
    - Extract and update user preferences and travel context
    """

    def __init__(self, service_registry):
        """Initialize the router node with enhanced classification capabilities."""
        super().__init__("router", service_registry)

        # Initialize classifier model with improved configuration
        self.classifier = ChatOpenAI(
            model="gpt-4o-mini",  # Use smaller, faster model for classification
            temperature=0.1,  # Low temperature for consistent routing decisions
            api_key=settings.openai_api_key.get_secret_value(),
        )

        # Available agent types and their capabilities
        self.agent_capabilities = {
            "flight_agent": {
                "description": "Flight search, booking, changes, airline information",
                "keywords": [
                    "flight",
                    "flights",
                    "fly",
                    "airline",
                    "airport",
                    "departure",
                    "arrival",
                    "booking",
                ],
                "entities": [
                    "origin",
                    "destination",
                    "departure_date",
                    "return_date",
                    "passengers",
                    "class",
                ],
            },
            "accommodation_agent": {
                "description": "Hotels, rentals, lodging, accommodation booking",
                "keywords": [
                    "hotel",
                    "hotels",
                    "accommodation",
                    "stay",
                    "rental",
                    "airbnb",
                    "lodging",
                    "room",
                ],
                "entities": [
                    "location",
                    "check_in",
                    "check_out",
                    "guests",
                    "room_type",
                ],
            },
            "budget_agent": {
                "description": "Budget planning, cost analysis, expense tracking",
                "keywords": [
                    "budget",
                    "cost",
                    "price",
                    "expensive",
                    "cheap",
                    "afford",
                    "money",
                    "expenses",
                ],
                "entities": ["budget_total", "currency", "price_range"],
            },
            "itinerary_agent": {
                "description": (
                    "Trip planning, scheduling, activities, day-by-day planning"
                ),
                "keywords": [
                    "itinerary",
                    "plan",
                    "schedule",
                    "activity",
                    "activities",
                    "tour",
                    "sightseeing",
                ],
                "entities": ["travel_dates", "duration", "activities", "preferences"],
            },
            "destination_research_agent": {
                "description": (
                    "Destination research, recommendations, local information"
                ),
                "keywords": [
                    "destination",
                    "place",
                    "city",
                    "country",
                    "visit",
                    "recommend",
                    "explore",
                    "travel",
                ],
                "entities": ["destination", "interests", "season", "duration"],
            },
            "travel_agent": {
                "description": (
                    "General travel assistance, documentation, travel tips, "
                    "multi-domain queries"
                ),
                "keywords": [
                    "travel",
                    "trip",
                    "vacation",
                    "passport",
                    "visa",
                    "insurance",
                    "tips",
                ],
                "entities": ["travel_type", "duration", "group_size"],
            },
        }

    def _initialize_tools(self) -> None:
        """Router doesn't need external tools, only classification model."""
        pass

    async def process(self, state: TravelPlanningState) -> TravelPlanningState:
        """
        Analyze user intent and route to appropriate agent.

        Args:
            state: Current travel planning state

        Returns:
            State updated with routing decision
        """
        # Get the last user message
        last_message = state["messages"][-1]["content"] if state["messages"] else ""

        # Get conversation context for better routing
        conversation_context = self._build_conversation_context(state)

        # Perform enhanced semantic classification with fallback strategies
        classification = await self._enhanced_classification_with_fallback(
            last_message, conversation_context
        )

        # Update state with routing decision
        state["current_agent"] = classification["agent"]
        state["handoff_context"] = {
            "routing_confidence": classification["confidence"],
            "routing_reasoning": classification["reasoning"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "message_analyzed": last_message[:100] + "..."
            if len(last_message) > 100
            else last_message,
        }

        self.logger.info(
            f"Routed to {classification['agent']} with confidence "
            f"{classification['confidence']:.2f}: {classification['reasoning']}"
        )

        return state

    async def _classify_intent(
        self, message: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Classify user intent using semantic analysis.

        Args:
            message: User message to classify
            context: Conversation context for better classification

        Returns:
            Classification result with agent, confidence, and reasoning
        """
        # Build classification prompt
        classification_prompt = self._build_classification_prompt(message, context)

        try:
            # Get classification from LLM
            messages = [
                SystemMessage(
                    content="You are an expert travel assistant intent classifier."
                ),
                HumanMessage(content=classification_prompt),
            ]

            response = await self.classifier.ainvoke(messages)
            # Handle different response formats
            content = (
                response.content if hasattr(response, "content") else str(response)
            )
            classification = json.loads(content)

            # Validate classification result
            if not self._validate_classification(classification):
                # Fallback to general travel agent
                return {
                    "agent": "travel_agent",
                    "confidence": 0.5,
                    "reasoning": "Fallback routing due to classification error",
                }

            return classification

        except Exception as e:
            self.logger.error(f"Intent classification failed: {str(e)}")
            # Fallback to general travel agent
            return {
                "agent": "travel_agent",
                "confidence": 0.3,
                "reasoning": f"Error in classification, using fallback: {str(e)}",
            }

    def _build_classification_prompt(
        self, message: str, context: Dict[str, Any]
    ) -> str:
        """
        Build the classification prompt for intent detection.

        Args:
            message: User message to classify
            context: Conversation context

        Returns:
            Formatted classification prompt
        """
        context_str = ""
        if context.get("previous_searches"):
            context_str += f"Previous searches: {context['previous_searches']}\n"
        if context.get("user_preferences"):
            context_str += f"User preferences: {context['user_preferences']}\n"
        if context.get("current_trip_context"):
            context_str += f"Current trip context: {context['current_trip_context']}\n"

        return f"""
        Analyze this travel-related message and classify the primary intent.
        
        Message: "{message}"
        
        Context:
        {context_str}
        
        Available agents and their specialties:
        - flight_agent: Flight search, booking, changes, airline information
        - accommodation_agent: Hotels, rentals, lodging, accommodation booking
        - budget_agent: Budget planning, cost analysis, expense tracking
        - itinerary_agent: Trip planning, scheduling, activities, day-by-day planning
        - destination_agent: Destination research, recommendations, local information
        - travel_agent: General travel assistance, documentation, travel tips, 
          multi-domain queries
        
        Classification Rules:
        1. If asking about specific flights, airlines, or flight booking → flight_agent
        2. If asking about hotels, accommodations, places to stay → accommodation_agent
        3. If asking about costs, budgets, expenses → budget_agent
        4. If asking about itineraries, schedules, daily plans → itinerary_agent
        5. If asking about destinations, attractions, local info → destination_agent
        6. For general travel questions or unclear intent → travel_agent
        
        Respond with valid JSON only:
        {{"agent": "agent_name", "confidence": 0.9, "reasoning": "brief explanation"}}
        """

    def _build_conversation_context(self, state: TravelPlanningState) -> Dict[str, Any]:
        """
        Build conversation context for better routing decisions.

        Args:
            state: Current travel planning state

        Returns:
            Context dictionary with relevant information
        """
        context = {}

        # Extract previous search patterns
        if state["flight_searches"]:
            context["previous_searches"] = "flights"
        elif state["accommodation_searches"]:
            context["previous_searches"] = "accommodations"
        elif state["activity_searches"]:
            context["previous_searches"] = "activities"

        # Add user preferences if available
        if state["user_preferences"]:
            context["user_preferences"] = state["user_preferences"]

        # Add current trip context
        if state["destination_info"]:
            context["current_trip_context"] = state["destination_info"]
        elif state["travel_dates"]:
            context["current_trip_context"] = state["travel_dates"]

        # Add agent history for context
        if state["agent_history"]:
            context["recent_agents"] = state["agent_history"][-3:]  # Last 3 agents

        return context

    def _validate_classification(self, classification: Dict[str, Any]) -> bool:
        """
        Validate the classification result.

        Args:
            classification: Classification result to validate

        Returns:
            True if valid, False otherwise
        """
        required_keys = ["agent", "confidence", "reasoning"]
        valid_agents = [
            "flight_agent",
            "accommodation_agent",
            "budget_agent",
            "itinerary_agent",
            "destination_research_agent",  # Updated to match actual agent name
            "general_agent",  # Updated to match actual fallback agent
        ]

        # Check required keys
        if not all(key in classification for key in required_keys):
            logger.warning(f"Classification missing required keys: {classification}")
            return False

        # Check agent is valid
        if classification["agent"] not in valid_agents:
            logger.warning(
                f"Invalid agent in classification: {classification['agent']}"
            )
            return False

        # Check confidence is reasonable
        if (
            not isinstance(classification["confidence"], (int, float))
            or not 0 <= classification["confidence"] <= 1
        ):
            logger.warning(f"Invalid confidence score: {classification['confidence']}")
            return False

        # Additional validation: ensure reasoning is not empty
        if not classification.get("reasoning", "").strip():
            logger.warning("Classification reasoning is empty")
            return False

        return True

    async def _enhanced_classification_with_fallback(
        self, message: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Enhanced classification with multiple fallback strategies.

        Args:
            message: User message to classify
            context: Conversation context

        Returns:
            Classification result with enhanced confidence scoring
        """
        try:
            # Primary classification
            classification = await self._classify_intent(message, context)

            # If confidence is too low, try keyword-based fallback
            if classification["confidence"] < 0.7:
                keyword_classification = self._keyword_based_classification(message)
                if keyword_classification["confidence"] > classification["confidence"]:
                    logger.info(
                        f"Using keyword-based classification over LLM: "
                        f"{keyword_classification['agent']} "
                        f"(confidence: {keyword_classification['confidence']})"
                    )
                    return keyword_classification

            return classification

        except Exception as e:
            logger.error(f"Enhanced classification failed: {str(e)}")
            return self._get_safe_fallback_classification()

    def _keyword_based_classification(self, message: str) -> Dict[str, Any]:
        """
        Keyword-based classification as fallback.

        Args:
            message: User message to classify

        Returns:
            Classification result based on keyword matching
        """
        message_lower = message.lower()

        # Calculate confidence scores for each agent based on keyword matches
        agent_scores = {}
        agent_keyword_counts = {}

        for agent, capabilities in self.agent_capabilities.items():
            score = 0
            keyword_matches = 0

            for keyword in capabilities.get("keywords", []):
                if keyword.lower() in message_lower:
                    keyword_matches += 1
                    # Weight certain keywords higher
                    if keyword.lower() in ["flight", "hotel", "budget", "destination"]:
                        score += 2
                    else:
                        score += 1

            # Store keyword count for this agent
            agent_keyword_counts[agent] = keyword_matches

            # Normalize score based on keyword count and message length
            if keyword_matches > 0:
                word_count = max(len(message_lower.split()), 1)
                agent_scores[agent] = min(0.95, score / word_count)

        # Find the best match
        if agent_scores:
            best_agent = max(agent_scores, key=agent_scores.get)
            confidence = agent_scores[best_agent]
            best_keyword_matches = agent_keyword_counts[best_agent]

            return {
                "agent": best_agent,
                "confidence": confidence,
                "reasoning": (
                    f"Keyword-based classification: {best_keyword_matches} "
                    f"keyword matches"
                ),
            }
        else:
            return self._get_safe_fallback_classification()

    def _get_safe_fallback_classification(self) -> Dict[str, Any]:
        """Get a safe fallback classification."""
        return {
            "agent": "general_agent",
            "confidence": 0.3,
            "reasoning": "Safe fallback due to classification failure",
        }
