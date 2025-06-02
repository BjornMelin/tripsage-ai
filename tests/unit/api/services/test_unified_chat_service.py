"""
Tests for unified ChatService API adapter.

This module tests the unified ChatService that acts as a thin adaptation
layer between API requests and core business logic.
"""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from tripsage.api.schemas.requests.chat import ChatRequest, SessionCreateRequest
from tripsage.api.services.chat import ChatService
from tripsage_core.services.business.auth_service import (
    AuthenticationService as CoreAuthService,
)
from tripsage_core.services.business.chat_service import ChatService as CoreChatService


class TestChatServiceAdapter:
    """Test the unified ChatService adapter functionality."""

    @pytest.fixture
    def mock_core_chat_service(self):
        """Mock core chat service."""
        return AsyncMock(spec=CoreChatService)

    @pytest.fixture
    def mock_core_auth_service(self):
        """Mock core auth service."""
        return AsyncMock(spec=CoreAuthService)

    @pytest.fixture
    def chat_service(self, mock_core_chat_service, mock_core_auth_service):
        """Create ChatService instance with mocked dependencies."""
        return ChatService(
            core_chat_service=mock_core_chat_service,
            core_auth_service=mock_core_auth_service,
        )

    @pytest.mark.asyncio
    async def test_chat_completion_delegates_to_core_service(
        self, chat_service, mock_core_chat_service
    ):
        """Test that chat_completion delegates to core service."""
        user_id = str(uuid4())
        request = ChatRequest(
            messages=[{"role": "user", "content": "Hello"}],
            stream=False,
        )

        # Mock core service response
        mock_response = {"content": "Hello back!", "session_id": str(uuid4())}
        mock_core_chat_service.chat_completion.return_value = mock_response

        result = await chat_service.chat_completion(user_id, request)

        # Verify core service was called
        mock_core_chat_service.chat_completion.assert_called_once_with(
            user_id=user_id, request=request
        )
        assert result == mock_response

    @pytest.mark.asyncio
    async def test_create_session_delegates_to_core_service(
        self, chat_service, mock_core_chat_service
    ):
        """Test that create_session delegates to core service."""
        user_id = str(uuid4())
        request = SessionCreateRequest(title="Test Session")

        # Mock core service response
        mock_session = {
            "id": str(uuid4()),
            "title": "Test Session",
            "user_id": user_id,
        }
        mock_core_chat_service.create_session.return_value = mock_session

        result = await chat_service.create_session(user_id, request)

        # Verify core service was called
        mock_core_chat_service.create_session.assert_called_once_with(
            user_id=user_id, request=request
        )
        assert result == mock_session

    @pytest.mark.asyncio
    async def test_list_sessions_delegates_to_core_service(
        self, chat_service, mock_core_chat_service
    ):
        """Test that list_sessions delegates to core service."""
        user_id = str(uuid4())

        # Mock core service response
        mock_sessions = [
            {"id": str(uuid4()), "title": "Session 1"},
            {"id": str(uuid4()), "title": "Session 2"},
        ]
        mock_core_chat_service.list_sessions.return_value = mock_sessions

        result = await chat_service.list_sessions(user_id)

        # Verify core service was called
        mock_core_chat_service.list_sessions.assert_called_once_with(user_id=user_id)
        assert result == mock_sessions

    @pytest.mark.asyncio
    async def test_get_session_delegates_to_core_service(
        self, chat_service, mock_core_chat_service
    ):
        """Test that get_session delegates to core service."""
        user_id = str(uuid4())
        session_id = uuid4()

        # Mock core service response
        mock_session = {"id": str(session_id), "title": "Test Session"}
        mock_core_chat_service.get_session.return_value = mock_session

        result = await chat_service.get_session(user_id, session_id)

        # Verify core service was called
        mock_core_chat_service.get_session.assert_called_once_with(
            user_id=user_id, session_id=session_id
        )
        assert result == mock_session

    @pytest.mark.asyncio
    async def test_get_messages_delegates_to_core_service(
        self, chat_service, mock_core_chat_service
    ):
        """Test that get_messages delegates to core service."""
        user_id = str(uuid4())
        session_id = uuid4()
        limit = 50

        # Mock core service response
        mock_messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]
        mock_core_chat_service.get_messages.return_value = mock_messages

        result = await chat_service.get_messages(user_id, session_id, limit)

        # Verify core service was called
        mock_core_chat_service.get_messages.assert_called_once_with(
            user_id=user_id, session_id=session_id, limit=limit
        )
        assert result == mock_messages

    @pytest.mark.asyncio
    async def test_delete_session_delegates_to_core_service(
        self, chat_service, mock_core_chat_service
    ):
        """Test that delete_session delegates to core service."""
        user_id = str(uuid4())
        session_id = uuid4()

        # Mock core service response
        mock_core_chat_service.delete_session.return_value = True

        result = await chat_service.delete_session(user_id, session_id)

        # Verify core service was called
        mock_core_chat_service.delete_session.assert_called_once_with(
            user_id=user_id, session_id=session_id
        )
        assert result is True


class TestChatServiceDependencyInjection:
    """Test ChatService dependency injection functionality."""

    @pytest.mark.asyncio
    async def test_get_chat_service_creates_instance(self):
        """Test that get_chat_service creates ChatService with proper dependencies."""
        with (
            patch(
                "tripsage.api.services.chat.get_core_chat_service"
            ) as mock_get_core_chat,
            patch(
                "tripsage.api.services.chat.get_core_auth_service"
            ) as mock_get_core_auth,
        ):
            mock_core_chat = AsyncMock()
            mock_core_auth = AsyncMock()
            mock_get_core_chat.return_value = mock_core_chat
            mock_get_core_auth.return_value = mock_core_auth

            from tripsage.api.services.chat import get_chat_service

            result = await get_chat_service()

            # Verify dependencies were retrieved
            mock_get_core_chat.assert_called_once()
            mock_get_core_auth.assert_called_once()

            # Verify ChatService was created with proper dependencies
            assert isinstance(result, ChatService)
            assert result.core_chat_service == mock_core_chat
            assert result.core_auth_service == mock_core_auth


class TestChatServiceErrorHandling:
    """Test error handling in ChatService adapter."""

    @pytest.fixture
    def chat_service(self):
        """Create ChatService with error-prone mocks."""
        mock_core_chat = AsyncMock()
        mock_core_auth = AsyncMock()
        return ChatService(
            core_chat_service=mock_core_chat,
            core_auth_service=mock_core_auth,
        )

    @pytest.mark.asyncio
    async def test_chat_completion_propagates_errors(self, chat_service):
        """Test that chat_completion propagates core service errors."""
        user_id = str(uuid4())
        request = ChatRequest(messages=[{"role": "user", "content": "Hello"}])

        # Mock core service to raise an error
        chat_service.core_chat_service.chat_completion.side_effect = Exception(
            "Core service error"
        )

        with pytest.raises(Exception) as exc_info:
            await chat_service.chat_completion(user_id, request)

        assert "Core service error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_session_propagates_errors(self, chat_service):
        """Test that create_session propagates core service errors."""
        user_id = str(uuid4())
        request = SessionCreateRequest(title="Test")

        # Mock core service to raise an error
        chat_service.core_chat_service.create_session.side_effect = Exception(
            "Session creation failed"
        )

        with pytest.raises(Exception) as exc_info:
            await chat_service.create_session(user_id, request)

        assert "Session creation failed" in str(exc_info.value)


class TestChatServiceModelAdaptation:
    """Test model adaptation between API and core schemas."""

    @pytest.fixture
    def chat_service(self):
        """Create ChatService with mocked dependencies."""
        mock_core_chat = AsyncMock()
        mock_core_auth = AsyncMock()
        return ChatService(
            core_chat_service=mock_core_chat,
            core_auth_service=mock_core_auth,
        )

    @pytest.mark.asyncio
    async def test_api_models_are_passed_correctly_to_core(self, chat_service):
        """Test that API models are correctly passed to core service."""
        user_id = str(uuid4())

        # Test ChatRequest adaptation
        chat_request = ChatRequest(
            messages=[{"role": "user", "content": "Hello"}],
            stream=True,
            save_history=True,
        )

        await chat_service.chat_completion(user_id, chat_request)

        # Verify that the request object is passed as-is (thin adapter pattern)
        chat_service.core_chat_service.chat_completion.assert_called_once_with(
            user_id=user_id, request=chat_request
        )

    @pytest.mark.asyncio
    async def test_session_create_request_adaptation(self, chat_service):
        """Test SessionCreateRequest adaptation."""
        user_id = str(uuid4())

        session_request = SessionCreateRequest(
            title="Test Session", metadata={"source": "api"}
        )

        await chat_service.create_session(user_id, session_request)

        # Verify request is passed correctly
        chat_service.core_chat_service.create_session.assert_called_once_with(
            user_id=user_id, request=session_request
        )
