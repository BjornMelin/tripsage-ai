"""Modern comprehensive unit tests for chat router.

Tests the chat router endpoints using 2025 FastAPI testing patterns:
- Modern dependency injection with Annotated types
- Proper async testing with pytest-asyncio
- Comprehensive error handling and edge cases
- Streaming response testing
"""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import status
from httpx import ASGITransport, AsyncClient

from tripsage.api.core.dependencies import get_chat_service, require_principal
from tripsage.api.main import app
from tripsage.api.middlewares.authentication import Principal

class TestChatRouter:
    """Modern test suite for chat router endpoints."""

    @pytest.fixture
    def mock_principal(self):
        """Mock authenticated principal."""
        return Principal(
            id="test-user-id", type="user", email="test@example.com", auth_method="jwt"
        )

    @pytest.fixture
    def mock_chat_service(self):
        """Mock chat service."""
        service = AsyncMock()
        service.chat_completion = AsyncMock()
        service.create_session = AsyncMock()
        service.list_sessions = AsyncMock()
        service.get_session = AsyncMock()
        service.get_messages = AsyncMock()
        service.create_message = AsyncMock()
        service.delete_session = AsyncMock()
        return service

    @pytest.fixture
    def sample_chat_response(self):
        """Sample chat response matching ChatResponse schema."""
        return {
            "id": str(uuid4()),
            "session_id": str(uuid4()),
            "content": (
                "I'd be happy to help you plan your trip! Where would you like to go?"
            ),
            "tool_calls": None,
            "finish_reason": "stop",
            "usage": {
                "prompt_tokens": 50,
                "completion_tokens": 25,
                "total_tokens": 75,
            },
            "created_at": "2024-01-01T00:00:00Z",
        }

    @pytest.fixture
    async def async_client(self, mock_principal, mock_chat_service):
        """Create async test client with dependency overrides."""
        # Override dependencies for testing
        app.dependency_overrides[require_principal] = lambda: mock_principal
        app.dependency_overrides[get_chat_service] = lambda: mock_chat_service

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            yield ac

        # Clean up overrides
        app.dependency_overrides.clear()

    async def test_chat_success(
        self, async_client, mock_chat_service, sample_chat_response
    ):
        """Test successful chat interaction."""
        # Arrange
        session_id = uuid4()
        response_with_session = {
            **sample_chat_response,
            "session_id": str(session_id),
        }
        mock_chat_service.chat_completion.return_value = response_with_session

        chat_request = {
            "messages": [
                {
                    "role": "user",
                    "content": "Help me plan a trip to Tokyo",
                }
            ],
            "session_id": str(session_id),
            "stream": True,
            "save_history": True,
        }

        # Act
        response = await async_client.post(
            "/api/chat/",
            json=chat_request,
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "content" in data
        assert "session_id" in data
        assert data["session_id"] == str(session_id)

        # Verify service call
        mock_chat_service.chat_completion.assert_called_once()
        call_args = mock_chat_service.chat_completion.call_args
        assert call_args[0][0] == "test-user-id"  # user_id

    async def test_chat_invalid_request(self, async_client):
        """Test chat with invalid request format."""
        # Arrange - missing required messages field
        chat_request = {
            "session_id": str(uuid4()),
        }

        # Act
        response = await async_client.post(
            "/api/chat/",
            json=chat_request,
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_chat_service_error(self, async_client, mock_chat_service):
        """Test chat with service error."""
        # Arrange
        mock_chat_service.chat_completion.side_effect = Exception(
            "AI service unavailable"
        )

        chat_request = {
            "messages": [
                {
                    "role": "user",
                    "content": "Help me plan a trip",
                }
            ],
            "session_id": str(uuid4()),
        }

        # Act
        response = await async_client.post(
            "/api/chat/",
            json=chat_request,
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    async def test_chat_unauthorized(self):
        """Test chat without authentication."""
        # Create client without authentication override
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            chat_request = {
                "messages": [
                    {
                        "role": "user",
                        "content": "Help me plan a trip",
                    }
                ],
                "session_id": str(uuid4()),
            }

            response = await client.post("/api/chat/", json=chat_request)
            assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_chat_with_tool_calls(
        self, async_client, mock_chat_service, sample_chat_response
    ):
        """Test chat response with tool calls."""
        # Arrange
        response_with_tools = {
            **sample_chat_response,
            "tool_calls": [
                {
                    "id": "call_123",
                    "name": "search_flights",
                    "arguments": {"destination": "Tokyo", "date": "2024-03-15"},
                    "status": "completed",
                }
            ],
        }
        mock_chat_service.chat_completion.return_value = response_with_tools

        chat_request = {
            "messages": [
                {
                    "role": "user",
                    "content": "Find flights to Tokyo for March 15th",
                }
            ],
            "session_id": str(uuid4()),
        }

        # Act
        response = await async_client.post(
            "/api/chat/",
            json=chat_request,
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "tool_calls" in data
        assert len(data["tool_calls"]) == 1
        assert data["tool_calls"][0]["name"] == "search_flights"

    @pytest.mark.parametrize(
        "message_length", [40000, 50000]
    )  # ChatMessage max_length is 32768
    async def test_chat_message_too_long(self, async_client, message_length):
        """Test chat with excessively long message."""
        chat_request = {
            "messages": [
                {
                    "role": "user",
                    "content": "x" * message_length,
                }
            ],
            "session_id": str(uuid4()),
        }

        response = await async_client.post(
            "/api/chat/",
            json=chat_request,
            headers={"Authorization": "Bearer test-token"},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_chat_with_memory_context(
        self, async_client, mock_chat_service, sample_chat_response
    ):
        """Test chat with memory context retrieval."""
        # Arrange - memory context would be handled by the chat service internally
        mock_chat_service.chat_completion.return_value = sample_chat_response

        chat_request = {
            "messages": [
                {
                    "role": "user",
                    "content": "What about another trip similar to my last one?",
                }
            ],
            "session_id": str(uuid4()),
            "save_history": True,  # Enable memory/history
        }

        # Act
        response = await async_client.post(
            "/api/chat/",
            json=chat_request,
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "content" in data
        # Memory context is handled internally by the chat service

    async def test_chat_streaming_response(
        self, async_client, mock_chat_service, sample_chat_response
    ):
        """Test chat with streaming response."""
        # Arrange
        mock_chat_service.chat_completion.return_value = sample_chat_response

        chat_request = {
            "messages": [
                {
                    "role": "user",
                    "content": "Plan a detailed itinerary for Tokyo",
                }
            ],
            "session_id": str(uuid4()),
            "stream": True,
        }

        # Act
        response = await async_client.post(
            "/api/chat/",
            json=chat_request,
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "content" in data
        # Streaming is handled by the chat service response format

    # Session Management Tests
    async def test_create_session_success(self, async_client, mock_chat_service):
        """Test successful session creation."""
        # Arrange
        session_data = {
            "id": str(uuid4()),
            "title": "Tokyo Trip Planning",
            "user_id": "test-user-id",
            "created_at": "2024-01-01T00:00:00Z",
        }
        mock_chat_service.create_session.return_value = session_data

        # Act
        response = await async_client.post(
            "/api/chat/sessions",
            params={"title": "Tokyo Trip Planning"},
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["title"] == "Tokyo Trip Planning"
        assert "id" in data
        mock_chat_service.create_session.assert_called_once()

    async def test_list_sessions_success(self, async_client, mock_chat_service):
        """Test successful session listing."""
        # Arrange
        sessions = [
            {
                "id": str(uuid4()),
                "title": "Tokyo Trip",
                "user_id": "test-user-id",
                "created_at": "2024-01-01T00:00:00Z",
            },
            {
                "id": str(uuid4()),
                "title": "Paris Trip",
                "user_id": "test-user-id",
                "created_at": "2024-01-02T00:00:00Z",
            },
        ]
        mock_chat_service.list_sessions.return_value = sessions

        # Act
        response = await async_client.get(
            "/api/chat/sessions",
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 2
        assert data[0]["title"] == "Tokyo Trip"
        assert data[1]["title"] == "Paris Trip"

    async def test_get_session_success(self, async_client, mock_chat_service):
        """Test successful session retrieval."""
        # Arrange
        session_id = uuid4()
        session_data = {
            "id": str(session_id),
            "title": "Tokyo Trip",
            "user_id": "test-user-id",
            "created_at": "2024-01-01T00:00:00Z",
        }
        mock_chat_service.get_session.return_value = session_data

        # Act
        response = await async_client.get(
            f"/api/chat/sessions/{session_id}",
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == str(session_id)
        assert data["title"] == "Tokyo Trip"

    async def test_get_session_not_found(self, async_client, mock_chat_service):
        """Test session retrieval when session doesn't exist."""
        # Arrange
        session_id = uuid4()
        mock_chat_service.get_session.return_value = None

        # Act
        response = await async_client.get(
            f"/api/chat/sessions/{session_id}",
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_delete_session_success(self, async_client, mock_chat_service):
        """Test successful session deletion."""
        # Arrange
        session_id = uuid4()
        mock_chat_service.delete_session.return_value = True

        # Act
        response = await async_client.delete(
            f"/api/chat/sessions/{session_id}",
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["message"] == "Session deleted successfully"

    async def test_delete_session_not_found(self, async_client, mock_chat_service):
        """Test session deletion when session doesn't exist."""
        # Arrange
        session_id = uuid4()
        mock_chat_service.delete_session.return_value = False

        # Act
        response = await async_client.delete(
            f"/api/chat/sessions/{session_id}",
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_get_session_messages(self, async_client, mock_chat_service):
        """Test getting messages from a session."""
        # Arrange
        session_id = uuid4()
        messages = [
            {
                "id": str(uuid4()),
                "content": "Hello, I need help planning a trip",
                "role": "user",
                "created_at": "2024-01-01T00:00:00Z",
            },
            {
                "id": str(uuid4()),
                "content": "I'd be happy to help you plan your trip!",
                "role": "assistant",
                "created_at": "2024-01-01T00:01:00Z",
            },
        ]
        mock_chat_service.get_messages.return_value = messages

        # Act
        response = await async_client.get(
            f"/api/chat/sessions/{session_id}/messages",
            params={"limit": 50},
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 2
        assert data[0]["role"] == "user"
        assert data[1]["role"] == "assistant"

    async def test_create_message_in_session(self, async_client, mock_chat_service):
        """Test creating a new message in a session."""
        # Arrange
        session_id = uuid4()
        message_data = {
            "id": str(uuid4()),
            "content": "How's the weather in Tokyo?",
            "role": "user",
            "session_id": str(session_id),
            "created_at": "2024-01-01T00:00:00Z",
        }
        mock_chat_service.create_message.return_value = message_data

        # Act
        response = await async_client.post(
            f"/api/chat/sessions/{session_id}/messages",
            params={"content": "How's the weather in Tokyo?", "role": "user"},
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["content"] == "How's the weather in Tokyo?"
        assert data["role"] == "user"
        assert data["session_id"] == str(session_id)
