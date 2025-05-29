"""
Modern memory tools for TripSage agents using Mem0.

This module provides memory management tools that wrap the TripSageMemoryService
for use with agents. This is a complete replacement of the old Neo4j-based
memory system with the new Mem0-based implementation.

Key Features:
- User-specific memory isolation
- Automatic conversation memory extraction
- Travel preference tracking
- Session-based memory management
- Fast semantic search (91% faster than baseline)
- 26% better accuracy than OpenAI memory
"""

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from tripsage.services.memory_service import TripSageMemoryService
from tripsage.tools.models import (
    ConversationMessage,
    MemorySearchQuery,
    SessionSummary,
    UserPreferences,
)
from tripsage_core.utils.logging_utils import get_logger
from tripsage_core.utils.decorator_utils import with_error_handling

# Set up logger
logger = get_logger(__name__)

# Global memory service instance
_memory_service: Optional[TripSageMemoryService] = None


def get_memory_service() -> TripSageMemoryService:
    """Get the global memory service instance."""
    global _memory_service
    if _memory_service is None:
        _memory_service = TripSageMemoryService()
    return _memory_service


async def add_conversation_memory(
    messages: List[ConversationMessage],
    user_id: str,
    session_id: Optional[str] = None,
    context_type: str = "travel_planning",
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Add conversation messages to user memory.

    This extracts meaningful information from conversations and stores it
    as searchable memories for future reference.

    Args:
        messages: List of conversation messages
        user_id: User identifier
        session_id: Optional session identifier
        context_type: Type of conversation context

    Returns:
        Dictionary with extraction results and metadata
    """
    # Validation - these should bubble up as ValueError exceptions
    if not messages:
        raise ValueError("Messages cannot be empty")
    if not user_id or user_id.strip() == "":
        raise ValueError("User ID cannot be empty")

    @with_error_handling
    async def _do_add_conversation_memory() -> Dict[str, Any]:
        logger.info(f"Adding conversation memory for user {user_id}")

        service = get_memory_service()

        # Convert to the format expected by Mem0
        message_dicts = [{"role": msg.role, "content": msg.content} for msg in messages]

        # Add travel-specific metadata
        enhanced_metadata = {
            "domain": "travel_planning",
            "context_type": context_type,
            "session_id": session_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": user_id,
        }
        if metadata:
            enhanced_metadata.update(metadata)

        result = await service.add_conversation_memory(
            messages=message_dicts,
            user_id=user_id,
            session_id=session_id,
            metadata=enhanced_metadata,
        )

        logger.info(
            f"Successfully extracted {len(result.get('results', []))} "
            f"memories for user {user_id}"
        )

        return {
            "status": "success",
            "memory_id": result.get("memory_id", "mem-generated"),
            "memories_extracted": len(result.get("results", [])),
            "tokens_used": result.get("usage", {}).get("total_tokens", 0),
            "extraction_time": result.get("processing_time", 0),
            "memories": result.get("results", []),
        }

    return await _do_add_conversation_memory()


@with_error_handling
async def search_user_memories(search_query: MemorySearchQuery) -> List[Dict[str, Any]]:
    """Search user memories with semantic similarity.

    Args:
        search_query: Memory search query object

    Returns:
        List of memory search results
    """
    try:
        logger.info(
            f"Searching memories for user {search_query.user_id} "
            f"with query: {search_query.query}"
        )

        service = get_memory_service()

        results = await service.search_memories(
            query=search_query.query,
            user_id=search_query.user_id,
            limit=search_query.limit,
            category_filter=search_query.category_filter,
        )

        return results

    except Exception as e:
        logger.error(f"Error searching user memories: {str(e)}")
        return []


async def get_user_context(
    user_id: str, context_type: Optional[str] = None
) -> Dict[str, Any]:
    """Get comprehensive user context for personalization.

    Args:
        user_id: User identifier
        context_type: Optional context type filter

    Returns:
        Dictionary with user context including preferences, history, and insights
    """
    if not user_id:
        raise ValueError("User ID cannot be empty")

    @with_error_handling
    async def _do_get_user_context() -> Dict[str, Any]:
        logger.info(f"Getting user context for user {user_id}")

        service = get_memory_service()

        context = await service.get_user_context(user_id)

        return context

    return await _do_get_user_context()


@with_error_handling
async def update_user_preferences(preferences: UserPreferences) -> Dict[str, Any]:
    """Update user travel preferences.

    Args:
        preferences: User preferences object

    Returns:
        Dictionary with update status
    """
    try:
        user_id = preferences.user_id
        logger.info(f"Updating preferences for user {user_id}")

        service = get_memory_service()

        # Convert preferences to dictionary
        preferences_dict = preferences.model_dump(
            exclude_none=True, exclude={"user_id"}, by_alias=True
        )

        await service.update_user_preferences(
            user_id=user_id, preferences=preferences_dict
        )

        return {
            "status": "success",
            "message": "User preferences updated successfully",
            "preferences_updated": len(preferences_dict),
        }

    except Exception as e:
        logger.error(f"Error updating user preferences: {str(e)}")
        return {"status": "error", "error": str(e)}


@with_error_handling
async def save_session_summary(session_summary: SessionSummary) -> Dict[str, Any]:
    """Save a summary of the conversation session.

    Args:
        session_summary: Session summary object

    Returns:
        Dictionary with save status
    """
    try:
        logger.info(f"Saving session summary for user {session_summary.user_id}")

        memory_service = get_memory_service()

        # Create conversation for the summary
        summary_messages = [
            {
                "role": "system",
                "content": (
                    "Extract key insights and decisions from this session summary."
                ),
            },
            {"role": "user", "content": f"Session Summary: {session_summary.summary}"},
        ]

        if session_summary.key_insights:
            summary_messages.append(
                {
                    "role": "user",
                    "content": (
                        f"Key Insights: {', '.join(session_summary.key_insights)}"
                    ),
                }
            )

        if session_summary.decisions_made:
            summary_messages.append(
                {
                    "role": "user",
                    "content": (
                        f"Decisions Made: {', '.join(session_summary.decisions_made)}"
                    ),
                }
            )

        result = await memory_service.add_conversation_memory(
            messages=summary_messages,
            user_id=session_summary.user_id,
            session_id=session_summary.session_id,
            metadata={
                "type": "session_summary",
                "category": "travel_planning",
                "session_end": datetime.now(timezone.utc).isoformat(),
            },
        )

        return {
            "status": "success",
            "message": "Session summary saved successfully",
            "memories_created": len(result.get("results", [])),
        }

    except Exception as e:
        logger.error(f"Error saving session summary: {str(e)}")
        return {"status": "error", "error": str(e)}


@with_error_handling
async def get_travel_insights(
    user_id: str, insight_type: Optional[str] = None
) -> Dict[str, Any]:
    """Get travel insights based on user's memory.

    Args:
        user_id: User identifier
        insight_type: Type of insights to retrieve

    Returns:
        Dictionary with travel insights
    """
    try:
        logger.info(f"Getting travel insights for user {user_id}")

        # Get user context first
        context_result = await get_user_context(user_id)

        if context_result["status"] != "success":
            return context_result

        context = context_result["context"]
        insights = context.get("insights", {})

        if insight_type and insight_type in insights:
            return {
                "status": "success",
                "insight_type": insight_type,
                "insights": {insight_type: insights[insight_type]},
            }

        return {"status": "success", "insights": insights}

    except Exception as e:
        logger.error(f"Error getting travel insights: {str(e)}")
        return {"status": "error", "error": str(e), "insights": {}}


@with_error_handling
async def find_similar_travelers(
    user_id: str, similarity_threshold: float = 0.8
) -> Dict[str, Any]:
    """Find users with similar travel preferences and history.

    Args:
        user_id: User identifier
        similarity_threshold: Minimum similarity threshold

    Returns:
        Dictionary with similar travelers
    """
    try:
        logger.info(f"Finding similar travelers for user {user_id}")

        # Get user's preferences
        context_result = await get_user_context(user_id)

        if context_result["status"] != "success":
            return context_result

        user_context = context_result["context"]

        # Search for users with similar preferences
        # preference_query = ""
        if user_context.get("preferences"):
            prefs = []
            for category, value in user_context["preferences"].items():
                prefs.append(f"{category}: {value}")
            # preference_query = ", ".join(prefs)

        # Note: This is a simplified implementation
        # In a full implementation, we'd have more sophisticated similarity matching
        # similar_memories = await search_user_memories(
        #     query=preference_query,
        #     user_id="*",  # Search across all users (if supported)
        #     limit=10,
        # )

        return {
            "status": "success",
            "similar_travelers_count": 0,  # Placeholder - needs cross-user search
            "message": "Similar traveler search requires cross-user memory access",
        }

    except Exception as e:
        logger.error(f"Error finding similar travelers: {str(e)}")
        return {"status": "error", "error": str(e), "similar_travelers": []}


@with_error_handling
async def get_destination_memories(
    destination: str, user_id: Optional[str] = None
) -> Dict[str, Any]:
    """Get memories related to a specific destination.

    Args:
        destination: Destination name
        user_id: Optional user ID for personalized results

    Returns:
        Dictionary with destination memories
    """
    try:
        logger.info(f"Getting destination memories for: {destination}")

        if user_id:
            # Get user-specific destination memories
            search_query = MemorySearchQuery(
                query=destination,
                user_id=user_id,
                limit=10,
                category_filter="destinations",
            )
            memories = await search_user_memories(search_query)
        else:
            # This would require system-wide search capability
            # For now, return empty results
            memories = {"memories": []}

        return {
            "status": "success",
            "destination": destination,
            "memories": memories if isinstance(memories, list) else [],
        }

    except Exception as e:
        logger.error(f"Error getting destination memories: {str(e)}")
        return {"status": "error", "error": str(e), "memories": []}


@with_error_handling
async def track_user_activity(
    user_id: str, activity_type: str, activity_data: Dict[str, Any]
) -> Dict[str, Any]:
    """Track user activity for behavior analysis.

    Args:
        user_id: User identifier
        activity_type: Type of activity (search, booking, view, etc.)
        activity_data: Activity data

    Returns:
        Dictionary with tracking status
    """
    try:
        logger.info(f"Tracking activity for user {user_id}: {activity_type}")

        # Create activity memory
        activity_messages = [
            {"role": "system", "content": "Track user activity for behavior analysis."},
            {
                "role": "user",
                "content": (
                    f"User performed {activity_type} activity: "
                    f"{json.dumps(activity_data)}"
                ),
            },
        ]

        result = await add_conversation_memory(
            messages=[ConversationMessage(**msg) for msg in activity_messages],
            user_id=user_id,
            context_type="user_activity",
        )

        return {
            "status": "success",
            "activity_tracked": activity_type,
            "memories_created": result.get("memories_extracted", 0),
        }

    except Exception as e:
        logger.error(f"Error tracking user activity: {str(e)}")
        return {"status": "error", "error": str(e)}


# Legacy compatibility functions (for gradual migration)


@with_error_handling
async def initialize_agent_memory(user_id: Optional[str] = None) -> Dict[str, Any]:
    """Initialize agent memory (legacy compatibility).

    Args:
        user_id: Optional user ID

    Returns:
        Dictionary with session memory data
    """
    logger.info(f"Initializing agent memory for user: {user_id}")

    if not user_id:
        return {
            "user": None,
            "preferences": {},
            "recent_trips": [],
            "popular_destinations": [],
        }

    # Get user context using new memory system
    context_result = await get_user_context(user_id)

    if context_result["status"] == "success":
        context = context_result["context"]

        return {
            "user": {"id": user_id, "name": f"User {user_id}"},
            "preferences": context.get("preferences", {}),
            "recent_trips": context.get("past_trips", [])[:5],
            "popular_destinations": [],  # Would need system-wide data
        }

    return {
        "user": None,
        "preferences": {},
        "recent_trips": [],
        "popular_destinations": [],
    }


@with_error_handling
async def update_agent_memory(user_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    """Update agent memory (legacy compatibility).

    Args:
        user_id: User ID
        updates: Dictionary with updates

    Returns:
        Dictionary with update status
    """
    logger.info(f"Updating agent memory for user: {user_id}")

    result = {"entities_created": 0, "relations_created": 0, "observations_added": 0}

    try:
        # Handle preferences
        if "preferences" in updates:
            prefs_data = updates["preferences"].copy()
            prefs_data["user_id"] = user_id
            prefs = UserPreferences(**prefs_data)
            await update_user_preferences(prefs)
            result["observations_added"] += len(updates["preferences"])

        # Handle learned facts as conversation memory
        if "learned_facts" in updates:
            facts_messages = [
                {"role": "system", "content": "Extract learned facts about travel."},
                {
                    "role": "user",
                    "content": f"Learned facts: {json.dumps(updates['learned_facts'])}",
                },
            ]

            await add_conversation_memory(
                messages=[ConversationMessage(**msg) for msg in facts_messages],
                user_id=user_id,
                context_type="learned_facts",
            )
            result["entities_created"] += len(updates["learned_facts"])

        return result

    except Exception as e:
        logger.error(f"Error updating agent memory: {str(e)}")
        return result


# Health check function
@with_error_handling
async def memory_health_check() -> Dict[str, Any]:
    """Check memory service health.

    Returns:
        Dictionary with health status
    """
    try:
        memory_service = get_memory_service()
        is_healthy = await memory_service.health_check()

        return {
            "status": "healthy" if is_healthy else "unhealthy",
            "service": "Mem0 Memory Service",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        logger.error(f"Memory health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "service": "Mem0 Memory Service",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
