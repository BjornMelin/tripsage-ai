"""
Chat service for managing chat sessions and messages.

This service consolidates chat-related business logic including session management,
message persistence, tool call tracking, and rate limiting. It provides clean
integration with the AI agents and maintains conversation context.
"""

import html
import logging
import re
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import Field, field_validator

from tripsage_core.config import get_settings
from tripsage_core.exceptions import (
    CoreAuthorizationError as PermissionError,
)
from tripsage_core.exceptions import (
    CoreResourceNotFoundError as NotFoundError,
)
from tripsage_core.exceptions import (
    CoreValidationError as ValidationError,
)
from tripsage_core.models.base_core_model import TripSageModel

logger = logging.getLogger(__name__)


class MessageRole(str):
    """Message role constants."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class ToolCallStatus(str):
    """Tool call status constants."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ChatSessionCreateRequest(TripSageModel):
    """Request model for chat session creation."""

    title: Optional[str] = Field(None, max_length=200, description="Session title")
    trip_id: Optional[str] = Field(None, description="Associated trip ID")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Session metadata")


class ChatSessionResponse(TripSageModel):
    """Response model for chat session."""

    id: str = Field(..., description="Session ID")
    user_id: str = Field(..., description="User ID")
    title: Optional[str] = Field(None, description="Session title")
    trip_id: Optional[str] = Field(None, description="Associated trip ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    ended_at: Optional[datetime] = Field(None, description="End timestamp")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Session metadata"
    )
    message_count: int = Field(default=0, description="Number of messages")
    last_message_at: Optional[datetime] = Field(
        None, description="Last message timestamp"
    )


class MessageCreateRequest(TripSageModel):
    """Request model for message creation."""

    role: str = Field(..., description="Message role")
    content: str = Field(..., min_length=1, description="Message content")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Message metadata")
    tool_calls: Optional[List[Dict[str, Any]]] = Field(
        None, description="Tool calls data"
    )

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        """Validate message role."""
        valid_roles = {
            MessageRole.USER,
            MessageRole.ASSISTANT,
            MessageRole.SYSTEM,
            MessageRole.TOOL,
        }
        if v not in valid_roles:
            raise ValueError(f"Role must be one of: {', '.join(valid_roles)}")
        return v


class MessageResponse(TripSageModel):
    """Response model for chat message."""

    id: str = Field(..., description="Message ID")
    session_id: str = Field(..., description="Session ID")
    role: str = Field(..., description="Message role")
    content: str = Field(..., description="Message content")
    created_at: datetime = Field(..., description="Creation timestamp")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Message metadata"
    )
    tool_calls: List[Dict[str, Any]] = Field(
        default_factory=list, description="Tool calls"
    )
    estimated_tokens: Optional[int] = Field(None, description="Estimated token count")


class ToolCallResponse(TripSageModel):
    """Response model for tool call."""

    id: str = Field(..., description="Tool call ID")
    message_id: str = Field(..., description="Message ID")
    tool_id: str = Field(..., description="Tool identifier")
    tool_name: str = Field(..., description="Tool name")
    arguments: Dict[str, Any] = Field(..., description="Tool arguments")
    result: Optional[Dict[str, Any]] = Field(None, description="Tool result")
    status: str = Field(..., description="Tool call status")
    created_at: datetime = Field(..., description="Creation timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")
    error_message: Optional[str] = Field(None, description="Error message if failed")


class RecentMessagesRequest(TripSageModel):
    """Request model for recent messages retrieval."""

    limit: int = Field(
        default=10, ge=1, le=100, description="Maximum number of messages"
    )
    max_tokens: int = Field(default=8000, ge=100, description="Maximum total tokens")
    offset: int = Field(default=0, ge=0, description="Number of messages to skip")


class RecentMessagesResponse(TripSageModel):
    """Response model for recent messages."""

    messages: List[MessageResponse] = Field(
        ..., description="Messages within token limit"
    )
    total_tokens: int = Field(..., description="Total estimated tokens")
    truncated: bool = Field(..., description="Whether results were truncated")


