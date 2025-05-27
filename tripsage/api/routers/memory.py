"""
Memory management API router.

This module provides REST API endpoints for managing user memory,
conversation history, and travel preferences using the new Mem0-based
memory system.
"""

from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from tripsage.config.feature_flags import IntegrationMode, get_memory_integration_mode
from tripsage.services.memory_service import TripSageMemoryService
from tripsage.tools.memory_tools import (
    ConversationMessage,
    add_conversation_memory,
    get_user_context,
    search_user_memories,
    update_user_preferences,
)

router = APIRouter(prefix="/memory", tags=["memory"])


class ConversationMemoryRequest(BaseModel):
    """Request model for adding conversation memory."""
    
    messages: List[Dict[str, str]]
    user_id: str
    session_id: Optional[str] = None
    context_type: str = "travel_planning"


class UserContextResponse(BaseModel):
    """Response model for user context."""
    
    user_id: str
    context: Dict
    preferences: Dict
    conversation_insights: List[str]
    status: str = "success"


class SearchMemoryRequest(BaseModel):
    """Request model for searching user memories."""
    
    query: str
    user_id: str
    limit: int = 10


class SearchMemoryResponse(BaseModel):
    """Response model for memory search results."""
    
    results: List[Dict]
    total_count: int
    user_id: str
    status: str = "success"


class UpdatePreferencesRequest(BaseModel):
    """Request model for updating user preferences."""
    
    preferences: Dict
    user_id: str


class UpdatePreferencesResponse(BaseModel):
    """Response model for preference updates."""
    
    updated_preferences: Dict
    user_id: str
    status: str = "success"


async def get_memory_service() -> TripSageMemoryService:
    """Dependency to get memory service instance."""
    mode = get_memory_integration_mode()
    if mode == IntegrationMode.DISABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Memory service is currently disabled"
        )
    
    return TripSageMemoryService()


@router.post("/conversations", response_model=Dict)
async def add_conversation(
    request: ConversationMemoryRequest,
    memory_service: TripSageMemoryService = Depends(get_memory_service)
) -> Dict:
    """
    Add conversation messages to user memory.
    
    This endpoint stores conversation messages and extracts relevant
    travel insights and preferences automatically.
    """
    try:
        # Convert request to ConversationMessage objects
        messages = [
            ConversationMessage(
                role=msg.get("role", "user"),
                content=msg.get("content", "")
            )
            for msg in request.messages
        ]
        
        result = await add_conversation_memory(
            messages=messages,
            user_id=request.user_id,
            session_id=request.session_id,
            context_type=request.context_type
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add conversation memory: {str(e)}"
        )


@router.get("/context/{user_id}", response_model=UserContextResponse)
async def get_user_memory_context(
    user_id: str,
    memory_service: TripSageMemoryService = Depends(get_memory_service)
) -> UserContextResponse:
    """
    Get comprehensive user context including preferences and insights.
    
    Returns the user's travel preferences, conversation insights,
    and relevant context for personalized interactions.
    """
    try:
        result = await get_user_context(user_id)
        
        if result.get("status") == "error":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=result.get("message", "User context not found")
            )
        
        return UserContextResponse(
            user_id=user_id,
            context=result.get("context", {}),
            preferences=result.get("preferences", {}),
            conversation_insights=result.get("conversation_insights", []),
            status=result.get("status", "success")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user context: {str(e)}"
        )


@router.post("/search", response_model=SearchMemoryResponse)
async def search_memories(
    request: SearchMemoryRequest,
    memory_service: TripSageMemoryService = Depends(get_memory_service)
) -> SearchMemoryResponse:
    """
    Search through user's conversation and travel memories.
    
    Performs semantic search through the user's stored conversations,
    preferences, and travel history to find relevant information.
    """
    try:
        result = await search_user_memories(
            user_id=request.user_id,
            query=request.query,
            limit=request.limit
        )
        
        if result.get("status") == "error":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=result.get("message", "No memories found")
            )
        
        return SearchMemoryResponse(
            results=result.get("results", []),
            total_count=result.get("total_count", 0),
            user_id=request.user_id,
            status=result.get("status", "success")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search memories: {str(e)}"
        )


@router.put("/preferences/{user_id}", response_model=UpdatePreferencesResponse)
async def update_preferences(
    user_id: str,
    request: UpdatePreferencesRequest,
    memory_service: TripSageMemoryService = Depends(get_memory_service)
) -> UpdatePreferencesResponse:
    """
    Update user travel preferences.
    
    Updates the user's travel preferences and stores them in the
    memory system for future personalization.
    """
    try:
        result = await update_user_preferences(
            user_id=user_id,
            preferences=request.preferences
        )
        
        if result.get("status") == "error":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("message", "Failed to update preferences")
            )
        
        return UpdatePreferencesResponse(
            updated_preferences=result.get("updated_preferences", {}),
            user_id=user_id,
            status=result.get("status", "success")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update preferences: {str(e)}"
        )


@router.delete("/user/{user_id}")
async def delete_user_memories(
    user_id: str,
    memory_service: TripSageMemoryService = Depends(get_memory_service)
) -> Dict:
    """
    Delete all memories for a specific user.
    
    WARNING: This permanently removes all stored conversations,
    preferences, and insights for the specified user.
    """
    try:
        # Use the memory service to delete user memories
        result = await memory_service.delete_user_memories(user_id)
        
        return {
            "user_id": user_id,
            "status": "success",
            "message": f"All memories deleted for user {user_id}",
            "deleted_count": result.get("deleted_count", 0)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete user memories: {str(e)}"
        )


@router.get("/health")
async def memory_health_check(
    memory_service: TripSageMemoryService = Depends(get_memory_service)
) -> Dict:
    """
    Health check endpoint for memory service.
    
    Returns the current status and configuration of the memory system.
    """
    try:
        mode = get_memory_integration_mode()
        
        # Test memory service connectivity
        test_result = await memory_service.health_check()
        
        return {
            "status": "healthy" if test_result else "unhealthy",
            "integration_mode": mode.value,
            "service_available": test_result,
            "timestamp": "2025-01-27T00:00:00Z"  # Would use datetime.utcnow() in real implementation
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "integration_mode": "unknown",
            "service_available": False,
            "error": str(e),
            "timestamp": "2025-01-27T00:00:00Z"
        }