"""Chat agent implementation for handling real-time chat interactions."""

from collections.abc import AsyncIterator
from typing import Any

from tripsage.agents.base import BaseAgent
from tripsage.app_state import AppServiceContainer
from tripsage.orchestration.graph import TripSageOrchestrator
from tripsage_core.services.business.chat_service import ChatService
from tripsage_core.utils.error_handling_utils import log_exception
from tripsage_core.utils.logging_utils import get_logger


logger = get_logger(__name__)

_CHAT_INSTRUCTIONS = (
    "You are the TripSage chat coordinator. Greet the traveller, determine their "
    "goal, and delegate to the appropriate specialized agents when needed. "
    "Keep responses friendly, actionable, and under 120 words."
)


class ChatAgent(BaseAgent):
    """Chat agent for handling real-time chat interactions."""

    def __init__(
        self,
        *,
        services: AppServiceContainer,
        orchestrator: TripSageOrchestrator,
    ):
        """Initialize the chat agent with orchestration-aware base behaviour."""
        super().__init__(
            "chat_agent",
            services=services,
            orchestrator=orchestrator,
            instructions=_CHAT_INSTRUCTIONS,
            summary_interval=8,
        )

    async def process_message(
        self,
        user_id: str,
        message: str,
        session_id: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Process a message using the LangGraph orchestrator."""
        return await self.run(
            message,
            user_id=user_id,
            session_id=session_id,
            context=context,
        )

    async def stream_message(
        self,
        user_input: str,
        *,
        user_id: str | None = None,
        session_id: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Stream a message through the orchestrator with status updates."""
        async for event in super().stream_message(
            user_input,
            user_id=user_id,
            session_id=session_id,
            context=context,
        ):
            yield event

    async def fetch_conversation_history(
        self, user_id: str, session_id: str, limit: int = 50
    ) -> list[dict[str, Any]]:
        """Get conversation history for a session.

        Args:
            user_id: User identifier
            session_id: Session identifier
            limit: Maximum number of messages to return

        Returns:
            List of conversation messages
        """
        try:
            # Use the chat service to get conversation history
            chat_service = self.services.get_optional_service(
                "chat_service", expected_type=ChatService
            )
            if chat_service:
                return [
                    m if isinstance(m, dict) else m.model_dump()
                    for m in await chat_service.get_messages(session_id, user_id, limit)
                ]

            logger.warning(
                "Chat service not available for history retrieval; using local history."
            )
            return self._local_history(limit)

        except Exception as exc:
            logger.exception("Error retrieving conversation history")
            log_exception(exc)
            return self._local_history(limit)

    async def clear_conversation_history(self, user_id: str, session_id: str) -> bool:
        """Clear conversation history for a session.

        Args:
            user_id: User identifier
            session_id: Session identifier

        Returns:
            True if successful, False otherwise
        """
        try:
            # Use the chat service to clear conversation
            chat_service = self.services.get_optional_service(
                "chat_service", expected_type=ChatService
            )
            if chat_service:
                result = await chat_service.end_session(session_id, user_id)
                if result:
                    self.reset_session()
                return result

            logger.warning(
                "Chat service unavailable for conversation clearing; "
                "resetting local session."
            )
            self.reset_session()
            return True

        except Exception as exc:
            logger.exception("Error clearing conversation")
            log_exception(exc)
            return False

    def _local_history(self, limit: int | None) -> list[dict[str, Any]]:
        """Return in-memory history respecting the provided limit."""
        if limit is None:
            history = self.messages_history
        else:
            history = self.messages_history[-limit:]
        return [message.copy() for message in history]

    def get_available_agents(self) -> list[str]:
        """Get list of available specialized agents.

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
        """Get capabilities of each specialized agent.

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