class RateLimiter:
    """Simple in-memory rate limiter for message creation."""

    def __init__(self, max_messages: int = 20, window_seconds: int = 60):
        """
        Initialize rate limiter.

        Args:
            max_messages: Maximum messages allowed per window
            window_seconds: Time window in seconds
        """
        self.max_messages = max_messages
        self.window_seconds = window_seconds
        self.user_windows: Dict[str, List[float]] = {}

    def is_allowed(self, user_id: str, count: int = 1) -> bool:
        """
        Check if user is allowed to send messages.

        Args:
            user_id: User ID to check
            count: Number of messages to check

        Returns:
            True if allowed, False if rate limited
        """
        now = time.time()
        window_start = now - self.window_seconds

        # Get user's message timestamps
        if user_id not in self.user_windows:
            self.user_windows[user_id] = []

        # Remove old timestamps
        self.user_windows[user_id] = [
            ts for ts in self.user_windows[user_id] if ts > window_start
        ]

        # Check if under limit
        if len(self.user_windows[user_id]) + count > self.max_messages:
            return False

        # Add current timestamps
        for _ in range(count):
            self.user_windows[user_id].append(now)

        return True

    def reset_user(self, user_id: str) -> None:
        """Reset rate limit for a user."""
        if user_id in self.user_windows:
            del self.user_windows[user_id]


