"""Chat service for managing sessions and messages.

Handles chat session lifecycle, message persistence, and context management.
"""

import asyncio
import html
import logging
import re
import time
from datetime import datetime
from typing import Any, Optional
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from tripsage.api.core.exceptions import NotFoundError, ValidationError
from tripsage.models.db.chat import (
    ChatMessageDB,
    ChatSessionDB,
    ChatSessionWithStats,
    ChatToolCallDB,
    MessageWithTokenEstimate,
    RecentMessagesResponse,
)

logger = logging.getLogger(__name__)


class RateLimiter:
    """Simple in-memory rate limiter for message creation."""

    def __init__(self, max_messages: int = 10, window_seconds: int = 60):
        """Initialize rate limiter.

        Args:
            max_messages: Maximum messages allowed per window
            window_seconds: Time window in seconds
        """
        self.max_messages = max_messages
        self.window_seconds = window_seconds
        self.user_windows: dict[int, list[float]] = {}

    def is_allowed(self, user_id: int, count: int = 1) -> bool:
        """Check if user is allowed to send messages.

        Args:
            user_id: User ID to check
            count: Number of messages to check (default 1)

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

    def check_rate_limit(self, user_id: int, count: int = 1) -> bool:
        """Alias for is_allowed for backward compatibility."""
        return self.is_allowed(user_id, count)

    def reset_user(self, user_id: int) -> None:
        """Reset rate limit for a user.

        Args:
            user_id: User ID to reset
        """
        if user_id in self.user_windows:
            del self.user_windows[user_id]


class ChatService:
    """Service for managing chat sessions and messages."""

    def __init__(
        self,
        db: AsyncSession,
        rate_limiter: Optional[RateLimiter] = None,
        chars_per_token: int = 4,
    ):
        """Initialize chat service.

        Args:
            db: Database session
            rate_limiter: Optional rate limiter instance
            chars_per_token: Characters per token for estimation
        """
        self.db = db
        self.rate_limiter = rate_limiter or RateLimiter()
        self.chars_per_token = chars_per_token
        self._retry_count = 3
        self._retry_delay = 0.1

    def _sanitize_content(self, content: str) -> str:
        """Sanitize message content to prevent XSS and injection attacks.

        Args:
            content: Raw message content

        Returns:
            Sanitized content
        """
        # HTML escape special characters
        content = html.escape(content)

        # Remove any null bytes
        content = content.replace("\x00", "")

        # Limit consecutive whitespace
        content = re.sub(r"\s{3,}", "  ", content)

        return content.strip()

    def _validate_metadata(self, metadata: Any) -> dict[str, Any]:
        """Validate and normalize metadata.

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

    async def _execute_with_retry(self, query, params: dict) -> Any:
        """Execute a database query with retry logic.

        Args:
            query: SQL query to execute
            params: Query parameters

        Returns:
            Query result

        Raises:
            OperationalError: If all retries fail
        """
        last_error = None

        for attempt in range(self._retry_count):
            try:
                return await self.db.execute(query, params)
            except OperationalError as e:
                last_error = e
                if attempt < self._retry_count - 1:
                    await asyncio.sleep(self._retry_delay * (attempt + 1))
                    logger.warning(
                        f"Database query failed (attempt {attempt + 1}/"
                        f"{self._retry_count}): {e}"
                    )
                else:
                    logger.error(
                        f"Database query failed after {self._retry_count} attempts: {e}"
                    )

        raise last_error

    async def create_session(
        self, user_id: int, metadata: Optional[dict[str, Any]] = None
    ) -> ChatSessionDB:
        """Create a new chat session.

        Args:
            user_id: ID of the user
            metadata: Optional session metadata

        Returns:
            Created chat session
        """
        session_id = uuid4()
        metadata = self._validate_metadata(metadata)

        query = text(
            """
            INSERT INTO chat_sessions (id, user_id, metadata)
            VALUES (:id, :user_id, :metadata)
            RETURNING id, user_id, created_at, updated_at, ended_at, metadata
            """
        )

        result = await self._execute_with_retry(
            query, {"id": session_id, "user_id": user_id, "metadata": metadata}
        )
        row = result.fetchone()

        if not row:
            raise ValidationError("Failed to create chat session")

        logger.info(f"Created chat session {session_id} for user {user_id}")

        return ChatSessionDB(
            id=row.id,
            user_id=row.user_id,
            created_at=row.created_at,
            updated_at=row.updated_at,
            ended_at=row.ended_at,
            metadata=row.metadata or {},
        )

    async def get_session(
        self, session_id: UUID, user_id: Optional[int] = None
    ) -> ChatSessionDB:
        """Get a chat session by ID.

        Args:
            session_id: Session ID
            user_id: Optional user ID for access control

        Returns:
            Chat session

        Raises:
            NotFoundError: If session not found
        """
        query = text(
            """
            SELECT id, user_id, created_at, updated_at, ended_at, metadata
            FROM chat_sessions
            WHERE id = :session_id
            """
        )
        params = {"session_id": session_id}

        if user_id is not None:
            query = text(query.text + " AND user_id = :user_id")
            params["user_id"] = user_id

        result = await self.db.execute(query, params)
        row = result.fetchone()

        if not row:
            raise NotFoundError(f"Chat session {session_id} not found")

        return ChatSessionDB(
            id=row.id,
            user_id=row.user_id,
            created_at=row.created_at,
            updated_at=row.updated_at,
            ended_at=row.ended_at,
            metadata=row.metadata or {},
        )

    async def get_active_sessions(
        self, user_id: int, limit: int = 10
    ) -> list[ChatSessionWithStats]:
        """Get active sessions for a user.

        Args:
            user_id: User ID
            limit: Maximum number of sessions to return

        Returns:
            List of active sessions with statistics
        """
        query = text(
            """
            SELECT 
                cs.id,
                cs.user_id,
                cs.created_at,
                cs.updated_at,
                cs.ended_at,
                cs.metadata,
                COUNT(cm.id) as message_count,
                MAX(cm.created_at) as last_message_at
            FROM chat_sessions cs
            LEFT JOIN chat_messages cm ON cs.id = cm.session_id
            WHERE cs.user_id = :user_id AND cs.ended_at IS NULL
            GROUP BY cs.id, cs.user_id, cs.created_at, cs.updated_at, 
                     cs.ended_at, cs.metadata
            ORDER BY cs.updated_at DESC
            LIMIT :limit
            """
        )

        result = await self.db.execute(query, {"user_id": user_id, "limit": limit})
        rows = result.fetchall()

        return [
            ChatSessionWithStats(
                id=row.id,
                user_id=row.user_id,
                created_at=row.created_at,
                updated_at=row.updated_at,
                ended_at=row.ended_at,
                metadata=row.metadata or {},
                message_count=row.message_count or 0,
                last_message_at=row.last_message_at,
            )
            for row in rows
        ]

    async def add_message(
        self,
        session_id: UUID,
        role: str,
        content: str,
        metadata: Optional[dict[str, Any]] = None,
        user_id: Optional[int] = None,
    ) -> ChatMessageDB:
        """Add a message to a chat session.

        Args:
            session_id: Session ID
            role: Message role (user/assistant/system)
            content: Message content
            metadata: Optional message metadata
            user_id: Optional user ID for rate limiting

        Returns:
            Created message

        Raises:
            ValidationError: If message validation fails or rate limit exceeded
        """
        # Check rate limit if user_id provided
        if user_id and role == "user":
            if not self.rate_limiter.check_rate_limit(user_id):
                raise ValidationError(
                    f"Rate limit exceeded. Maximum {self.rate_limiter.max_messages} "
                    f"messages per {self.rate_limiter.window_seconds} seconds."
                )

        # Sanitize content
        content = self._sanitize_content(content)

        # Validate metadata
        metadata = self._validate_metadata(metadata)

        # Validate message structure
        try:
            ChatMessageDB(
                id=0,  # Dummy ID for validation
                session_id=session_id,
                role=role,
                content=content,
                created_at=datetime.now(datetime.UTC),
                metadata=metadata,
            )
        except ValueError as e:
            raise ValidationError(str(e)) from e

        # Insert message
        query = text(
            """
            INSERT INTO chat_messages (session_id, role, content, metadata)
            VALUES (:session_id, :role, :content, :metadata)
            RETURNING id, session_id, role, content, created_at, metadata
            """
        )

        result = await self._execute_with_retry(
            query,
            {
                "session_id": session_id,
                "role": role,
                "content": content,
                "metadata": metadata,
            },
        )
        row = result.fetchone()

        if not row:
            raise ValidationError("Failed to create message")

        # Update session updated_at
        await self.db.execute(
            text("UPDATE chat_sessions SET updated_at = NOW() WHERE id = :session_id"),
            {"session_id": session_id},
        )

        return ChatMessageDB(
            id=row.id,
            session_id=row.session_id,
            role=row.role,
            content=row.content,
            created_at=row.created_at,
            metadata=row.metadata or {},
        )

    async def add_messages_batch(
        self,
        session_id: UUID,
        messages: list[tuple[str, str, Optional[dict[str, Any]]]],
        user_id: Optional[int] = None,
    ) -> list[ChatMessageDB]:
        """Add multiple messages to a chat session in a single transaction.

        Args:
            session_id: Session ID
            messages: List of (role, content, metadata) tuples
            user_id: Optional user ID for rate limiting

        Returns:
            List of created messages

        Raises:
            ValidationError: If any message validation fails or rate limit exceeded
        """
        # Count user messages for rate limiting
        if user_id:
            user_message_count = sum(1 for role, _, _ in messages if role == "user")
            if user_message_count > 0 and not self.rate_limiter.check_rate_limit(
                user_id, count=user_message_count
            ):
                raise ValidationError(
                    f"Rate limit exceeded. Maximum {self.rate_limiter.max_messages} "
                    f"messages per {self.rate_limiter.window_seconds} seconds."
                )

        # Prepare batch data
        batch_data = []
        for role, content, metadata in messages:
            # Sanitize and validate each message
            sanitized_content = self._sanitize_content(content)
            validated_metadata = self._validate_metadata(metadata)

            # Validate message structure
            try:
                ChatMessageDB(
                    id=0,  # Dummy ID for validation
                    session_id=session_id,
                    role=role,
                    content=sanitized_content,
                    created_at=datetime.now(datetime.UTC),
                    metadata=validated_metadata,
                )
            except ValueError as e:
                raise ValidationError(f"Invalid message: {str(e)}") from e

            batch_data.append(
                {
                    "session_id": session_id,
                    "role": role,
                    "content": sanitized_content,
                    "metadata": validated_metadata,
                }
            )

        # Insert all messages in a single query
        query = text(
            """
            INSERT INTO chat_messages (session_id, role, content, metadata)
            VALUES (:session_id, :role, :content, :metadata)
            RETURNING id, session_id, role, content, created_at, metadata
            """
        )

        created_messages = []
        async with self.db.begin():
            for data in batch_data:
                result = await self.db.execute(query, data)
                row = result.fetchone()
                if row:
                    created_messages.append(
                        ChatMessageDB(
                            id=row.id,
                            session_id=row.session_id,
                            role=row.role,
                            content=row.content,
                            created_at=row.created_at,
                            metadata=row.metadata or {},
                        )
                    )

            # Update session updated_at
            await self.db.execute(
                text(
                    "UPDATE chat_sessions SET updated_at = NOW() WHERE id = :session_id"
                ),
                {"session_id": session_id},
            )

        logger.info(f"Added {len(created_messages)} messages to session {session_id}")
        return created_messages

    async def get_messages(
        self, session_id: UUID, limit: Optional[int] = None, offset: int = 0
    ) -> list[ChatMessageDB]:
        """Get messages for a session.

        Args:
            session_id: Session ID
            limit: Maximum number of messages
            offset: Number of messages to skip

        Returns:
            List of messages
        """
        query = text(
            """
            SELECT id, session_id, role, content, created_at, metadata
            FROM chat_messages
            WHERE session_id = :session_id
            ORDER BY created_at ASC
            """
        )
        params = {"session_id": session_id}

        if limit is not None:
            query = text(query.text + " LIMIT :limit OFFSET :offset")
            params.update({"limit": limit, "offset": offset})

        result = await self.db.execute(query, params)
        rows = result.fetchall()

        return [
            ChatMessageDB(
                id=row.id,
                session_id=row.session_id,
                role=row.role,
                content=row.content,
                created_at=row.created_at,
                metadata=row.metadata or {},
            )
            for row in rows
        ]

    async def get_recent_messages(
        self,
        session_id: UUID,
        limit: int = 10,
        max_tokens: int = 8000,
        offset: int = 0,
        chars_per_token: Optional[int] = None,
    ) -> RecentMessagesResponse:
        """Get recent messages within token limit.

        Uses the database function to retrieve messages that fit within
        the specified token limit for context window management.

        Args:
            session_id: Session ID
            limit: Maximum number of messages to consider
            max_tokens: Maximum total tokens to include
            offset: Number of messages to skip (for pagination)
            chars_per_token: Characters per token for estimation
                (uses service default if None)

        Returns:
            Recent messages response with token information
        """
        if chars_per_token is None:
            chars_per_token = self._chars_per_token

        query = text(
            (
                "SELECT * FROM get_recent_messages("
                ":session_id, :limit, :max_tokens, :offset, :chars_per_token"
                ") ORDER BY created_at ASC"
            )
        )

        result = await self._execute_with_retry(
            query,
            {
                "session_id": session_id,
                "limit": limit,
                "max_tokens": max_tokens,
                "offset": offset,
                "chars_per_token": chars_per_token,
            },
        )
        rows = result.fetchall()

        messages = [
            MessageWithTokenEstimate(
                id=row.id,
                session_id=session_id,
                role=row.role,
                content=row.content,
                created_at=row.created_at,
                metadata=row.metadata or {},
                estimated_tokens=row.estimated_tokens,
            )
            for row in rows
        ]

        total_tokens = sum(msg.estimated_tokens for msg in messages)

        # Check if we got fewer messages than requested (indicating truncation)
        truncated = len(messages) < limit

        return RecentMessagesResponse(
            messages=messages, total_tokens=total_tokens, truncated=truncated
        )

    async def add_tool_call(
        self,
        message_id: int,
        tool_id: str,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> ChatToolCallDB:
        """Add a tool call record.

        Args:
            message_id: Message ID that triggered the tool call
            tool_id: Unique identifier for this tool call
            tool_name: Name of the tool
            arguments: Tool arguments

        Returns:
            Created tool call record
        """
        query = text(
            """
            INSERT INTO chat_tool_calls (message_id, tool_id, tool_name, arguments)
            VALUES (:message_id, :tool_id, :tool_name, :arguments)
            RETURNING id, message_id, tool_id, tool_name, arguments, result, 
                      status, created_at, completed_at, error_message
            """
        )

        result = await self.db.execute(
            query,
            {
                "message_id": message_id,
                "tool_id": tool_id,
                "tool_name": tool_name,
                "arguments": arguments,
            },
        )
        row = result.fetchone()

        if not row:
            raise ValidationError("Failed to create tool call")

        return ChatToolCallDB(
            id=row.id,
            message_id=row.message_id,
            tool_id=row.tool_id,
            tool_name=row.tool_name,
            arguments=row.arguments or {},
            result=row.result,
            status=row.status,
            created_at=row.created_at,
            completed_at=row.completed_at,
            error_message=row.error_message,
        )

    async def update_tool_call(
        self,
        tool_call_id: int,
        status: str,
        result: Optional[dict[str, Any]] = None,
        error_message: Optional[str] = None,
    ) -> ChatToolCallDB:
        """Update a tool call with result or error.

        Args:
            tool_call_id: Tool call ID
            status: New status
            result: Tool result (if successful)
            error_message: Error message (if failed)

        Returns:
            Updated tool call record
        """
        # Validate status
        ChatToolCallDB(
            id=tool_call_id,
            message_id=0,
            tool_id="",
            tool_name="",
            status=status,
            created_at=datetime.now(datetime.UTC),
        )

        completed_at = (
            datetime.now(datetime.UTC) if status in {"completed", "failed"} else None
        )

        query = text(
            """
            UPDATE chat_tool_calls
            SET status = :status,
                result = :result,
                error_message = :error_message,
                completed_at = :completed_at
            WHERE id = :id
            RETURNING id, message_id, tool_id, tool_name, arguments, result, 
                      status, created_at, completed_at, error_message
            """
        )

        result_row = await self.db.execute(
            query,
            {
                "id": tool_call_id,
                "status": status,
                "result": result,
                "error_message": error_message,
                "completed_at": completed_at,
            },
        )
        row = result_row.fetchone()

        if not row:
            raise NotFoundError(f"Tool call {tool_call_id} not found")

        return ChatToolCallDB(
            id=row.id,
            message_id=row.message_id,
            tool_id=row.tool_id,
            tool_name=row.tool_name,
            arguments=row.arguments or {},
            result=row.result,
            status=row.status,
            created_at=row.created_at,
            completed_at=row.completed_at,
            error_message=row.error_message,
        )

    async def end_session(self, session_id: UUID) -> ChatSessionDB:
        """End a chat session.

        Args:
            session_id: Session ID

        Returns:
            Updated session

        Raises:
            NotFoundError: If session not found
        """
        query = text(
            """
            UPDATE chat_sessions
            SET ended_at = NOW(), updated_at = NOW()
            WHERE id = :session_id
            RETURNING id, user_id, created_at, updated_at, ended_at, metadata
            """
        )

        result = await self.db.execute(query, {"session_id": session_id})
        row = result.fetchone()

        if not row:
            raise NotFoundError(f"Chat session {session_id} not found")

        return ChatSessionDB(
            id=row.id,
            user_id=row.user_id,
            created_at=row.created_at,
            updated_at=row.updated_at,
            ended_at=row.ended_at,
            metadata=row.metadata or {},
        )

    async def cleanup_old_sessions(self, days_old: int = 30) -> int:
        """Clean up old ended sessions.

        Args:
            days_old: Age threshold in days

        Returns:
            Number of sessions deleted
        """
        query = text("SELECT cleanup_old_sessions(:days_old)")
        result = await self.db.execute(query, {"days_old": days_old})
        count = result.scalar()
        return count or 0

    async def expire_inactive_sessions(self, hours_inactive: int = 24) -> int:
        """Expire inactive sessions.

        Args:
            hours_inactive: Hours of inactivity before expiration

        Returns:
            Number of sessions expired
        """
        query = text("SELECT expire_inactive_sessions(:hours_inactive)")
        result = await self._execute_with_retry(
            query, {"hours_inactive": hours_inactive}
        )
        count = result.scalar()

        if count:
            logger.info(f"Expired {count} inactive sessions")

        return count or 0
