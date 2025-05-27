"""
Session Memory Bridge for LangGraph Integration

This module provides integration between LangGraph state management and TripSage's
existing session memory utilities, enabling seamless memory persistence and retrieval
across agent interactions.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from tripsage.mcp_abstraction.manager import MCPManager
from tripsage.orchestration.state import TravelPlanningState
from tripsage.utils.session_memory import (
    initialize_session_memory,
    update_session_memory,
)

logger = logging.getLogger(__name__)


class SessionMemoryBridge:
    """
    Bridge between LangGraph state and TripSage session memory utilities.

    This class handles bidirectional synchronization between:
    - LangGraph TravelPlanningState (ephemeral)
    - Neo4j Knowledge Graph (persistent session memory)
    - User preferences and learned insights
    """

    def __init__(self, mcp_manager: Optional[MCPManager] = None):
        """Initialize the memory bridge."""
        self.mcp_manager = mcp_manager or MCPManager()

    async def hydrate_state(self, state: TravelPlanningState) -> TravelPlanningState:
        """
        Load user context and preferences into LangGraph state.

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
            logger.debug(f"Hydrating state for user: {user_id}")

            # Load session memory data
            session_data = await initialize_session_memory(user_id)

            # Map session data to LangGraph state format
            if session_data:
                state = await self._map_session_to_state(state, session_data)
                logger.info(f"Successfully hydrated state for user {user_id}")
            else:
                logger.info(f"No existing session data found for user {user_id}")

        except Exception as e:
            logger.error(f"Failed to hydrate state for user {user_id}: {e}")
            # Continue without memory data rather than failing

        return state

    async def _map_session_to_state(
        self, state: TravelPlanningState, session_data: Dict[str, Any]
    ) -> TravelPlanningState:
        """
        Map session memory data to LangGraph state format.

        Args:
            state: Current state
            session_data: Data from session memory

        Returns:
            Updated state with memory data
        """
        # Extract user preferences
        preferences = session_data.get("preferences", {})
        if preferences:
            state["user_preferences"] = {
                "accommodation_type": preferences.get("preferred_accommodation_type"),
                "budget_level": preferences.get("budget_preference"),
                "travel_style": preferences.get("travel_style"),
                "dietary_restrictions": preferences.get("dietary_restrictions", []),
                "accessibility_needs": preferences.get("accessibility_needs", []),
                "language_preferences": preferences.get("language_preferences", []),
            }

        # Extract recent destinations and travel patterns
        recent_trips = session_data.get("recent_trips", [])
        if recent_trips:
            state["destination_info"] = {
                "recent_destinations": [
                    trip.get("destination")
                    for trip in recent_trips[-5:]  # Last 5 trips
                ],
                "favorite_destinations": self._extract_favorite_destinations(
                    recent_trips
                ),
                "travel_frequency": len(recent_trips),
            }

        # Extract budget insights
        budget_history = session_data.get("budget_history", [])
        if budget_history:
            state["budget_constraints"] = {
                "typical_range": self._calculate_typical_budget_range(budget_history),
                "last_budget": budget_history[-1].get("total_budget")
                if budget_history
                else None,
                "spending_patterns": self._analyze_spending_patterns(budget_history),
            }

        # Extract learned insights and facts
        insights = session_data.get("insights", [])
        if insights:
            state["user_insights"] = {
                "learned_facts": [insight.get("fact") for insight in insights],
                "preferences_learned": [
                    insight.get("preference")
                    for insight in insights
                    if insight.get("type") == "preference"
                ],
                "dislikes": [
                    insight.get("dislike")
                    for insight in insights
                    if insight.get("type") == "dislike"
                ],
            }

        # Add session metadata
        state["session_metadata"] = {
            "last_activity": session_data.get("last_activity"),
            "session_count": session_data.get("session_count", 0),
            "memory_loaded_at": datetime.utcnow().isoformat(),
        }

        return state

    def _extract_favorite_destinations(self, trips: List[Dict[str, Any]]) -> List[str]:
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
        self, budget_history: List[Dict[str, Any]]
    ) -> Dict[str, float]:
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
        self, budget_history: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
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
                for category in patterns.keys():
                    category_amount = budget.get(category.replace("_percentage", ""), 0)
                    patterns[category].append((category_amount / total) * 100)

        # Calculate averages
        return {
            category: sum(values) / len(values) if values else 0
            for category, values in patterns.items()
        }

    async def extract_and_persist_insights(
        self, state: TravelPlanningState
    ) -> Dict[str, Any]:
        """
        Extract insights from state and update knowledge graph.

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
            logger.debug(f"Extracting insights for user: {user_id}")

            # Extract insights from current state
            insights = await self._extract_insights_from_state(state)

            if insights:
                # Update session memory with new insights
                result = await update_session_memory(user_id, insights)
                logger.info(f"Successfully persisted insights for user {user_id}")
                return result
            else:
                logger.debug(f"No new insights to persist for user {user_id}")
                return {}

        except Exception as e:
            logger.error(f"Failed to persist insights for user {user_id}: {e}")
            return {"error": str(e)}

    async def _extract_insights_from_state(
        self, state: TravelPlanningState
    ) -> Dict[str, Any]:
        """
        Extract insights from LangGraph state.

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
        if state.get("destination_searches"):
            search_history.extend(state["destination_searches"])

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
            "timestamp": datetime.utcnow().isoformat(),
            "session_id": state.get("session_id"),
            "agent_interactions": state.get("agent_history", []),
            "total_messages": len(messages),
        }

        return insights

    def _extract_facts_from_messages(self, messages: List[Dict[str, Any]]) -> List[str]:
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

    def state_to_checkpoint_format(self, state: TravelPlanningState) -> Dict[str, Any]:
        """
        Convert state to format suitable for checkpointing.

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
        self, checkpoint_data: Dict[str, Any]
    ) -> TravelPlanningState:
        """
        Restore state from checkpoint data.

        Args:
            checkpoint_data: Saved checkpoint data

        Returns:
            Restored TravelPlanningState
        """
        state = TravelPlanningState()

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
        metadata: Dict[str, Any],
    ) -> None:
        """
        Store reference to checkpoint in knowledge graph.

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
                "timestamp": datetime.utcnow().isoformat(),
                "metadata": metadata,
            }

            # Store in session memory as checkpoint reference
            await update_session_memory(
                user_id, {"checkpoint_references": [checkpoint_ref]}
            )

            logger.debug(
                f"Stored checkpoint reference {checkpoint_id} for user {user_id}"
            )

        except Exception as e:
            logger.error(f"Failed to store checkpoint reference: {e}")


# Global bridge instance
_global_memory_bridge: Optional[SessionMemoryBridge] = None


def get_memory_bridge() -> SessionMemoryBridge:
    """Get the global session memory bridge instance."""
    global _global_memory_bridge
    if _global_memory_bridge is None:
        _global_memory_bridge = SessionMemoryBridge()
    return _global_memory_bridge
