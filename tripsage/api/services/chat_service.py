"""Chat service for managing sessions and messages.

Handles chat session lifecycle, message persistence, and context management.
"""

import logging
from datetime import datetime
from typing import Any, Optional
from uuid import UUID, uuid4

from sqlalchemy import text
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


class ChatService:
    """Service for managing chat sessions and messages."""

    def __init__(self, db: AsyncSession):
        """Initialize chat service.

        Args:
            db: Database session
        """
        self.db = db

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
        metadata = metadata or {}

        query = text(
            """
            INSERT INTO chat_sessions (id, user_id, metadata)
            VALUES (:id, :user_id, :metadata)
            RETURNING id, user_id, created_at, updated_at, ended_at, metadata
            """
        )

        result = await self.db.execute(
            query, {"id": session_id, "user_id": user_id, "metadata": metadata}
        )
        row = result.fetchone()

        if not row:
            raise ValidationError("Failed to create chat session")

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
    ) -> ChatMessageDB:
        """Add a message to a chat session.

        Args:
            session_id: Session ID
            role: Message role (user/assistant/system)
            content: Message content
            metadata: Optional message metadata

        Returns:
            Created message

        Raises:
            ValidationError: If message validation fails
        """
        metadata = metadata or {}

        # Validate message
        try:
            ChatMessageDB(
                id=0,  # Dummy ID for validation
                session_id=session_id,
                role=role,
                content=content,
                created_at=datetime.utcnow(),
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

        result = await self.db.execute(
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
        self, session_id: UUID, limit: int = 10, max_tokens: int = 8000
    ) -> RecentMessagesResponse:
        """Get recent messages within token limit.

        Uses the database function to retrieve messages that fit within
        the specified token limit for context window management.

        Args:
            session_id: Session ID
            limit: Maximum number of messages to consider
            max_tokens: Maximum total tokens to include

        Returns:
            Recent messages response with token information
        """
        query = text(
            """
            SELECT * FROM get_recent_messages(:session_id, :limit, :max_tokens)
            ORDER BY created_at ASC
            """
        )

        result = await self.db.execute(
            query,
            {"session_id": session_id, "limit": limit, "max_tokens": max_tokens},
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
            created_at=datetime.utcnow(),
        )

        completed_at = datetime.utcnow() if status in {"completed", "failed"} else None

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
