"""Chat service for TripSage API.

This service acts as a thin wrapper around the core chat service,
handling API-specific concerns like model adaptation and FastAPI integration.
"""

import logging
from typing import List, Optional
from uuid import UUID

from tripsage.api.schemas.requests.chat import (
    ChatRequest,
    CreateMessageRequest,
    SessionCreateRequest,
)
from tripsage_core.exceptions.exceptions import (
    CoreAuthenticationError,
    CoreAuthorizationError,
    CoreResourceNotFoundError,
    CoreValidationError,
)
from tripsage_core.services.business.chat_service import (
    ChatService as CoreChatService,
)
from tripsage_core.services.business.chat_service import (
    ChatSessionCreateRequest,
)
from tripsage_core.services.business.chat_service import (
    MessageCreateRequest as CoreMessageCreateRequest,
)

logger = logging.getLogger(__name__)


class ChatServiceError(Exception):
    """Base exception for chat service errors."""

    pass


class ChatServiceValidationError(ChatServiceError):
    """Validation error in chat service."""

    pass


class ChatServiceNotFoundError(ChatServiceError):
    """Resource not found error in chat service."""

    pass


class ChatServicePermissionError(ChatServiceError):
    """Permission error in chat service."""

    pass


class ChatService:
    """
    API chat service that delegates to core business services.

    This service acts as a thin wrapper that delegates all operations
    to the core chat service, adapting between API models and core models.
    Implements consistent error handling and model adaptation patterns.
    """

    def __init__(self, core_chat_service: CoreChatService):
        """Initialize the API chat service with core dependencies."""
        self.core_chat_service = core_chat_service

    def _handle_core_exception(self, e: Exception) -> None:
        """Convert core exceptions to API service exceptions."""
        if isinstance(e, CoreValidationError):
            raise ChatServiceValidationError(str(e)) from e
        elif isinstance(e, CoreResourceNotFoundError):
            raise ChatServiceNotFoundError(str(e)) from e
        elif isinstance(e, (CoreAuthenticationError, CoreAuthorizationError)):
            raise ChatServicePermissionError(str(e)) from e
        else:
            logger.error(f"Unexpected core service error: {e}")
            raise ChatServiceError(f"Internal service error: {e}") from e

    async def chat_completion(self, user_id: str, request: ChatRequest) -> dict:
        """Handle chat completion request."""
        try:
            # This method may need to be implemented differently
            # as it's not a direct core method. For now, delegate to
            # any existing implementation or raise NotImplementedError
            raise NotImplementedError(
                "Chat completion not yet implemented in core service"
            )
        except Exception as e:
            logger.error(f"Chat completion failed for user {user_id}: {e}")
            self._handle_core_exception(e)

    async def create_session(self, user_id: str, request: SessionCreateRequest) -> dict:
        """Create a new chat session."""
        try:
            logger.debug(f"Creating chat session for user {user_id}")

            # Validate input
            if not user_id:
                raise ChatServiceValidationError("User ID is required")
            if not request.title:
                raise ChatServiceValidationError("Session title is required")

            # Adapt API request to core request
            core_request = ChatSessionCreateRequest(
                title=request.title,
                trip_id=getattr(request, "trip_id", None),
                metadata=getattr(request, "metadata", None),
            )

            result = await self.core_chat_service.create_session(
                user_id=user_id, session_data=core_request
            )

            logger.info(f"Chat session created: {result.id} for user {user_id}")

            # Convert core response to dict for API compatibility
            return {
                "id": result.id,
                "user_id": result.user_id,
                "title": result.title,
                "trip_id": result.trip_id,
                "created_at": result.created_at.isoformat(),
                "updated_at": result.updated_at.isoformat(),
                "metadata": result.metadata,
            }
        except (ChatServiceError, NotImplementedError):
            raise  # Re-raise our own exceptions
        except Exception as e:
            logger.error(f"Session creation failed for user {user_id}: {e}")
            self._handle_core_exception(e)

    async def list_sessions(self, user_id: str) -> List[dict]:
        """List chat sessions for user."""
        try:
            logger.debug(f"Listing sessions for user {user_id}")

            # Validate input
            if not user_id:
                raise ChatServiceValidationError("User ID is required")

            # Use correct core method name: get_user_sessions
            sessions = await self.core_chat_service.get_user_sessions(user_id=user_id)

            logger.debug(f"Found {len(sessions)} sessions for user {user_id}")

            # Convert core responses to dicts for API compatibility
            return [
                {
                    "id": session.id,
                    "user_id": session.user_id,
                    "title": session.title,
                    "trip_id": session.trip_id,
                    "created_at": session.created_at.isoformat(),
                    "updated_at": session.updated_at.isoformat(),
                    "message_count": session.message_count,
                    "last_message_at": session.last_message_at.isoformat()
                    if session.last_message_at
                    else None,
                    "metadata": session.metadata,
                }
                for session in sessions
            ]
        except ChatServiceError:
            raise  # Re-raise our own exceptions
        except Exception as e:
            logger.error(f"Session listing failed for user {user_id}: {e}")
            self._handle_core_exception(e)

    async def get_session(self, user_id: str, session_id: UUID) -> Optional[dict]:
        """Get a specific chat session."""
        try:
            logger.debug(f"Getting session {session_id} for user {user_id}")

            # Validate input
            if not user_id:
                raise ChatServiceValidationError("User ID is required")
            if not session_id:
                raise ChatServiceValidationError("Session ID is required")

            # Use correct core method signature: get_session(session_id, user_id)
            result = await self.core_chat_service.get_session(
                session_id=str(session_id), user_id=user_id
            )

            if result is None:
                logger.debug(f"Session {session_id} not found for user {user_id}")
                return None

            logger.debug(f"Session {session_id} retrieved for user {user_id}")

            # Convert core response to dict for API compatibility
            return {
                "id": result.id,
                "user_id": result.user_id,
                "title": result.title,
                "trip_id": result.trip_id,
                "created_at": result.created_at.isoformat(),
                "updated_at": result.updated_at.isoformat(),
                "metadata": result.metadata,
            }
        except ChatServiceError:
            raise  # Re-raise our own exceptions
        except Exception as e:
            logger.error(
                f"Session retrieval failed for session {session_id}, "
                f"user {user_id}: {e}"
            )
            self._handle_core_exception(e)

    async def get_messages(
        self, user_id: str, session_id: UUID, limit: int = 50
    ) -> List[dict]:
        """Get messages from a chat session."""
        try:
            logger.debug(
                f"Getting messages for session {session_id}, "
                f"user {user_id}, limit {limit}"
            )

            # Validate input
            if not user_id:
                raise ChatServiceValidationError("User ID is required")
            if not session_id:
                raise ChatServiceValidationError("Session ID is required")
            if limit < 1 or limit > 1000:
                raise ChatServiceValidationError("Limit must be between 1 and 1000")

            # Use correct core method signature
            messages = await self.core_chat_service.get_messages(
                session_id=str(session_id), user_id=user_id, limit=limit
            )

            logger.debug(f"Retrieved {len(messages)} messages for session {session_id}")

            # Convert core responses to dicts for API compatibility
            return [
                {
                    "id": message.id,
                    "session_id": message.session_id,
                    "role": message.role,
                    "content": message.content,
                    "created_at": message.created_at.isoformat(),
                    "metadata": message.metadata,
                    "tool_calls": message.tool_calls,
                }
                for message in messages
            ]
        except ChatServiceError:
            raise  # Re-raise our own exceptions
        except Exception as e:
            logger.error(
                f"Message retrieval failed for session {session_id}, "
                f"user {user_id}: {e}"
            )
            self._handle_core_exception(e)

    async def create_message(
        self, user_id: str, session_id: UUID, request: CreateMessageRequest
    ) -> dict:
        """Create a new message in a session."""
        try:
            logger.debug(f"Creating message in session {session_id} for user {user_id}")

            # Validate input
            if not user_id:
                raise ChatServiceValidationError("User ID is required")
            if not session_id:
                raise ChatServiceValidationError("Session ID is required")
            if not request.content or not request.content.strip():
                raise ChatServiceValidationError("Message content is required")
            if not request.role:
                raise ChatServiceValidationError("Message role is required")

            # Adapt API request to core request
            core_request = CoreMessageCreateRequest(
                role=request.role,
                content=request.content,
                metadata=getattr(request, "metadata", None),
                tool_calls=getattr(request, "tool_calls", None),
            )

            # Use correct core method name: add_message with proper signature
            result = await self.core_chat_service.add_message(
                session_id=str(session_id), user_id=user_id, message_data=core_request
            )

            logger.info(f"Message created: {result.id} in session {session_id}")

            # Convert core response to dict for API compatibility
            return {
                "id": result.id,
                "session_id": result.session_id,
                "role": result.role,
                "content": result.content,
                "created_at": result.created_at.isoformat(),
                "metadata": result.metadata,
                "tool_calls": result.tool_calls,
            }
        except ChatServiceError:
            raise  # Re-raise our own exceptions
        except Exception as e:
            logger.error(
                f"Message creation failed for session {session_id}, user {user_id}: {e}"
            )
            self._handle_core_exception(e)

    async def delete_session(self, user_id: str, session_id: UUID) -> bool:
        """Delete a chat session."""
        try:
            logger.debug(f"Deleting session {session_id} for user {user_id}")

            # Validate input
            if not user_id:
                raise ChatServiceValidationError("User ID is required")
            if not session_id:
                raise ChatServiceValidationError("Session ID is required")

            # Core service uses end_session instead of delete_session
            result = await self.core_chat_service.end_session(
                session_id=str(session_id), user_id=user_id
            )

            logger.info(
                f"Session {'deleted' if result else 'not found'}: "
                f"{session_id} for user {user_id}"
            )
            return result
        except ChatServiceError:
            raise  # Re-raise our own exceptions
        except Exception as e:
            logger.error(
                f"Session deletion failed for session {session_id}, user {user_id}: {e}"
            )
            self._handle_core_exception(e)


async def get_core_chat_service() -> CoreChatService:
    """Get core chat service instance."""
    # Simplified for now - in real implementation this would have proper DI
    return CoreChatService()


async def get_chat_service() -> ChatService:
    """Get ChatService instance with dependencies."""
    core_chat = await get_core_chat_service()
    return ChatService(core_chat)
