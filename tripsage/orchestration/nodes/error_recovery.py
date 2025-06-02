"""
Error recovery node implementation for LangGraph orchestration.

This module provides sophisticated error handling and recovery mechanisms
for the TripSage travel planning system.
"""

from datetime import datetime

from tripsage.agents.service_registry import ServiceRegistry
from tripsage.orchestration.nodes.base import BaseAgentNode
from tripsage.orchestration.state import TravelPlanningState
from tripsage_core.utils.logging_utils import get_logger

logger = get_logger(__name__)


class ErrorRecoveryNode(BaseAgentNode):
    """
    Sophisticated error handling and recovery node.

    This node implements intelligent error recovery strategies including
    retry logic, fallback options, and escalation to human support.
    """

    def __init__(self, service_registry):
        """Initialize the error recovery node."""
        super().__init__("error_recovery", service_registry)
        self.max_retries = 3
        self.escalation_threshold = 5

    def _initialize_tools(self) -> None:
        """Error recovery doesn't need external tools."""
        pass

    async def process(self, state: TravelPlanningState) -> TravelPlanningState:
        """
        Handle errors with intelligent recovery strategies.

        Args:
            state: Current travel planning state with error information

        Returns:
            Updated state with recovery actions taken
        """
        error_count = state.get("error_count", 0)
        current_agent = state.get("current_agent", "")

        logger.info(
            f"Processing error recovery: count={error_count}, agent={current_agent}"
        )

        # Determine recovery strategy based on error severity
        if error_count < self.max_retries:
            return await self._attempt_retry(state)
        elif error_count < self.escalation_threshold:
            return await self._attempt_fallback(state)
        else:
            return await self._escalate_to_human(state)

    async def _attempt_retry(self, state: TravelPlanningState) -> TravelPlanningState:
        """
        Attempt retry with modified parameters.

        Args:
            state: Current state with error information

        Returns:
            State configured for retry attempt
        """
        current_agent = state.get("current_agent", "")
        retry_count = state["retry_attempts"].get(current_agent, 0)

        logger.info(f"Attempting retry #{retry_count + 1} for {current_agent}")

        # Clear the error state for retry
        state["last_error"] = None

        # Add retry message to conversation
        retry_message = {
            "role": "assistant",
            "content": (
                "I encountered an issue with that request. "
                "Let me try a different approach..."
            ),
            "agent": "error_recovery",
            "retry_attempt": retry_count + 1,
            "timestamp": datetime.now(datetime.UTC).isoformat(),
        }
        state["messages"].append(retry_message)

        # Set routing back to router for intelligent retry
        state["current_agent"] = "router"

        # Add retry context to handoff information
        state["handoff_context"] = {
            "retry_context": {
                "original_agent": current_agent,
                "retry_attempt": retry_count + 1,
                "original_error": state.get("last_error", "Unknown error"),
            },
            "timestamp": datetime.now(datetime.UTC).isoformat(),
        }

        return state

    async def _attempt_fallback(
        self, state: TravelPlanningState
    ) -> TravelPlanningState:
        """
        Use fallback strategies when retries aren't working.

        Args:
            state: Current state with persistent errors

        Returns:
            State with fallback approach
        """
        current_agent = state.get("current_agent", "")

        logger.info(f"Attempting fallback strategy for {current_agent}")

        # Determine appropriate fallback agent
        fallback_agent = self._get_fallback_agent(current_agent)

        fallback_message = {
            "role": "assistant",
            "content": self._generate_fallback_message(current_agent, fallback_agent),
            "agent": "error_recovery",
            "fallback_strategy": True,
            "timestamp": datetime.now(datetime.UTC).isoformat(),
        }
        state["messages"].append(fallback_message)

        # Route to fallback agent
        state["current_agent"] = fallback_agent

        # Add fallback context
        state["handoff_context"] = {
            "fallback_context": {
                "original_agent": current_agent,
                "fallback_agent": fallback_agent,
                "reason": "Multiple errors in original agent",
            },
            "timestamp": datetime.now(datetime.UTC).isoformat(),
        }

        return state

    async def _escalate_to_human(
        self, state: TravelPlanningState
    ) -> TravelPlanningState:
        """
        Escalate to human support for complex issues.

        Args:
            state: State with persistent errors requiring human intervention

        Returns:
            State with escalation information
        """
        logger.warning(
            f"Escalating to human support for session {state.get('session_id')}"
        )

        escalation_message = {
            "role": "assistant",
            "content": self._generate_escalation_message(),
            "agent": "error_recovery",
            "escalation": True,
            "timestamp": datetime.now(datetime.UTC).isoformat(),
        }
        state["messages"].append(escalation_message)

        # Log escalation for human support team
        await self._log_escalation(state)

        # Mark for human review
        state["handoff_context"] = {
            "escalation": {
                "reason": "Multiple error recovery attempts failed",
                "error_count": state.get("error_count", 0),
                "session_id": state.get("session_id"),
                "user_id": state.get("user_id"),
                "timestamp": datetime.now(datetime.UTC).isoformat(),
            }
        }

        return state

    def _get_fallback_agent(self, failed_agent: str) -> str:
        """
        Determine appropriate fallback agent.

        Args:
            failed_agent: The agent that failed

        Returns:
            Name of fallback agent
        """
        # Define fallback hierarchy
        fallback_mapping = {
            "flight_agent": "travel_agent",
            "accommodation_agent": "travel_agent",
            "budget_agent": "travel_agent",
            "itinerary_agent": "destination_agent",
            "destination_agent": "travel_agent",
        }

        return fallback_mapping.get(failed_agent, "travel_agent")

    def _generate_fallback_message(
        self, original_agent: str, fallback_agent: str
    ) -> str:
        """
        Generate appropriate fallback message.

        Args:
            original_agent: The agent that failed
            fallback_agent: The fallback agent being used

        Returns:
            User-friendly fallback message
        """
        agent_descriptions = {
            "flight_agent": "flight search",
            "accommodation_agent": "accommodation search",
            "budget_agent": "budget planning",
            "itinerary_agent": "itinerary planning",
            "destination_agent": "destination research",
            "travel_agent": "general travel assistance",
        }

        original_desc = agent_descriptions.get(original_agent, "that service")
        fallback_desc = agent_descriptions.get(fallback_agent, "alternative assistance")

        return (
            f"I'm having trouble with {original_desc} at the moment. "
            f"Let me help you with {fallback_desc} instead, or we can try "
            f"a different approach to your request.\n\n"
            "Would you like to:\n"
            "1. Try rephrasing your request\n"
            "2. Break down your request into smaller parts\n"
            "3. Explore alternative options\n\n"
            "I'm here to help however I can!"
        )

    def _generate_escalation_message(self) -> str:
        """
        Generate escalation message for human support.

        Returns:
            User-friendly escalation message
        """
        return (
            "I apologize, but I'm experiencing technical difficulties that "
            "prevent me from completing your request effectively. A human "
            "travel specialist has been notified and will assist you shortly.\n\n"
            "In the meantime, you can:\n\n"
            "1. **Try a simpler request** - Break down what you need into "
            "smaller steps\n"
            "2. **Check back in a few minutes** - Our systems may have recovered\n"
            "3. **Contact support directly** - Use the help menu for immediate "
            "assistance\n\n"
            "Your conversation has been saved, and we'll follow up with you soon. "
            "Thank you for your patience!"
        )

    async def _log_escalation(self, state: TravelPlanningState) -> None:
        """
        Log escalation details for human support team.

        Args:
            state: Current state with error information
        """
        escalation_data = {
            "session_id": state.get("session_id"),
            "user_id": state.get("user_id"),
            "error_count": state.get("error_count", 0),
            "last_error": state.get("last_error"),
            "agent_history": state.get("agent_history", []),
            "retry_attempts": state.get("retry_attempts", {}),
            "timestamp": datetime.now(datetime.UTC).isoformat(),
            "conversation_length": len(state.get("messages", [])),
        }

        logger.error(f"ESCALATION: {escalation_data}")

        # TODO: Integrate with support ticketing system
        # await support_system.create_ticket(escalation_data)
