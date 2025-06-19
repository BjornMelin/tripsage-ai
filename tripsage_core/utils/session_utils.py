"""
Session memory utilities for TripSage Core using Mem0.

This module provides utilities for initializing and updating session memory
using the new Mem0-based memory system. Complete replacement of the old
Neo4j-based implementation.

Key Features:
- User context initialization from memory
- Preference tracking and updates
- Session summary storage
- Learned facts processing
- Integration with Core memory service
"""

from typing import Any

from pydantic import BaseModel, Field

from tripsage_core.utils.logging_utils import get_logger

logger = get_logger(__name__)


# Session memory models
class ConversationMessage(BaseModel):
    """Model for conversation messages."""

    role: str = Field(..., description="Message role (system/user/assistant)")
    content: str = Field(..., description="Message content")


class SessionSummary(BaseModel):
    """Model for session summary data."""

    user_id: str = Field(..., description="User ID")
    session_id: str = Field(..., description="Session ID")
    summary: str = Field(..., description="Session summary text")
    key_insights: list[str] | None = Field(
        None, description="Key insights from the session"
    )
    decisions_made: list[str] | None = Field(
        None, description="Decisions made during the session"
    )


class UserPreferences(BaseModel):
    """Model for user preferences."""

    budget_range: dict[str, float] | None = None
    preferred_destinations: list[str] | None = None
    travel_style: str | None = None
    accommodation_preferences: dict[str, Any] | None = None
    dietary_restrictions: list[str] | None = None
    accessibility_needs: list[str] | None = None


async def initialize_session_memory(user_id: str | None = None) -> dict[str, Any]:
    """Initialize session memory by retrieving relevant user context.

    This function retrieves user preferences, past trips, and other relevant
    context from the Mem0 memory system to initialize the session memory.

    Args:
        user_id: Optional user ID

    Returns:
        Dictionary with session memory data
    """
    logger.info(f"Initializing session memory for user: {user_id}")

    # Default session data structure
    session_data = {
        "user": None,
        "preferences": {},
        "recent_trips": [],
        "popular_destinations": [],
        "insights": {},
    }

    # Retrieve user information if available
    if user_id:
        try:
            # Import here to avoid circular dependencies
            from tripsage_core.services.business import MemoryService

            memory_service = MemoryService()

            # Get comprehensive user context from memory
            memories = await memory_service.get_memories(
                user_id=user_id, memory_type="user_preferences"
            )

            # Extract preferences from memories
            preferences = {}
            for memory in memories:
                if hasattr(memory, "content") and isinstance(memory.content, dict):
                    preferences.update(memory.content)

            # Get past trips
            trip_memories = await memory_service.get_memories(
                user_id=user_id, memory_type="trip_history"
            )
            recent_trips = []
            for memory in trip_memories[:5]:  # Limit to 5 most recent
                if hasattr(memory, "content"):
                    recent_trips.append(memory.content)

            # Update session data
            session_data.update(
                {
                    "user": {"id": user_id, "name": f"User {user_id}"},
                    "preferences": preferences,
                    "recent_trips": recent_trips,
                    "insights": {},  # Populated from conversation context
                }
            )

            logger.info(
                f"Loaded {len(preferences)} preferences and "
                f"{len(recent_trips)} trips for user {user_id}"
            )

        except Exception as e:
            logger.error(f"Error loading user context for {user_id}: {str(e)}")
            # Continue with default session data

    return session_data


async def update_session_memory(
    user_id: str, updates: dict[str, Any]
) -> dict[str, Any]:
    """Update session memory with new knowledge.

    This function updates the memory system with new information
    learned during the session using the Mem0 memory service.

    Args:
        user_id: User ID
        updates: Dictionary with updates containing:
            - preferences: Dict of user preferences
            - learned_facts: List of learned facts/insights
            - conversation_context: Dict with conversation context

    Returns:
        Dictionary with update status
    """
    logger.info(f"Updating session memory for user {user_id}")

    result = {
        "preferences_updated": 0,
        "facts_processed": 0,
        "memories_created": 0,
        "success": True,
        "errors": [],
    }

    try:
        # Import here to avoid circular dependencies
        from tripsage_core.services.business.memory_service import MemoryService

        memory_service = MemoryService()

        # Process user preferences
        if "preferences" in updates and updates["preferences"]:
            await _update_user_preferences_memory(
                user_id, updates["preferences"], result, memory_service
            )

        # Process learned facts
        if "learned_facts" in updates and updates["learned_facts"]:
            await _process_learned_facts(
                user_id, updates["learned_facts"], result, memory_service
            )

        # Process general conversation context
        if "conversation_context" in updates and updates["conversation_context"]:
            await _process_conversation_context(
                user_id, updates["conversation_context"], result, memory_service
            )

    except Exception as e:
        logger.error(f"Error updating session memory: {str(e)}")
        result["success"] = False
        result["errors"].append(str(e))

    # Check if any errors occurred in helper functions
    if result["errors"]:
        result["success"] = False

    return result


