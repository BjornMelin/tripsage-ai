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
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from tripsage.config.feature_flags import feature_flags, IntegrationMode
from tripsage.services.memory_service import TripSageMemoryService
from tripsage.utils.decorators import with_error_handling
from tripsage.utils.logging import get_logger

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


class ConversationMessage(BaseModel):
    """Message model for conversation memory."""
    
    role: str = Field(..., description="Message role (user, assistant, system)")
    content: str = Field(..., description="Message content")


class UserPreferences(BaseModel):
    """User travel preferences model."""
    
    budget_range: Optional[str] = Field(None, description="Preferred budget range")
    accommodation_type: Optional[str] = Field(None, description="Preferred accommodation type")
    travel_style: Optional[str] = Field(None, description="Travel style (luxury, budget, adventure, etc.)")
    destinations: Optional[List[str]] = Field(None, description="Preferred destinations")
    activities: Optional[List[str]] = Field(None, description="Preferred activities")
    dietary_restrictions: Optional[List[str]] = Field(None, description="Dietary restrictions")
    accessibility_needs: Optional[List[str]] = Field(None, description="Accessibility requirements")


class TravelMemoryQuery(BaseModel):
    """Query model for travel memory search."""
    
    query: str = Field(..., description="Search query")
    user_id: str = Field(..., description="User ID")
    limit: int = Field(default=5, description="Maximum number of results")
    category: Optional[str] = Field(None, description="Memory category filter")
    
    
class SessionSummary(BaseModel):
    """Session summary for memory storage."""
    
    user_id: str = Field(..., description="User ID")
    session_id: str = Field(..., description="Session ID")
    summary: str = Field(..., description="Session summary")
    key_insights: Optional[List[str]] = Field(None, description="Key insights from session")
    decisions_made: Optional[List[str]] = Field(None, description="Decisions made during session")


