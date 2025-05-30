"""
Intelligent routing node for LangGraph orchestration.

This module implements semantic intent detection and routing logic to determine
which specialized agent should handle each user request.
"""

import json
from datetime import datetime
from typing import Any, Dict

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from tripsage.orchestration.nodes.base import BaseAgentNode
from tripsage.orchestration.state import TravelPlanningState
from tripsage_core.config.base_app_settings import settings


class RouterNode(BaseAgentNode):
    """
    Intelligent routing node using semantic analysis to determine agent routing.

    This node analyzes user messages and determines which specialized agent
    should handle the request based on intent detection and context analysis.
    """

    def __init__(self):
        """Initialize the router node with semantic classification capabilities."""
        super().__init__("router")

        # Initialize classifier model
        self.classifier = ChatOpenAI(
            model="gpt-4o-mini",  # Use smaller, faster model for classification
            temperature=0.1,  # Low temperature for consistent routing decisions
            api_key=settings.openai_api_key.get_secret_value(),
        )

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

        # Perform semantic classification
        classification = await self._classify_intent(last_message, conversation_context)

        # Update state with routing decision
        state["current_agent"] = classification["agent"]
        state["handoff_context"] = {
            "routing_confidence": classification["confidence"],
            "routing_reasoning": classification["reasoning"],
            "timestamp": datetime.now(datetime.UTC).isoformat(),
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
            classification = json.loads(response.content)

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
            "destination_agent",
            "travel_agent",
        ]

        # Check required keys
        if not all(key in classification for key in required_keys):
            return False

        # Check agent is valid
        if classification["agent"] not in valid_agents:
            return False

        # Check confidence is reasonable
        if (
            not isinstance(classification["confidence"], (int, float))
            or not 0 <= classification["confidence"] <= 1
        ):
            return False

        return True