class ChatService:
    """
    Comprehensive chat service for session and message management.

    This service handles:
    - Chat session lifecycle management
    - Message creation and retrieval
    - Tool call tracking and status
    - Rate limiting and security
    - Context window management
    - Message sanitization and validation
    """

    def __init__(
        self,
        database_service=None,
        rate_limiter: Optional[RateLimiter] = None,
        chars_per_token: int = 4,
    ):
        """
        Initialize the chat service.

        Args:
            database_service: Database service for persistence
            rate_limiter: Rate limiter instance
            chars_per_token: Characters per token for estimation
        """
        # Import here to avoid circular imports
        if database_service is None:
            from tripsage_core.services.infrastructure import get_database_service

            database_service = get_database_service()

        self.db = database_service
        self.rate_limiter = rate_limiter or RateLimiter()
        self.chars_per_token = chars_per_token
        self._retry_count = 3
        self._retry_delay = 0.1

    async def create_session(
        self, user_id: str, session_data: ChatSessionCreateRequest
    ) -> ChatSessionResponse:
        """
        Create a new chat session.

        Args:
            user_id: User ID
            session_data: Session creation data

        Returns:
            Created chat session
        """
        try:
            session_id = str(uuid4())

            # Prepare session data for database
            now = datetime.now(timezone.utc)
            db_session_data = {
                "id": session_id,
                "user_id": user_id,
                "title": session_data.title,
                "trip_id": session_data.trip_id,
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
                "metadata": self._validate_metadata(session_data.metadata),
            }

            # Store in database
            result = await self.db.create_chat_session(db_session_data)

            logger.info(
                "Chat session created",
                extra={"session_id": session_id, "user_id": user_id},
            )

            return ChatSessionResponse(
                id=result["id"],
                user_id=result["user_id"],
                title=result.get("title"),
                trip_id=result.get("trip_id"),
                created_at=datetime.fromisoformat(result["created_at"]),
                updated_at=datetime.fromisoformat(result["updated_at"]),
                ended_at=datetime.fromisoformat(result["ended_at"])
                if result.get("ended_at")
                else None,
                metadata=result.get("metadata", {}),
            )

        except Exception as e:
            logger.error(
                "Failed to create chat session",
                extra={"user_id": user_id, "error": str(e)},
            )
            raise

    # This method is replaced by _get_session_internal to avoid router conflicts

    async def get_user_sessions(
        self, user_id: str, limit: int = 10, include_ended: bool = False
    ) -> List[ChatSessionResponse]:
        """
        Get chat sessions for a user.

        Args:
            user_id: User ID
            limit: Maximum number of sessions
            include_ended: Whether to include ended sessions

        Returns:
            List of user's chat sessions
        """
        try:
            results = await self.db.get_user_chat_sessions(
                user_id, limit, include_ended
            )

            sessions = []
            for result in results:
                sessions.append(
                    ChatSessionResponse(
                        id=result["id"],
                        user_id=result["user_id"],
                        title=result.get("title"),
                        trip_id=result.get("trip_id"),
                        created_at=datetime.fromisoformat(result["created_at"]),
                        updated_at=datetime.fromisoformat(result["updated_at"]),
                        ended_at=datetime.fromisoformat(result["ended_at"])
                        if result.get("ended_at")
                        else None,
                        metadata=result.get("metadata", {}),
                        message_count=result.get("message_count", 0),
                        last_message_at=datetime.fromisoformat(
                            result["last_message_at"]
                        )
                        if result.get("last_message_at")
                        else None,
                    )
                )

            return sessions

        except Exception as e:
            logger.error(
                "Failed to get user sessions",
                extra={"user_id": user_id, "error": str(e)},
            )
            return []

    async def add_message(
        self, session_id: str, user_id: str, message_data: MessageCreateRequest
    ) -> MessageResponse:
        """
        Add message to chat session.

        Args:
            session_id: Session ID
            user_id: User ID
            message_data: Message creation data

        Returns:
            Created message

        Raises:
            ValidationError: If rate limit exceeded or validation fails
            NotFoundError: If session not found
            PermissionError: If user doesn't have access
        """
        try:
            # Check rate limit for user messages
            if message_data.role == MessageRole.USER:
                if not self.rate_limiter.is_allowed(user_id):
                    raise ValidationError(
                        f"Rate limit exceeded. Max {self.rate_limiter.max_messages} "
                        f"messages per {self.rate_limiter.window_seconds} seconds."
                    )

            # Verify session access
            session = await self._get_session_internal(session_id, user_id)
            if not session:
                raise NotFoundError("Chat session not found")

            # Sanitize content
            content = self._sanitize_content(message_data.content)

            # Generate message ID
            message_id = str(uuid4())

            # Prepare message data for database
            now = datetime.now(timezone.utc)
            db_message_data = {
                "id": message_id,
                "session_id": session_id,
                "role": message_data.role,
                "content": content,
                "created_at": now.isoformat(),
                "metadata": self._validate_metadata(message_data.metadata),
            }

            # Store message in database
            result = await self.db.create_chat_message(db_message_data)

            # Handle tool calls if present
            tool_calls = []
            if message_data.tool_calls:
                for tool_call_data in message_data.tool_calls:
                    tool_call = await self._create_tool_call(message_id, tool_call_data)
                    tool_calls.append(tool_call.model_dump())

            # Update session timestamp
            await self.db.update_session_timestamp(session_id)

            logger.info(
                "Message added to session",
                extra={
                    "message_id": message_id,
                    "session_id": session_id,
                    "user_id": user_id,
                    "role": message_data.role,
                },
            )

            return MessageResponse(
                id=result["id"],
                session_id=result["session_id"],
                role=result["role"],
                content=result["content"],
                created_at=datetime.fromisoformat(result["created_at"]),
                metadata=result.get("metadata", {}),
                tool_calls=tool_calls,
                estimated_tokens=self._estimate_tokens(content),
            )

        except (ValidationError, NotFoundError, PermissionError):
            raise
        except Exception as e:
            logger.error(
                "Failed to add message",
                extra={"session_id": session_id, "user_id": user_id, "error": str(e)},
            )
            raise

    # This method is replaced by _get_messages_internal to avoid router conflicts

    async def get_recent_messages(
        self, session_id: str, user_id: str, request: RecentMessagesRequest
    ) -> RecentMessagesResponse:
        """
        Get recent messages within token limit.

        Args:
            session_id: Session ID
            user_id: User ID (for access control)
            request: Recent messages request

        Returns:
            Recent messages response with token information
        """
        try:
            # Verify session access
            session = await self._get_session_internal(session_id, user_id)
            if not session:
                return RecentMessagesResponse(
                    messages=[], total_tokens=0, truncated=False
                )

            # Get messages with token estimation
            results = await self.db.get_recent_messages_with_tokens(
                session_id,
                request.limit,
                request.max_tokens,
                request.offset,
                self.chars_per_token,
            )

            messages = []
            total_tokens = 0

            for result in results:
                # Get tool calls for this message
                tool_calls = await self.db.get_message_tool_calls(result["id"])

                message = MessageResponse(
                    id=result["id"],
                    session_id=result["session_id"],
                    role=result["role"],
                    content=result["content"],
                    created_at=datetime.fromisoformat(result["created_at"]),
                    metadata=result.get("metadata", {}),
                    tool_calls=[tc for tc in tool_calls],
                    estimated_tokens=result.get(
                        "estimated_tokens", self._estimate_tokens(result["content"])
                    ),
                )

                messages.append(message)
                total_tokens += message.estimated_tokens or 0

            # Check if truncation occurred based on token limits
            # The database should handle token limiting, so if we get results,
            # we assume no truncation unless the database indicates otherwise
            # For now, assume no truncation if we got any results within token limit
            truncated = False
            if messages and total_tokens >= request.max_tokens:
                truncated = True

            return RecentMessagesResponse(
                messages=messages, total_tokens=total_tokens, truncated=truncated
            )

        except Exception as e:
            logger.error(
                "Failed to get recent messages",
                extra={"session_id": session_id, "user_id": user_id, "error": str(e)},
            )
            return RecentMessagesResponse(messages=[], total_tokens=0, truncated=False)

    async def end_session(self, session_id: str, user_id: str) -> bool:
        """
        End a chat session.

        Args:
            session_id: Session ID
            user_id: User ID (for access control)

        Returns:
            True if session ended successfully

        Raises:
            NotFoundError: If session not found
            ValidationError: If session already ended
        """
        try:
            # Verify session access
            session = await self._get_session_internal(session_id, user_id)
            if not session:
                raise NotFoundError("Chat session not found")

            # Check if session is already ended
            if session.ended_at is not None:
                raise ValidationError("Session already ended")

            # End the session
            success = await self.db.end_chat_session(session_id)

            if success:
                logger.info(
                    "Chat session ended",
                    extra={"session_id": session_id, "user_id": user_id},
                )

            return success

        except (NotFoundError, ValidationError):
            raise
        except Exception as e:
            logger.error(
                "Failed to end session",
                extra={"session_id": session_id, "user_id": user_id, "error": str(e)},
            )
            return False

    async def update_tool_call_status(
        self,
        tool_call_id: str,
        status: str,
        result: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Update tool call status and result.

        Args:
            tool_call_id: Tool call ID
            status: New status
            result: Tool result (if successful)
            error_message: Error message (if failed)

        Returns:
            Updated tool call data if successful, None if failed
        """
        try:
            completed_at = None
            if status in {ToolCallStatus.COMPLETED, ToolCallStatus.FAILED}:
                completed_at = datetime.now(timezone.utc)

            update_data = {
                "status": status,
                "result": result,
                "error_message": error_message,
                "completed_at": completed_at.isoformat() if completed_at else None,
            }

            updated_tool_call = await self.db.update_tool_call(
                tool_call_id, update_data
            )

            if updated_tool_call:
                logger.info(
                    "Tool call status updated",
                    extra={
                        "tool_call_id": tool_call_id,
                        "status": status,
                        "success": True,
                    },
                )
                return updated_tool_call
            else:
                return None

        except Exception as e:
            logger.error(
                "Failed to update tool call status",
                extra={"tool_call_id": tool_call_id, "status": status, "error": str(e)},
            )
            return None

    def _sanitize_content(self, content: str) -> str:
        """
        Sanitize message content to prevent XSS and injection attacks.

        Args:
            content: Raw message content

        Returns:
            Sanitized content
        """
        # HTML escape special characters
        content = html.escape(content)

        # Remove null bytes
        content = content.replace("\x00", "")

        # Normalize whitespace - replace multiple whitespace chars with single space
        content = re.sub(r"\s+", " ", content)

        return content.strip()

    def _validate_metadata(self, metadata: Any) -> Dict[str, Any]:
        """
        Validate and normalize metadata.

        Args:
            metadata: Raw metadata

        Returns:
            Validated metadata dictionary
        """
        if metadata is None:
            return {}

        if not isinstance(metadata, dict):
            raise ValidationError("Metadata must be a dictionary")

        # Remove None values and ensure all keys are strings
        cleaned = {}
        for key, value in metadata.items():
            if not isinstance(key, str):
                raise ValidationError("Metadata keys must be strings")
            if value is not None:
                cleaned[key] = value

        return cleaned

    def _estimate_tokens(self, content: str) -> int:
        """
        Estimate token count for content.

        Args:
            content: Text content

        Returns:
            Estimated token count
        """
        if not content:
            return 0
        return max(1, len(content) // self.chars_per_token)

    async def add_tool_call(
        self, message_id: str, tool_call_data: Dict[str, Any]
    ) -> ToolCallResponse:
        """
        Create a tool call record.

        Args:
            message_id: Message ID
            tool_call_data: Tool call data

        Returns:
            Created tool call
        """
        tool_call_id = str(uuid4())

        now = datetime.now(timezone.utc)
        db_tool_call_data = {
            "id": tool_call_id,
            "message_id": message_id,
            "tool_id": tool_call_data.get("tool_id", tool_call_data.get("id", "")),
            "tool_name": tool_call_data.get(
                "tool_name", tool_call_data.get("function", {}).get("name", "")
            ),
            "arguments": tool_call_data.get(
                "arguments", tool_call_data.get("function", {}).get("arguments", {})
            ),
            "status": ToolCallStatus.PENDING,
            "created_at": now.isoformat(),
        }

        result = await self.db.create_tool_call(db_tool_call_data)

        return ToolCallResponse(
            id=result["id"],
            message_id=result["message_id"],
            tool_id=result["tool_id"],
            tool_name=result["tool_name"],
            arguments=result["arguments"],
            status=result["status"],
            created_at=datetime.fromisoformat(result["created_at"]),
        )

    # ===== Router Compatibility Methods =====
    # These methods provide compatibility with the router's expected interface

    async def chat_completion(self, user_id: str, request) -> Dict[str, Any]:
        """
        Handle chat completion requests (main chat endpoint).

        This method provides AI chat functionality by processing messages,
        managing sessions, and returning AI responses.

        Args:
            user_id: User ID
            request: Chat request containing messages and options

        Returns:
            Chat response with AI assistant message
        """
        try:
            # Generate or use existing session ID
            session_id = str(request.session_id) if request.session_id else str(uuid4())

            logger.info(
                "Chat completion request",
                extra={
                    "user_id": user_id,
                    "session_id": session_id,
                    "message_count": len(request.messages),
                },
            )

            # Initialize ChatOpenAI with settings
            settings = get_settings()
            model_name = getattr(request, "model", "gpt-4")
            temperature = getattr(request, "temperature", 0.7)
            max_tokens = getattr(request, "max_tokens", 4096)

            llm = ChatOpenAI(
                model=model_name,
                temperature=temperature,
                max_tokens=max_tokens,
                api_key=settings.openai_api_key.get_secret_value(),
            )

            # Convert request messages to LangChain format
            langchain_messages = []

            # Add system message for travel assistant context
            system_prompt = (
                "You are TripSage AI, an expert travel planning assistant. "
                "You help users plan trips, find flights and accommodations, "
                "create itineraries, and provide destination recommendations. "
                "Be helpful, informative, and personalized in your responses."
            )
            langchain_messages.append(SystemMessage(content=system_prompt))

            # Process user messages
            for msg in request.messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")

                if role == "user":
                    langchain_messages.append(HumanMessage(content=content))
                elif role == "assistant":
                    langchain_messages.append(AIMessage(content=content))
                elif role == "system":
                    langchain_messages.append(SystemMessage(content=content))

            # Get AI response
            response = await llm.ainvoke(langchain_messages)

            # Extract token usage information
            usage_metadata = getattr(response, "response_metadata", {})
            token_usage = usage_metadata.get("token_usage", {})
            finish_reason = usage_metadata.get("finish_reason", "stop")

            # Store the conversation in the session if we have a session ID
            if session_id and hasattr(self, "db"):
                try:
                    # Create session if it doesn't exist
                    session = await self._get_session_internal(session_id, user_id)
                    if not session:
                        session_data = ChatSessionCreateRequest(
                            title="Chat with TripSage AI",
                            metadata={"model": model_name},
                        )
                        await self.create_session(user_id, session_data)

                    # Add user message to session
                    if request.messages:
                        last_user_msg = request.messages[-1]
                        if last_user_msg.get("role") == "user":
                            user_msg_data = MessageCreateRequest(
                                role="user",
                                content=last_user_msg.get("content", ""),
                            )
                            await self.add_message(session_id, user_id, user_msg_data)

                    # Add AI response to session
                    ai_msg_data = MessageCreateRequest(
                        role="assistant",
                        content=response.content,
                        metadata={"model": model_name, "usage": token_usage},
                    )
                    await self.add_message(session_id, user_id, ai_msg_data)

                except Exception as e:
                    logger.warning(
                        "Failed to store chat in session",
                        extra={"session_id": session_id, "error": str(e)},
                    )

            # Return formatted response
            return {
                "content": response.content,
                "session_id": session_id,
                "model": model_name,
                "usage": {
                    "prompt_tokens": token_usage.get("prompt_tokens", 0),
                    "completion_tokens": token_usage.get("completion_tokens", 0),
                    "total_tokens": token_usage.get("total_tokens", 0),
                },
                "finish_reason": finish_reason,
            }

        except Exception as e:
            logger.error(
                "Chat completion failed",
                extra={"user_id": user_id, "error": str(e)},
            )
            raise

    async def list_sessions(self, user_id: str) -> List[Dict[str, Any]]:
        """
        List chat sessions for a user (router compatibility method).

        Args:
            user_id: User ID

        Returns:
            List of user's chat sessions
        """
        sessions = await self.get_user_sessions(user_id)
        return [session.model_dump() for session in sessions]

    async def create_message(
        self, user_id: str, session_id: str, message_request
    ) -> Dict[str, Any]:
        """
        Create a message in a session (router compatibility method).

        Args:
            user_id: User ID
            session_id: Session ID
            message_request: Message creation request

        Returns:
            Created message data
        """
        # Convert the API request to service request
        service_request = MessageCreateRequest(
            role=message_request.role,
            content=message_request.content,
        )

        message = await self.add_message(session_id, user_id, service_request)
        return message.model_dump()

    async def delete_session(self, user_id: str, session_id: str) -> bool:
        """
        Delete a chat session (router compatibility method).

        Args:
            user_id: User ID
            session_id: Session ID

        Returns:
            True if session was deleted successfully
        """
        return await self.end_session(session_id, user_id)

    # Rename original methods to avoid conflicts with router compatibility methods
    async def _get_session_internal(
        self, session_id: str, user_id: str
    ) -> Optional[ChatSessionResponse]:
        """Internal get_session method with original signature."""
        try:
            result = await self.db.get_chat_session(session_id, user_id)
            if not result:
                return None

            # Get message statistics
            stats = await self.db.get_session_stats(session_id)

            return ChatSessionResponse(
                id=result["id"],
                user_id=result["user_id"],
                title=result.get("title"),
                trip_id=result.get("trip_id"),
                created_at=datetime.fromisoformat(result["created_at"]),
                updated_at=datetime.fromisoformat(result["updated_at"]),
                ended_at=datetime.fromisoformat(result["ended_at"])
                if result.get("ended_at")
                else None,
                metadata=result.get("metadata", {}),
                message_count=stats.get("message_count", 0),
                last_message_at=datetime.fromisoformat(stats["last_message_at"])
                if stats.get("last_message_at")
                else None,
            )

        except Exception as e:
            logger.error(
                "Failed to get chat session",
                extra={"session_id": session_id, "user_id": user_id, "error": str(e)},
            )
            return None

    async def _get_messages_internal(
        self,
        session_id: str,
        user_id: str,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> List[MessageResponse]:
        """Internal get_messages method with original signature."""
        try:
            # Verify session access
            session = await self._get_session_internal(session_id, user_id)
            if not session:
                return []

            results = await self.db.get_session_messages(session_id, limit, offset)

            messages = []
            for result in results:
                # Get tool calls for this message
                tool_calls = await self.db.get_message_tool_calls(result["id"])

                messages.append(
                    MessageResponse(
                        id=result["id"],
                        session_id=result["session_id"],
                        role=result["role"],
                        content=result["content"],
                        created_at=datetime.fromisoformat(result["created_at"]),
                        metadata=result.get("metadata", {}),
                        tool_calls=[tc for tc in tool_calls],
                        estimated_tokens=self._estimate_tokens(result["content"]),
                    )
                )

            return messages

        except Exception as e:
            logger.error(
                "Failed to get messages",
                extra={"session_id": session_id, "user_id": user_id, "error": str(e)},
            )
            return []

    # Router-compatible methods with simplified signatures
    async def get_session(
        self, user_id: str, session_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get chat session (router-compatible method).

        Args:
            user_id: User ID (router parameter order)
            session_id: Session ID (router parameter order)

        Returns:
            Chat session data as dictionary or None if not found
        """
        session = await self._get_session_internal(session_id, user_id)
        return session.model_dump() if session else None

    async def get_messages(
        self, user_id: str, session_id: str, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get messages (router-compatible method).

        Args:
            user_id: User ID (router parameter order)
            session_id: Session ID (router parameter order)
            limit: Maximum number of messages

        Returns:
            List of messages as dictionaries
        """
        messages = await self._get_messages_internal(session_id, user_id, limit, 0)
        return [message.model_dump() for message in messages]


# Dependency function for FastAPI
async def get_chat_service() -> ChatService:
    """
    Get chat service instance for dependency injection.

    Returns:
        ChatService instance
    """
    return ChatService()
