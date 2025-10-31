# pylint: disable=too-many-lines
"""Chat service for managing chat sessions and messages.

This service consolidates chat-related business logic including session management,
message persistence, tool call tracking, and rate limiting. It provides clean
integration with the AI agents and maintains conversation context.
"""

import html
import logging
import re
import time
from datetime import UTC, datetime
from typing import Any, Protocol, cast
from uuid import uuid4

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import Field, field_validator

from tripsage_core.config import get_settings
from tripsage_core.exceptions import (
    RECOVERABLE_ERRORS,
    CoreResourceNotFoundError as NotFoundError,
    CoreValidationError as ValidationError,
)
from tripsage_core.models.base_core_model import TripSageModel
from tripsage_core.observability.otel import record_histogram, trace_span
from tripsage_core.services.infrastructure.database_operations_mixin import (
    DatabaseOperationsMixin,
)
from tripsage_core.services.infrastructure.error_handling_mixin import (
    ErrorHandlingMixin,
)
from tripsage_core.services.infrastructure.logging_mixin import LoggingMixin
from tripsage_core.services.infrastructure.validation_mixin import ValidationMixin
from tripsage_core.utils.error_handling_utils import tripsage_safe_execute


logger = logging.getLogger(__name__)


def _empty_metadata() -> dict[str, Any]:
    """Typed empty metadata factory for pydantic defaults."""
    return {}


def _empty_tool_calls() -> list[dict[str, Any]]:
    """Typed empty tool-calls factory for pydantic defaults."""
    return []


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

    title: str | None = Field(None, max_length=200, description="Session title")
    trip_id: str | None = Field(None, description="Associated trip ID")
    metadata: dict[str, Any] | None = Field(None, description="Session metadata")


class ChatSessionResponse(TripSageModel):
    """Response model for chat session."""

    id: str = Field(..., description="Session ID")
    user_id: str = Field(..., description="User ID")
    title: str | None = Field(None, description="Session title")
    trip_id: str | None = Field(None, description="Associated trip ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    ended_at: datetime | None = Field(None, description="End timestamp")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Session metadata"
    )
    message_count: int = Field(default=0, description="Number of messages")
    last_message_at: datetime | None = Field(None, description="Last message timestamp")


class MessageCreateRequest(TripSageModel):
    """Request model for message creation."""

    role: str = Field(..., description="Message role")
    content: str = Field(..., min_length=1, description="Message content")
    metadata: dict[str, Any] | None = Field(None, description="Message metadata")
    tool_calls: list[dict[str, Any]] | None = Field(None, description="Tool calls data")

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
    metadata: dict[str, Any] = Field(
        default_factory=_empty_metadata, description="Message metadata"
    )
    tool_calls: list[dict[str, Any]] = Field(
        default_factory=_empty_tool_calls, description="Tool calls"
    )
    estimated_tokens: int | None = Field(None, description="Estimated token count")


class ToolCallResponse(TripSageModel):
    """Response model for tool call."""

    id: str = Field(..., description="Tool call ID")
    message_id: str = Field(..., description="Message ID")
    tool_id: str = Field(..., description="Tool identifier")
    tool_name: str = Field(..., description="Tool name")
    arguments: dict[str, Any] = Field(..., description="Tool arguments")
    result: dict[str, Any] | None = Field(None, description="Tool result")
    status: str = Field(..., description="Tool call status")
    created_at: datetime = Field(..., description="Creation timestamp")
    completed_at: datetime | None = Field(None, description="Completion timestamp")
    error_message: str | None = Field(None, description="Error message if failed")


class RecentMessagesRequest(TripSageModel):
    """Request model for recent messages retrieval."""

    limit: int = Field(
        default=10, ge=1, le=100, description="Maximum number of messages"
    )
    max_tokens: int = Field(default=8000, ge=100, description="Maximum total tokens")
    offset: int = Field(default=0, ge=0, description="Number of messages to skip")


class RecentMessagesResponse(TripSageModel):
    """Response model for recent messages."""

    messages: list[MessageResponse] = Field(
        ..., description="Messages within token limit"
    )
    total_tokens: int = Field(..., description="Total estimated tokens")
    truncated: bool = Field(..., description="Whether results were truncated")


