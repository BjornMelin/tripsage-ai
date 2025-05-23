"""Tests for chat API endpoints."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import status
from httpx import AsyncClient

from tripsage.models.db.chat import ChatMessageDB, ChatSessionDB
from tripsage.models.db.user import UserDB


@pytest.mark.asyncio
class TestChatEndpoints:
    """Test cases for chat API endpoints."""

    @pytest.fixture
    def mock_user(self):
        """Create a mock user."""
        return UserDB(
            id=1,
            email="test@example.com",
            username="testuser",
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

    @pytest.fixture
    def auth_headers(self):
        """Create authentication headers."""
        return {"Authorization": "Bearer test-token"}

    async def test_chat_create_new_session(
        self, client: AsyncClient, auth_headers, mock_user
    ):
        """Test creating a new chat session."""
        with patch(
            "tripsage.api.routers.chat.get_current_user", return_value=mock_user
        ):
            with patch("tripsage.api.routers.chat.get_chat_service") as mock_service:
                # Mock chat service
                mock_session = ChatSessionDB(
                    id=uuid4(),
                    user_id=mock_user.id,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                    ended_at=None,
                    metadata={},
                )
                mock_service.return_value.create_session = AsyncMock(
                    return_value=mock_session
                )
                mock_service.return_value.add_message = AsyncMock()
                mock_service.return_value.get_recent_messages = AsyncMock(
                    return_value=MagicMock(messages=[], total_tokens=0, truncated=False)
                )

                # Mock agent response
                with patch("tripsage.api.routers.chat.get_travel_agent") as mock_agent:
                    mock_agent.return_value.run = AsyncMock(
                        return_value={
                            "content": "Hello! How can I help you plan your trip?",
                            "tool_calls": [],
                        }
                    )

                    # Send request
                    response = await client.post(
                        "/api/chat/",
                        headers=auth_headers,
                        json={
                            "messages": [{"role": "user", "content": "Hello"}],
                            "stream": False,
                        },
                    )

                    assert response.status_code == status.HTTP_200_OK
                    data = response.json()
                    assert "content" in data
                    assert (
                        data["content"] == "Hello! How can I help you plan your trip?"
                    )

    async def test_chat_continue_session(
        self, client: AsyncClient, auth_headers, mock_user
    ):
        """Test continuing an existing chat session."""
        session_id = uuid4()

        with patch(
            "tripsage.api.routers.chat.get_current_user", return_value=mock_user
        ):
            with patch("tripsage.api.routers.chat.get_chat_service") as mock_service:
                # Mock chat service
                mock_session = ChatSessionDB(
                    id=session_id,
                    user_id=mock_user.id,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                    ended_at=None,
                    metadata={},
                )
                mock_service.return_value.get_session = AsyncMock(
                    return_value=mock_session
                )
                mock_service.return_value.add_message = AsyncMock()
                mock_service.return_value.get_recent_messages = AsyncMock(
                    return_value=MagicMock(
                        messages=[
                            MagicMock(role="user", content="Hello"),
                            MagicMock(role="assistant", content="Hi there!"),
                        ],
                        total_tokens=10,
                        truncated=False,
                    )
                )

                # Mock agent response
                with patch("tripsage.api.routers.chat.get_travel_agent") as mock_agent:
                    mock_agent.return_value.run = AsyncMock(
                        return_value={
                            "content": "Sure, I can help with that!",
                            "tool_calls": [],
                        }
                    )

                    # Send request
                    response = await client.post(
                        f"/api/chat/sessions/{session_id}/continue",
                        headers=auth_headers,
                        json={
                            "messages": [
                                {"role": "user", "content": "Plan a trip to Paris"}
                            ],
                            "stream": False,
                        },
                    )

                    assert response.status_code == status.HTTP_200_OK
                    data = response.json()
                    assert str(data["id"]) == str(session_id)

    async def test_chat_rate_limit_exceeded(
        self, client: AsyncClient, auth_headers, mock_user
    ):
        """Test rate limit handling."""
        with patch(
            "tripsage.api.routers.chat.get_current_user", return_value=mock_user
        ):
            with patch("tripsage.api.routers.chat.get_chat_service") as mock_service:
                # Mock rate limit error
                mock_service.return_value.create_session = AsyncMock()
                mock_service.return_value.add_message = AsyncMock(
                    side_effect=Exception(
                        "Rate limit exceeded. Maximum 10 messages per 60 seconds."
                    )
                )

                # Send request
                response = await client.post(
                    "/api/chat/",
                    headers=auth_headers,
                    json={
                        "messages": [{"role": "user", "content": "Hello"}],
                        "stream": False,
                    },
                )

                assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS

    async def test_get_session_history(
        self, client: AsyncClient, auth_headers, mock_user
    ):
        """Test getting session history."""
        session_id = uuid4()

        with patch(
            "tripsage.api.routers.chat.get_current_user", return_value=mock_user
        ):
            with patch("tripsage.api.routers.chat.get_chat_service") as mock_service:
                # Mock session and messages
                mock_session = ChatSessionDB(
                    id=session_id,
                    user_id=mock_user.id,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                    ended_at=None,
                    metadata={"agent": "travel_planning"},
                )
                mock_messages = [
                    ChatMessageDB(
                        id=1,
                        session_id=session_id,
                        role="user",
                        content="Hello",
                        created_at=datetime.utcnow(),
                        metadata={},
                    ),
                    ChatMessageDB(
                        id=2,
                        session_id=session_id,
                        role="assistant",
                        content="Hi! How can I help?",
                        created_at=datetime.utcnow(),
                        metadata={},
                    ),
                ]

                mock_service.return_value.get_session = AsyncMock(
                    return_value=mock_session
                )
                mock_service.return_value.get_messages = AsyncMock(
                    return_value=mock_messages
                )

                # Send request
                response = await client.get(
                    f"/api/chat/sessions/{session_id}/history",
                    headers=auth_headers,
                )

                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert str(data["session_id"]) == str(session_id)
                assert len(data["messages"]) == 2
                assert data["messages"][0]["role"] == "user"
                assert data["messages"][1]["role"] == "assistant"

    async def test_list_sessions(self, client: AsyncClient, auth_headers, mock_user):
        """Test listing active sessions."""
        with patch(
            "tripsage.api.routers.chat.get_current_user", return_value=mock_user
        ):
            with patch("tripsage.api.routers.chat.get_chat_service") as mock_service:
                # Mock sessions
                mock_sessions = [
                    MagicMock(
                        id=uuid4(),
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                        message_count=5,
                        last_message_at=datetime.utcnow(),
                        metadata={},
                    ),
                    MagicMock(
                        id=uuid4(),
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                        message_count=3,
                        last_message_at=None,
                        metadata={},
                    ),
                ]

                mock_service.return_value.get_active_sessions = AsyncMock(
                    return_value=mock_sessions
                )

                # Send request
                response = await client.get(
                    "/api/chat/sessions",
                    headers=auth_headers,
                )

                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert len(data["sessions"]) == 2
                assert data["sessions"][0]["message_count"] == 5
                assert data["sessions"][1]["message_count"] == 3

    async def test_end_session(self, client: AsyncClient, auth_headers, mock_user):
        """Test ending a chat session."""
        session_id = uuid4()

        with patch(
            "tripsage.api.routers.chat.get_current_user", return_value=mock_user
        ):
            with patch("tripsage.api.routers.chat.get_chat_service") as mock_service:
                # Mock session
                mock_session = ChatSessionDB(
                    id=session_id,
                    user_id=mock_user.id,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                    ended_at=None,
                    metadata={},
                )

                mock_service.return_value.get_session = AsyncMock(
                    return_value=mock_session
                )
                mock_service.return_value.end_session = AsyncMock()

                # Send request
                response = await client.post(
                    f"/api/chat/sessions/{session_id}/end",
                    headers=auth_headers,
                )

                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert data["message"] == "Session ended successfully"
                assert str(data["session_id"]) == str(session_id)

    async def test_chat_session_not_found(
        self, client: AsyncClient, auth_headers, mock_user
    ):
        """Test accessing non-existent session."""
        session_id = uuid4()

        with patch(
            "tripsage.api.routers.chat.get_current_user", return_value=mock_user
        ):
            with patch("tripsage.api.routers.chat.get_chat_service") as mock_service:
                # Mock session not found
                mock_service.return_value.get_session = AsyncMock(
                    side_effect=Exception("Not found")
                )

                # Send request
                response = await client.get(
                    f"/api/chat/sessions/{session_id}/history",
                    headers=auth_headers,
                )

                assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_chat_streaming_response(
        self, client: AsyncClient, auth_headers, mock_user
    ):
        """Test streaming chat response."""
        with patch(
            "tripsage.api.routers.chat.get_current_user", return_value=mock_user
        ):
            with patch("tripsage.api.routers.chat.get_chat_service") as mock_service:
                # Mock chat service
                mock_session = ChatSessionDB(
                    id=uuid4(),
                    user_id=mock_user.id,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                    ended_at=None,
                    metadata={},
                )
                mock_service.return_value.create_session = AsyncMock(
                    return_value=mock_session
                )
                mock_service.return_value.add_message = AsyncMock()
                mock_service.return_value.get_recent_messages = AsyncMock(
                    return_value=MagicMock(messages=[], total_tokens=0, truncated=False)
                )

                # Mock agent response
                with patch("tripsage.api.routers.chat.get_travel_agent") as mock_agent:
                    mock_agent.return_value.run = AsyncMock(
                        return_value={
                            "content": "Streaming response test",
                            "tool_calls": [],
                        }
                    )

                    # Send request with streaming enabled
                    response = await client.post(
                        "/api/chat/",
                        headers=auth_headers,
                        json={
                            "messages": [{"role": "user", "content": "Hello"}],
                            "stream": True,
                        },
                    )

                    assert response.status_code == status.HTTP_200_OK
                    assert (
                        response.headers["content-type"]
                        == "text/event-stream; charset=utf-8"
                    )
                    assert response.headers.get("x-vercel-ai-data-stream") == "v1"
                    assert response.headers.get("x-session-id") is not None
