"""Memory management API router.

This module provides REST API endpoints for managing user memory,
conversation history, and travel preferences using the unified memory service.
"""

import logging

from fastapi import APIRouter, HTTPException, Request, Response, status

from tripsage.api.core.dependencies import (
    MemoryServiceDep,
    RequiredPrincipalDep,
    get_principal_id,
)
from tripsage.api.limiting import limiter
from tripsage.api.schemas.memory import (
    ConversationMemoryRequest,
    MemorySearchResponse,
    SearchMemoryRequest,
    UpdatePreferencesRequest,
)
from tripsage_core.services.business.memory_service import (
    UserContextResponse,
)


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/memory", tags=["memory"])


@router.post("/conversation", response_model=dict)
@limiter.limit("30/minute")
async def add_conversation_memory(
    payload: ConversationMemoryRequest,
    principal: RequiredPrincipalDep,
    memory_service: MemoryServiceDep,
    response: Response,
    *,
    request: Request,
) -> dict:
    """Add conversation messages to user memory.

    Args:
        payload: Conversation memory request
        principal: Current authenticated principal
        memory_service: Unified memory service
        response: Response object for SlowAPI header injection
        request: Raw HTTP request (required by SlowAPI limiter)

    Returns:
        Operation result
    """
    try:
        user_id = get_principal_id(principal)
        _ = response  # SlowAPI mutates response headers post-call.
        logger.debug(
            "Adding conversation memory for user %s via %s",
            user_id,
            request.url.path,
        )

        # Import the core ConversationMemoryRequest model
        from tripsage_core.services.business.memory_service import (
            ConversationMemoryRequest as CoreMemoryRequest,
        )

        # Convert API request to core request
        core_request = CoreMemoryRequest(
            messages=payload.messages,
            session_id=payload.session_id,
            # context_type is not in the core model, add to metadata if needed
            metadata=(
                {"context_type": payload.context_type} if payload.context_type else None
            ),
            trip_id=None,
        )
        from typing import Any, cast

        return await cast(Any, memory_service).add_conversation_memory(
            user_id, core_request
        )

    except Exception as e:
        logger.exception("Add conversation memory failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add conversation memory",
        ) from e


@router.get("/context", response_model=UserContextResponse)
async def get_user_context(
    principal: RequiredPrincipalDep,
    memory_service: MemoryServiceDep,
) -> UserContextResponse:
    """Get user context and preferences.

    Args:
        principal: Current authenticated principal
        memory_service: Unified memory service

    Returns:
        UserContextResponse model with preferences and context
    """
    try:
        user_id = get_principal_id(principal)
        return await memory_service.get_user_context(user_id)

    except Exception as e:
        logger.exception("Get user context failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user context",
        ) from e


@router.post("/search", response_model=MemorySearchResponse)
@limiter.limit("30/minute")
async def search_memories(
    payload: SearchMemoryRequest,
    principal: RequiredPrincipalDep,
    memory_service: MemoryServiceDep,
    response: Response,
    *,
    request: Request,
) -> MemorySearchResponse:
    """Search user memories.

    Args:
        payload: Search request
        principal: Current authenticated principal
        memory_service: Unified memory service
        response: Response object for SlowAPI header injection
        request: Raw HTTP request (required by SlowAPI limiter)

    Returns:
        List of matching memories
    """
    try:
        user_id = get_principal_id(principal)
        _ = response  # SlowAPI mutates response headers post-call.
        logger.debug("Searching memories for user %s via %s", user_id, request.url.path)
        # Convert router request to service request
        from tripsage_core.services.business.memory_service import MemorySearchRequest

        search_request = MemorySearchRequest(
            query=payload.query, limit=payload.limit, filters=None
        )
        from typing import Any, cast

        memories = await cast(Any, memory_service).search_memories(
            user_id, search_request
        )
        return MemorySearchResponse(
            results=memories, query=payload.query, total=len(memories)
        )

    except Exception as e:
        logger.exception("Search memories failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search memories",
        ) from e


@router.put("/preferences", response_model=dict)
async def update_preferences(
    payload: UpdatePreferencesRequest,
    principal: RequiredPrincipalDep,
    memory_service: MemoryServiceDep,
) -> dict:
    """Update user preferences.

    Args:
        payload: Preferences update request
        principal: Current authenticated principal
        memory_service: Unified memory service

    Returns:
        Updated preferences
    """
    try:
        user_id = get_principal_id(principal)
        from typing import Any, cast

        return await cast(Any, memory_service).update_user_preferences(
            user_id, payload.preferences
        )

    except Exception as e:
        logger.exception("Update preferences failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update preferences",
        ) from e


@router.post("/preference", response_model=dict)
@limiter.limit("30/minute")
async def add_preference(  # pylint: disable=too-many-positional-arguments
    key: str,
    value: str,
    principal: RequiredPrincipalDep,
    memory_service: MemoryServiceDep,
    response: Response,
    category: str = "general",
    *,
    request: Request,
) -> dict:
    """Add or update a single user preference.

    Args:
        key: Preference key
        value: Preference value
        principal: Current authenticated principal
        memory_service: Unified memory service
        response: Response object for SlowAPI header injection
        category: Preference category
        request: Raw HTTP request (required by SlowAPI limiter)

    Returns:
        Updated preference
    """
    try:
        user_id = get_principal_id(principal)
        _ = response  # SlowAPI mutates response headers post-call.
        from typing import Any, cast

        logger.debug("Adding preference for user %s via %s", user_id, request.url.path)

        return await cast(Any, memory_service).add_user_preference(
            user_id, key, value, category
        )

    except Exception as e:
        logger.exception("Add preference failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add preference",
        ) from e


@router.delete("/memory/{memory_id}", response_model=dict)
async def delete_memory(
    memory_id: str,
    principal: RequiredPrincipalDep,
    memory_service: MemoryServiceDep,
) -> dict:
    """Delete a specific memory.

    Args:
        memory_id: Memory ID to delete
        principal: Current authenticated principal
        memory_service: Unified memory service

    Returns:
        Success message
    """
    try:
        user_id = get_principal_id(principal)
        from typing import Any, cast

        success = await cast(Any, memory_service).delete_memory(user_id, memory_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Memory not found"
            )

        return {"message": "Memory deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Delete memory failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete memory",
        ) from e


@router.get("/stats", response_model=dict)
async def get_memory_stats(
    principal: RequiredPrincipalDep,
    memory_service: MemoryServiceDep,
) -> dict:
    """Get memory statistics for the user.

    Args:
        principal: Current authenticated principal
        memory_service: Unified memory service

    Returns:
        Memory statistics
    """
    try:
        user_id = get_principal_id(principal)
        from typing import Any, cast

        return await cast(Any, memory_service).get_memory_stats(user_id)

    except Exception as e:
        logger.exception("Get memory stats failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get memory stats",
        ) from e


@router.delete("/clear", response_model=dict)
async def clear_user_memory(
    principal: RequiredPrincipalDep,
    memory_service: MemoryServiceDep,
    confirm: bool = False,
) -> dict:
    """Clear all memories for the user.

    Args:
        confirm: Confirmation flag
        principal: Current authenticated principal
        memory_service: Unified memory service

    Returns:
        Operation result
    """
    try:
        user_id = get_principal_id(principal)
        from typing import Any, cast

        return await cast(Any, memory_service).clear_user_memory(user_id, confirm)

    except Exception as e:
        logger.exception("Clear memory failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear memory",
        ) from e