class RateLimiter:
    """Simple in-memory rate limiter for message creation."""

    def __init__(self, max_messages: int = 20, window_seconds: int = 60):
        """Initialize rate limiter.

        Args:
            max_messages: Maximum messages allowed per window
            window_seconds: Time window in seconds
        """
        self.max_messages = max_messages
        self.window_seconds = window_seconds
        self.user_windows: dict[str, list[float]] = {}

    def is_allowed(self, user_id: str, count: int = 1) -> bool:
        """Check if user is allowed to send messages.

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


class _ChatDbProtocol(Protocol):
    """Minimal database surface used by ChatService."""

    async def insert(
        self, table: str, data: dict[str, Any], user_id: str | None = None
    ) -> list[dict[str, Any]]:
        """Insert data into a table."""
        ...

    async def get_user_chat_sessions(
        self, user_id: str, limit: int = 10, include_ended: bool = False
    ) -> list[dict[str, Any]]:
        """Get chat sessions for a user."""
        ...

    async def get_chat_session(
        self, session_id: str, user_id: str
    ) -> dict[str, Any] | None:
        """Get a chat session by ID."""
        ...

    async def update_session_timestamp(self, session_id: str) -> bool:
        """Update the timestamp of a chat session."""
        ...

    async def get_session_messages(
        self, session_id: str, limit: int | None = None, offset: int = 0
    ) -> list[dict[str, Any]]:
        """Get messages for a chat session."""
        ...

    async def get_message_tool_calls(self, message_id: str) -> list[dict[str, Any]]:
        """Get tool calls for a message."""
        ...

    async def create_tool_call(self, tool_call_data: dict[str, Any]) -> dict[str, Any]:
        """Create a tool call by data."""
        ...

    async def update_tool_call(
        self, tool_call_id: str, update_data: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Update a tool call by ID."""
        ...

    async def end_chat_session(self, session_id: str) -> bool:
        """End a chat session."""
        ...


