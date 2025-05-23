"""Tests for the chat service."""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from tripsage.api.core.exceptions import NotFoundError, ValidationError
from tripsage.api.services.chat_service import ChatService
from tripsage.models.db.chat import (
    ChatMessageDB,
    ChatSessionDB,
    ChatSessionWithStats,
    ChatToolCallDB,
    MessageWithTokenEstimate,
    RecentMessagesResponse,
)


@pytest.fixture
async def mock_db():
    """Create a mock database session."""
    db = AsyncMock(spec=AsyncSession)
    return db


@pytest.fixture
async def chat_service(mock_db):
    """Create a chat service instance with mock database."""
    return ChatService(mock_db)


class TestChatService:
    """Test cases for ChatService."""

    async def test_create_session(self, chat_service, mock_db):
        """Test creating a new chat session."""
        # Arrange
        user_id = 1
        metadata = {"source": "web", "device": "desktop"}
        session_id = uuid4()
        created_at = datetime.utcnow()

        # Mock database response
        mock_result = MagicMock()
        mock_row = MagicMock()
        mock_row.id = session_id
        mock_row.user_id = user_id
        mock_row.created_at = created_at
        mock_row.updated_at = created_at
        mock_row.ended_at = None
        mock_row.metadata = metadata
        mock_result.fetchone.return_value = mock_row
        mock_db.execute.return_value = mock_result

        # Act
        session = await chat_service.create_session(user_id, metadata)

        # Assert
        assert isinstance(session, ChatSessionDB)
        assert session.user_id == user_id
        assert session.metadata == metadata
        assert session.ended_at is None
        mock_db.execute.assert_called_once()

    async def test_create_session_failure(self, chat_service, mock_db):
        """Test create session failure."""
        # Arrange
        mock_result = MagicMock()
        mock_result.fetchone.return_value = None
        mock_db.execute.return_value = mock_result

        # Act & Assert
        with pytest.raises(ValidationError, match="Failed to create chat session"):
            await chat_service.create_session(1)

    async def test_get_session(self, chat_service, mock_db):
        """Test getting a session by ID."""
        # Arrange
        session_id = uuid4()
        user_id = 1

        mock_result = MagicMock()
        mock_row = MagicMock()
        mock_row.id = session_id
        mock_row.user_id = user_id
        mock_row.created_at = datetime.utcnow()
        mock_row.updated_at = datetime.utcnow()
        mock_row.ended_at = None
        mock_row.metadata = {}
        mock_result.fetchone.return_value = mock_row
        mock_db.execute.return_value = mock_result

        # Act
        session = await chat_service.get_session(session_id, user_id)

        # Assert
        assert isinstance(session, ChatSessionDB)
        assert session.id == session_id
        assert session.user_id == user_id

    async def test_get_session_not_found(self, chat_service, mock_db):
        """Test get session not found."""
        # Arrange
        session_id = uuid4()
        mock_result = MagicMock()
        mock_result.fetchone.return_value = None
        mock_db.execute.return_value = mock_result

        # Act & Assert
        with pytest.raises(NotFoundError, match=f"Chat session {session_id} not found"):
            await chat_service.get_session(session_id)

    async def test_get_active_sessions(self, chat_service, mock_db):
        """Test getting active sessions for a user."""
        # Arrange
        user_id = 1
        session_id = uuid4()

        mock_result = MagicMock()
        mock_row = MagicMock()
        mock_row.id = session_id
        mock_row.user_id = user_id
        mock_row.created_at = datetime.utcnow()
        mock_row.updated_at = datetime.utcnow()
        mock_row.ended_at = None
        mock_row.metadata = {}
        mock_row.message_count = 5
        mock_row.last_message_at = datetime.utcnow()
        mock_result.fetchall.return_value = [mock_row]
        mock_db.execute.return_value = mock_result

        # Act
        sessions = await chat_service.get_active_sessions(user_id)

        # Assert
        assert len(sessions) == 1
        assert isinstance(sessions[0], ChatSessionWithStats)
        assert sessions[0].message_count == 5

    async def test_add_message(self, chat_service, mock_db):
        """Test adding a message to a session."""
        # Arrange
        session_id = uuid4()
        role = "user"
        content = "Hello, I need help planning a trip"
        metadata = {"timestamp": 123456}

        mock_result = MagicMock()
        mock_row = MagicMock()
        mock_row.id = 1
        mock_row.session_id = session_id
        mock_row.role = role
        mock_row.content = content
        mock_row.created_at = datetime.utcnow()
        mock_row.metadata = metadata
        mock_result.fetchone.return_value = mock_row
        mock_db.execute.return_value = mock_result

        # Act
        message = await chat_service.add_message(session_id, role, content, metadata)

        # Assert
        assert isinstance(message, ChatMessageDB)
        assert message.role == role
        assert message.content == content
        assert message.metadata == metadata
        assert mock_db.execute.call_count == 2  # Insert message + update session

    async def test_add_message_invalid_role(self, chat_service, mock_db):
        """Test adding a message with invalid role."""
        # Act & Assert
        with pytest.raises(ValidationError, match="Role must be one of"):
            await chat_service.add_message(uuid4(), "invalid_role", "content")

    async def test_add_message_content_too_long(self, chat_service, mock_db):
        """Test adding a message with content exceeding limit."""
        # Arrange
        long_content = "x" * 40000  # Exceeds 32KB limit

        # Act & Assert
        with pytest.raises(ValidationError, match="exceeds 32KB limit"):
            await chat_service.add_message(uuid4(), "user", long_content)

    async def test_get_messages(self, chat_service, mock_db):
        """Test getting messages for a session."""
        # Arrange
        session_id = uuid4()

        mock_result = MagicMock()
        mock_row1 = MagicMock()
        mock_row1.id = 1
        mock_row1.session_id = session_id
        mock_row1.role = "user"
        mock_row1.content = "Hello"
        mock_row1.created_at = datetime.utcnow()
        mock_row1.metadata = {}

        mock_row2 = MagicMock()
        mock_row2.id = 2
        mock_row2.session_id = session_id
        mock_row2.role = "assistant"
        mock_row2.content = "Hi! How can I help?"
        mock_row2.created_at = datetime.utcnow()
        mock_row2.metadata = {}

        mock_result.fetchall.return_value = [mock_row1, mock_row2]
        mock_db.execute.return_value = mock_result

        # Act
        messages = await chat_service.get_messages(session_id, limit=10)

        # Assert
        assert len(messages) == 2
        assert messages[0].role == "user"
        assert messages[1].role == "assistant"

    async def test_get_recent_messages(self, chat_service, mock_db):
        """Test getting recent messages with token limit."""
        # Arrange
        session_id = uuid4()

        mock_result = MagicMock()
        mock_row = MagicMock()
        mock_row.id = 1
        mock_row.role = "user"
        mock_row.content = "Hello world"
        mock_row.created_at = datetime.utcnow()
        mock_row.metadata = {}
        mock_row.estimated_tokens = 3
        mock_result.fetchall.return_value = [mock_row]
        mock_db.execute.return_value = mock_result

        # Act
        response = await chat_service.get_recent_messages(session_id)

        # Assert
        assert isinstance(response, RecentMessagesResponse)
        assert len(response.messages) == 1
        assert response.total_tokens == 3
        assert not response.truncated

    async def test_add_tool_call(self, chat_service, mock_db):
        """Test adding a tool call."""
        # Arrange
        message_id = 1
        tool_id = "call_123"
        tool_name = "search_flights"
        arguments = {"from": "NYC", "to": "LAX"}

        mock_result = MagicMock()
        mock_row = MagicMock()
        mock_row.id = 1
        mock_row.message_id = message_id
        mock_row.tool_id = tool_id
        mock_row.tool_name = tool_name
        mock_row.arguments = arguments
        mock_row.result = None
        mock_row.status = "pending"
        mock_row.created_at = datetime.utcnow()
        mock_row.completed_at = None
        mock_row.error_message = None
        mock_result.fetchone.return_value = mock_row
        mock_db.execute.return_value = mock_result

        # Act
        tool_call = await chat_service.add_tool_call(
            message_id, tool_id, tool_name, arguments
        )

        # Assert
        assert isinstance(tool_call, ChatToolCallDB)
        assert tool_call.tool_name == tool_name
        assert tool_call.arguments == arguments
        assert tool_call.status == "pending"

    async def test_update_tool_call_success(self, chat_service, mock_db):
        """Test updating a tool call with success."""
        # Arrange
        tool_call_id = 1
        result = {"flights": [{"id": "123", "price": 299}]}

        mock_result = MagicMock()
        mock_row = MagicMock()
        mock_row.id = tool_call_id
        mock_row.message_id = 1
        mock_row.tool_id = "call_123"
        mock_row.tool_name = "search_flights"
        mock_row.arguments = {}
        mock_row.result = result
        mock_row.status = "completed"
        mock_row.created_at = datetime.utcnow()
        mock_row.completed_at = datetime.utcnow()
        mock_row.error_message = None
        mock_result.fetchone.return_value = mock_row
        mock_db.execute.return_value = mock_result

        # Act
        tool_call = await chat_service.update_tool_call(
            tool_call_id, "completed", result=result
        )

        # Assert
        assert tool_call.status == "completed"
        assert tool_call.result == result
        assert tool_call.completed_at is not None

    async def test_update_tool_call_failure(self, chat_service, mock_db):
        """Test updating a tool call with failure."""
        # Arrange
        tool_call_id = 1
        error_message = "API rate limit exceeded"

        mock_result = MagicMock()
        mock_row = MagicMock()
        mock_row.id = tool_call_id
        mock_row.message_id = 1
        mock_row.tool_id = "call_123"
        mock_row.tool_name = "search_flights"
        mock_row.arguments = {}
        mock_row.result = None
        mock_row.status = "failed"
        mock_row.created_at = datetime.utcnow()
        mock_row.completed_at = datetime.utcnow()
        mock_row.error_message = error_message
        mock_result.fetchone.return_value = mock_row
        mock_db.execute.return_value = mock_result

        # Act
        tool_call = await chat_service.update_tool_call(
            tool_call_id, "failed", error_message=error_message
        )

        # Assert
        assert tool_call.status == "failed"
        assert tool_call.error_message == error_message

    async def test_end_session(self, chat_service, mock_db):
        """Test ending a chat session."""
        # Arrange
        session_id = uuid4()

        mock_result = MagicMock()
        mock_row = MagicMock()
        mock_row.id = session_id
        mock_row.user_id = 1
        mock_row.created_at = datetime.utcnow()
        mock_row.updated_at = datetime.utcnow()
        mock_row.ended_at = datetime.utcnow()
        mock_row.metadata = {}
        mock_result.fetchone.return_value = mock_row
        mock_db.execute.return_value = mock_result

        # Act
        session = await chat_service.end_session(session_id)

        # Assert
        assert session.ended_at is not None

    async def test_cleanup_old_sessions(self, chat_service, mock_db):
        """Test cleaning up old sessions."""
        # Arrange
        deleted_count = 5
        mock_result = MagicMock()
        mock_result.scalar.return_value = deleted_count
        mock_db.execute.return_value = mock_result

        # Act
        count = await chat_service.cleanup_old_sessions(30)

        # Assert
        assert count == deleted_count
