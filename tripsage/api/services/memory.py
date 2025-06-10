"""Memory service for TripSage API.

This service acts as a thin wrapper around the core memory service,
handling API-specific concerns like model adaptation and FastAPI integration.
"""

import logging
from typing import Dict, List, Optional

from tripsage_core.exceptions.exceptions import (
    CoreAuthenticationError,
    CoreAuthorizationError,
    CoreResourceNotFoundError,
    CoreValidationError,
)
from tripsage_core.services.business.memory_service import (
    ConversationMemoryRequest,
    MemorySearchRequest,
    PreferencesUpdateRequest,
)
from tripsage_core.services.business.memory_service import (
    MemoryService as CoreMemoryService,
)
from tripsage_core.services.business.memory_service import (
    get_memory_service as get_core_memory_service,
)

logger = logging.getLogger(__name__)


class MemoryServiceError(Exception):
    """Base exception for memory service errors."""

    pass


class MemoryServiceValidationError(MemoryServiceError):
    """Validation error in memory service."""

    pass


class MemoryServiceNotFoundError(MemoryServiceError):
    """Resource not found error in memory service."""

    pass


class MemoryServicePermissionError(MemoryServiceError):
    """Permission error in memory service."""

    pass


class MemoryService:
    """
    API memory service that delegates to core business services.

    This service acts as a thin wrapper that delegates all operations
    to the core memory service, adapting between API models and core models.
    Implements consistent error handling and model adaptation patterns.
    """

    def __init__(self, core_memory_service: CoreMemoryService):
        """Initialize the API memory service with core dependencies."""
        self.core_memory_service = core_memory_service

    def _handle_core_exception(self, e: Exception) -> None:
        """Convert core exceptions to API service exceptions."""
        if isinstance(e, CoreValidationError):
            raise MemoryServiceValidationError(str(e)) from e
        elif isinstance(e, CoreResourceNotFoundError):
            raise MemoryServiceNotFoundError(str(e)) from e
        elif isinstance(e, (CoreAuthenticationError, CoreAuthorizationError)):
            raise MemoryServicePermissionError(str(e)) from e
        else:
            logger.error(f"Unexpected core service error: {e}")
            raise MemoryServiceError(f"Internal service error: {e}") from e

    async def add_conversation_memory(
        self,
        user_id: str,
        messages: List[Dict[str, str]],
        session_id: Optional[str] = None,
    ) -> dict:
        """Add conversation memory."""
        try:
            logger.debug(f"Adding conversation memory for user {user_id}")

            # Validate input
            if not user_id:
                raise MemoryServiceValidationError("User ID is required")
            if not messages or len(messages) == 0:
                raise MemoryServiceValidationError("Messages are required")
            if not isinstance(messages, list):
                raise MemoryServiceValidationError("Messages must be a list")

            # Validate message structure
            for i, message in enumerate(messages):
                if not isinstance(message, dict):
                    raise MemoryServiceValidationError(
                        f"Message {i} must be a dictionary"
                    )
                if "role" not in message or "content" not in message:
                    raise MemoryServiceValidationError(
                        f"Message {i} must have 'role' and 'content' fields"
                    )

            memory_request = ConversationMemoryRequest(
                messages=messages,
                session_id=session_id,
            )

            result = await self.core_memory_service.add_conversation_memory(
                user_id=user_id, memory_request=memory_request
            )

            logger.info(
                f"Conversation memory added for user {user_id}, session {session_id}"
            )

            # Ensure consistent dict response
            if hasattr(result, "model_dump"):
                return result.model_dump()
            return (
                result
                if isinstance(result, dict)
                else {"success": True, "result": result}
            )

        except MemoryServiceError:
            raise  # Re-raise our own exceptions
        except Exception as e:
            logger.error(f"Conversation memory addition failed for user {user_id}: {e}")
            self._handle_core_exception(e)

    async def search_memories(
        self, user_id: str, query: str, limit: int = 10
    ) -> List[dict]:
        """Search user memories."""
        try:
            logger.debug(
                f"Searching memories for user {user_id}, query: '{query}', "
                f"limit: {limit}"
            )

            # Validate input
            if not user_id:
                raise MemoryServiceValidationError("User ID is required")
            if not query or not query.strip():
                raise MemoryServiceValidationError("Search query is required")
            if limit < 1 or limit > 100:
                raise MemoryServiceValidationError("Limit must be between 1 and 100")

            search_request = MemorySearchRequest(query=query.strip(), limit=limit)
            results = await self.core_memory_service.search_memories(
                user_id=user_id, search_request=search_request
            )

            logger.debug(f"Found {len(results)} memories for user {user_id}")

            # Convert MemorySearchResult objects to dictionaries
            return [
                result.model_dump()
                if hasattr(result, "model_dump")
                else result
                if isinstance(result, dict)
                else {"content": str(result)}
                for result in results
            ]

        except MemoryServiceError:
            raise  # Re-raise our own exceptions
        except Exception as e:
            logger.error(f"Memory search failed for user {user_id}: {e}")
            self._handle_core_exception(e)

    async def get_user_context(self, user_id: str) -> dict:
        """Get user context and preferences."""
        try:
            logger.debug(f"Getting user context for user {user_id}")

            # Validate input
            if not user_id:
                raise MemoryServiceValidationError("User ID is required")

            context = await self.core_memory_service.get_user_context(user_id=user_id)

            logger.debug(f"User context retrieved for user {user_id}")

            return context.model_dump() if hasattr(context, "model_dump") else context

        except MemoryServiceError:
            raise  # Re-raise our own exceptions
        except Exception as e:
            logger.error(f"User context retrieval failed for user {user_id}: {e}")
            self._handle_core_exception(e)

    async def update_user_preferences(self, user_id: str, preferences: Dict) -> dict:
        """Update user preferences."""
        try:
            logger.debug(f"Updating preferences for user {user_id}")

            # Validate input
            if not user_id:
                raise MemoryServiceValidationError("User ID is required")
            if not preferences or not isinstance(preferences, dict):
                raise MemoryServiceValidationError(
                    "Preferences must be a non-empty dictionary"
                )

            preferences_request = PreferencesUpdateRequest(preferences=preferences)
            result = await self.core_memory_service.update_user_preferences(
                user_id=user_id, preferences_request=preferences_request
            )

            logger.info(
                f"Preferences updated for user {user_id}: {list(preferences.keys())}"
            )

            # Ensure consistent dict response
            if hasattr(result, "model_dump"):
                return result.model_dump()
            return (
                result
                if isinstance(result, dict)
                else {"success": True, "updated": list(preferences.keys())}
            )

        except MemoryServiceError:
            raise  # Re-raise our own exceptions
        except Exception as e:
            logger.error(f"Preferences update failed for user {user_id}: {e}")
            self._handle_core_exception(e)

    async def add_user_preference(
        self, user_id: str, key: str, value: str, category: str = "general"
    ) -> dict:
        """Add a single user preference."""
        try:
            logger.debug(f"Adding preference for user {user_id}: {key}={value}")

            # Validate input
            if not user_id:
                raise MemoryServiceValidationError("User ID is required")
            if not key or not key.strip():
                raise MemoryServiceValidationError("Preference key is required")
            if value is None:
                raise MemoryServiceValidationError("Preference value is required")
            if not category or not category.strip():
                raise MemoryServiceValidationError("Category is required")

            preferences = {key.strip(): value}
            preferences_request = PreferencesUpdateRequest(
                preferences=preferences, category=category.strip()
            )
            result = await self.core_memory_service.update_user_preferences(
                user_id=user_id, preferences_request=preferences_request
            )

            logger.info(
                f"Preference added for user {user_id}: {key} in category {category}"
            )

            # Ensure consistent dict response
            if hasattr(result, "model_dump"):
                return result.model_dump()
            return (
                result
                if isinstance(result, dict)
                else {"success": True, "key": key, "category": category}
            )

        except MemoryServiceError:
            raise  # Re-raise our own exceptions
        except Exception as e:
            logger.error(f"Preference addition failed for user {user_id}: {e}")
            self._handle_core_exception(e)

    async def delete_memory(self, user_id: str, memory_id: str) -> bool:
        """Delete a specific memory."""
        try:
            logger.debug(f"Deleting memory {memory_id} for user {user_id}")

            # Validate input
            if not user_id:
                raise MemoryServiceValidationError("User ID is required")
            if not memory_id or not memory_id.strip():
                raise MemoryServiceValidationError("Memory ID is required")

            result = await self.core_memory_service.delete_user_memories(
                user_id=user_id, memory_ids=[memory_id.strip()]
            )

            success = (
                result.get("success", False)
                if isinstance(result, dict)
                else bool(result)
            )

            logger.info(
                f"Memory {'deleted' if success else 'not found'}: {memory_id} "
                f"for user {user_id}"
            )
            return success

        except MemoryServiceError:
            raise  # Re-raise our own exceptions
        except Exception as e:
            logger.error(
                f"Memory deletion failed for memory {memory_id}, user {user_id}: {e}"
            )
            self._handle_core_exception(e)

    async def get_memory_stats(self, user_id: str) -> dict:
        """Get memory statistics for user."""
        try:
            logger.debug(f"Getting memory stats for user {user_id}")

            # Validate input
            if not user_id:
                raise MemoryServiceValidationError("User ID is required")

            # Get user context and derive stats from it
            context = await self.core_memory_service.get_user_context(user_id=user_id)

            # Handle both model objects and dict responses
            if hasattr(context, "preferences") and hasattr(context, "past_trips"):
                preferences_count = (
                    len(context.preferences) if context.preferences else 0
                )
                trips_count = len(context.past_trips) if context.past_trips else 0
            else:
                # Fallback for dict response
                context_dict = context if isinstance(context, dict) else {}
                preferences_count = len(context_dict.get("preferences", []))
                trips_count = len(context_dict.get("past_trips", []))

            stats = {
                "total_memories": preferences_count + trips_count,
                "conversation_memories": trips_count,
                "preference_count": preferences_count,
                "last_activity": "unknown",  # This would need to be tracked separately
            }

            logger.debug(f"Memory stats retrieved for user {user_id}: {stats}")
            return stats

        except MemoryServiceError:
            raise  # Re-raise our own exceptions
        except Exception as e:
            logger.error(f"Memory stats retrieval failed for user {user_id}: {e}")
            self._handle_core_exception(e)

    async def clear_user_memory(self, user_id: str, confirm: bool = False) -> dict:
        """Clear all memories for user."""
        try:
            logger.debug(
                f"Clearing all memories for user {user_id}, confirm: {confirm}"
            )

            # Validate input
            if not user_id:
                raise MemoryServiceValidationError("User ID is required")

            if not confirm:
                return {
                    "error": "Confirmation required to clear all memories",
                    "cleared": False,
                }

            result = await self.core_memory_service.delete_user_memories(
                user_id=user_id
            )

            # Handle both model objects and dict responses
            if isinstance(result, dict):
                success = result.get("success", False)
                count = result.get("deleted_count", 0)
            else:
                success = bool(result)
                count = 0  # Unknown count

            logger.warning(
                f"All memories cleared for user {user_id}: "
                f"success={success}, count={count}"
            )

            return {
                "cleared": success,
                "count": count,
            }

        except MemoryServiceError:
            raise  # Re-raise our own exceptions
        except Exception as e:
            logger.error(f"Memory clearing failed for user {user_id}: {e}")
            self._handle_core_exception(e)


async def get_memory_service() -> MemoryService:
    """Get MemoryService instance with dependencies."""
    core_memory = await get_core_memory_service()
    return MemoryService(core_memory)
