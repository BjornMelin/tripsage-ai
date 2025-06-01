"""Memory service for TripSage API.

This service acts as a thin wrapper around the core memory service,
handling API-specific concerns like model adaptation and FastAPI integration.
"""

import logging
from typing import Dict, List, Optional

from fastapi import Depends

from tripsage_core.exceptions.exceptions import (
    CoreServiceError as ServiceError,
)
from tripsage_core.exceptions.exceptions import (
    CoreValidationError as ValidationError,
)
from tripsage_core.services.business.memory_service import (
    MemoryService as CoreMemoryService,
)
from tripsage_core.services.business.memory_service import (
    get_memory_service as get_core_memory_service,
)

logger = logging.getLogger(__name__)


class MemoryService:
    """
    API memory service that delegates to core business services.

    This service acts as a façade, handling:
    - Model adaptation between API and core models
    - API-specific error handling
    - FastAPI dependency integration
    """

    def __init__(self, core_memory_service: Optional[CoreMemoryService] = None):
        """
        Initialize the API memory service.

        Args:
            core_memory_service: Core memory service
        """
        self.core_memory_service = core_memory_service

    async def _get_core_memory_service(self) -> CoreMemoryService:
        """Get or create core memory service instance."""
        if self.core_memory_service is None:
            self.core_memory_service = await get_core_memory_service()
        return self.core_memory_service

    async def add_conversation_memory(
        self, user_id: str, messages: List[Dict], session_id: Optional[str] = None
    ) -> Dict:
        """Add conversation messages to user memory.

        Args:
            user_id: User ID
            messages: List of conversation messages
            session_id: Optional session ID

        Returns:
            Operation result

        Raises:
            ValidationError: If request data is invalid
            ServiceError: If operation fails
        """
        try:
            logger.info(f"Adding conversation memory for user: {user_id}")

            # Add conversation memory via core service
            core_service = await self._get_core_memory_service()
            core_response = await core_service.add_conversation_memory(
                user_id, messages, session_id
            )

            return self._adapt_memory_response(core_response)

        except (ValidationError, ServiceError) as e:
            logger.error(f"Add conversation memory failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error adding conversation memory: {str(e)}")
            raise ServiceError("Add conversation memory failed") from e

    async def get_user_context(self, user_id: str) -> Dict:
        """Get user context and preferences.

        Args:
            user_id: User ID

        Returns:
            User context and preferences

        Raises:
            ServiceError: If retrieval fails
        """
        try:
            logger.info(f"Getting user context for user: {user_id}")

            # Get user context via core service
            core_service = await self._get_core_memory_service()
            core_response = await core_service.get_user_context(user_id)

            return self._adapt_context_response(core_response)

        except Exception as e:
            logger.error(f"Failed to get user context: {str(e)}")
            raise ServiceError("Failed to get user context") from e

    async def search_memories(
        self, user_id: str, query: str, limit: int = 10
    ) -> List[Dict]:
        """Search user memories.

        Args:
            user_id: User ID
            query: Search query
            limit: Maximum number of results

        Returns:
            List of matching memories

        Raises:
            ServiceError: If search fails
        """
        try:
            logger.info(f"Searching memories for user: {user_id}")

            # Search memories via core service
            core_service = await self._get_core_memory_service()
            core_response = await core_service.search_memories(user_id, query, limit)

            return [self._adapt_memory_item(item) for item in core_response]

        except Exception as e:
            logger.error(f"Failed to search memories: {str(e)}")
            raise ServiceError("Failed to search memories") from e

    async def update_user_preferences(self, user_id: str, preferences: Dict) -> Dict:
        """Update user preferences.

        Args:
            user_id: User ID
            preferences: Preferences to update

        Returns:
            Updated preferences

        Raises:
            ValidationError: If preferences are invalid
            ServiceError: If update fails
        """
        try:
            logger.info(f"Updating preferences for user: {user_id}")

            # Update preferences via core service
            core_service = await self._get_core_memory_service()
            core_response = await core_service.update_user_preferences(
                user_id, preferences
            )

            return self._adapt_preferences_response(core_response)

        except (ValidationError, ServiceError) as e:
            logger.error(f"Update preferences failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error updating preferences: {str(e)}")
            raise ServiceError("Update preferences failed") from e

    async def delete_memory(self, user_id: str, memory_id: str) -> bool:
        """Delete a specific memory.

        Args:
            user_id: User ID
            memory_id: Memory ID to delete

        Returns:
            True if deleted successfully

        Raises:
            ServiceError: If deletion fails
        """
        try:
            logger.info(f"Deleting memory {memory_id} for user: {user_id}")

            # Delete memory via core service
            core_service = await self._get_core_memory_service()
            return await core_service.delete_memory(user_id, memory_id)

        except Exception as e:
            logger.error(f"Failed to delete memory: {str(e)}")
            raise ServiceError("Failed to delete memory") from e

    async def add_user_preference(
        self, user_id: str, key: str, value: str, category: str = "general"
    ) -> Dict:
        """Add or update a user preference.

        Args:
            user_id: User ID
            key: Preference key
            value: Preference value
            category: Preference category

        Returns:
            Updated preference

        Raises:
            ValidationError: If preference is invalid
            ServiceError: If operation fails
        """
        try:
            logger.info(f"Adding preference {key} for user: {user_id}")

            # Add preference via core service
            core_service = await self._get_core_memory_service()
            core_response = await core_service.add_user_preference(
                user_id, key, value, category
            )

            return self._adapt_preference_response(core_response)

        except (ValidationError, ServiceError) as e:
            logger.error(f"Add preference failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error adding preference: {str(e)}")
            raise ServiceError("Add preference failed") from e

    async def get_memory_stats(self, user_id: str) -> Dict:
        """Get memory statistics for a user.

        Args:
            user_id: User ID

        Returns:
            Memory statistics

        Raises:
            ServiceError: If retrieval fails
        """
        try:
            logger.info(f"Getting memory stats for user: {user_id}")

            # Get memory stats via core service
            core_service = await self._get_core_memory_service()
            core_response = await core_service.get_memory_stats(user_id)

            return self._adapt_stats_response(core_response)

        except Exception as e:
            logger.error(f"Failed to get memory stats: {str(e)}")
            raise ServiceError("Failed to get memory stats") from e

    async def clear_user_memory(self, user_id: str, confirm: bool = False) -> Dict:
        """Clear all memories for a user.

        Args:
            user_id: User ID
            confirm: Confirmation flag

        Returns:
            Operation result

        Raises:
            ValidationError: If confirmation is required
            ServiceError: If operation fails
        """
        try:
            logger.info(f"Clearing memory for user: {user_id}")

            if not confirm:
                raise ValidationError("Confirmation required to clear user memory")

            # Clear memory via core service
            core_service = await self._get_core_memory_service()
            core_response = await core_service.clear_user_memory(user_id)

            return self._adapt_memory_response(core_response)

        except (ValidationError, ServiceError) as e:
            logger.error(f"Clear memory failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error clearing memory: {str(e)}")
            raise ServiceError("Clear memory failed") from e

    def _adapt_memory_response(self, core_response) -> Dict:
        """Adapt core memory response to API model."""
        return {
            "status": core_response.get("status", "success"),
            "message": core_response.get("message", ""),
            "memory_id": core_response.get("memory_id"),
            "metadata": core_response.get("metadata", {}),
        }

    def _adapt_context_response(self, core_response) -> Dict:
        """Adapt core context response to API model."""
        return {
            "user_id": core_response.get("user_id", ""),
            "context": core_response.get("context", {}),
            "preferences": core_response.get("preferences", {}),
            "conversation_insights": core_response.get("conversation_insights", []),
            "status": core_response.get("status", "success"),
        }

    def _adapt_memory_item(self, core_item) -> Dict:
        """Adapt core memory item to API model."""
        return {
            "id": core_item.get("id", ""),
            "content": core_item.get("content", ""),
            "timestamp": core_item.get("timestamp", ""),
            "score": core_item.get("score", 0.0),
            "metadata": core_item.get("metadata", {}),
        }

    def _adapt_preferences_response(self, core_response) -> Dict:
        """Adapt core preferences response to API model."""
        return {
            "user_id": core_response.get("user_id", ""),
            "preferences": core_response.get("preferences", {}),
            "updated_at": core_response.get("updated_at", ""),
            "status": core_response.get("status", "success"),
        }

    def _adapt_preference_response(self, core_response) -> Dict:
        """Adapt core preference response to API model."""
        return {
            "key": core_response.get("key", ""),
            "value": core_response.get("value", ""),
            "category": core_response.get("category", ""),
            "updated_at": core_response.get("updated_at", ""),
        }

    def _adapt_stats_response(self, core_response) -> Dict:
        """Adapt core stats response to API model."""
        return {
            "user_id": core_response.get("user_id", ""),
            "total_memories": core_response.get("total_memories", 0),
            "total_preferences": core_response.get("total_preferences", 0),
            "memory_categories": core_response.get("memory_categories", {}),
            "last_activity": core_response.get("last_activity", ""),
        }


# Module-level dependency annotation
_core_memory_service_dep = Depends(get_core_memory_service)


# Dependency function for FastAPI
async def get_memory_service(
    core_memory_service: CoreMemoryService = _core_memory_service_dep,
) -> MemoryService:
    """
    Get memory service instance for dependency injection.

    Args:
        core_memory_service: Core memory service

    Returns:
        MemoryService instance
    """
    return MemoryService(core_memory_service=core_memory_service)