async def store_session_summary(
    user_id: str,
    summary: str,
    session_id: str,
    key_insights: list[str] | None = None,
    decisions_made: list[str] | None = None,
) -> dict[str, Any]:
    """Store session summary in the memory system.

    This function stores a summary of the session using the Mem0 memory service.

    Args:
        user_id: User ID
        summary: Session summary text
        session_id: Session ID
        key_insights: Optional list of key insights from the session
        decisions_made: Optional list of decisions made during the session

    Returns:
        Dictionary with storage status
    """
    logger.info(f"Storing session summary for user {user_id}, session {session_id}")

    try:
        # Import here to avoid circular dependencies
        from tripsage_core.services.business.memory_service import MemoryService

        memory_service = MemoryService()

        # Create session summary content
        summary_content = {
            "session_id": session_id,
            "summary": summary,
            "key_insights": key_insights or [],
            "decisions_made": decisions_made or [],
        }

        # Store as conversation context memory
        memory_id = await memory_service.add_memory(
            user_id=user_id,
            content=summary_content,
            memory_type="conversation_context",
            metadata={
                "session_id": session_id,
                "type": "session_summary",
            },
        )

        if memory_id:
            logger.info(
                f"Successfully stored session summary with memory ID: {memory_id}"
            )
            return {
                "status": "success",
                "memory_id": memory_id,
                "memories_created": 1,
            }
        else:
            logger.warning("Failed to store session summary")
            return {
                "status": "error",
                "error": "Failed to create memory",
                "memories_created": 0,
            }

    except Exception as e:
        logger.error(f"Error storing session summary: {str(e)}")
        return {"status": "error", "error": str(e), "memories_created": 0}


# Private helper functions


async def _update_user_preferences_memory(
    user_id: str, preferences: dict[str, Any], result: dict[str, Any], memory_service
) -> None:
    """Update user preferences in memory.

    Args:
        user_id: User ID
        preferences: Dictionary of preferences
        result: Result dictionary to update
        memory_service: Memory service instance
    """
    try:
        # Convert to UserPreferences model
        user_prefs = UserPreferences(**preferences)

        # Update preferences in memory
        memory_id = await memory_service.add_memory(
            user_id=user_id,
            content=user_prefs.model_dump(exclude_none=True),
            memory_type="user_preferences",
            metadata={"updated_from": "session"},
        )

        if memory_id:
            result["preferences_updated"] = 1
            result["memories_created"] += 1
        else:
            result["errors"].append("Failed to update preferences")

    except Exception as e:
        logger.error(f"Error updating preferences: {str(e)}")
        result["errors"].append(f"Preference processing error: {str(e)}")


async def _process_learned_facts(
    user_id: str, facts: list[dict[str, Any]], result: dict[str, Any], memory_service
) -> None:
    """Process learned facts as conversation memory.

    Args:
        user_id: User ID
        facts: List of fact dictionaries
        result: Result dictionary to update
        memory_service: Memory service instance
    """
    try:
        # Store each fact as a memory
        for fact in facts:
            memory_id = await memory_service.add_memory(
                user_id=user_id,
                content=fact if isinstance(fact, dict) else {"fact": str(fact)},
                memory_type="search_patterns",  # Store as search patterns for insights
                metadata={"source": "learned_facts"},
            )
            if memory_id:
                result["memories_created"] += 1

        result["facts_processed"] = len(facts)

    except Exception as e:
        logger.error(f"Error processing learned facts: {str(e)}")
        result["errors"].append(f"Facts processing error: {str(e)}")


async def _process_conversation_context(
    user_id: str, context: dict[str, Any], result: dict[str, Any], memory_service
) -> None:
    """Process general conversation context as memory.

    Args:
        user_id: User ID
        context: Conversation context dictionary
        result: Result dictionary to update
        memory_service: Memory service instance
    """
    try:
        # Extract meaningful context for memory storage
        relevant_keys = [
            "destinations_discussed",
            "travel_intent",
            "budget_mentioned",
            "dates_mentioned",
        ]

        context_data = {
            key: value
            for key, value in context.items()
            if key in relevant_keys and value
        }

        if context_data:
            memory_id = await memory_service.add_memory(
                user_id=user_id,
                content=context_data,
                memory_type="conversation_context",
                metadata={"source": "session_context"},
            )
            if memory_id:
                result["memories_created"] += 1

    except Exception as e:
        logger.error(f"Error processing conversation context: {str(e)}")
        result["errors"].append(f"Context processing error: {str(e)}")


# Simple SessionMemory utility class for API dependencies
class SessionMemory:
    """Simple session memory utility class for API integration.

    This is a lightweight utility class that provides a simple interface for
    session memory operations while the full domain models handle the data storage.
    """

    def __init__(self, session_id: str, user_id: str | None = None):
        """Initialize session memory utility.

        Args:
            session_id: Session identifier
            user_id: Optional user identifier
        """
        self.session_id = session_id
        self.user_id = user_id
        self._memory_data: dict[str, Any] = {}

    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from session memory.

        Args:
            key: Memory key
            default: Default value if key not found

        Returns:
            Value from memory or default
        """
        return self._memory_data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a value in session memory.

        Args:
            key: Memory key
            value: Value to store
        """
        self._memory_data[key] = value

    def update(self, data: dict[str, Any]) -> None:
        """Update session memory with multiple values.

        Args:
            data: Dictionary of key-value pairs to update
        """
        self._memory_data.update(data)

    def clear(self) -> None:
        """Clear all session memory data."""
        self._memory_data.clear()

    def to_dict(self) -> dict[str, Any]:
        """Convert session memory to dictionary.

        Returns:
            Dictionary representation of session memory
        """
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "data": self._memory_data.copy(),
        }


__all__ = [
    "ConversationMessage",
    "SessionSummary",
    "UserPreferences",
    "SessionMemory",
    "initialize_session_memory",
    "update_session_memory",
    "store_session_summary",
]
