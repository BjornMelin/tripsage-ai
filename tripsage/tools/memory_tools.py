"""Final LangGraph-aligned memory utilities for TripSage.

This module provides the definitive, library-first implementation for
conversation memory and user context using `tripsage_core`'s MemoryService.
All legacy adapters/tool-context shims have been removed.

Features:
- Strict models via `tripsage.tools.models`.
- Direct use of `MemoryService` request models.
- OpenTelemetry tracing and histograms (see `tripsage_core.observability.otel`).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from tripsage.tools.models import (
    ConversationMessage,
    MemorySearchQuery,
    SessionSummary,
    UserPreferences,
)
from tripsage_core.observability.otel import record_histogram, trace_span
from tripsage_core.utils.logging_utils import get_logger


if TYPE_CHECKING:  # pragma: no cover - type checking only
    from tripsage_core.services.business.memory_service import (
        MemoryService as _MemoryService,
    )


logger = get_logger(__name__)


_memory_service_singleton: _MemoryService | None = None


async def get_memory_service() -> _MemoryService:
    """Return a connected MemoryService instance (singleton).

    Returns:
        A connected MemoryService.

    Raises:
        RuntimeError: If the service fails to connect.
    """
    global _memory_service_singleton  # pylint: disable=global-statement
    if _memory_service_singleton is None:
        # Deferred import to avoid triggering heavy model imports during module load
        from tripsage_core.services.business.memory_service import MemoryService

        svc = MemoryService()
        await svc.connect()
        _memory_service_singleton = svc
    return _memory_service_singleton


@trace_span("memory.add_conversation")
@record_histogram("tripsage.memory.add.seconds")
async def add_conversation_memory(
    *,
    messages: list[ConversationMessage],
    user_id: str,
    session_id: str | None = None,
    context_type: str = "travel_planning",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Extract and persist memories from a conversation.

    Args:
        messages: Ordered conversation messages.
        user_id: Subject user identifier.
        session_id: Optional session identifier.
        context_type: Domain context tag for metadata.
        metadata: Additional metadata to persist with the memory.

    Returns:
        A JSON-serializable result with extraction stats and items.

    Raises:
        ValueError: If inputs are invalid.
    """
    if not messages:
        raise ValueError("messages cannot be empty")
    if not user_id.strip():
        raise ValueError("user_id cannot be empty")

    message_dicts = [{"role": m.role, "content": m.content} for m in messages]
    meta: dict[str, Any] = {
        "domain": "travel_planning",
        "context_type": context_type,
        "session_id": session_id,
        "timestamp": datetime.now(UTC).isoformat(),
        "user_id": user_id,
    }
    if metadata:
        meta.update(metadata)

    from tripsage_core.services.business.memory_service import (
        ConversationMemoryRequest,
    )

    req = ConversationMemoryRequest(
        messages=message_dicts, session_id=session_id, trip_id=None, metadata=meta
    )
    svc = await get_memory_service()
    result = await svc.add_conversation_memory(user_id, req)

    return {
        "status": "success",
        "memories_extracted": len(result.get("results", [])),
        "tokens_used": result.get("usage", {}).get("total_tokens", 0),
        "extraction_time": result.get("processing_time", 0),
        "memories": result.get("results", []),
    }


@trace_span("memory.search")
@record_histogram("tripsage.memory.search.seconds")
async def search_user_memories(search_query: MemorySearchQuery) -> list[dict[str, Any]]:
    """Search user memories with semantic similarity.

    Args:
        search_query: Query parameters including user_id, query, limit, filters.

    Returns:
        List of memory records as dictionaries (JSON-safe).
    """
    svc = await get_memory_service()
    from tripsage_core.services.business.memory_service import MemorySearchRequest

    req = MemorySearchRequest(
        query=search_query.query,
        limit=search_query.limit,
        filters=(
            {"category": search_query.category_filter}
            if search_query.category_filter
            else None
        ),
    )
    results = await svc.search_memories(search_query.user_id, req)
    return [r.model_dump() for r in results]


@trace_span("memory.user_context")
@record_histogram("tripsage.memory.user_context.seconds")
async def get_user_context(user_id: str) -> dict[str, Any]:
    """Return user context for personalization.

    Args:
        user_id: Subject user identifier.

    Returns:
        JSON-serializable context dict with preferences, history, insights.
    """
    if not user_id.strip():
        raise ValueError("user_id cannot be empty")

    svc = await get_memory_service()
    from tripsage_core.services.business.memory_service import UserContextResponse

    ctx: UserContextResponse = await svc.get_user_context(user_id)
    return {"status": "success", "context": ctx.model_dump(exclude_none=True)}


