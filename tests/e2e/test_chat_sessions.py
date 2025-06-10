"""Tests for chat session management endpoints."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from tripsage_core.models.db.chat import (
    ChatMessageDB,
    ChatSessionDB,
    ChatSessionWithStats,
    MessageWithTokenEstimate,
    RecentMessagesResponse,
)


@pytest.fixture
def mock_chat_service():
    """Create a mock chat service."""
    with patch("tripsage_core.services.business.chat_service.ChatService") as mock:
        # Create an instance mock
        instance = AsyncMock()
        
        # Mock the chat_completion method to return a proper response
        instance.chat_completion = AsyncMock(
            return_value={
                "content": "I can help you plan your trip!",
                "session_id": str(uuid4()),
                "model": "gpt-4",
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 20,
                    "total_tokens": 30
                }
            }
        )
        
        # Make the class return our instance
        mock.return_value = instance
        yield instance


class TestChatSessionEndpoints:
    """Test cases for chat session endpoints."""

    def test_create_new_session(
        self, client: TestClient, mock_chat_service
    ):
        """Test creating a new chat session on first message."""
        # Arrange
        session_id = uuid4()
        user_id = 1

        # Mock chat service
        mock_service_instance = AsyncMock()
        mock_chat_service.return_value = mock_service_instance

        # Mock create session
        mock_session = ChatSessionDB(
            id=session_id,
            user_id=user_id,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            ended_at=None,
            metadata={},
        )
        mock_service_instance.create_session.return_value = mock_session

        # Mock get recent messages
        mock_service_instance.get_recent_messages.return_value = RecentMessagesResponse(
            messages=[],
            total_tokens=0,
            truncated=False,
        )

        # Mock add message
        mock_service_instance.add_message.return_value = AsyncMock()

        # Act
        response = client.post(
            "/api/chat/",
            json={
                "messages": [{"role": "user", "content": "Hello"}],
                "stream": False,
            },
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "session_id" in data
        assert data["content"] == "I can help you plan your trip!"
        mock_service_instance.create_session.assert_called_once()

    def test_continue_existing_session(
        self, client: TestClient, mock_chat_service
    ):
        """Test continuing an existing chat session."""
        # Arrange
        session_id = uuid4()
        user_id = 1

        # Mock chat service
        mock_service_instance = AsyncMock()
        mock_chat_service.return_value = mock_service_instance

        # Mock get session
        mock_session = ChatSessionDB(
            id=session_id,
            user_id=user_id,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            ended_at=None,
            metadata={},
        )
        mock_service_instance.get_session.return_value = mock_session

        # Mock get recent messages with history
        mock_messages = [
            MessageWithTokenEstimate(
                id=1,
                session_id=session_id,
                role="user",
                content="Hello",
                created_at=datetime.now(timezone.utc),
                metadata={},
                estimated_tokens=2,
            ),
            MessageWithTokenEstimate(
                id=2,
                session_id=session_id,
                role="assistant",
                content="Hi! How can I help?",
                created_at=datetime.now(timezone.utc),
                metadata={},
                estimated_tokens=5,
            ),
        ]
        mock_service_instance.get_recent_messages.return_value = RecentMessagesResponse(
            messages=mock_messages,
            total_tokens=7,
            truncated=False,
        )

        # Mock add message
        mock_service_instance.add_message.return_value = AsyncMock()

        # Act
        response = client.post(
            "/api/chat/",
            json={
                "messages": [{"role": "user", "content": "Plan a trip to Paris"}],
                "session_id": str(session_id),
                "stream": False,
            },
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["session_id"] == str(session_id)
        mock_service_instance.get_session.assert_called_once_with(session_id, user_id)

    def test_session_not_found(self, client: TestClient, mock_chat_service):
        """Test handling of non-existent session."""
        # Arrange
        session_id = uuid4()

        # Mock chat service
        mock_service_instance = AsyncMock()
        mock_chat_service.return_value = mock_service_instance
        mock_service_instance.get_session.side_effect = Exception("Session not found")

        # Act
        response = client.post(
            "/api/chat/",
            json={
                "messages": [{"role": "user", "content": "Hello"}],
                "session_id": str(session_id),
                "stream": False,
            },
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Session not found" in response.json()["detail"]

    def test_streaming_response(
        self, client: TestClient, mock_chat_service
    ):
        """Test streaming chat response."""
        # Arrange
        session_id = uuid4()
        user_id = 1

        # Mock chat service
        mock_service_instance = AsyncMock()
        mock_chat_service.return_value = mock_service_instance

        # Mock create session
        mock_session = ChatSessionDB(
            id=session_id,
            user_id=user_id,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            ended_at=None,
            metadata={},
        )
        mock_service_instance.create_session.return_value = mock_session
        mock_service_instance.get_recent_messages.return_value = RecentMessagesResponse(
            messages=[],
            total_tokens=0,
            truncated=False,
        )
        mock_service_instance.add_message.return_value = AsyncMock()

        # Act
        with client.stream(
            "POST",
            "/api/chat/",
            json={
                "messages": [{"role": "user", "content": "Hello"}],
                "stream": True,
            },
            headers={"Authorization": "Bearer test-token"},
        ) as response:
            # Assert
            assert response.status_code == status.HTTP_200_OK
            assert (
                response.headers["content-type"] == "text/event-stream; charset=utf-8"
            )
            assert "X-Session-Id" in response.headers

            # Read streaming content
            chunks = []
            for chunk in response.iter_text():
                chunks.append(chunk)

            # Should have text chunks and finish message
            assert len(chunks) > 0
            assert any('0:"' in chunk for chunk in chunks)  # Text chunks
            assert any(
                'd:{"finishReason":"stop"' in chunk for chunk in chunks
            )  # Finish

    def test_get_session_history(self, client: TestClient, mock_chat_service):
        """Test getting session history."""
        # Arrange
        session_id = uuid4()
        user_id = 1

        # Mock chat service
        mock_service_instance = AsyncMock()
        mock_chat_service.return_value = mock_service_instance

        # Mock get session
        mock_session = ChatSessionDB(
            id=session_id,
            user_id=user_id,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            ended_at=None,
            metadata={"source": "web"},
        )
        mock_service_instance.get_session.return_value = mock_session

        # Mock get messages
        mock_messages = [
            ChatMessageDB(
                id=1,
                session_id=session_id,
                role="user",
                content="Hello",
                created_at=datetime.now(timezone.utc),
                metadata={},
            ),
            ChatMessageDB(
                id=2,
                session_id=session_id,
                role="assistant",
                content="Hi there!",
                created_at=datetime.now(timezone.utc),
                metadata={},
            ),
        ]
        mock_service_instance.get_messages.return_value = mock_messages

        # Act
        response = client.get(
            f"/api/chat/sessions/{session_id}/history",
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["session_id"] == str(session_id)
        assert len(data["messages"]) == 2
        assert data["messages"][0]["role"] == "user"
        assert data["messages"][1]["role"] == "assistant"
        assert data["metadata"] == {"source": "web"}

    def test_get_active_sessions(self, client: TestClient, mock_chat_service):
        """Test getting active sessions for a user."""
        # Arrange
        user_id = 1
        session_id = uuid4()

        # Mock chat service
        mock_service_instance = AsyncMock()
        mock_chat_service.return_value = mock_service_instance

        # Mock active sessions
        mock_sessions = [
            ChatSessionWithStats(
                id=session_id,
                user_id=user_id,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                ended_at=None,
                metadata={},
                message_count=10,
                last_message_at=datetime.now(timezone.utc),
            )
        ]
        mock_service_instance.get_active_sessions.return_value = mock_sessions

        # Act
        response = client.get(
            "/api/chat/sessions/active?limit=5",
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["sessions"]) == 1
        assert data["sessions"][0]["id"] == str(session_id)
        assert data["sessions"][0]["message_count"] == 10

    def test_end_session(self, client: TestClient, mock_chat_service):
        """Test ending a chat session."""
        # Arrange
        session_id = uuid4()
        user_id = 1

        # Mock chat service
        mock_service_instance = AsyncMock()
        mock_chat_service.return_value = mock_service_instance

        # Mock get session (for verification)
        mock_session = ChatSessionDB(
            id=session_id,
            user_id=user_id,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            ended_at=None,
            metadata={},
        )
        mock_service_instance.get_session.return_value = mock_session

        # Mock end session
        mock_service_instance.end_session.return_value = AsyncMock()

        # Act
        response = client.post(
            f"/api/chat/sessions/{session_id}/end",
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["message"] == "Session ended successfully"
        assert data["session_id"] == str(session_id)
        mock_service_instance.end_session.assert_called_once_with(session_id)

    def test_continue_session_endpoint(
        self, client: TestClient, mock_chat_service
    ):
        """Test the continue session specific endpoint."""
        # Arrange
        session_id = uuid4()
        user_id = 1

        # Mock chat service
        mock_service_instance = AsyncMock()
        mock_chat_service.return_value = mock_service_instance

        # Mock get session
        mock_session = ChatSessionDB(
            id=session_id,
            user_id=user_id,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            ended_at=None,
            metadata={},
        )
        mock_service_instance.get_session.return_value = mock_session
        mock_service_instance.get_recent_messages.return_value = RecentMessagesResponse(
            messages=[],
            total_tokens=0,
            truncated=False,
        )
        mock_service_instance.add_message.return_value = AsyncMock()

        # Act
        response = client.post(
            f"/api/chat/sessions/{session_id}/continue",
            json={
                "messages": [{"role": "user", "content": "What about hotels?"}],
                "stream": False,
            },
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["session_id"] == str(session_id)

    def test_invalid_message_format(self, client: TestClient):
        """Test handling of invalid message format."""
        # Act
        response = client.post(
            "/api/chat/",
            json={
                "messages": [],  # Empty messages
                "stream": False,
            },
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "No messages provided" in response.json()["detail"]

    def test_last_message_not_user(self, client: TestClient):
        """Test that last message must be from user."""
        # Act
        response = client.post(
            "/api/chat/",
            json={
                "messages": [
                    {"role": "user", "content": "Hello"},
                    {
                        "role": "assistant",
                        "content": "Hi",
                    },  # Last message not from user
                ],
                "stream": False,
            },
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Last message must be from user" in response.json()["detail"]
