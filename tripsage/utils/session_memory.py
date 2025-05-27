"""
Session memory utilities for TripSage using Mem0.

This module provides utilities for initializing and updating session memory
using the new Mem0-based memory system. Complete replacement of the old
Neo4j-based implementation.

Key Features:
- User context initialization from memory
- Preference tracking and updates
- Session summary storage
- Learned facts processing
- Integration with TripSageMemoryService
"""

from typing import Any, Dict, List, Optional

from tripsage.tools.memory_tools import (
    ConversationMessage,
    SessionSummary,
    UserPreferences,
    add_conversation_memory,
    get_user_context,
    save_session_summary,
    update_user_preferences,
)
from tripsage.utils.logging import get_logger

logger = get_logger(__name__)


async def initialize_session_memory(user_id: Optional[str] = None) -> Dict[str, Any]:
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
            # Get comprehensive user context from memory
            context_result = await get_user_context(user_id)

            if context_result.get("status") == "success":
                context = context_result.get("context", {})

                # Map memory context to session data format
                session_data.update(
                    {
                        "user": {"id": user_id, "name": f"User {user_id}"},
                        "preferences": context.get("preferences", {}),
                        "recent_trips": context.get("past_trips", [])[
                            :5
                        ],  # Limit to 5 most recent
                        "insights": context.get("insights", {}),
                    }
                )

                logger.info(
                    f"Loaded {len(context.get('preferences', {}))} preferences and "
                    f"{len(context.get('past_trips', []))} trips for user {user_id}"
                )
            else:
                logger.warning(
                    f"Could not load user context: "
                    f"{context_result.get('error', 'Unknown error')}"
                )

        except Exception as e:
            logger.error(f"Error loading user context for {user_id}: {str(e)}")
            # Continue with default session data

    return session_data


async def update_session_memory(
    user_id: str, updates: Dict[str, Any]
) -> Dict[str, Any]:
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
        # Process user preferences
        if "preferences" in updates and updates["preferences"]:
            await _update_user_preferences_memory(
                user_id, updates["preferences"], result
            )

        # Process learned facts
        if "learned_facts" in updates and updates["learned_facts"]:
            await _process_learned_facts(user_id, updates["learned_facts"], result)

        # Process general conversation context
        if "conversation_context" in updates and updates["conversation_context"]:
            await _process_conversation_context(
                user_id, updates["conversation_context"], result
            )

    except Exception as e:
        logger.error(f"Error updating session memory: {str(e)}")
        result["success"] = False
        result["errors"].append(str(e))

    return result


async def store_session_summary(
    user_id: str,
    summary: str,
    session_id: str,
    key_insights: Optional[List[str]] = None,
    decisions_made: Optional[List[str]] = None,
) -> Dict[str, Any]:
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
        # Create session summary object
        session_summary = SessionSummary(
            user_id=user_id,
            session_id=session_id,
            summary=summary,
            key_insights=key_insights,
            decisions_made=decisions_made,
        )

        # Save using the memory tools
        result = await save_session_summary(session_summary)

        if result.get("status") == "success":
            logger.info(
                f"Successfully stored session summary with "
                f"{result.get('memories_created', 0)} memories created"
            )
        else:
            logger.warning(
                f"Session summary storage had issues: "
                f"{result.get('error', 'Unknown error')}"
            )

        return result

    except Exception as e:
        logger.error(f"Error storing session summary: {str(e)}")
        return {"status": "error", "error": str(e), "memories_created": 0}


# Private helper functions


async def _update_user_preferences_memory(
    user_id: str, preferences: Dict[str, Any], result: Dict[str, Any]
) -> None:
    """Update user preferences in memory.

    Args:
        user_id: User ID
        preferences: Dictionary of preferences
        result: Result dictionary to update
    """
    try:
        # Convert to UserPreferences model
        user_prefs = UserPreferences(**preferences)

        # Update preferences using memory tools
        pref_result = await update_user_preferences(user_id, user_prefs)

        if pref_result.get("status") == "success":
            result["preferences_updated"] = pref_result.get("preferences_updated", 0)
        else:
            result["errors"].append(
                f"Preference update failed: {pref_result.get('error')}"
            )

    except Exception as e:
        logger.error(f"Error updating preferences: {str(e)}")
        result["errors"].append(f"Preference processing error: {str(e)}")


