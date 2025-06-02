"""Chat service for TripSage API.

This service acts as a thin wrapper around the core chat service,
handling API-specific concerns like model adaptation and FastAPI integration.
"""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import Depends

from tripsage.api.schemas.requests.chat import (
    ChatRequest,
    CreateMessageRequest,
    SessionCreateRequest,
)
from tripsage.api.schemas.responses.chat import ChatResponse
from tripsage_core.services.business.chat_service import ChatService as CoreChatService
from tripsage_core.services.business.auth_service import AuthenticationService as CoreAuthService

logger = logging.getLogger(__name__)


class ChatService:
    """
    API chat service that delegates to core business services.

    This service acts as a thin wrapper that delegates all operations
    to the core chat service.
    """

    def __init__(self, core_chat_service: CoreChatService, core_auth_service: CoreAuthService):
        """Initialize the API chat service with core dependencies."""
        self.core_chat_service = core_chat_service
        self.core_auth_service = core_auth_service

    async def chat_completion(self, user_id: str, request: ChatRequest) -> dict:
        """Handle chat completion request."""
        return await self.core_chat_service.chat_completion(
            user_id=user_id, request=request
        )

    async def create_session(self, user_id: str, request: SessionCreateRequest) -> dict:
        """Create a new chat session."""
        return await self.core_chat_service.create_session(
            user_id=user_id, request=request
        )

    async def list_sessions(self, user_id: str) -> List[dict]:
        """List chat sessions for user."""
        return await self.core_chat_service.list_sessions(user_id=user_id)

    async def get_session(self, user_id: str, session_id: UUID) -> Optional[dict]:
        """Get a specific chat session."""
        return await self.core_chat_service.get_session(
            user_id=user_id, session_id=session_id
        )

    async def get_messages(self, user_id: str, session_id: UUID, limit: int = 50) -> List[dict]:
        """Get messages from a chat session."""
        return await self.core_chat_service.get_messages(
            user_id=user_id, session_id=session_id, limit=limit
        )

    async def create_message(self, user_id: str, session_id: UUID, request: CreateMessageRequest) -> dict:
        """Create a new message in a session."""
        return await self.core_chat_service.create_message(
            user_id=user_id, session_id=session_id, request=request
        )

    async def delete_session(self, user_id: str, session_id: UUID) -> bool:
        """Delete a chat session."""
        return await self.core_chat_service.delete_session(
            user_id=user_id, session_id=session_id
        )


async def get_core_chat_service() -> CoreChatService:
    """Get core chat service instance."""
    # Simplified for now - in real implementation this would have proper DI
    return CoreChatService()


async def get_core_auth_service() -> CoreAuthService:
    """Get core auth service instance."""
    # Simplified for now - in real implementation this would have proper DI  
    return CoreAuthService()


async def get_chat_service() -> ChatService:
    """Get ChatService instance with dependencies."""
    core_chat = await get_core_chat_service()
    core_auth = await get_core_auth_service()
    return ChatService(core_chat, core_auth)