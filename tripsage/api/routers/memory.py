"""Memory management API router.

This module provides REST API endpoints for managing user memory,
conversation history, and travel preferences using the unified memory service.
"""

import logging
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from tripsage.api.core.dependencies import (
    MemoryServiceDep,
    RequiredPrincipalDep,
    get_principal_id,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/memory", tags=["memory"])


class ConversationMemoryRequest(BaseModel):
    """Request model for adding conversation memory."""

    messages: List[Dict[str, str]] = Field(..., description="Conversation messages")
    session_id: Optional[str] = Field(None, description="Session ID")
    context_type: str = Field("travel_planning", description="Context type")


class SearchMemoryRequest(BaseModel):
    """Request model for searching user memories."""

    query: str = Field(..., description="Search query")
    limit: int = Field(10, description="Maximum results to return")


class UpdatePreferencesRequest(BaseModel):
    """Request model for updating user preferences."""

    preferences: Dict = Field(..., description="User preferences to update")


@router.post("/conversation")
async def add_conversation_memory(
    request: ConversationMemoryRequest,
    principal: RequiredPrincipalDep,
    memory_service: MemoryServiceDep,
):
    """Add conversation messages to user memory.

    Args:
        request: Conversation memory request
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
            metadata=({"context_type": request.context_type} if request.context_type else None),
        )

        result = await memory_service.add_conversation_memory(user_id, core_request)
        return result

    except Exception as e:
        logger.error(f"Add conversation memory failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add conversation memory",
        ) from e


@router.get("/context")
async def get_user_context(
    principal: RequiredPrincipalDep,
    memory_service: MemoryServiceDep,
):
    """Get user context and preferences.

    Args:
        principal: Current authenticated principal
        memory_service: Unified memory service

    Returns:
        User context and preferences
    """
    try:
        user_id = get_principal_id(principal)
        context = await memory_service.get_user_context(user_id)
        return context

    except Exception as e:
        logger.error(f"Get user context failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user context",
        ) from e


@router.post("/search")
async def search_memories(
    request: SearchMemoryRequest,
    principal: RequiredPrincipalDep,
    memory_service: MemoryServiceDep,
):
    """Search user memories.

    Args:
        request: Search request
        principal: Current authenticated principal
        memory_service: Unified memory service

    Returns:
        List of matching memories
    """
    try:
        user_id = get_principal_id(principal)
        # Convert router request to service request
        from tripsage_core.services.business.memory_service import MemorySearchRequest

        search_request = MemorySearchRequest(query=request.query, limit=request.limit)
        memories = await memory_service.search_memories(user_id, search_request)
        return {"results": memories, "query": request.query, "total": len(memories)}

    except Exception as e:
        logger.error(f"Search memories failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search memories",
        ) from e


@router.put("/preferences")
async def update_preferences(
    request: UpdatePreferencesRequest,
    principal: RequiredPrincipalDep,
    memory_service: MemoryServiceDep,
):
    """Update user preferences.

    Args:
        request: Preferences update request
        principal: Current authenticated principal
        memory_service: Unified memory service

    Returns:
        Updated preferences
    """
    try:
        user_id = get_principal_id(principal)
        result = await memory_service.update_user_preferences(user_id, request.preferences)
        return result

    except Exception as e:
        logger.error(f"Update preferences failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update preferences",
        ) from e


@router.post("/preference")
async def add_preference(
    key: str,
    value: str,
    principal: RequiredPrincipalDep,
    memory_service: MemoryServiceDep,
    category: str = "general",
):
    """Add or update a single user preference.

    Args:
        key: Preference key
        value: Preference value
        category: Preference category
        principal: Current authenticated principal
        memory_service: Unified memory service

    Returns:
        Updated preference
    """
    try:
        user_id = get_principal_id(principal)
        result = await memory_service.add_user_preference(user_id, key, value, category)
        return result

    except Exception as e:
        logger.error(f"Add preference failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add preference",
        ) from e


@router.delete("/memory/{memory_id}")
async def delete_memory(
    memory_id: str,
    principal: RequiredPrincipalDep,
    memory_service: MemoryServiceDep,
):
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
        success = await memory_service.delete_memory(user_id, memory_id)

        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory not found")

        return {"message": "Memory deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete memory failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete memory",
        ) from e


@router.get("/stats")
async def get_memory_stats(
    principal: RequiredPrincipalDep,
    memory_service: MemoryServiceDep,
):
    """Get memory statistics for the user.

    Args:
        principal: Current authenticated principal
        memory_service: Unified memory service

    Returns:
        Memory statistics
    """
    try:
        user_id = get_principal_id(principal)
        stats = await memory_service.get_memory_stats(user_id)
        return stats

    except Exception as e:
        logger.error(f"Get memory stats failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get memory stats",
        ) from e


@router.delete("/clear")
async def clear_user_memory(
    principal: RequiredPrincipalDep,
    memory_service: MemoryServiceDep,
    confirm: bool = False,
):
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
        result = await memory_service.clear_user_memory(user_id, confirm)
        return result

    except Exception as e:
        logger.error(f"Clear memory failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear memory",
        ) from e
