"""Session Memory Bridge for LangGraph integration.

Reads user context via MemoryService and maps it into the LangGraph state.
Legacy utils-based session functions have been removed.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Awaitable
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, cast

from tripsage.orchestration.state import TravelPlanningState


if TYPE_CHECKING:  # pragma: no cover - import only for typing
    from tripsage_core.services.business.memory_service import MemoryService


logger = logging.getLogger(__name__)


class SessionMemoryBridge:
    """Bridge between LangGraph state and TripSage session memory utilities.

    This class handles bidirectional synchronization between:
    - LangGraph TravelPlanningState (ephemeral)
    - Neo4j Knowledge Graph (persistent session memory)
    - User preferences and learned insights
    """

    def __init__(self, memory_service: MemoryService | None = None):
        """Initialize the memory bridge."""
        self._memory_service = memory_service

    async def _get_service(self) -> MemoryService:
        """Get or create a MemoryService instance (lazy)."""
        if self._memory_service is None:
            # Deferred import to avoid heavy pydantic model import during module load
            from tripsage_core.services.business.memory_service import MemoryService

            self._memory_service = MemoryService()
        await cast(Awaitable[None], self._memory_service.connect())
        return self._memory_service

    async def hydrate_state(self, state: TravelPlanningState) -> TravelPlanningState:
        """Load user context and preferences into LangGraph state.

        Args:
            state: Current LangGraph state

        Returns:
            State enriched with session memory data
        """
        user_id = state.get("user_id", None)
        if not user_id:
            logger.warning("No user_id in state, skipping memory hydration")
            return state

        try:
            logger.debug("Hydrating state for user: %s", user_id)
            svc = await self._get_service()
            context_any = await cast(Awaitable[Any], svc.get_user_context(user_id))

            context_dict = (
                context_any.model_dump()
                if hasattr(context_any, "model_dump")
                else cast(dict[str, Any], context_any)
            )
            state = self._map_user_context_to_state(state, context_dict)
            logger.info("Successfully hydrated state for user %s", user_id)

        except Exception:
            logger.exception("Failed to hydrate state for user %s", user_id)
            # Continue without memory data rather than failing

        return state

    def _map_user_context_to_state(
        self, state: TravelPlanningState, context: dict[str, Any]
    ) -> TravelPlanningState:
        """Map MemoryService user context response to state."""
        prefs = context.get("preferences", [])
        if prefs:
            # Store raw items into user_preferences (schema allows dict)
            state["user_preferences"] = {"items": prefs}

        # Past trips and destinations
        past_trips_raw = context.get("past_trips", [])
        if past_trips_raw:
            past_trips: list[dict[str, Any]] = [
                t for t in past_trips_raw if isinstance(t, dict)
            ]
            state["destination_info"] = {
                "recent_destinations": [str(t.get("destination")) for t in past_trips][
                    :5
                ],
            }

        # Derived insights/summary
        insights: dict[str, Any] = context.get("insights", {})
        summary = context.get("summary")
        if insights:
            state["extracted_entities"] = {
                **state.get("extracted_entities", {}),
                "insights": insights,
                "memory_loaded_at": datetime.now(UTC).isoformat(),
            }
        if summary:
            state["conversation_summary"] = summary
        return state

    async def extract_and_persist_insights(
        self, state: TravelPlanningState
    ) -> dict[str, Any]:
        """Extract insights from state and update knowledge graph.

        Args:
            state: Current LangGraph state

        Returns:
            Result of memory update operation
        """
        user_id = state.get("user_id")
        if not user_id:
            logger.warning("No user_id in state, skipping insight persistence")
            return {}

        try:
            logger.debug("Extracting insights for user: %s", user_id)

            # Extract insights from current state
            insights = self._extract_insights_from_state(state)

            if insights:
                # Persist insights via MemoryService as a structured note
                svc = await self._get_service()
                from tripsage_core.services.business.memory_service import (
                    ConversationMemoryRequest,
                )

                payload = ConversationMemoryRequest(
                    messages=[
                        {
                            "role": "system",
                            "content": "Store state insights for personalization.",
                        },
                        {
                            "role": "user",
                            "content": json.dumps(insights, sort_keys=True),
                        },
                    ],
                    session_id=state.get("session_id"),
                    trip_id=None,
                    metadata={"type": "state_insights"},
                )
                result = await cast(
                    Awaitable[dict[str, Any]],
                    svc.add_conversation_memory(user_id, payload),
                )
                logger.info("Successfully persisted insights for user %s", user_id)
                return result
            logger.debug("No new insights to persist for user %s", user_id)
            return {}

        except Exception as e:
            logger.exception("Failed to persist insights for user %s", user_id)
            return {"error": str(e)}

    def _extract_insights_from_state(
        self, state: TravelPlanningState
    ) -> dict[str, Any]:
        """Extract insights from LangGraph state.

        Args:
            state: Current state

        Returns:
            Extracted insights
        """
        insights: dict[str, Any] = {}

        # Extract updated preferences
        user_preferences = state.get("user_preferences", {})
        if user_preferences:
            insights["preferences"] = user_preferences

        # Extract learned facts from interactions
        messages_list = state.get("messages", [])
        if messages_list:
            facts = self._extract_facts_from_messages(messages_list)
            if facts:
                insights["learned_facts"] = facts

        # Extract search patterns
        search_history: list[dict[str, Any]] = []
        flight_searches: list[dict[str, Any]] = state.get("flight_searches", [])
        accommodation_searches: list[dict[str, Any]] = state.get(
            "accommodation_searches", []
        )
        if flight_searches:
            search_history.extend(flight_searches)
        if accommodation_searches:
            search_history.extend(accommodation_searches)
        # Destination searches are folded into activity or other agent results.

        if search_history:
            insights["search_history"] = search_history[-10:]  # Keep last 10 searches

        # Extract budget insights
        budget_data = state.get("budget_constraints")
        if budget_data:
            insights["budget_insights"] = budget_data

        # Extract destination preferences
        destination_info = state.get("destination_info")
        if destination_info:
            insights["destination_preferences"] = destination_info

        # If nothing meaningful was extracted, return an empty dict to avoid
        # persisting no-op insights. Otherwise, append lightweight context.
        if not insights:
            return {}

        insights["session_context"] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "session_id": state.get("session_id"),
            "agent_interactions": state.get("agent_history", []),
            "total_messages": len(messages_list),
        }

        return insights

    def _extract_facts_from_messages(self, messages: list[dict[str, Any]]) -> list[str]:
        """Extract facts and insights from conversation messages."""
        facts: list[str] = []

        for message in messages:
            content = message.get("content", "")
            role = message.get("role", "")

            # Extract facts from user messages (preferences, constraints, etc.)
            if role == "user":
                # Look for preference statements
                if any(
                    keyword in content.lower()
                    for keyword in ["prefer", "like", "want", "need"]
                ):
                    facts.append(f"User preference: {content}")

                # Look for constraints
                if any(
                    keyword in content.lower()
                    for keyword in ["budget", "cost", "price", "afford"]
                ):
                    facts.append(f"Budget constraint: {content}")

                # Look for requirements
                if any(
                    keyword in content.lower()
                    for keyword in ["must", "require", "need", "necessary"]
                ):
                    facts.append(f"Requirement: {content}")

        return facts[-5:]  # Keep last 5 facts to avoid overwhelming memory

    def state_to_checkpoint_format(self, state: TravelPlanningState) -> dict[str, Any]:
        """Convert state to format suitable for checkpointing.

        Args:
            state: Current state

        Returns:
            Checkpoint-ready state data
        """
        # Remove large objects and keep essential state for checkpointing
        checkpoint_data = {
            "user_id": state.get("user_id"),
            "session_id": state.get("session_id"),
            "user_preferences": state.get("user_preferences"),
            "budget_constraints": state.get("budget_constraints"),
            "travel_dates": state.get("travel_dates"),
            "destination_info": state.get("destination_info"),
            "agent_history": state.get("agent_history", [])[
                -10:
            ],  # Last 10 interactions
            "current_context": state.get("current_context"),
            "session_metadata": state.get("session_metadata"),
        }

        # Add summary of key search results (not full results)
        if state.get("flight_searches"):
            checkpoint_data["flight_search_summary"] = {
                "count": len(state["flight_searches"]),
                "last_search": state["flight_searches"][-1]
                if state["flight_searches"]
                else None,
            }

        if state.get("accommodation_searches"):
            checkpoint_data["accommodation_search_summary"] = {
                "count": len(state["accommodation_searches"]),
                "last_search": state["accommodation_searches"][-1]
                if state["accommodation_searches"]
                else None,
            }

        return checkpoint_data

    async def restore_from_checkpoint(
        self, checkpoint_data: dict[str, Any]
    ) -> TravelPlanningState:
        """Restore state from checkpoint data.

        Args:
            checkpoint_data: Saved checkpoint data

        Returns:
            Restored TravelPlanningState
        """
        # Initialize minimal state using available IDs
        user_id = checkpoint_data.get("user_id", "restored_user")
        session_id = checkpoint_data.get("session_id")
        from tripsage.orchestration.state import create_initial_state

        state = create_initial_state(user_id=user_id, message="", session_id=session_id)

        # Restore basic state
        for key, value in checkpoint_data.items():
            if key.endswith("_summary"):
                # Skip summary fields, we'll restore full data if needed
                continue
            state[key] = value

        # If we have a user_id, hydrate with current memory
        if state.get("user_id"):
            state = await self.hydrate_state(state)

        return state

    async def store_session_checkpoint_reference(
        self,
        user_id: str,
        session_id: str,
        checkpoint_id: str,
        metadata: dict[str, Any],
    ) -> None:
        """Store reference to checkpoint in knowledge graph.

        Args:
            user_id: User identifier
            session_id: Session identifier
            checkpoint_id: LangGraph checkpoint identifier
            metadata: Additional checkpoint metadata
        """
        try:
            checkpoint_ref = {
                "checkpoint_id": checkpoint_id,
                "session_id": session_id,
                "timestamp": datetime.now(UTC).isoformat(),
                "metadata": metadata,
            }

            # Store in session memory as checkpoint reference
            svc = await self._get_service()
            from tripsage_core.services.business.memory_service import (
                ConversationMemoryRequest,
            )

            payload = ConversationMemoryRequest(
                messages=[
                    {
                        "role": "system",
                        "content": "Store checkpoint reference",
                    },
                    {
                        "role": "user",
                        "content": json.dumps(checkpoint_ref, sort_keys=True),
                    },
                ],
                session_id=session_id,
                trip_id=None,
                metadata={"type": "checkpoint_reference"},
            )
            await cast(
                Awaitable[dict[str, Any]],
                svc.add_conversation_memory(user_id, payload),
            )

            logger.debug(
                "Stored checkpoint reference %s for user %s", checkpoint_id, user_id
            )

        except Exception:
            logger.exception("Failed to store checkpoint reference")
