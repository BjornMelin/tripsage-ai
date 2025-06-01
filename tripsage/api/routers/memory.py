"""Memory management API router.

This module provides REST API endpoints for managing user memory,
conversation history, and travel preferences using the unified memory service.
"""

import logging
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from tripsage.api.core.dependencies import (
    get_memory_service_dep,
    get_principal_id,
    require_principal_dep,
)
from tripsage.api.middlewares.authentication import Principal
from tripsage.api.services.memory import MemoryService

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
    principal: Principal = require_principal_dep,
    memory_service: MemoryService = get_memory_service_dep,
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
        result = await memory_service.add_conversation_memory(
            user_id, request.messages, request.session_id
        )
        return result

    except Exception as e:
        logger.error(f"Add conversation memory failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add conversation memory"
        ) from e


@router.get("/context")
async def get_user_context(
    principal: Principal = require_principal_dep,
    memory_service: MemoryService = get_memory_service_dep,
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
            detail="Failed to get user context"
        ) from e


@router.post("/search")
async def search_memories(
    request: SearchMemoryRequest,
    principal: Principal = require_principal_dep,
    memory_service: MemoryService = get_memory_service_dep,
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
        memories = await memory_service.search_memories(
            user_id, request.query, request.limit
        )
        return {"memories": memories, "count": len(memories)}

    except Exception as e:
        logger.error(f"Search memories failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search memories"
        ) from e


@router.put("/preferences")
async def update_preferences(
    request: UpdatePreferencesRequest,
    principal: Principal = require_principal_dep,
    memory_service: MemoryService = get_memory_service_dep,
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
        result = await memory_service.update_user_preferences(
            user_id, request.preferences
        )
        return result

    except Exception as e:
        logger.error(f"Update preferences failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update preferences"
        ) from e


@router.post("/preference")
async def add_preference(
    key: str,
    value: str,
    category: str = "general",
    principal: Principal = require_principal_dep,
    memory_service: MemoryService = get_memory_service_dep,
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
            detail="Failed to add preference"
        ) from e


@router.delete("/memory/{memory_id}")
async def delete_memory(
    memory_id: str,
    principal: Principal = require_principal_dep,
    memory_service: MemoryService = get_memory_service_dep,
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
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Memory not found"
            )
            
        return {"message": "Memory deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete memory failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete memory"
        ) from e


@router.get("/stats")
async def get_memory_stats(
    principal: Principal = require_principal_dep,
    memory_service: MemoryService = get_memory_service_dep,
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
            detail="Failed to get memory stats"
        ) from e


@router.delete("/clear")
async def clear_user_memory(
    confirm: bool = False,
    principal: Principal = require_principal_dep,
    memory_service: MemoryService = get_memory_service_dep,
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
            detail="Failed to clear memory"
        ) from e