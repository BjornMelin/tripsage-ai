"""Memory management API router.

This module provides REST API endpoints for managing user memory,
conversation history, and travel preferences using the unified memory service.
"""

import logging

from fastapi import APIRouter, HTTPException, Request, Response, status
from pydantic import BaseModel, Field

from tripsage.api.core.dependencies import (
    MemoryServiceDep,
    RequiredPrincipalDep,
    get_principal_id,
)


from tripsage.api.limiting import limiter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/memory", tags=["memory"])


class ConversationMemoryRequest(BaseModel):
    """Request model for adding conversation memory."""

    messages: list[dict[str, str]] = Field(..., description="Conversation messages")
    session_id: str | None = Field(None, description="Session ID")
    context_type: str = Field("travel_planning", description="Context type")


class SearchMemoryRequest(BaseModel):
    """Request model for searching user memories."""

    query: str = Field(..., description="Search query")
    limit: int = Field(10, description="Maximum results to return")


class UpdatePreferencesRequest(BaseModel):
    """Request model for updating user preferences."""

    preferences: dict = Field(..., description="User preferences to update")


@router.post("/conversation")
@limiter.limit("30/minute")
async def add_conversation_memory(
    request: ConversationMemoryRequest,
    http_request: Request,
    http_response: Response,
    principal: RequiredPrincipalDep,
    memory_service: MemoryServiceDep,
):
    """Add conversation messages to user memory.

    Args:
        request: Conversation memory request
        http_request: Raw HTTP request (required by SlowAPI for headers)
        http_response: Raw HTTP response (required by SlowAPI for headers)
        principal: Current authenticated principal
        memory_service: Unified memory service

    Returns:
        Operation result
    """
    try:
        user_id = get_principal_id(principal)

        # Import the core ConversationMemoryRequest model
        from tripsage_core.services.business.memory_service import (
            ConversationMemoryRequest as CoreMemoryRequest,
        )

        # Convert API request to core request
        core_request = CoreMemoryRequest(
            messages=request.messages,
            session_id=request.session_id,
            # context_type is not in the core model, add to metadata if needed
            metadata=(
                {"context_type": request.context_type} if request.context_type else None
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


@router.get("/context")
async def get_user_context(
    http_request: Request,
    http_response: Response,
    principal: RequiredPrincipalDep,
    memory_service: MemoryServiceDep,
):
    """Get user context and preferences.

    Args:
        http_request: Raw HTTP request (required by SlowAPI for headers)
        http_response: Raw HTTP response (required by SlowAPI for headers)
        principal: Current authenticated principal
        memory_service: Unified memory service

    Returns:
        User context and preferences
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


@router.post("/search")
@limiter.limit("30/minute")
async def search_memories(
    request: SearchMemoryRequest,
    http_request: Request,
    http_response: Response,
    principal: RequiredPrincipalDep,
    memory_service: MemoryServiceDep,
):
    """Search user memories.

    Args:
        request: Search request
        http_request: Raw HTTP request (required by SlowAPI for headers)
        http_response: Raw HTTP response (required by SlowAPI for headers)
        principal: Current authenticated principal
        memory_service: Unified memory service

    Returns:
        List of matching memories
    """
    try:
        user_id = get_principal_id(principal)
        # Convert router request to service request
        from tripsage_core.services.business.memory_service import MemorySearchRequest

        search_request = MemorySearchRequest(
            query=request.query, limit=request.limit, filters=None
        )
        from typing import Any, cast
        memories = await cast(Any, memory_service).search_memories(
            user_id, search_request
        )
        return {"results": memories, "query": request.query, "total": len(memories)}

    except Exception as e:
        logger.exception("Search memories failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search memories",
        ) from e


@router.put("/preferences")
async def update_preferences(
    request: UpdatePreferencesRequest,
    http_request: Request,
    http_response: Response,
    principal: RequiredPrincipalDep,
    memory_service: MemoryServiceDep,
):
    """Update user preferences.

    Args:
        request: Preferences update request
        http_request: Raw HTTP request (required by SlowAPI for headers)
        http_response: Raw HTTP response (required by SlowAPI for headers)
        principal: Current authenticated principal
        memory_service: Unified memory service

    Returns:
        Updated preferences
    """
    try:
        user_id = get_principal_id(principal)
        from typing import Any, cast
        return await cast(Any, memory_service).update_user_preferences(
            user_id, request.preferences
        )

    except Exception as e:
        logger.exception("Update preferences failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update preferences",
        ) from e


@router.post("/preference")
@limiter.limit("30/minute")
async def add_preference(  # pylint: disable=too-many-positional-arguments
    key: str,
    value: str,
    http_request: Request,
    http_response: Response,
    principal: RequiredPrincipalDep,
    memory_service: MemoryServiceDep,
    category: str = "general",
):
    """Add or update a single user preference.

    Args:
        key: Preference key
        value: Preference value
        category: Preference category
        http_request: Raw HTTP request (required by SlowAPI for headers)
        http_response: Raw HTTP response (required by SlowAPI for headers)
        principal: Current authenticated principal
        memory_service: Unified memory service

    Returns:
        Updated preference
    """
    try:
        user_id = get_principal_id(principal)
        from typing import Any, cast
        return await cast(Any, memory_service).add_user_preference(
            user_id, key, value, category
        )

    except Exception as e:
        logger.exception("Add preference failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add preference",
        ) from e


@router.delete("/memory/{memory_id}")
async def delete_memory(
    memory_id: str,
    http_request: Request,
    http_response: Response,
    principal: RequiredPrincipalDep,
    memory_service: MemoryServiceDep,
):
    """Delete a specific memory.

    Args:
        memory_id: Memory ID to delete
        http_request: Raw HTTP request (required by SlowAPI for headers)
        http_response: Raw HTTP response (required by SlowAPI for headers)
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


@router.get("/stats")
async def get_memory_stats(
    http_request: Request,
    http_response: Response,
    principal: RequiredPrincipalDep,
    memory_service: MemoryServiceDep,
):
    """Get memory statistics for the user.

    Args:
        http_request: Raw HTTP request (required by SlowAPI for headers)
        http_response: Raw HTTP response (required by SlowAPI for headers)
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


@router.delete("/clear")
async def clear_user_memory(
    http_request: Request,
    http_response: Response,
    principal: RequiredPrincipalDep,
    memory_service: MemoryServiceDep,
    confirm: bool = False,
):
    """Clear all memories for the user.

    Args:
        confirm: Confirmation flag
        http_request: Raw HTTP request (required by SlowAPI for headers)
        http_response: Raw HTTP response (required by SlowAPI for headers)
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
