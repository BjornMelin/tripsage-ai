"""
Comprehensive tests for ChatService.

This module provides full test coverage for chat session management operations
including session creation, message handling, context management, and AI interactions.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from tripsage_core.exceptions import (
    CoreResourceNotFoundError as NotFoundError,
)
from tripsage_core.exceptions import (
    CoreValidationError as ValidationError,
)
from tripsage_core.services.business.chat_service import (
    ChatService,
    ChatSessionCreateRequest,
    ChatSessionResponse,
    MessageCreateRequest,
    MessageResponse,
    MessageRole,
    RateLimiter,
    RecentMessagesRequest,
    RecentMessagesResponse,
    ToolCallResponse,
    ToolCallStatus,
    get_chat_service,
)


class TestChatService:
    """Test suite for ChatService."""

    @pytest.fixture
    def mock_database_service(self):
        """Mock database service."""
        db = AsyncMock()
        return db

    @pytest.fixture
    def rate_limiter(self):
        """Create rate limiter instance."""
        return RateLimiter(max_messages=10, window_seconds=60)

    @pytest.fixture
    def chat_service(self, mock_database_service, rate_limiter):
        """Create ChatService instance with mocked dependencies."""
        return ChatService(
            database_service=mock_database_service,
            rate_limiter=rate_limiter,
            chars_per_token=4,
        )

    @pytest.fixture
    def sample_session_create_request(self):
        """Sample chat session creation request."""
        return ChatSessionCreateRequest(
            title="Trip Planning Chat",
            trip_id=str(uuid4()),
            metadata={"destination": "Europe", "budget": 5000, "duration": "2 weeks"},
        )

    @pytest.fixture
    def sample_chat_session(self):
        """Sample chat session response."""
        session_id = str(uuid4())
        user_id = str(uuid4())
        trip_id = str(uuid4())
        now = datetime.now(timezone.utc)

        return ChatSessionResponse(
            id=session_id,
            user_id=user_id,
            title="Trip Planning Chat",
            trip_id=trip_id,
            created_at=now,
            updated_at=now,
            ended_at=None,
            metadata={"destination": "Europe"},
            message_count=0,
            last_message_at=None,
        )

    @pytest.fixture
    def sample_message_create_request(self):
        """Sample message creation request."""
        return MessageCreateRequest(
            role=MessageRole.USER,
            content="I want to plan a trip to Paris for 2 weeks",
            metadata={"intent": "trip_planning"},
        )

    @pytest.fixture
    def sample_message_response(self, sample_chat_session):
        """Sample message response."""
        message_id = str(uuid4())
        now = datetime.now(timezone.utc)

        return MessageResponse(
            id=message_id,
            session_id=sample_chat_session.id,
            role=MessageRole.USER,
            content="I want to plan a trip to Paris for 2 weeks",
            created_at=now,
            metadata={"intent": "trip_planning"},
            tool_calls=[],
            estimated_tokens=12,
        )

    async def test_create_session_success(
        self, chat_service, mock_database_service, sample_session_create_request
    ):
        """Test successful chat session creation."""
        user_id = str(uuid4())

        # Mock database response
        mock_database_service.create_chat_session.return_value = {
            "id": str(uuid4()),
            "user_id": user_id,
            "title": sample_session_create_request.title,
            "trip_id": sample_session_create_request.trip_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "metadata": sample_session_create_request.metadata or {},
            "message_count": 0,
        }

        result = await chat_service.create_session(
            user_id, sample_session_create_request
        )

        # Assertions
        assert isinstance(result, ChatSessionResponse)
        assert result.user_id == user_id
        assert result.title == sample_session_create_request.title
        assert result.trip_id == sample_session_create_request.trip_id
        assert result.message_count == 0

        # Verify database call
        mock_database_service.create_chat_session.assert_called_once()

    async def test_get_session_success(
        self, chat_service, mock_database_service, sample_chat_session
    ):
        """Test successful session retrieval."""
        # Mock database response
        mock_database_service.get_chat_session.return_value = {
            "id": sample_chat_session.id,
            "user_id": sample_chat_session.user_id,
            "title": sample_chat_session.title,
            "trip_id": sample_chat_session.trip_id,
            "created_at": sample_chat_session.created_at.isoformat(),
            "updated_at": sample_chat_session.updated_at.isoformat(),
            "metadata": sample_chat_session.metadata,
            "message_count": sample_chat_session.message_count,
        }

        result = await chat_service.get_session(
            sample_chat_session.id, sample_chat_session.user_id
        )

        assert result is not None
        assert result.id == sample_chat_session.id
        assert result.user_id == sample_chat_session.user_id

        mock_database_service.get_chat_session.assert_called_once_with(
            sample_chat_session.id, sample_chat_session.user_id
        )

    async def test_get_session_not_found(self, chat_service, mock_database_service):
        """Test session retrieval when not found."""
        session_id = str(uuid4())
        user_id = str(uuid4())

        mock_database_service.get_chat_session.return_value = None

        with pytest.raises(NotFoundError, match="Chat session not found"):
            await chat_service.get_session(session_id, user_id)

    async def test_add_message_success(
        self,
        chat_service,
        mock_database_service,
        sample_chat_session,
        sample_message_create_request,
    ):
        """Test successful message addition."""
        # Mock session exists
        mock_database_service.get_chat_session.return_value = {
            "id": sample_chat_session.id,
            "user_id": sample_chat_session.user_id,
            "title": sample_chat_session.title,
        }

        # Mock message creation
        message_id = str(uuid4())
        mock_database_service.create_chat_message.return_value = {
            "id": message_id,
            "session_id": sample_chat_session.id,
            "role": sample_message_create_request.role,
            "content": sample_message_create_request.content,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "metadata": sample_message_create_request.metadata or {},
            "estimated_tokens": 12,
        }

        result = await chat_service.add_message(
            sample_chat_session.id,
            sample_chat_session.user_id,
            sample_message_create_request,
        )

        assert isinstance(result, MessageResponse)
        assert result.session_id == sample_chat_session.id
        assert result.role == sample_message_create_request.role
        assert result.content == sample_message_create_request.content

        # Verify database calls
        mock_database_service.get_chat_session.assert_called_once()
        mock_database_service.create_chat_message.assert_called_once()

    async def test_add_message_rate_limited(
        self,
        chat_service,
        mock_database_service,
        sample_chat_session,
        sample_message_create_request,
    ):
        """Test message addition when rate limited."""
        # Mock session exists
        mock_database_service.get_chat_session.return_value = {
            "id": sample_chat_session.id,
            "user_id": sample_chat_session.user_id,
        }

        # Exhaust rate limit
        for _ in range(10):
            chat_service.rate_limiter.is_allowed(sample_chat_session.user_id)

        # Next message should be rate limited
        with pytest.raises(ValidationError, match="Rate limit exceeded"):
            await chat_service.add_message(
                sample_chat_session.id,
                sample_chat_session.user_id,
                sample_message_create_request,
            )

    async def test_add_message_invalid_role(self, chat_service):
        """Test message creation with invalid role."""
        with pytest.raises(ValueError, match="Role must be one of"):
            MessageCreateRequest(role="invalid_role", content="Test message")

    async def test_get_recent_messages_success(
        self,
        chat_service,
        mock_database_service,
        sample_chat_session,
        sample_message_response,
    ):
        """Test successful recent messages retrieval."""
        # Mock database response
        mock_database_service.get_recent_messages.return_value = [
            {
                "id": sample_message_response.id,
                "session_id": sample_message_response.session_id,
                "role": sample_message_response.role,
                "content": sample_message_response.content,
                "created_at": sample_message_response.created_at.isoformat(),
                "metadata": sample_message_response.metadata,
                "estimated_tokens": sample_message_response.estimated_tokens,
            }
        ]

        request = RecentMessagesRequest(limit=10, max_tokens=8000)
        result = await chat_service.get_recent_messages(
            sample_chat_session.id, sample_chat_session.user_id, request
        )

        assert isinstance(result, RecentMessagesResponse)
        assert len(result.messages) == 1
        assert result.messages[0].id == sample_message_response.id
        assert result.total_tokens == sample_message_response.estimated_tokens
        assert not result.truncated

        mock_database_service.get_recent_messages.assert_called_once()

    async def test_get_recent_messages_token_limit(
        self, chat_service, mock_database_service, sample_chat_session
    ):
        """Test recent messages with token limit."""
        # Create messages that exceed token limit
        messages = []
        for _ in range(5):
            messages.append(
                {
                    "id": str(uuid4()),
                    "session_id": sample_chat_session.id,
                    "role": MessageRole.USER,
                    "content": "A" * 2000,  # ~500 tokens each
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "metadata": {},
                    "estimated_tokens": 500,
                }
            )

        mock_database_service.get_recent_messages.return_value = messages

        request = RecentMessagesRequest(limit=10, max_tokens=1000)
        result = await chat_service.get_recent_messages(
            sample_chat_session.id, sample_chat_session.user_id, request
        )

        # Should only include messages that fit within token limit
        assert len(result.messages) == 2  # 2 messages = 1000 tokens
        assert result.total_tokens == 1000
        assert result.truncated

    async def test_add_tool_call_success(
        self, chat_service, mock_database_service, sample_message_response
    ):
        """Test successful tool call addition."""
        tool_call_data = {
            "tool_id": "search_flights",
            "tool_name": "Flight Search",
            "arguments": {
                "origin": "JFK",
                "destination": "CDG",
                "departure_date": "2024-07-15",
            },
        }

        # Mock database response
        tool_call_id = str(uuid4())
        mock_database_service.create_tool_call.return_value = {
            "id": tool_call_id,
            "message_id": sample_message_response.id,
            "tool_id": tool_call_data["tool_id"],
            "tool_name": tool_call_data["tool_name"],
            "arguments": tool_call_data["arguments"],
            "status": ToolCallStatus.PENDING,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        result = await chat_service.add_tool_call(
            sample_message_response.id, tool_call_data
        )

        assert isinstance(result, ToolCallResponse)
        assert result.message_id == sample_message_response.id
        assert result.tool_id == tool_call_data["tool_id"]
        assert result.status == ToolCallStatus.PENDING

        mock_database_service.create_tool_call.assert_called_once()

    async def test_update_tool_call_status_success(
        self, chat_service, mock_database_service
    ):
        """Test successful tool call status update."""
        tool_call_id = str(uuid4())
        result_data = {"flights": [{"flight_number": "AF123", "price": 450.00}]}

        # Mock database update
        mock_database_service.update_tool_call.return_value = {
            "id": tool_call_id,
            "status": ToolCallStatus.COMPLETED,
            "result": result_data,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }

        result = await chat_service.update_tool_call_status(
            tool_call_id, ToolCallStatus.COMPLETED, result=result_data
        )

        assert result["status"] == ToolCallStatus.COMPLETED
        assert result["result"] == result_data
        assert "completed_at" in result

        mock_database_service.update_tool_call.assert_called_once()

    async def test_end_session_success(
        self, chat_service, mock_database_service, sample_chat_session
    ):
        """Test successful session ending."""
        # Mock session exists
        mock_database_service.get_chat_session.return_value = {
            "id": sample_chat_session.id,
            "user_id": sample_chat_session.user_id,
            "ended_at": None,
        }

        # Mock update
        mock_database_service.update_chat_session.return_value = {
            "id": sample_chat_session.id,
            "ended_at": datetime.now(timezone.utc).isoformat(),
        }

        result = await chat_service.end_session(
            sample_chat_session.id, sample_chat_session.user_id
        )

        assert result["ended_at"] is not None

        mock_database_service.update_chat_session.assert_called_once()

    async def test_end_session_already_ended(
        self, chat_service, mock_database_service, sample_chat_session
    ):
        """Test ending an already ended session."""
        # Mock session already ended
        mock_database_service.get_chat_session.return_value = {
            "id": sample_chat_session.id,
            "user_id": sample_chat_session.user_id,
            "ended_at": datetime.now(timezone.utc).isoformat(),
        }

        with pytest.raises(ValidationError, match="Session already ended"):
            await chat_service.end_session(
                sample_chat_session.id, sample_chat_session.user_id
            )

    async def test_get_user_sessions_success(
        self, chat_service, mock_database_service, sample_chat_session
    ):
        """Test successful user sessions retrieval."""
        user_id = sample_chat_session.user_id

        # Mock database response
        mock_database_service.get_user_chat_sessions.return_value = [
            {
                "id": sample_chat_session.id,
                "user_id": user_id,
                "title": sample_chat_session.title,
                "created_at": sample_chat_session.created_at.isoformat(),
                "updated_at": sample_chat_session.updated_at.isoformat(),
                "message_count": 5,
            }
        ]

        results = await chat_service.get_user_sessions(user_id)

        assert len(results) == 1
        assert results[0].id == sample_chat_session.id
        assert results[0].user_id == user_id

        mock_database_service.get_user_chat_sessions.assert_called_once_with(user_id)

    def test_estimate_tokens(self, chat_service):
        """Test token estimation."""
        # Test various content lengths
        content = "Hello, world!"
        tokens = chat_service._estimate_tokens(content)
        assert tokens == len(content) // chat_service.chars_per_token

        # Test empty content
        assert chat_service._estimate_tokens("") == 0

        # Test long content
        long_content = "A" * 1000
        tokens = chat_service._estimate_tokens(long_content)
        assert tokens == 250  # 1000 / 4

    def test_sanitize_content(self, chat_service):
        """Test content sanitization."""
        # Test HTML escape
        html_content = "<script>alert('xss')</script>"
        sanitized = chat_service._sanitize_content(html_content)
        assert "<script>" not in sanitized
        assert "&lt;script&gt;" in sanitized

        # Test whitespace normalization
        spaced_content = "Hello    \n\n\n   world"
        sanitized = chat_service._sanitize_content(spaced_content)
        assert sanitized == "Hello world"

        # Test combined
        combined = "<b>Hello</b>    world"
        sanitized = chat_service._sanitize_content(combined)
        assert sanitized == "&lt;b&gt;Hello&lt;/b&gt; world"

    def test_rate_limiter(self):
        """Test rate limiter functionality."""
        limiter = RateLimiter(max_messages=3, window_seconds=60)
        user_id = str(uuid4())

        # Should allow first 3 messages
        assert limiter.is_allowed(user_id) is True
        assert limiter.is_allowed(user_id) is True
        assert limiter.is_allowed(user_id) is True

        # Fourth should be blocked
        assert limiter.is_allowed(user_id) is False

        # Reset should clear limit
        limiter.reset_user(user_id)
        assert limiter.is_allowed(user_id) is True

    async def test_get_chat_service_dependency(self):
        """Test the dependency injection function."""
        service = await get_chat_service()
        assert isinstance(service, ChatService)

    async def test_concurrent_message_creation(
        self, chat_service, mock_database_service, sample_chat_session
    ):
        """Test concurrent message creation."""
        # Mock session exists
        mock_database_service.get_chat_session.return_value = {
            "id": sample_chat_session.id,
            "user_id": sample_chat_session.user_id,
        }

        # Mock message creation
        mock_database_service.create_chat_message.return_value = {
            "id": str(uuid4()),
            "session_id": sample_chat_session.id,
            "role": MessageRole.USER,
            "content": "Test message",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "estimated_tokens": 3,
        }

        # Create multiple messages concurrently
        import asyncio

        tasks = []
        for i in range(3):
            request = MessageCreateRequest(
                role=MessageRole.USER, content=f"Message {i}"
            )
            task = chat_service.add_message(
                sample_chat_session.id, sample_chat_session.user_id, request
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks)

        assert len(results) == 3
        assert all(isinstance(r, MessageResponse) for r in results)
