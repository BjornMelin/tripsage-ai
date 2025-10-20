"""Modern memory tools for TripSage agents using Mem0.

This module provides memory management tools that wrap the TripSageMemoryService
for use with agents. Refactored to use dependency injection instead of global state.

Key Features:
- User-specific memory isolation
- Automatic conversation memory extraction
- Travel preference tracking
- Session-based memory management
- Fast semantic search (91% faster than baseline)
- 26% better accuracy than OpenAI memory
"""

import json
from datetime import UTC, datetime
from typing import Any


try:
    from agents import function_tool
except ImportError:
    from unittest.mock import MagicMock

    function_tool = MagicMock

from tripsage.agents.service_registry import ServiceRegistry
from tripsage.tools.models import (
    ConversationMessage,
    MemorySearchQuery,
    SessionSummary,
    UserPreferences,
)
from tripsage_core.utils.decorator_utils import with_error_handling
from tripsage_core.utils.logging_utils import get_logger


# Set up logger
logger = get_logger(__name__)


@function_tool
async def add_conversation_memory(
    messages: list[ConversationMessage],
    user_id: str,
    service_registry: ServiceRegistry,
    session_id: str | None = None,
    context_type: str = "travel_planning",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Add conversation messages to user memory.

    This extracts meaningful information from conversations and stores it
    as searchable memories for future reference.

    Args:
        messages: List of conversation messages
        user_id: User identifier
        service_registry: Service registry for accessing services
        session_id: Optional session identifier
        context_type: Type of conversation context
        metadata: Additional metadata

    Returns:
        Dictionary with extraction results and metadata
    """
    # Validation - these should bubble up as ValueError exceptions
    if not messages:
        raise ValueError("Messages cannot be empty")
    if not user_id or user_id.strip() == "":
        raise ValueError("User ID cannot be empty")

    @with_error_handling()
    async def _do_add_conversation_memory() -> dict[str, Any]:
        logger.info(f"Adding conversation memory for user {user_id}")

        memory_service = service_registry.get_required_service("memory_service")

        # Convert to the format expected by Mem0
        message_dicts = [{"role": msg.role, "content": msg.content} for msg in messages]

        # Add travel-specific metadata
        enhanced_metadata = {
            "domain": "travel_planning",
            "context_type": context_type,
            "session_id": session_id,
            "timestamp": datetime.now(UTC).isoformat(),
            "user_id": user_id,
        }
        if metadata:
            enhanced_metadata.update(metadata)

        result = await memory_service.add_conversation_memory(
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


@function_tool
@with_error_handling()
async def search_user_memories(
    search_query: MemorySearchQuery,
    service_registry: ServiceRegistry,
) -> list[dict[str, Any]]:
    """Search user memories with semantic similarity.

    Args:
        search_query: Memory search query object
        service_registry: Service registry for accessing services

    Returns:
        List of memory search results
    """
    try:
        logger.info(
            f"Searching memories for user {search_query.user_id} "
            f"with query: {search_query.query}"
        )

        memory_service = service_registry.get_required_service("memory_service")

        results = await memory_service.search_memories(
            query=search_query.query,
            user_id=search_query.user_id,
            limit=search_query.limit,
            category_filter=search_query.category_filter,
        )

        return results

    except Exception as e:
        logger.exception(f"Error searching user memories: {e!s}")
        return []


@function_tool
async def get_user_context(
    user_id: str,
    service_registry: ServiceRegistry,
    context_type: str | None = None,
) -> dict[str, Any]:
    """Get comprehensive user context for personalization.

    Args:
        user_id: User identifier
        service_registry: Service registry for accessing services
        context_type: Optional context type filter

    Returns:
        Dictionary with user context including preferences, history, and insights
    """
    if not user_id:
        raise ValueError("User ID cannot be empty")

    @with_error_handling()
    async def _do_get_user_context() -> dict[str, Any]:
        logger.info(f"Getting user context for user {user_id}")

        memory_service = service_registry.get_required_service("memory_service")

        context = await memory_service.get_user_context(user_id)

        return context

    return await _do_get_user_context()


@function_tool
@with_error_handling()
async def update_user_preferences(
    preferences: UserPreferences,
    service_registry: ServiceRegistry,
) -> dict[str, Any]:
    """Update user travel preferences.

    Args:
        preferences: User preferences object
        service_registry: Service registry for accessing services

    Returns:
        Dictionary with update status
    """
    try:
        user_id = preferences.user_id
        logger.info(f"Updating preferences for user {user_id}")

        memory_service = service_registry.get_required_service("memory_service")

        # Convert preferences to dictionary
        preferences_dict = preferences.model_dump(
            exclude_none=True, exclude={"user_id"}, by_alias=True
        )

        await memory_service.update_user_preferences(
            user_id=user_id, preferences=preferences_dict
        )

        return {
            "status": "success",
            "message": "User preferences updated successfully",
            "preferences_updated": len(preferences_dict),
        }

    except Exception as e:
        logger.exception(f"Error updating user preferences: {e!s}")
        return {"status": "error", "error": str(e)}


@function_tool
@with_error_handling()
async def save_session_summary(
    session_summary: SessionSummary,
    service_registry: ServiceRegistry,
) -> dict[str, Any]:
    """Save a summary of the conversation session.

    Args:
        session_summary: Session summary object
        service_registry: Service registry for accessing services

    Returns:
        Dictionary with save status
    """
    try:
        logger.info(f"Saving session summary for user {session_summary.user_id}")

        memory_service = service_registry.get_required_service("memory_service")

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
                "session_end": datetime.now(UTC).isoformat(),
            },
        )

        return {
            "status": "success",
            "message": "Session summary saved successfully",
            "memories_created": len(result.get("results", [])),
        }

    except Exception as e:
        logger.exception(f"Error saving session summary: {e!s}")
        return {"status": "error", "error": str(e)}


@function_tool
@with_error_handling()
async def get_travel_insights(
    user_id: str,
    service_registry: ServiceRegistry,
    insight_type: str | None = None,
) -> dict[str, Any]:
    """Get travel insights based on user's memory.

    Args:
        user_id: User identifier
        service_registry: Service registry for accessing services
        insight_type: Type of insights to retrieve

    Returns:
        Dictionary with travel insights
    """
    try:
        logger.info(f"Getting travel insights for user {user_id}")

        # Get user context first
        context_result = await get_user_context(user_id, service_registry)

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
        logger.exception(f"Error getting travel insights: {e!s}")
        return {"status": "error", "error": str(e), "insights": {}}


@function_tool
@with_error_handling()
async def find_similar_travelers(
    user_id: str,
    service_registry: ServiceRegistry,
    similarity_threshold: float = 0.8,
) -> dict[str, Any]:
    """Find users with similar travel preferences and history.

    Args:
        user_id: User identifier
        service_registry: Service registry for accessing services
        similarity_threshold: Minimum similarity threshold

    Returns:
        Dictionary with similar travelers
    """
    try:
        logger.info(f"Finding similar travelers for user {user_id}")

        # Get user's preferences
        context_result = await get_user_context(user_id, service_registry)

        if context_result["status"] != "success":
            return context_result

        # Note: user_context would be used for similarity matching in full impl
        # user_context = context_result["context"]

        # Note: This is a simplified implementation
        # In a full implementation, we'd have more sophisticated similarity matching
        return {
            "status": "success",
            "similar_travelers_count": 0,  # Placeholder - needs cross-user search
            "message": "Similar traveler search requires cross-user memory access",
        }

    except Exception as e:
        logger.exception(f"Error finding similar travelers: {e!s}")
        return {"status": "error", "error": str(e), "similar_travelers": []}


@function_tool
@with_error_handling()
async def get_destination_memories(
    destination: str,
    service_registry: ServiceRegistry,
    user_id: str | None = None,
) -> dict[str, Any]:
    """Get memories related to a specific destination.

    Args:
        destination: Destination name
        service_registry: Service registry for accessing services
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
            memories = await search_user_memories(search_query, service_registry)
        else:
            # This would require system-wide search capability
            # For now, return empty results
            memories = []

        return {
            "status": "success",
            "destination": destination,
            "memories": memories if isinstance(memories, list) else [],
        }

    except Exception as e:
        logger.exception(f"Error getting destination memories: {e!s}")
        return {"status": "error", "error": str(e), "memories": []}


@function_tool
@with_error_handling()
async def track_user_activity(
    user_id: str,
    activity_type: str,
    activity_data: dict[str, Any],
    service_registry: ServiceRegistry,
) -> dict[str, Any]:
    """Track user activity for behavior analysis.

    Args:
        user_id: User identifier
        activity_type: Type of activity (search, booking, view, etc.)
        activity_data: Activity data
        service_registry: Service registry for accessing services

    Returns:
        Dictionary with tracking status
    """
    try:
        logger.info(f"Tracking activity for user {user_id}: {activity_type}")

        # Create activity memory
        activity_messages = [
            ConversationMessage(
                role="system", content="Track user activity for behavior analysis."
            ),
            ConversationMessage(
                role="user",
                content=(
                    f"User performed {activity_type} activity: "
                    f"{json.dumps(activity_data)}"
                ),
            ),
        ]

        result = await add_conversation_memory(
            messages=activity_messages,
            user_id=user_id,
            service_registry=service_registry,
            context_type="user_activity",
        )

        return {
            "status": "success",
            "activity_tracked": activity_type,
            "memories_created": result.get("memories_extracted", 0),
        }

    except Exception as e:
        logger.exception(f"Error tracking user activity: {e!s}")
        return {"status": "error", "error": str(e)}


# Health check function
@function_tool
@with_error_handling()
async def memory_health_check(service_registry: ServiceRegistry) -> dict[str, Any]:
    """Check memory service health.

    Args:
        service_registry: Service registry for accessing services

    Returns:
        Dictionary with health status
    """
    try:
        memory_service = service_registry.get_required_service("memory_service")
        is_healthy = await memory_service.health_check()

        return {
            "status": "healthy" if is_healthy else "unhealthy",
            "service": "Mem0 Memory Service",
            "timestamp": datetime.now(UTC).isoformat(),
        }

    except Exception as e:
        logger.exception(f"Memory health check failed: {e!s}")
        return {
            "status": "unhealthy",
            "service": "Mem0 Memory Service",
            "error": str(e),
            "timestamp": datetime.now(UTC).isoformat(),
        }


# Compatibility aliases for legacy test imports
search_memory_tool = search_user_memories
add_memory_tool = add_conversation_memory