async def _process_learned_facts(
    user_id: str, facts: List[Dict[str, Any]], result: Dict[str, Any]
) -> None:
    """Process learned facts as conversation memory.

    Args:
        user_id: User ID
        facts: List of fact dictionaries
        result: Result dictionary to update
    """
    try:
        # Convert facts to conversation messages for memory extraction
        if facts:
            facts_messages = [
                ConversationMessage(
                    role="system",
                    content=(
                        "Extract travel insights and preferences from learned facts."
                    ),
                ),
                ConversationMessage(
                    role="user",
                    content=(
                        f"Learned facts from conversation: "
                        f"{', '.join(str(fact) for fact in facts)}"
                    ),
                ),
            ]

            # Add to conversation memory
            memory_result = await add_conversation_memory(
                messages=facts_messages, user_id=user_id, context_type="learned_facts"
            )

            if memory_result.get("status") == "success":
                result["facts_processed"] = len(facts)
                result["memories_created"] += memory_result.get("memories_extracted", 0)
            else:
                result["errors"].append(
                    f"Facts processing failed: {memory_result.get('error')}"
                )

    except Exception as e:
        logger.error(f"Error processing learned facts: {str(e)}")
        result["errors"].append(f"Facts processing error: {str(e)}")


async def _process_conversation_context(
    user_id: str, context: Dict[str, Any], result: Dict[str, Any]
) -> None:
    """Process general conversation context as memory.

    Args:
        user_id: User ID
        context: Conversation context dictionary
        result: Result dictionary to update
    """
    try:
        # Extract meaningful context for memory storage
        context_messages = [
            ConversationMessage(
                role="system",
                content="Extract travel-related insights from conversation context.",
            )
        ]

        # Add context information as user messages
        for key, value in context.items():
            if value and key in [
                "destinations_discussed",
                "travel_intent",
                "budget_mentioned",
                "dates_mentioned",
            ]:
                context_messages.append(
                    ConversationMessage(role="user", content=f"{key}: {value}")
                )

        if len(context_messages) > 1:  # Only process if we have actual context
            # Add to conversation memory
            memory_result = await add_conversation_memory(
                messages=context_messages,
                user_id=user_id,
                context_type="conversation_context",
            )

            if memory_result.get("status") == "success":
                result["memories_created"] += memory_result.get("memories_extracted", 0)
            else:
                result["errors"].append(
                    f"Context processing failed: {memory_result.get('error')}"
                )

    except Exception as e:
        logger.error(f"Error processing conversation context: {str(e)}")
        result["errors"].append(f"Context processing error: {str(e)}")


# Legacy compatibility functions for gradual migration


async def get_session_memory_legacy(user_id: str) -> Dict[str, Any]:
    """Legacy wrapper for session memory initialization.

    Provides backward compatibility for existing code that expects the old format.

    Args:
        user_id: User ID

    Returns:
        Session memory data in legacy format
    """
    logger.warning(
        "Using legacy session memory function - consider updating to new API"
    )
    return await initialize_session_memory(user_id)


async def update_memory_legacy(user_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    """Legacy wrapper for memory updates.

    Args:
        user_id: User ID
        updates: Updates dictionary

    Returns:
        Update result in legacy format
    """
    logger.warning("Using legacy memory update function - consider updating to new API")
    result = await update_session_memory(user_id, updates)

    # Convert to legacy format
    return {
        "entities_created": 0,  # Not applicable in new system
        "relations_created": 0,  # Not applicable in new system
        "observations_added": result.get("memories_created", 0),
    }