@with_error_handling
async def add_conversation_memory(
    messages: List[ConversationMessage],
    user_id: str,
    session_id: Optional[str] = None,
    context_type: str = "travel_planning"
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
    try:
        logger.info(f"Adding conversation memory for user {user_id}")
        
        memory_service = get_memory_service()
        
        # Convert to the format expected by Mem0
        message_dicts = [
            {"role": msg.role, "content": msg.content} 
            for msg in messages
        ]
        
        # Add travel-specific metadata
        metadata = {
            "domain": "travel_planning",
            "context_type": context_type,
            "session_id": session_id,
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id
        }
        
        result = await memory_service.add_conversation_memory(
            messages=message_dicts,
            user_id=user_id,
            session_id=session_id,
            metadata=metadata
        )
        
        logger.info(
            f"Successfully extracted {len(result.get('results', []))} memories for user {user_id}"
        )
        
        return {
            "status": "success",
            "memories_extracted": len(result.get("results", [])),
            "tokens_used": result.get("usage", {}).get("total_tokens", 0),
            "extraction_time": result.get("processing_time", 0),
            "memories": result.get("results", [])
        }
        
    except Exception as e:
        logger.error(f"Error adding conversation memory: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "memories_extracted": 0
        }


@with_error_handling
async def search_user_memories(
    query: str,
    user_id: str,
    limit: int = 5,
    category: Optional[str] = None
) -> Dict[str, Any]:
    """Search user memories with semantic similarity.
    
    Args:
        query: Search query
        user_id: User identifier
        limit: Maximum number of results
        category: Optional category filter
        
    Returns:
        Dictionary with search results
    """
    try:
        logger.info(f"Searching memories for user {user_id} with query: {query}")
        
        memory_service = get_memory_service()
        
        # Build filters
        filters = {}
        if category:
            filters["category"] = category
            
        results = await memory_service.search_memories(
            query=query,
            user_id=user_id,
            limit=limit,
            filters=filters
        )
        
        return {
            "status": "success",
            "query": query,
            "results_count": len(results),
            "memories": results
        }
        
    except Exception as e:
        logger.error(f"Error searching user memories: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "memories": []
        }


@with_error_handling
async def get_user_context(
    user_id: str,
    context_type: Optional[str] = None
) -> Dict[str, Any]:
    """Get comprehensive user context for personalization.
    
    Args:
        user_id: User identifier
        context_type: Optional context type filter
        
    Returns:
        Dictionary with user context including preferences, history, and insights
    """
    try:
        logger.info(f"Getting user context for user {user_id}")
        
        memory_service = get_memory_service()
        
        context = await memory_service.get_user_context(
            user_id=user_id,
            context_type=context_type
        )
        
        return {
            "status": "success",
            "user_id": user_id,
            "context": context
        }
        
    except Exception as e:
        logger.error(f"Error getting user context: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "context": {}
        }


@with_error_handling
async def update_user_preferences(
    user_id: str,
    preferences: UserPreferences
) -> Dict[str, Any]:
    """Update user travel preferences.
    
    Args:
        user_id: User identifier
        preferences: User preferences object
        
    Returns:
        Dictionary with update status
    """
    try:
        logger.info(f"Updating preferences for user {user_id}")
        
        memory_service = get_memory_service()
        
        # Convert preferences to dictionary
        preferences_dict = preferences.model_dump(exclude_none=True)
        
        await memory_service.update_user_preferences(
            user_id=user_id,
            preferences=preferences_dict
        )
        
        return {
            "status": "success",
            "message": "User preferences updated successfully",
            "preferences_updated": len(preferences_dict)
        }
        
    except Exception as e:
        logger.error(f"Error updating user preferences: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }


@with_error_handling
async def save_session_summary(
    session_summary: SessionSummary
) -> Dict[str, Any]:
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
                "content": "Extract key insights and decisions from this session summary."
            },
            {
                "role": "user",
                "content": f"Session Summary: {session_summary.summary}"
            }
        ]
        
        if session_summary.key_insights:
            summary_messages.append({
                "role": "user", 
                "content": f"Key Insights: {', '.join(session_summary.key_insights)}"
            })
            
        if session_summary.decisions_made:
            summary_messages.append({
                "role": "user",
                "content": f"Decisions Made: {', '.join(session_summary.decisions_made)}"
            })
        
        result = await memory_service.add_conversation_memory(
            messages=summary_messages,
            user_id=session_summary.user_id,
            session_id=session_summary.session_id,
            metadata={
                "type": "session_summary",
                "category": "travel_planning",
                "session_end": datetime.utcnow().isoformat()
            }
        )
        
        return {
            "status": "success",
            "message": "Session summary saved successfully",
            "memories_created": len(result.get("results", []))
        }
        
    except Exception as e:
        logger.error(f"Error saving session summary: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }


@with_error_handling
async def get_travel_insights(
    user_id: str,
    insight_type: Optional[str] = None
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
                "insights": {insight_type: insights[insight_type]}
            }
        
        return {
            "status": "success",
            "insights": insights
        }
        
    except Exception as e:
        logger.error(f"Error getting travel insights: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "insights": {}
        }


@with_error_handling
async def find_similar_travelers(
    user_id: str,
    similarity_threshold: float = 0.8
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
        preference_query = ""
        if user_context.get("preferences"):
            prefs = []
            for category, value in user_context["preferences"].items():
                prefs.append(f"{category}: {value}")
            preference_query = ", ".join(prefs)
        
        # Note: This is a simplified implementation
        # In a full implementation, we'd have more sophisticated similarity matching
        similar_memories = await search_user_memories(
            query=preference_query,
            user_id="*",  # Search across all users (if supported)
            limit=10
        )
        
        return {
            "status": "success",
            "similar_travelers_count": 0,  # Placeholder - needs cross-user search
            "message": "Similar traveler search requires cross-user memory access"
        }
        
    except Exception as e:
        logger.error(f"Error finding similar travelers: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "similar_travelers": []
        }


@with_error_handling
async def get_destination_memories(
    destination: str,
    user_id: Optional[str] = None
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
            memories = await search_user_memories(
                query=destination,
                user_id=user_id,
                limit=10,
                category="destinations"
            )
        else:
            # This would require system-wide search capability
            # For now, return empty results
            memories = {"memories": []}
        
        return {
            "status": "success",
            "destination": destination,
            "memories": memories.get("memories", [])
        }
        
    except Exception as e:
        logger.error(f"Error getting destination memories: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "memories": []
        }


@with_error_handling
async def track_user_activity(
    user_id: str,
    activity_type: str,
    activity_data: Dict[str, Any]
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
            {
                "role": "system",
                "content": "Track user activity for behavior analysis."
            },
            {
                "role": "user",
                "content": f"User performed {activity_type} activity: {json.dumps(activity_data)}"
            }
        ]
        
        result = await add_conversation_memory(
            messages=[ConversationMessage(**msg) for msg in activity_messages],
            user_id=user_id,
            context_type="user_activity"
        )
        
        return {
            "status": "success",
            "activity_tracked": activity_type,
            "memories_created": result.get("memories_extracted", 0)
        }
        
    except Exception as e:
        logger.error(f"Error tracking user activity: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }


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
            "popular_destinations": []
        }
    
    # Get user context using new memory system
    context_result = await get_user_context(user_id)
    
    if context_result["status"] == "success":
        context = context_result["context"]
        
        return {
            "user": {"id": user_id, "name": f"User {user_id}"},
            "preferences": context.get("preferences", {}),
            "recent_trips": context.get("past_trips", [])[:5],
            "popular_destinations": []  # Would need system-wide data
        }
    
    return {
        "user": None,
        "preferences": {},
        "recent_trips": [],
        "popular_destinations": []
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
    
    result = {
        "entities_created": 0,
        "relations_created": 0,
        "observations_added": 0
    }
    
    try:
        # Handle preferences
        if "preferences" in updates:
            prefs = UserPreferences(**updates["preferences"])
            await update_user_preferences(user_id, prefs)
            result["observations_added"] += len(updates["preferences"])
        
        # Handle learned facts as conversation memory
        if "learned_facts" in updates:
            facts_messages = [
                {
                    "role": "system",
                    "content": "Extract learned facts about travel."
                },
                {
                    "role": "user",
                    "content": f"Learned facts: {json.dumps(updates['learned_facts'])}"
                }
            ]
            
            await add_conversation_memory(
                messages=[ConversationMessage(**msg) for msg in facts_messages],
                user_id=user_id,
                context_type="learned_facts"
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
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Memory health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "service": "Mem0 Memory Service",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }