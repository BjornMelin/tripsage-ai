"""
Tests for unified ChatService API adapter.

This module tests the unified ChatService that acts as a thin adaptation
layer between API requests and core business logic.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from pydantic import BaseModel

from tripsage.api.schemas.requests.chat import (
    ChatRequest,
    CreateMessageRequest,
    SessionCreateRequest,
)
from tripsage.api.services.chat import (
    ChatService,
    ChatServiceError,
    ChatServiceNotFoundError,
    ChatServicePermissionError,
    ChatServiceValidationError,
    get_chat_service,
    get_core_chat_service,
)
from tripsage_core.exceptions.exceptions import (
    CoreAuthenticationError,
    CoreResourceNotFoundError,
    CoreValidationError,
)
from tripsage_core.services.business.chat_service import (
    ChatService as CoreChatService,
)


# Mock models for testing
class MockChatSession(BaseModel):
    """Mock chat session model."""

    id: str
    user_id: str
    title: str
    trip_id: str | None = None
    created_at: datetime
    updated_at: datetime
    metadata: dict | None = None
    message_count: int = 0
    last_message_at: datetime | None = None


class MockMessage(BaseModel):
    """Mock message model."""

    id: str
    session_id: str
    role: str
    content: str
    created_at: datetime
    metadata: dict | None = None
    tool_calls: list | None = None


class TestChatServiceAdapter:
    """Test the unified ChatService adapter functionality."""

    @pytest.fixture
    def mock_core_chat_service(self):
        """Mock core chat service."""
        return AsyncMock(spec=CoreChatService)

    @pytest.fixture
    def chat_service(self, mock_core_chat_service):
        """Create ChatService instance with mocked dependencies."""
        return ChatService(core_chat_service=mock_core_chat_service)

    @pytest.fixture
    def sample_session(self):
        """Create sample session data."""
        now = datetime.now(timezone.utc)
        return MockChatSession(
            id="session-123",
            user_id="user-456",
            title="Test Session",
            trip_id="trip-789",
            created_at=now,
            updated_at=now,
            metadata={"key": "value"},
            message_count=5,
            last_message_at=now,
        )

    @pytest.fixture
    def sample_message(self):
        """Create sample message data."""
        return MockMessage(
            id="msg-123",
            session_id="session-123",
            role="user",
            content="Hello, world!",
            created_at=datetime.now(timezone.utc),
            metadata={"timestamp": "2025-06-04"},
            tool_calls=None,
        )

    @pytest.mark.asyncio
    async def test_chat_completion_not_implemented(self, chat_service):
        """Test that chat_completion raises ChatServiceError for NotImplementedError."""
        request = ChatRequest(
            messages=[{"role": "user", "content": "Hello"}],
            stream=False,
        )

        with pytest.raises(ChatServiceError, match="Internal service error"):
            await chat_service.chat_completion("user-123", request)

    @pytest.mark.asyncio
    async def test_create_session_success(
        self, chat_service, mock_core_chat_service, sample_session
    ):
        """Test successful session creation."""
        mock_core_chat_service.create_session.return_value = sample_session

        request = SessionCreateRequest(
            title="Test Session",
            metadata={"key": "value"},
        )

        result = await chat_service.create_session("user-456", request)

        # Verify core service was called correctly
        mock_core_chat_service.create_session.assert_called_once()
        call_args = mock_core_chat_service.create_session.call_args
        assert call_args[1]["user_id"] == "user-456"
        assert call_args[1]["session_data"].title == "Test Session"
        assert (
            call_args[1]["session_data"].trip_id is None
        )  # trip_id not in request schema

        # Verify response format
        assert result["id"] == "session-123"
        assert result["user_id"] == "user-456"
        assert result["title"] == "Test Session"
        assert result["trip_id"] == "trip-789"  # From sample_session
        assert "created_at" in result
        assert "updated_at" in result
        assert result["metadata"] == {"key": "value"}

    @pytest.mark.asyncio
    async def test_create_session_validation_errors(self, chat_service):
        """Test session creation validation errors."""
        request = SessionCreateRequest(title="Test")

        # Test empty user_id
        with pytest.raises(ChatServiceValidationError, match="User ID is required"):
            await chat_service.create_session("", request)

        # Test empty title
        request_no_title = SessionCreateRequest(title="")
        with pytest.raises(
            ChatServiceValidationError, match="Session title is required"
        ):
            await chat_service.create_session("user-123", request_no_title)

    @pytest.mark.asyncio
    async def test_list_sessions_success(
        self, chat_service, mock_core_chat_service, sample_session
    ):
        """Test successful session listing."""
        mock_core_chat_service.get_user_sessions.return_value = [sample_session]

        result = await chat_service.list_sessions("user-456")

        # Verify core service was called correctly
        mock_core_chat_service.get_user_sessions.assert_called_once_with(
            user_id="user-456"
        )

        # Verify response format
        assert len(result) == 1
        session = result[0]
        assert session["id"] == "session-123"
        assert session["user_id"] == "user-456"
        assert session["title"] == "Test Session"
        assert session["message_count"] == 5
        assert "last_message_at" in session

    @pytest.mark.asyncio
    async def test_list_sessions_validation_error(self, chat_service):
        """Test session listing validation error."""
        with pytest.raises(ChatServiceValidationError, match="User ID is required"):
            await chat_service.list_sessions("")

    @pytest.mark.asyncio
    async def test_get_session_success(
        self, chat_service, mock_core_chat_service, sample_session
    ):
        """Test successful session retrieval."""
        mock_core_chat_service.get_session.return_value = sample_session
        session_id = UUID("12345678-1234-5678-9abc-123456789012")

        result = await chat_service.get_session("user-456", session_id)

        # Verify core service was called correctly
        mock_core_chat_service.get_session.assert_called_once_with(
            session_id=str(session_id), user_id="user-456"
        )

        # Verify response format
        assert result["id"] == "session-123"
        assert result["user_id"] == "user-456"
        assert result["title"] == "Test Session"

    @pytest.mark.asyncio
    async def test_get_session_not_found(self, chat_service, mock_core_chat_service):
        """Test session not found."""
        mock_core_chat_service.get_session.return_value = None
        session_id = UUID("12345678-1234-5678-9abc-123456789012")

        result = await chat_service.get_session("user-456", session_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_session_validation_errors(self, chat_service):
        """Test session retrieval validation errors."""
        session_id = UUID("12345678-1234-5678-9abc-123456789012")

        # Test empty user_id
        with pytest.raises(ChatServiceValidationError, match="User ID is required"):
            await chat_service.get_session("", session_id)

    @pytest.mark.asyncio
    async def test_get_messages_success(
        self, chat_service, mock_core_chat_service, sample_message
    ):
        """Test successful message retrieval."""
        mock_core_chat_service.get_messages.return_value = [sample_message]
        session_id = UUID("12345678-1234-5678-9abc-123456789012")

        result = await chat_service.get_messages("user-456", session_id, limit=50)

        # Verify core service was called correctly
        mock_core_chat_service.get_messages.assert_called_once_with(
            session_id=str(session_id), user_id="user-456", limit=50
        )

        # Verify response format
        assert len(result) == 1
        message = result[0]
        assert message["id"] == "msg-123"
        assert message["session_id"] == "session-123"
        assert message["role"] == "user"
        assert message["content"] == "Hello, world!"

    @pytest.mark.asyncio
    async def test_get_messages_validation_errors(self, chat_service):
        """Test message retrieval validation errors."""
        session_id = UUID("12345678-1234-5678-9abc-123456789012")

        # Test empty user_id
        with pytest.raises(ChatServiceValidationError, match="User ID is required"):
            await chat_service.get_messages("", session_id)

        # Test invalid limit
        with pytest.raises(
            ChatServiceValidationError, match="Limit must be between 1 and 1000"
        ):
            await chat_service.get_messages("user-123", session_id, limit=0)

        with pytest.raises(
            ChatServiceValidationError, match="Limit must be between 1 and 1000"
        ):
            await chat_service.get_messages("user-123", session_id, limit=1001)

    @pytest.mark.asyncio
    async def test_create_message_success(
        self, chat_service, mock_core_chat_service, sample_message
    ):
        """Test successful message creation."""
        mock_core_chat_service.add_message.return_value = sample_message
        session_id = UUID("12345678-1234-5678-9abc-123456789012")

        request = CreateMessageRequest(
            role="user",
            content="Hello, world!",
            metadata={"timestamp": "2025-06-04"},
        )

        result = await chat_service.create_message("user-456", session_id, request)

        # Verify core service was called correctly
        mock_core_chat_service.add_message.assert_called_once()
        call_args = mock_core_chat_service.add_message.call_args
        assert call_args[1]["session_id"] == str(session_id)
        assert call_args[1]["user_id"] == "user-456"
        assert call_args[1]["message_data"].role == "user"
        assert call_args[1]["message_data"].content == "Hello, world!"

        # Verify response format
        assert result["id"] == "msg-123"
        assert result["session_id"] == "session-123"
        assert result["role"] == "user"
        assert result["content"] == "Hello, world!"

    @pytest.mark.asyncio
    async def test_create_message_validation_errors(self, chat_service):
        """Test message creation validation errors."""
        session_id = UUID("12345678-1234-5678-9abc-123456789012")

        # Test empty user_id
        request = CreateMessageRequest(role="user", content="Hello")
        with pytest.raises(ChatServiceValidationError, match="User ID is required"):
            await chat_service.create_message("", session_id, request)

        # Test empty content
        request_no_content = CreateMessageRequest(role="user", content="")
        with pytest.raises(
            ChatServiceValidationError, match="Message content is required"
        ):
            await chat_service.create_message(
                "user-123", session_id, request_no_content
            )

        # Test empty role
        request_no_role = CreateMessageRequest(role="", content="Hello")
        with pytest.raises(
            ChatServiceValidationError, match="Message role is required"
        ):
            await chat_service.create_message("user-123", session_id, request_no_role)

    @pytest.mark.asyncio
    async def test_delete_session_success(self, chat_service, mock_core_chat_service):
        """Test successful session deletion."""
        mock_core_chat_service.end_session.return_value = True
        session_id = UUID("12345678-1234-5678-9abc-123456789012")

        result = await chat_service.delete_session("user-456", session_id)

        # Verify core service was called correctly
        mock_core_chat_service.end_session.assert_called_once_with(
            session_id=str(session_id), user_id="user-456"
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_delete_session_not_found(self, chat_service, mock_core_chat_service):
        """Test session deletion when session not found."""
        mock_core_chat_service.end_session.return_value = False
        session_id = UUID("12345678-1234-5678-9abc-123456789012")

        result = await chat_service.delete_session("user-456", session_id)

        assert result is False

    @pytest.mark.asyncio
    async def test_delete_session_validation_errors(self, chat_service):
        """Test session deletion validation errors."""
        session_id = UUID("12345678-1234-5678-9abc-123456789012")

        # Test empty user_id
        with pytest.raises(ChatServiceValidationError, match="User ID is required"):
            await chat_service.delete_session("", session_id)


class TestChatServiceErrorHandling:
    """Test error handling and exception conversion."""

    @pytest.fixture
    def mock_core_chat_service(self):
        """Mock core chat service."""
        return AsyncMock(spec=CoreChatService)

    @pytest.fixture
    def chat_service(self, mock_core_chat_service):
        """Create ChatService instance with mocked dependencies."""
        return ChatService(core_chat_service=mock_core_chat_service)

    @pytest.mark.asyncio
    async def test_handle_core_validation_error(
        self, chat_service, mock_core_chat_service
    ):
        """Test conversion of CoreValidationError."""
        mock_core_chat_service.get_user_sessions.side_effect = CoreValidationError(
            "Invalid input"
        )

        with pytest.raises(ChatServiceValidationError, match="Invalid input"):
            await chat_service.list_sessions("user-123")

    @pytest.mark.asyncio
    async def test_handle_core_not_found_error(
        self, chat_service, mock_core_chat_service
    ):
        """Test conversion of CoreResourceNotFoundError."""
        mock_core_chat_service.get_user_sessions.side_effect = (
            CoreResourceNotFoundError("Not found")
        )

        with pytest.raises(ChatServiceNotFoundError, match="Not found"):
            await chat_service.list_sessions("user-123")

    @pytest.mark.asyncio
    async def test_handle_core_auth_error(self, chat_service, mock_core_chat_service):
        """Test conversion of CoreAuthenticationError."""
        mock_core_chat_service.get_user_sessions.side_effect = CoreAuthenticationError(
            "Unauthorized"
        )

        with pytest.raises(ChatServicePermissionError, match="Unauthorized"):
            await chat_service.list_sessions("user-123")

    @pytest.mark.asyncio
    async def test_handle_generic_error(self, chat_service, mock_core_chat_service):
        """Test conversion of generic exceptions."""
        mock_core_chat_service.get_user_sessions.side_effect = RuntimeError(
            "Unexpected error"
        )

        with pytest.raises(ChatServiceError, match="Internal service error"):
            await chat_service.list_sessions("user-123")


class TestChatServiceDependencyInjection:
    """Test dependency injection functions."""

    @pytest.mark.asyncio
    async def test_get_core_chat_service_creates_instance(self):
        """Test that get_core_chat_service creates a CoreChatService instance."""
        service = await get_core_chat_service()
        assert isinstance(service, CoreChatService)

    @pytest.mark.asyncio
    async def test_get_chat_service_creates_instance(self):
        """Test that get_chat_service creates a ChatService instance."""
        service = await get_chat_service()
        assert isinstance(service, ChatService)
        assert service.core_chat_service is not None


class TestChatServiceExceptionTypes:
    """Test custom exception classes."""

    def test_chat_service_error_inheritance(self):
        """Test that all custom exceptions inherit from base exception."""
        error = ChatServiceError("Base error")
        assert isinstance(error, Exception)
        assert str(error) == "Base error"

    def test_validation_error_inheritance(self):
        """Test validation error inheritance."""
        error = ChatServiceValidationError("Validation failed")
        assert isinstance(error, ChatServiceError)
        assert isinstance(error, Exception)

    def test_not_found_error_inheritance(self):
        """Test not found error inheritance."""
        error = ChatServiceNotFoundError("Resource not found")
        assert isinstance(error, ChatServiceError)
        assert isinstance(error, Exception)

    def test_permission_error_inheritance(self):
        """Test permission error inheritance."""
        error = ChatServicePermissionError("Access denied")
        assert isinstance(error, ChatServiceError)
        assert isinstance(error, Exception)
