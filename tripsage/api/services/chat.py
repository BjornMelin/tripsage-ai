"""Chat service for TripSage API.

This service acts as a thin wrapper around the core chat service,
handling API-specific concerns like model adaptation and FastAPI integration.
"""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import Depends

from tripsage.api.schemas.requests.chat import (
    ChatCompletionRequest,
    CreateMessageRequest,
    SessionCreateRequest,
)
from tripsage.api.schemas.responses.chat import (
    ChatCompletionResponse,
    MessageResponse,
    SessionResponse,
)
from tripsage_core.exceptions.exceptions import (
    CoreServiceError as ServiceError,
)
from tripsage_core.exceptions.exceptions import (
    CoreValidationError as ValidationError,
)
from tripsage_core.services.business.chat_service import (
    ChatService as CoreChatService,
)
from tripsage_core.services.business.chat_service import (
    get_chat_service as get_core_chat_service,
)

logger = logging.getLogger(__name__)


class ChatService:
    """
    API chat service that delegates to core business services.

    This service acts as a façade, handling:
    - Model adaptation between API and core models
    - API-specific error handling
    - FastAPI dependency integration
    """

    def __init__(self, core_chat_service: Optional[CoreChatService] = None):
        """
        Initialize the API chat service.

        Args:
            core_chat_service: Core chat service
        """
        self.core_chat_service = core_chat_service

    async def _get_core_chat_service(self) -> CoreChatService:
        """Get or create core chat service instance."""
        if self.core_chat_service is None:
            self.core_chat_service = await get_core_chat_service()
        return self.core_chat_service

    async def create_session(
        self, user_id: str, request: SessionCreateRequest
    ) -> SessionResponse:
        """Create a new chat session.

        Args:
            user_id: User ID
            request: Session creation request

        Returns:
            Created session response

        Raises:
            ValidationError: If request data is invalid
            ServiceError: If creation fails
        """
        try:
            logger.info(f"Creating chat session for user: {user_id}")

            # Adapt API request to core model
            core_request = self._adapt_session_create_request(request)

            # Create session via core service
            core_service = await self._get_core_chat_service()
            core_response = await core_service.create_session(user_id, core_request)

            # Adapt core response to API model
            return self._adapt_session_response(core_response)

        except (ValidationError, ServiceError) as e:
            logger.error(f"Session creation failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error creating session: {str(e)}")
            raise ServiceError("Session creation failed") from e

    async def get_session(
        self, user_id: str, session_id: UUID
    ) -> Optional[SessionResponse]:
        """Get a chat session.

        Args:
            user_id: User ID
            session_id: Session ID

        Returns:
            Session response if found, None otherwise

        Raises:
            ServiceError: If retrieval fails
        """
        try:
            logger.info(f"Getting session {session_id} for user: {user_id}")

            # Get session via core service
            core_service = await self._get_core_chat_service()
            core_response = await core_service.get_session(user_id, str(session_id))

            if core_response is None:
                return None

            # Adapt core response to API model
            return self._adapt_session_response(core_response)

        except Exception as e:
            logger.error(f"Failed to get session: {str(e)}")
            raise ServiceError("Failed to get session") from e

    async def list_sessions(self, user_id: str) -> List[SessionResponse]:
        """List chat sessions for a user.

        Args:
            user_id: User ID

        Returns:
            List of sessions

        Raises:
            ServiceError: If listing fails
        """
        try:
            logger.info(f"Listing sessions for user: {user_id}")

            # List sessions via core service
            core_service = await self._get_core_chat_service()
            core_sessions = await core_service.list_sessions(user_id)

            # Adapt core response to API model
            return [self._adapt_session_response(session) for session in core_sessions]

        except Exception as e:
            logger.error(f"Failed to list sessions: {str(e)}")
            raise ServiceError("Failed to list sessions") from e

    async def create_message(
        self, user_id: str, session_id: UUID, request: CreateMessageRequest
    ) -> MessageResponse:
        """Create a new message in a session.

        Args:
            user_id: User ID
            session_id: Session ID
            request: Message creation request

        Returns:
            Created message response

        Raises:
            ValidationError: If request data is invalid
            ServiceError: If creation fails
        """
        try:
            logger.info(f"Creating message in session {session_id} for user: {user_id}")

            # Adapt API request to core model
            core_request = self._adapt_message_create_request(request)

            # Create message via core service
            core_service = await self._get_core_chat_service()
            core_response = await core_service.create_message(
                user_id, str(session_id), core_request
            )

            # Adapt core response to API model
            return self._adapt_message_response(core_response)

        except (ValidationError, ServiceError) as e:
            logger.error(f"Message creation failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error creating message: {str(e)}")
            raise ServiceError("Message creation failed") from e

    async def get_messages(
        self, user_id: str, session_id: UUID, limit: int = 50
    ) -> List[MessageResponse]:
        """Get messages from a session.

        Args:
            user_id: User ID
            session_id: Session ID
            limit: Maximum number of messages to return

        Returns:
            List of messages

        Raises:
            ServiceError: If retrieval fails
        """
        try:
            logger.info(
                f"Getting messages from session {session_id} for user: {user_id}"
            )

            # Get messages via core service
            core_service = await self._get_core_chat_service()
            core_messages = await core_service.get_messages(
                user_id, str(session_id), limit
            )

            # Adapt core response to API model
            return [self._adapt_message_response(message) for message in core_messages]

        except Exception as e:
            logger.error(f"Failed to get messages: {str(e)}")
            raise ServiceError("Failed to get messages") from e

    async def chat_completion(
        self, user_id: str, request: ChatCompletionRequest
    ) -> ChatCompletionResponse:
        """Generate chat completion response.

        Args:
            user_id: User ID
            request: Chat completion request

        Returns:
            Chat completion response

        Raises:
            ValidationError: If request data is invalid
            ServiceError: If completion fails
        """
        try:
            logger.info(f"Generating chat completion for user: {user_id}")

            # Adapt API request to core model
            core_request = self._adapt_chat_completion_request(request)

            # Generate completion via core service
            core_service = await self._get_core_chat_service()
            core_response = await core_service.chat_completion(user_id, core_request)

            # Adapt core response to API model
            return self._adapt_chat_completion_response(core_response)

        except (ValidationError, ServiceError) as e:
            logger.error(f"Chat completion failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in chat completion: {str(e)}")
            raise ServiceError("Chat completion failed") from e

    async def delete_session(self, user_id: str, session_id: UUID) -> bool:
        """Delete a chat session.

        Args:
            user_id: User ID
            session_id: Session ID

        Returns:
            True if deleted successfully

        Raises:
            ServiceError: If deletion fails
        """
        try:
            logger.info(f"Deleting session {session_id} for user: {user_id}")

            # Delete session via core service
            core_service = await self._get_core_chat_service()
            return await core_service.delete_session(user_id, str(session_id))

        except Exception as e:
            logger.error(f"Failed to delete session: {str(e)}")
            raise ServiceError("Failed to delete session") from e

    def _adapt_session_create_request(self, request: SessionCreateRequest) -> dict:
        """Adapt session create request to core model."""
        return {
            "title": request.title,
            "description": getattr(request, "description", None),
            "metadata": getattr(request, "metadata", {}),
        }

    def _adapt_message_create_request(self, request: CreateMessageRequest) -> dict:
        """Adapt message create request to core model."""
        return {
            "content": request.content,
            "role": request.role,
            "tool_calls": getattr(request, "tool_calls", None),
            "metadata": getattr(request, "metadata", {}),
        }

    def _adapt_chat_completion_request(self, request: ChatCompletionRequest) -> dict:
        """Adapt chat completion request to core model."""
        return {
            "messages": [
                {
                    "role": msg.role,
                    "content": msg.content,
                    "tool_calls": getattr(msg, "tool_calls", None),
                    "metadata": getattr(msg, "metadata", {}),
                }
                for msg in request.messages
            ],
            "model": getattr(request, "model", "gpt-4"),
            "temperature": getattr(request, "temperature", 0.7),
            "max_tokens": getattr(request, "max_tokens", None),
            "stream": getattr(request, "stream", False),
            "tools": getattr(request, "tools", None),
            "session_id": getattr(request, "session_id", None),
        }

    def _adapt_session_response(self, core_response) -> SessionResponse:
        """Adapt core session response to API model."""
        return SessionResponse(
            id=core_response.get("id", ""),
            user_id=core_response.get("user_id", ""),
            title=core_response.get("title", ""),
            description=core_response.get("description"),
            created_at=core_response.get("created_at", ""),
            updated_at=core_response.get("updated_at", ""),
            message_count=core_response.get("message_count", 0),
            metadata=core_response.get("metadata", {}),
        )

    def _adapt_message_response(self, core_response) -> MessageResponse:
        """Adapt core message response to API model."""
        return MessageResponse(
            id=core_response.get("id", ""),
            session_id=core_response.get("session_id", ""),
            role=core_response.get("role", "user"),
            content=core_response.get("content", ""),
            tool_calls=core_response.get("tool_calls"),
            created_at=core_response.get("created_at", ""),
            metadata=core_response.get("metadata", {}),
        )

    def _adapt_chat_completion_response(self, core_response) -> ChatCompletionResponse:
        """Adapt core chat completion response to API model."""
        return ChatCompletionResponse(
            id=core_response.get("id", ""),
            object=core_response.get("object", "chat.completion"),
            created=core_response.get("created", 0),
            model=core_response.get("model", "gpt-4"),
            choices=[
                {
                    "index": choice.get("index", 0),
                    "message": {
                        "role": choice.get("message", {}).get("role", "assistant"),
                        "content": choice.get("message", {}).get("content", ""),
                        "tool_calls": choice.get("message", {}).get("tool_calls"),
                    },
                    "finish_reason": choice.get("finish_reason", "stop"),
                }
                for choice in core_response.get("choices", [])
            ],
            usage=core_response.get("usage", {}),
        )


# Module-level dependency annotation
_core_chat_service_dep = Depends(get_core_chat_service)


# Dependency function for FastAPI
async def get_chat_service(
    core_chat_service: CoreChatService = _core_chat_service_dep,
) -> ChatService:
    """
    Get chat service instance for dependency injection.

    Args:
        core_chat_service: Core chat service

    Returns:
        ChatService instance
    """
    return ChatService(core_chat_service=core_chat_service)
