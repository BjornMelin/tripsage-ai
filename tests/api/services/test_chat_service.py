"""Tests for the chat service."""

import time
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from tripsage.api.core.exceptions import NotFoundError, ValidationError
from tripsage.api.services.chat_service import ChatService, RateLimiter
from tripsage.models.db.chat import (
    ChatMessageDB,
    ChatSessionDB,
    ChatSessionWithStats,
    ChatToolCallDB,
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


class TestRateLimiter:
    """Test cases for RateLimiter."""

    def test_rate_limiter_init(self):
        """Test rate limiter initialization."""
        limiter = RateLimiter(max_messages=5, window_seconds=30)
        assert limiter.max_messages == 5
        assert limiter.window_seconds == 30
        assert limiter.user_windows == {}

    def test_rate_limiter_allows_first_message(self):
        """Test that rate limiter allows first message."""
        limiter = RateLimiter(max_messages=5, window_seconds=30)
        assert limiter.is_allowed(user_id=1) is True

    def test_rate_limiter_blocks_after_limit(self):
        """Test that rate limiter blocks after limit reached."""
        limiter = RateLimiter(max_messages=3, window_seconds=30)
        user_id = 1

        # Allow first 3 messages
        for _ in range(3):
            assert limiter.is_allowed(user_id) is True

        # Block 4th message
        assert limiter.is_allowed(user_id) is False

    def test_rate_limiter_allows_after_window(self):
        """Test that rate limiter allows messages after time window."""
        limiter = RateLimiter(max_messages=1, window_seconds=0.1)
        user_id = 1

        # First message allowed
        assert limiter.is_allowed(user_id) is True

        # Second message blocked
        assert limiter.is_allowed(user_id) is False

        # Wait for window to expire
        time.sleep(0.2)

        # Message allowed again
        assert limiter.is_allowed(user_id) is True

    def test_rate_limiter_batch_messages(self):
        """Test rate limiter with batch message checking."""
        limiter = RateLimiter(max_messages=5, window_seconds=30)
        user_id = 1

        # Allow batch of 3 messages
        assert limiter.is_allowed(user_id, count=3) is True

        # Allow 1 more message
        assert limiter.is_allowed(user_id, count=1) is True

        # Block batch that would exceed limit
        assert limiter.is_allowed(user_id, count=2) is False

        # But allow 1 more message
        assert limiter.is_allowed(user_id, count=1) is True

    def test_rate_limiter_reset_user(self):
        """Test resetting rate limit for a user."""
        limiter = RateLimiter(max_messages=1, window_seconds=30)
        user_id = 1

        # Use up limit
        assert limiter.is_allowed(user_id) is True
        assert limiter.is_allowed(user_id) is False

        # Reset user
        limiter.reset_user(user_id)

        # Should be allowed again
        assert limiter.is_allowed(user_id) is True


class TestChatServiceEnhancements:
    """Test cases for enhanced ChatService features."""

    @pytest.fixture
    async def mock_db(self):
        """Create a mock database session."""
        db = AsyncMock(spec=AsyncSession)
        return db

    @pytest.fixture
    async def chat_service(self, mock_db):
        """Create a chat service instance with mock database."""
        rate_limiter = RateLimiter(max_messages=10, window_seconds=60)
        return ChatService(mock_db, rate_limiter=rate_limiter)

    async def test_add_message_with_rate_limiting(self, chat_service, mock_db):
        """Test adding messages with rate limiting."""
        session_id = uuid4()
        user_id = 1

        # Mock database response
        mock_result = MagicMock()
        mock_row = MagicMock()
        mock_row.id = 1
        mock_row.session_id = session_id
        mock_row.role = "user"
        mock_row.content = "Test"
        mock_row.created_at = datetime.utcnow()
        mock_row.metadata = {}
        mock_result.fetchone.return_value = mock_row
        mock_db.execute.return_value = mock_result

        # Exhaust rate limit
        chat_service.rate_limiter.max_messages = 1
        chat_service.rate_limiter.is_allowed(user_id)

        # Should raise ValidationError
        with pytest.raises(ValidationError, match="Rate limit exceeded"):
            await chat_service.add_message(
                session_id=session_id,
                role="user",
                content="Test",
                user_id=user_id,
            )

    async def test_add_message_content_sanitization(self, chat_service, mock_db):
        """Test that message content is sanitized."""
        session_id = uuid4()

        # Mock database response
        mock_result = MagicMock()
        mock_row = MagicMock()
        mock_row.id = 1
        mock_row.session_id = session_id
        mock_row.role = "user"
        mock_row.content = "Test content"
        mock_row.created_at = datetime.utcnow()
        mock_row.metadata = {}
        mock_result.fetchone.return_value = mock_row
        mock_db.execute.return_value = mock_result

        # Test with content that needs sanitization
        dirty_content = "<script>alert('xss')</script>Test content"
        message = await chat_service.add_message(
            session_id=session_id,
            role="user",
            content=dirty_content,
        )

        # Verify execute was called with sanitized content
        call_args = mock_db.execute.call_args[0][1]
        assert "<script>" not in call_args["content"]

    async def test_add_messages_batch(self, chat_service, mock_db):
        """Test adding multiple messages in batch."""
        session_id = uuid4()
        messages = [
            ("user", "First message", None),
            ("assistant", "Response", {"tool": "test"}),
            ("user", "Follow up", None),
        ]

        # Mock database responses
        mock_db.begin.return_value.__aenter__ = AsyncMock()
        mock_db.begin.return_value.__aexit__ = AsyncMock()

        mock_results = []
        for i, (role, content, metadata) in enumerate(messages):
            mock_result = MagicMock()
            mock_row = MagicMock()
            mock_row.id = i + 1
            mock_row.session_id = session_id
            mock_row.role = role
            mock_row.content = content
            mock_row.created_at = datetime.utcnow()
            mock_row.metadata = metadata or {}
            mock_result.fetchone.return_value = mock_row
            mock_results.append(mock_result)

        mock_db.execute.side_effect = mock_results + [MagicMock()]  # +1 for update

        # Add messages
        created = await chat_service.add_messages_batch(session_id, messages)

        # Verify results
        assert len(created) == 3
        assert created[0].role == "user"
        assert created[1].role == "assistant"
        assert created[2].role == "user"

    async def test_retry_logic_on_database_error(self, chat_service, mock_db):
        """Test retry logic on database errors."""
        session_id = uuid4()

        # First two attempts fail, third succeeds
        mock_result = MagicMock()
        mock_row = MagicMock()
        mock_row.id = session_id
        mock_row.user_id = 1
        mock_row.created_at = datetime.utcnow()
        mock_row.updated_at = datetime.utcnow()
        mock_row.ended_at = None
        mock_row.metadata = {}
        mock_result.fetchone.return_value = mock_row

        mock_db.execute.side_effect = [
            OperationalError("Connection lost", None, None),
            OperationalError("Connection lost", None, None),
            mock_result,
        ]

        # Should succeed after retries
        session = await chat_service.get_session(session_id)
        assert session.id == session_id
        assert mock_db.execute.call_count == 3

    async def test_get_recent_messages_with_pagination(self, chat_service, mock_db):
        """Test getting recent messages with pagination support."""
        session_id = uuid4()

        # Mock database response
        mock_result = MagicMock()
        mock_row = MagicMock()
        mock_row.id = 1
        mock_row.role = "user"
        mock_row.content = "Hello"
        mock_row.created_at = datetime.utcnow()
        mock_row.metadata = {}
        mock_row.estimated_tokens = 2
        mock_row.total_messages = 10
        mock_result.fetchall.return_value = [mock_row]
        mock_db.execute.return_value = mock_result

        # Get recent messages with custom parameters
        response = await chat_service.get_recent_messages(
            session_id, limit=5, max_tokens=100, offset=10, chars_per_token=3
        )

        # Verify parameters passed correctly
        call_args = mock_db.execute.call_args[0][1]
        assert call_args["limit"] == 5
        assert call_args["max_tokens"] == 100
        assert call_args["offset"] == 10
        assert call_args["chars_per_token"] == 3

    async def test_expire_inactive_sessions(self, chat_service, mock_db):
        """Test expiring inactive sessions."""
        # Mock database response
        mock_result = MagicMock()
        mock_result.scalar.return_value = 7
        mock_db.execute.return_value = mock_result

        # Expire sessions
        count = await chat_service.expire_inactive_sessions(hours_inactive=12)

        # Verify result
        assert count == 7

        # Verify function called with correct parameter
        call_args = mock_db.execute.call_args[0][1]
        assert call_args["hours_inactive"] == 12