@trace_span("memory.update_preferences")
@record_histogram("tripsage.memory.update_preferences.seconds")
async def update_user_preferences(preferences: UserPreferences) -> dict[str, Any]:
    """Update user travel preferences in persistent memory.

    Args:
        preferences: User travel preferences model.

    Returns:
        Operation status with count of updated items.
    """
    svc = await get_memory_service()
    pref_dict = preferences.model_dump(
        exclude_none=True, exclude={"user_id"}, by_alias=True
    )
    from tripsage_core.services.business.memory_service import (
        PreferencesUpdateRequest,
    )

    req = PreferencesUpdateRequest(preferences=pref_dict, category=None)
    await svc.update_user_preferences(preferences.user_id, req)
    return {"status": "success", "preferences_updated": len(pref_dict)}


@trace_span("memory.save_session_summary")
@record_histogram("tripsage.memory.save_session_summary.seconds")
async def save_session_summary(session_summary: SessionSummary) -> dict[str, Any]:
    """Persist a conversational session summary as memory.

    Args:
        session_summary: Summary payload.

    Returns:
        Operation status including memories created.
    """
    sys_msg = {
        "role": "system",
        "content": "Extract key insights and decisions from this session summary.",
    }
    msgs = [
        sys_msg,
        {"role": "user", "content": f"Session Summary: {session_summary.summary}"},
    ]
    if session_summary.key_insights:
        msgs.append(
            {
                "role": "user",
                "content": f"Key Insights: {', '.join(session_summary.key_insights)}",
            }
        )
    if session_summary.decisions_made:
        joined = ", ".join(session_summary.decisions_made)
        msgs.append({"role": "user", "content": f"Decisions Made: {joined}"})

    svc = await get_memory_service()
    from tripsage_core.services.business.memory_service import (
        ConversationMemoryRequest,
    )

    req = ConversationMemoryRequest(
        messages=msgs,
        session_id=session_summary.session_id,
        trip_id=None,
        metadata={
            "type": "session_summary",
            "category": "travel_planning",
            "session_end": datetime.now(UTC).isoformat(),
        },
    )
    result = await svc.add_conversation_memory(session_summary.user_id, req)
    return {"status": "success", "memories_created": len(result.get("results", []))}


@trace_span("memory.get_destination")
@record_histogram("tripsage.memory.get_destination.seconds")
async def get_destination_memories(
    destination: str, user_id: str | None = None
) -> dict[str, Any]:
    """Return memories relevant to a destination, optionally scoped to a user.

    Args:
        destination: Destination name.
        user_id: Optional user identifier for personalized results.

    Returns:
        Dictionary with destination and list of memories.
    """
    memories: list[dict[str, Any]] = []
    if user_id:
        memories = await search_user_memories(
            MemorySearchQuery(
                query=destination,
                user_id=user_id,
                limit=10,
                category_filter="destinations",
            )
        )
    return {"status": "success", "destination": destination, "memories": memories}


@trace_span("memory.track_activity")
@record_histogram("tripsage.memory.track_activity.seconds")
async def track_user_activity(
    *, user_id: str, activity_type: str, activity_data: dict[str, Any]
) -> dict[str, Any]:
    """Track a user activity as a memory event.

    Args:
        user_id: User identifier.
        activity_type: Activity type, e.g. "search" or "booking".
        activity_data: Arbitrary JSON-safe payload.

    Returns:
        Operation status with created memory count.
    """
    messages = [
        ConversationMessage(
            role="system", content="Track user activity for behavior analysis."
        ),
        ConversationMessage(
            role="user",
            content=(
                f"User performed {activity_type} activity: {json.dumps(activity_data)}"
            ),
        ),
    ]
    result = await add_conversation_memory(
        messages=messages, user_id=user_id, context_type="user_activity"
    )
    return {
        "status": "success",
        "activity_tracked": activity_type,
        "memories_created": result.get("memories_extracted", 0),
    }


@trace_span("memory.health_check")
@record_histogram("tripsage.memory.health_check.seconds")
async def memory_health_check() -> dict[str, Any]:
    """Perform a lightweight health check against the memory backend.

    Returns:
        Health status payload.
    """
    try:
        svc = await get_memory_service()
        ok = await svc.health_check()
        if ok:
            return {
                "status": "healthy",
                "service": "Mem0 Memory Service",
                "timestamp": datetime.now(UTC).isoformat(),
            }
        return {
            "status": "unhealthy",
            "service": "Mem0 Memory Service",
            "timestamp": datetime.now(UTC).isoformat(),
        }
    except Exception as exc:
        logger.exception("Memory health check failed")
        return {
            "status": "unhealthy",
            "service": "Mem0 Memory Service",
            "error": str(exc),
            "timestamp": datetime.now(UTC).isoformat(),
        }


__all__ = [
    "ConversationMessage",
    "MemorySearchQuery",
    "SessionSummary",
    "UserPreferences",
    "add_conversation_memory",
    "get_destination_memories",
    "get_memory_service",
    "get_user_context",
    "memory_health_check",
    "save_session_summary",
    "search_user_memories",
    "track_user_activity",
    "update_user_preferences",
]
