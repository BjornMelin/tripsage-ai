"""Memory service for TripSage API.

This service acts as a thin wrapper around the core memory service,
handling API-specific concerns like model adaptation and FastAPI integration.
"""

import logging
from typing import Dict, List, Optional

from fastapi import Depends

from tripsage_core.services.business.memory_service import MemoryService as CoreMemoryService

logger = logging.getLogger(__name__)


class MemoryService:
    """
    API memory service that delegates to core business services.

    This service acts as a thin wrapper that delegates all operations
    to the core memory service.
    """

    def __init__(self, core_memory_service: CoreMemoryService):
        """Initialize the API memory service with core dependencies."""
        self.core_memory_service = core_memory_service

    async def add_conversation_memory(
        self, user_id: str, messages: List[Dict[str, str]], session_id: Optional[str] = None
    ) -> dict:
        """Add conversation memory."""
        return await self.core_memory_service.add_conversation_memory(
            user_id=user_id, messages=messages, session_id=session_id
        )

    async def search_memories(self, user_id: str, query: str, limit: int = 10) -> List[dict]:
        """Search user memories."""
        return await self.core_memory_service.search_memories(
            user_id=user_id, query=query, limit=limit
        )

    async def get_user_context(self, user_id: str) -> dict:
        """Get user context and preferences."""
        return await self.core_memory_service.get_user_context(user_id=user_id)

    async def update_user_preferences(self, user_id: str, preferences: Dict) -> dict:
        """Update user preferences."""
        return await self.core_memory_service.update_user_preferences(
            user_id=user_id, preferences=preferences
        )

    async def add_user_preference(
        self, user_id: str, key: str, value: str, category: str = "general"
    ) -> dict:
        """Add a single user preference."""
        return await self.core_memory_service.add_user_preference(
            user_id=user_id, key=key, value=value, category=category
        )

    async def delete_memory(self, user_id: str, memory_id: str) -> bool:
        """Delete a specific memory."""
        return await self.core_memory_service.delete_memory(
            user_id=user_id, memory_id=memory_id
        )

    async def get_memory_stats(self, user_id: str) -> dict:
        """Get memory statistics for user."""
        return await self.core_memory_service.get_memory_stats(user_id=user_id)

    async def clear_user_memory(self, user_id: str, confirm: bool = False) -> dict:
        """Clear all memories for user."""
        return await self.core_memory_service.clear_user_memory(
            user_id=user_id, confirm=confirm
        )


async def get_core_memory_service() -> CoreMemoryService:
    """Get core memory service instance."""
    # Simplified for now - in real implementation this would have proper DI
    return CoreMemoryService()


async def get_memory_service() -> MemoryService:
    """Get MemoryService instance with dependencies."""
    core_memory = await get_core_memory_service()
    return MemoryService(core_memory)