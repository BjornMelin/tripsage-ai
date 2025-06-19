"""
Chat agent implementation for handling real-time chat interactions.

This module provides the ChatAgent class that integrates with the LangGraph
orchestration system for processing user messages through specialized agents.
"""

from typing import Any

from tripsage.agents.base import BaseAgent
from tripsage.agents.service_registry import ServiceRegistry

# TripSageOrchestrator imported lazily to avoid circular imports
from tripsage_core.utils.logging_utils import get_logger

logger = get_logger(__name__)


class ChatAgent(BaseAgent):
    """
    Chat agent for handling real-time chat interactions.

    This agent orchestrates the conversation flow by routing user messages
    to appropriate specialized agents through the LangGraph system.
    """

    def __init__(self, service_registry: ServiceRegistry):
        """Initialize the chat agent."""
        super().__init__("chat_agent", service_registry)
        self.orchestrator = None
        self._initialize_orchestrator()

    def _initialize_orchestrator(self):
        """Initialize the TripSage orchestrator."""
        try:
            # Lazy import to avoid circular imports
            from tripsage.orchestration.graph import TripSageOrchestrator

            self.orchestrator = TripSageOrchestrator(self.service_registry)
            logger.info("Chat agent orchestrator initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize chat agent orchestrator: {e}")
            self.orchestrator = None

    async def process_message(
        self,
        user_id: str,
        message: str,
        session_id: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Process a user message through the orchestration system.

        Args:
            user_id: User identifier
            message: User message content
            session_id: Optional session identifier
            context: Optional additional context

        Returns:
            Processing result with agent response
        """
        if not self.orchestrator:
            logger.error("Chat agent orchestrator not initialized")
            return {
                "error": "Chat system not available",
                "message": (
                    "I apologize, but the chat system is currently unavailable. "
                    "Please try again later."
                ),
            }

        try:
            # Process through the orchestrator
            result = await self.orchestrator.process_message(
                user_id=user_id,
                message=message,
                session_id=session_id,
                context=context or {},
            )

            # The orchestrator already returns a properly formatted response
            return result

        except Exception as e:
            logger.error(f"Error processing chat message: {e}")
            return {
                "error": str(e),
                "message": (
                    "I encountered an error while processing your request. "
                    "Please try again."
                ),
            }

    async def stream_message(
        self,
        user_id: str,
        message: str,
        session_id: str | None = None,
        context: dict[str, Any] | None = None,
    ):
        """
        Stream processing of a user message.

        Args:
            user_id: User identifier
            message: User message content
            session_id: Optional session identifier
            context: Optional additional context

        Yields:
            Processing updates and final response
        """
        if not self.orchestrator:
            yield {
                "type": "error",
                "data": {
                    "error": "Chat system not available",
                    "message": (
                        "I apologize, but the chat system is currently unavailable."
                    ),
                },
            }
            return

        try:
            # Yield initial status
            yield {
                "type": "status",
                "data": {
                    "status": "processing",
                    "message": "Processing your request...",
                },
            }

            # Process through the orchestrator
            result = await self.orchestrator.process_message(
                user_id=user_id,
                message=message,
                session_id=session_id,
                context=context or {},
            )

            # Yield final response
            yield {"type": "response", "data": result}

        except Exception as e:
            logger.error(f"Error in streaming chat message: {e}")
            yield {
                "type": "error",
                "data": {
                    "error": str(e),
                    "message": "I encountered an error while processing your request.",
                },
            }

    async def get_conversation_history(
        self, user_id: str, session_id: str, limit: int = 50
    ) -> list[dict[str, Any]]:
        """
        Get conversation history for a session.

        Args:
            user_id: User identifier
            session_id: Session identifier
            limit: Maximum number of messages to return

        Returns:
            List of conversation messages
        """
        try:
            # Use the chat service to get conversation history
            chat_service = self.service_registry.get_optional_service("chat_service")
            if chat_service:
                return await chat_service.get_conversation_history(
                    user_id, session_id, limit
                )
            else:
                logger.warning("Chat service not available for history retrieval")
                return []

        except Exception as e:
            logger.error(f"Error retrieving conversation history: {e}")
            return []

    async def clear_conversation(self, user_id: str, session_id: str) -> bool:
        """
        Clear conversation history for a session.

        Args:
            user_id: User identifier
            session_id: Session identifier

        Returns:
            True if successful, False otherwise
        """
        try:
            # Use the chat service to clear conversation
            chat_service = self.service_registry.get_optional_service("chat_service")
            if chat_service:
                return await chat_service.clear_conversation(user_id, session_id)
            else:
                logger.warning("Chat service not available for conversation clearing")
                return False

        except Exception as e:
            logger.error(f"Error clearing conversation: {e}")
            return False

    def get_available_agents(self) -> list[str]:
        """
        Get list of available specialized agents.

        Returns:
            List of agent names
        """
        return [
            "flight_agent",
            "accommodation_agent",
            "budget_agent",
            "destination_research_agent",
            "itinerary_agent",
        ]

    def get_agent_capabilities(self) -> dict[str, list[str]]:
        """
        Get capabilities of each specialized agent.

        Returns:
            Dictionary mapping agent names to their capabilities
        """
        return {
            "flight_agent": [
                "Search flights",
                "Compare flight options",
                "Book flights",
                "Track flight status",
            ],
            "accommodation_agent": [
                "Search hotels and accommodations",
                "Compare accommodation options",
                "Book accommodations",
                "Find vacation rentals",
            ],
            "budget_agent": [
                "Budget planning and optimization",
                "Expense tracking",
                "Cost comparisons",
                "Budget recommendations",
            ],
            "destination_research_agent": [
                "Destination research",
                "Attraction recommendations",
                "Local culture and customs",
                "Weather and seasonal information",
            ],
            "itinerary_agent": [
                "Create detailed itineraries",
                "Optimize travel schedules",
                "Activity planning",
                "Calendar integration",
            ],
        }
