"""Session Memory Bridge for LangGraph integration.

Reads user context via MemoryService and maps it into the
LangGraph state. Legacy utils-based session functions have been removed.
"""

import logging
from datetime import UTC, datetime
from typing import Any

from tripsage.orchestration.state import TravelPlanningState
from tripsage_core.services.business.memory_service import (
    ConversationMemoryRequest,
    MemoryService,
)


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
            self._memory_service = MemoryService()
            await self._memory_service.connect()
        return self._memory_service

    async def hydrate_state(self, state: TravelPlanningState) -> TravelPlanningState:
        """Load user context and preferences into LangGraph state.

        Args:
            state: Current LangGraph state

        Returns:
            State enriched with session memory data
        """
        user_id = state.get("user_id")
        if not user_id:
            logger.warning("No user_id in state, skipping memory hydration")
            return state

        try:
            logger.debug("Hydrating state for user: %s", user_id)
            svc = await self._get_service()
            context = await svc.get_user_context(user_id)

            state = await self._map_user_context_to_state(state, context.model_dump())
            logger.info("Successfully hydrated state for user %s", user_id)

        except Exception:
            logger.exception("Failed to hydrate state for user %s", user_id)
            # Continue without memory data rather than failing

        return state

    async def _map_user_context_to_state(
        self, state: TravelPlanningState, context: dict[str, Any]
    ) -> TravelPlanningState:
        """Map MemoryService user context response to state."""
        prefs = context.get("preferences", [])
        if prefs:
            # Store raw items into user_preferences (schema allows dict)
            state["user_preferences"] = {"items": prefs}

        # Past trips and destinations
        past_trips = context.get("past_trips", [])
        if past_trips:
            state["destination_info"] = {
                "recent_destinations": [
                    t.get("destination") for t in past_trips if isinstance(t, dict)
                ][:5],
            }

        # Derived insights/summary
        insights = context.get("insights", {})
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

    def _extract_favorite_destinations(self, trips: list[dict[str, Any]]) -> list[str]:
        """Extract frequently visited destinations."""
        destination_counts = {}
        for trip in trips:
            dest = trip.get("destination")
            if dest:
                destination_counts[dest] = destination_counts.get(dest, 0) + 1

        # Return destinations visited more than once, sorted by frequency
        return [
            dest
            for dest, count in sorted(
                destination_counts.items(), key=lambda x: x[1], reverse=True
            )
            if count > 1
        ]

    def _calculate_typical_budget_range(
        self, budget_history: list[dict[str, Any]]
    ) -> dict[str, float]:
        """Calculate typical budget range from history."""
        budgets = [
            b.get("total_budget", 0) for b in budget_history if b.get("total_budget")
        ]
        if not budgets:
            return {}

        budgets.sort()
        return {
            "min": min(budgets),
            "max": max(budgets),
            "median": budgets[len(budgets) // 2],
            "average": sum(budgets) / len(budgets),
        }

    def _analyze_spending_patterns(
        self, budget_history: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Analyze spending patterns from budget history."""
        patterns = {
            "accommodation_percentage": [],
            "transportation_percentage": [],
            "food_percentage": [],
            "activities_percentage": [],
        }

        for budget in budget_history:
            total = budget.get("total_budget", 0)
            if total > 0:
                for category in patterns:
                    category_amount = budget.get(category.replace("_percentage", ""), 0)
                    patterns[category].append((category_amount / total) * 100)

        # Calculate averages
        return {
            category: sum(values) / len(values) if values else 0
            for category, values in patterns.items()
        }

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
            insights = await self._extract_insights_from_state(state)

            if insights:
                # Persist insights via MemoryService as a structured note
                svc = await self._get_service()
                payload = ConversationMemoryRequest(
                    messages=[
                        {
                            "role": "system",
                            "content": "Store state insights for personalization.",
                        },
                        {"role": "user", "content": str(insights)},
                    ],
                    session_id=state.get("session_id"),
                    trip_id=None,
                    metadata={"type": "state_insights"},
                )
                result = await svc.add_conversation_memory(user_id, payload)
                logger.info("Successfully persisted insights for user %s", user_id)
                return result
            else:
                logger.debug("No new insights to persist for user %s", user_id)
                return {}

        except Exception as e:
            logger.exception("Failed to persist insights for user %s", user_id)
            return {"error": str(e)}

    async def _extract_insights_from_state(
        self, state: TravelPlanningState
    ) -> dict[str, Any]:
        """Extract insights from LangGraph state.

        Args:
            state: Current state

        Returns:
            Extracted insights
        """
        insights = {}

        # Extract updated preferences
        user_preferences = state.get("user_preferences", {})
        if user_preferences:
            insights["preferences"] = user_preferences

        # Extract learned facts from interactions
        messages = state.get("messages", [])
        if messages:
            insights["learned_facts"] = self._extract_facts_from_messages(messages)

        # Extract search patterns
        search_history = []
        if state.get("flight_searches"):
            search_history.extend(state["flight_searches"])
        if state.get("accommodation_searches"):
            search_history.extend(state["accommodation_searches"])
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

        # Add session context
        insights["session_context"] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "session_id": state.get("session_id"),
            "agent_interactions": state.get("agent_history", []),
            "total_messages": len(messages),
        }

        return insights

    def _extract_facts_from_messages(self, messages: list[dict[str, Any]]) -> list[str]:
        """Extract facts and insights from conversation messages."""
        facts = []

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
            payload = ConversationMemoryRequest(
                messages=[
                    {
                        "role": "system",
                        "content": "Store checkpoint reference",
                    },
                    {"role": "user", "content": str(checkpoint_ref)},
                ],
                session_id=session_id,
                trip_id=None,
                metadata={"type": "checkpoint_reference"},
            )
            await svc.add_conversation_memory(user_id, payload)

            logger.debug(
                "Stored checkpoint reference %s for user %s", checkpoint_id, user_id
            )

        except Exception:
            logger.exception("Failed to store checkpoint reference")


# Global bridge instance
_global_memory_bridge: SessionMemoryBridge | None = None


def get_memory_bridge() -> SessionMemoryBridge:
    """Get the global session memory bridge instance."""
    global _global_memory_bridge  # pylint: disable=global-statement
    if _global_memory_bridge is None:
        _global_memory_bridge = SessionMemoryBridge()
    return _global_memory_bridge