class ChatService(
    DatabaseOperationsMixin, ValidationMixin, LoggingMixin, ErrorHandlingMixin
):
    """Comprehensive chat service for session and message management.

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
        database_service: _ChatDbProtocol,
        rate_limiter: RateLimiter | None = None,
        chars_per_token: int = 4,
    ):
        """Initialize the chat service.

        Args:
            database_service: Database service for persistence
            rate_limiter: Rate limiter instance
            chars_per_token: Characters per token for estimation
        """
        # DatabaseService is injected by the FastAPI dependency factory.
        self._db: _ChatDbProtocol = database_service
        self.rate_limiter = rate_limiter or RateLimiter()
        self.chars_per_token = chars_per_token
        self._retry_count = 3
        self._retry_delay = 0.1

    @property
    def db(self) -> _ChatDbProtocol:  # type: ignore[override]
        """Database accessor used by service and mixins."""
        return self._db

    @tripsage_safe_execute()
    @trace_span(name="svc.chat.sessions.create")
    @record_histogram("svc.op.duration", unit="s")
    async def create_session(
        self, user_id: str, session_data: ChatSessionCreateRequest
    ) -> ChatSessionResponse:
        """Create a new chat session.

        Args:
            user_id: User ID
            session_data: Session creation data

        Returns:
            Created chat session
        """
        try:
            # Validate user ID
            self._validate_user_id(user_id)

            session_id = str(uuid4())

            # Prepare session data for database
            now = datetime.now(UTC)
            db_session_data = {
                "id": session_id,
                "user_id": user_id,
                "title": session_data.title,
                "trip_id": session_data.trip_id,
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
                "metadata": self._validate_metadata(session_data.metadata),
            }

            # Store in database (final-only, no legacy helpers)
            rows = await self.db.insert("chat_sessions", db_session_data, user_id)
            result: dict[str, Any] = rows[0] if rows else db_session_data

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
                message_count=result.get("message_count", 0),
                last_message_at=datetime.fromisoformat(result["last_message_at"])
                if result.get("last_message_at")
                else None,
            )

        except RECOVERABLE_ERRORS as error:
            logger.exception(
                "Failed to create chat session",
                extra={"user_id": user_id, "error": str(error)},
            )
            raise

    # This method is replaced by _get_session_internal to avoid router conflicts

    @tripsage_safe_execute()
    @trace_span(name="svc.chat.sessions.list")
    @record_histogram("svc.op.duration", unit="s")
    async def get_user_sessions(
        self, user_id: str, limit: int = 10, include_ended: bool = False
    ) -> list[ChatSessionResponse]:
        """Get chat sessions for a user.

        Args:
            user_id: User ID
            limit: Maximum number of sessions
            include_ended: Whether to include ended sessions

        Returns:
            List of user's chat sessions
        """
        try:
            results = await self.db.get_user_chat_sessions(
                user_id, limit=limit, include_ended=include_ended
            )

            return [
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
                    last_message_at=datetime.fromisoformat(result["last_message_at"])
                    if result.get("last_message_at")
                    else None,
                )
                for result in results
            ]

        except RECOVERABLE_ERRORS as error:
            logger.exception(
                "Failed to get user sessions",
                extra={"user_id": user_id, "error": str(error)},
            )
            return []

    @tripsage_safe_execute()
    @trace_span(name="svc.chat.messages.create")
    @record_histogram("svc.op.duration", unit="s")
    async def add_message(
        self, session_id: str, user_id: str, message_data: MessageCreateRequest
    ) -> MessageResponse:
        """Add message to chat session.

        Args:
            session_id: Session ID
            user_id: User ID
            message_data: Message creation data

        Returns:
            Created message

        Raises:
            ValidationError: If rate limit exceeded or validation fails
            NotFoundError: If session not found
            AuthPermissionError: If user doesn't have access
        """
        try:
            # Check rate limit for user messages
            if (
                message_data.role == MessageRole.USER
                and not self.rate_limiter.is_allowed(user_id)
            ):
                raise ValidationError(
                    f"Rate limit exceeded. Max {self.rate_limiter.max_messages} "
                    f"messages per {self.rate_limiter.window_seconds} seconds.",
                )

            # Verify session access
            session = await self.get_session(session_id, user_id)
            if not session:
                raise NotFoundError("Chat session not found")

            # Sanitize content
            content = self._sanitize_content(message_data.content)

            # Generate message ID
            message_id = str(uuid4())

            # Prepare message data for database
            now = datetime.now(UTC)
            db_message_data = {
                "id": message_id,
                "session_id": session_id,
                "role": message_data.role,
                "content": content,
                "created_at": now.isoformat(),
                "metadata": self._validate_metadata(message_data.metadata),
            }

            # Store message in database (final API)
            rows = await self.db.insert("chat_messages", db_message_data, user_id)
            result: dict[str, Any] = rows[0] if rows else db_message_data

            # Handle tool calls if present
            tool_calls: list[dict[str, Any]] = []
            if message_data.tool_calls:
                tool_calls = [
                    (await self.add_tool_call(message_id, tool_call_data)).model_dump()
                    for tool_call_data in message_data.tool_calls
                ]

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

        except RECOVERABLE_ERRORS as error:
            logger.exception(
                "Failed to add message",
                extra={
                    "session_id": session_id,
                    "user_id": user_id,
                    "error": str(error),
                },
            )
            raise

    # This method is replaced by _get_messages_internal to avoid router conflicts

    @tripsage_safe_execute()
    @trace_span(name="svc.chat.messages.recent")
    @record_histogram("svc.op.duration", unit="s")
    async def get_recent_messages(
        self, session_id: str, user_id: str, request: RecentMessagesRequest
    ) -> RecentMessagesResponse:
        """Get recent messages within token limit.

        Args:
            session_id: Session ID
            user_id: User ID (for access control)
            request: Recent messages request

        Returns:
            Recent messages response with token information
        """
        try:
            # Verify session access
            session = await self.get_session(session_id, user_id)
            if not session:
                return RecentMessagesResponse(
                    messages=[], total_tokens=0, truncated=False
                )

            # Fetch messages directly from database
            raw = await self.db.get_session_messages(
                session_id, limit=(request.limit + request.offset), offset=0
            )

            # Keep the most recent (limit + offset) then apply offset
            raw = raw[-(request.limit + request.offset) :] if raw else []
            if request.offset:
                raw = raw[request.offset :]

            # Apply max_tokens constraint from most recent backwards
            selected: list[dict[str, Any]] = []
            running_tokens = 0
            for item in reversed(raw):
                tokens = self._estimate_tokens(item.get("content", ""))
                # Always include at least one message
                if running_tokens + tokens > request.max_tokens and selected:
                    break
                running_tokens += tokens
                selected.append(item)

            selected.reverse()

            messages: list[MessageResponse] = []
            for result in selected:
                tool_calls: list[dict[str, Any]] = await self.db.get_message_tool_calls(
                    result["id"]
                )
                messages.append(
                    MessageResponse(
                        id=result["id"],
                        session_id=result["session_id"],
                        role=result["role"],
                        content=result["content"],
                        created_at=datetime.fromisoformat(result["created_at"]),
                        metadata=result.get("metadata", {}),
                        tool_calls=tool_calls,
                        estimated_tokens=self._estimate_tokens(result["content"]),
                    )
                )

            total_tokens = sum(m.estimated_tokens or 0 for m in messages)
            # Truncated if we couldn't include all available messages within caps
            truncated = len(messages) < len(raw)

            return RecentMessagesResponse(
                messages=messages, total_tokens=total_tokens, truncated=truncated
            )

        except RECOVERABLE_ERRORS as error:
            logger.exception(
                "Failed to get recent messages",
                extra={
                    "session_id": session_id,
                    "user_id": user_id,
                    "error": str(error),
                },
            )
            return RecentMessagesResponse(messages=[], total_tokens=0, truncated=False)

    @tripsage_safe_execute()
    @trace_span(name="svc.chat.sessions.end")
    @record_histogram("svc.op.duration", unit="s")
    async def end_session(self, session_id: str, user_id: str) -> bool:
        """End a chat session.

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
            session = await self.get_session(session_id, user_id)
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

        except RECOVERABLE_ERRORS as error:
            logger.exception(
                "Failed to end session",
                extra={
                    "session_id": session_id,
                    "user_id": user_id,
                    "error": str(error),
                },
            )
            return False

    @tripsage_safe_execute()
    @trace_span(name="svc.chat.tool_calls.update")
    @record_histogram("svc.op.duration", unit="s")
    async def update_tool_call_status(
        self,
        tool_call_id: str,
        status: str,
        result: dict[str, Any] | None = None,
        error_message: str | None = None,
    ) -> dict[str, Any] | None:
        """Update tool call status and result.

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
                completed_at = datetime.now(UTC)

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
            return None

        except RECOVERABLE_ERRORS as error:
            logger.exception(
                "Failed to update tool call status",
                extra={
                    "tool_call_id": tool_call_id,
                    "status": status,
                    "error": str(error),
                },
            )
            return None

    def _sanitize_content(self, content: str) -> str:
        """Sanitize message content to prevent XSS and injection attacks.

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

    def _validate_metadata(self, metadata: Any) -> dict[str, Any]:
        """Validate and normalize metadata."""
        if metadata is None:
            return {}

        if not isinstance(metadata, dict):
            raise ValidationError("Metadata must be a dictionary")

        # Remove None values and ensure all keys are strings
        typed_metadata = cast(dict[str, Any], metadata)
        sanitized: dict[str, Any] = {}
        for key, value in typed_metadata.items():
            if value is None:
                continue
            sanitized[str(key)] = value
        return sanitized

    def _estimate_tokens(self, content: str) -> int:
        """Estimate token count for content."""
        if content == "":
            return 0
        return max(1, len(content) // self.chars_per_token)

    @staticmethod
    def _convert_request_message(
        message: dict[str, Any],
    ) -> HumanMessage | AIMessage | SystemMessage | None:
        """Convert stored request message into a LangChain-compatible message."""
        role = message.get("role", "user")
        content = message.get("content", "")
        if role == "user":
            return HumanMessage(content=content)
        if role == "assistant":
            return AIMessage(content=content)
        if role == "system":
            return SystemMessage(content=content)
        return None

    async def add_tool_call(
        self, message_id: str, tool_call_data: dict[str, Any]
    ) -> ToolCallResponse:
        """Create a tool call record.

        Args:
            message_id: Message ID
            tool_call_data: Tool call data

        Returns:
            Created tool call
        """
        tool_call_id = str(uuid4())

        now = datetime.now(UTC)
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
            result=None,
            completed_at=None,
            error_message=None,
        )

    # ===== Public Chat Methods =====
    @tripsage_safe_execute()
    @trace_span(name="svc.chat.completion")
    @record_histogram("svc.op.duration", unit="s")
    async def chat_completion(self, user_id: str, request: Any) -> dict[str, Any]:
        """Handle chat completion requests (main chat endpoint).

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

            # Prefer user's BYOK for OpenAI when available
            user_key: str | None = None
            if hasattr(self.db, "fetch_user_service_api_key"):
                try:
                    fetch_key = self.db.fetch_user_service_api_key  # type: ignore[misc]
                    user_key = await fetch_key(user_id, "openai")  # type: ignore[misc]
                except Exception:  # noqa: BLE001 - non-critical
                    user_key = None

            llm = ChatOpenAI(
                model=model_name,
                temperature=temperature,
                api_key=(user_key or settings.openai_api_key),  # type: ignore[arg-type]
                model_kwargs={"max_tokens": max_tokens},
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
            mapped_messages = [
                converted
                for converted in (
                    self._convert_request_message(message)
                    for message in request.messages
                )
                if converted is not None
            ]
            langchain_messages = [
                SystemMessage(content=system_prompt),
                *mapped_messages,
            ]

            # Get AI response
            response: Any = await llm.ainvoke(langchain_messages)

            # Extract token usage information
            usage_metadata = getattr(response, "response_metadata", {})
            token_usage = usage_metadata.get("token_usage", {})
            finish_reason = usage_metadata.get("finish_reason", "stop")

            # Store the conversation in the session if we have a session ID
            if session_id and hasattr(self, "db"):
                try:
                    # Create session if it doesn't exist
                    session = await self.get_session(session_id, user_id)
                    if not session:
                        session_data = ChatSessionCreateRequest(
                            title="Chat with TripSage AI",
                            metadata={"model": model_name},
                            trip_id=None,
                        )
                        new_session = await self.create_session(user_id, session_data)
                        session_id = new_session.id

                    # Add user message to session
                    if request.messages:
                        last_user_msg = request.messages[-1]
                        if last_user_msg.get("role") == "user":
                            user_msg_data = MessageCreateRequest(
                                role="user",
                                content=last_user_msg.get("content", ""),
                                metadata=None,
                                tool_calls=None,
                            )
                            await self.add_message(session_id, user_id, user_msg_data)

                    # Add AI response to session
                    ai_content: str = str(getattr(response, "content", ""))
                    ai_msg_data = MessageCreateRequest(
                        role="assistant",
                        content=ai_content,
                        metadata={"model": model_name, "usage": token_usage},
                        tool_calls=None,
                    )
                    await self.add_message(session_id, user_id, ai_msg_data)

                except RECOVERABLE_ERRORS as error:
                    logger.warning(
                        "Failed to store chat in session",
                        extra={"session_id": session_id, "error": str(error)},
                    )

            # Return formatted response
            resp_content: str = str(getattr(response, "content", ""))
            return {
                "content": resp_content,
                "session_id": session_id,
                "model": model_name,
                "usage": {
                    "prompt_tokens": token_usage.get("prompt_tokens", 0),
                    "completion_tokens": token_usage.get("completion_tokens", 0),
                    "total_tokens": token_usage.get("total_tokens", 0),
                },
                "finish_reason": finish_reason,
            }

        except RECOVERABLE_ERRORS as error:
            logger.exception(
                "Chat completion failed",
                extra={"user_id": user_id, "error": str(error)},
            )
            raise

    # Router compatibility wrappers removed in final-only alignment.

    @tripsage_safe_execute()
    @trace_span(name="svc.chat.sessions.get")
    @record_histogram("svc.op.duration", unit="s")
    async def get_session(
        self, session_id: str, user_id: str
    ) -> ChatSessionResponse | None:
        """Get a chat session by id for a user.

        Args:
            session_id: Session identifier.
            user_id: User identifier.

        Returns:
            ChatSessionResponse if found, otherwise None.
        """
        try:
            result = await self.db.get_chat_session(session_id, user_id)
            if not result:
                return None

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
                message_count=0,
                last_message_at=None,
            )

        except RECOVERABLE_ERRORS as error:
            logger.exception(
                "Failed to get chat session",
                extra={
                    "session_id": session_id,
                    "user_id": user_id,
                    "error": str(error),
                },
            )
            return None

    @tripsage_safe_execute()
    @trace_span(name="svc.chat.messages.list")
    @record_histogram("svc.op.duration", unit="s")
    async def get_messages(
        self,
        session_id: str,
        user_id: str,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[MessageResponse]:
        """List messages for a chat session ordered by creation time."""
        try:
            # Verify session access
            session = await self.get_session(session_id, user_id)
            if not session:
                return []

            results = await self.db.get_session_messages(session_id, limit, offset)

            return [
                MessageResponse(
                    id=result["id"],
                    session_id=result["session_id"],
                    role=result["role"],
                    content=result["content"],
                    created_at=datetime.fromisoformat(result["created_at"]),
                    metadata=result.get("metadata", {}),
                    tool_calls=list(await self.db.get_message_tool_calls(result["id"])),
                    estimated_tokens=self._estimate_tokens(result["content"]),
                )
                for result in results
            ]

        except RECOVERABLE_ERRORS as error:
            logger.exception(
                "Failed to get messages",
                extra={
                    "session_id": session_id,
                    "user_id": user_id,
                    "error": str(error),
                },
            )
            return []

    # End of public methods


# Dependency function for FastAPI
async def get_chat_service() -> ChatService:
    """Get chat service instance for dependency injection."""
    from tripsage_core.services.infrastructure import get_database_service

    db = await get_database_service()
    return ChatService(database_service=db)
