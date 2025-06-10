"""Tests for chat session management endpoints."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
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
def client(mock_settings_and_redis):
    """Create FastAPI test client with comprehensive mocking."""
    # Import test config utilities
    from tests.test_config import MockCacheService, MockDatabaseService
    
    # Create comprehensive mock instances
    mock_cache = MockCacheService()
    mock_db = MockDatabaseService()
    
    # Create a mock principal for authentication
    from tripsage.api.middlewares.authentication import Principal
    mock_principal = Principal(
        id="test-user-123",
        type="user",
        email="test@example.com",
        auth_method="jwt",
        scopes=["chat", "search"],
        metadata={"test": True}
    )
    
    # Mock all Redis connections and services comprehensively
    with (
        # Mock Redis clients at import level
        patch("redis.asyncio.from_url", return_value=AsyncMock()),
        patch("redis.from_url", return_value=MagicMock()),
        
        # Mock all service getters
        patch("tripsage_core.services.infrastructure.cache_service.get_cache_service", 
              return_value=mock_cache),
        patch("tripsage_core.services.infrastructure.database_service.get_database_service", 
              return_value=mock_db),
        
        # Mock settings
        patch("tripsage_core.config.base_app_settings.get_settings", 
              side_effect=lambda: mock_settings_and_redis["settings"]),
        
        # Mock authentication dependencies
        patch("tripsage.api.core.dependencies.require_principal", 
              return_value=mock_principal),
        patch("tripsage.api.core.dependencies.get_current_principal", 
              return_value=mock_principal),
        
        # Mock the app startup lifespan events to avoid MCP initialization
        patch("tripsage_core.mcp_abstraction.mcp_manager.initialize_all_enabled", 
              new_callable=AsyncMock),
        patch("tripsage_core.services.infrastructure.websocket_manager.websocket_manager.start", 
              new_callable=AsyncMock),
        patch("tripsage_core.services.infrastructure.websocket_manager.websocket_manager.stop", 
              new_callable=AsyncMock),
        patch("tripsage_core.mcp_abstraction.mcp_manager.shutdown", 
              new_callable=AsyncMock),
        
        # Mock middleware dependencies to avoid Redis connections
        patch("tripsage.api.middlewares.rate_limiting.DragonflyRateLimiter._ensure_cache", 
              new_callable=AsyncMock),
        patch("tripsage.api.middlewares.rate_limiting.DragonflyRateLimiter.is_rate_limited", 
              return_value=(False, {})),
        
        # Mock Supabase client
        patch("supabase.create_client", return_value=MagicMock()),
    ):
        # Import and create the app after all patches are in place
        from tripsage.api.main import app
        return TestClient(app)


@pytest.fixture
def mock_chat_service():
    """Create a mock chat service."""
    with patch("tripsage_core.services.business.chat_service.get_chat_service") as mock_get:
        # Create an instance mock
        instance = AsyncMock()
        
        # Mock all the chat service methods
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
        
        instance.create_session = AsyncMock()
        instance.list_sessions = AsyncMock(return_value=[])
        instance.get_session = AsyncMock()
        instance.get_messages = AsyncMock(return_value=[])
        instance.create_message = AsyncMock()
        instance.delete_session = AsyncMock(return_value=True)
        
        # Make get_chat_service return our instance
        mock_get.return_value = instance
        yield instance


class TestChatEndpoints:
    """Test cases for chat endpoints that actually exist."""

    def test_chat_endpoint_basic(self, client: TestClient, mock_chat_service):
        """Test basic chat endpoint functionality."""
        # Arrange - mock the chat service response
        mock_service_instance = mock_chat_service
        mock_service_instance.chat_completion.return_value = {
            "content": "I can help you plan your trip!",
            "session_id": str(uuid4()),
            "model": "gpt-4",
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 20,
                "total_tokens": 30
            }
        }

        # Act
        response = client.post(
            "/api/v1/chat/",
            json={
                "messages": [{"role": "user", "content": "Hello"}],
                "stream": False,
            },
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["content"] == "I can help you plan your trip!"
        mock_service_instance.chat_completion.assert_called_once()

    def test_list_sessions_endpoint(self, client: TestClient, mock_chat_service):
        """Test listing chat sessions."""
        # Arrange
        mock_service_instance = mock_chat_service
        mock_sessions = [
            {
                "id": str(uuid4()),
                "title": "Test Session",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        ]
        mock_service_instance.list_sessions.return_value = mock_sessions

        # Act
        response = client.get(
            "/api/v1/chat/sessions",
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == "Test Session"
        mock_service_instance.list_sessions.assert_called_once()

    def test_get_session_endpoint(self, client: TestClient, mock_chat_service):
        """Test getting a specific chat session."""
        # Arrange
        session_id = uuid4()
        mock_service_instance = mock_chat_service
        mock_session = {
            "id": str(session_id),
            "title": "Test Session",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        mock_service_instance.get_session.return_value = mock_session

        # Act
        response = client.get(
            f"/api/v1/chat/sessions/{session_id}",
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == str(session_id)
        assert data["title"] == "Test Session"
        mock_service_instance.get_session.assert_called_once()

    def test_session_not_found(self, client: TestClient, mock_chat_service):
        """Test handling of non-existent session."""
        # Arrange
        session_id = uuid4()
        mock_service_instance = mock_chat_service
        mock_service_instance.get_session.return_value = None

        # Act
        response = client.get(
            f"/api/v1/chat/sessions/{session_id}",
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "Session not found" in data["detail"]

    def test_create_session_endpoint(self, client: TestClient, mock_chat_service):
        """Test creating a new chat session."""
        # Arrange
        mock_service_instance = mock_chat_service
        session_id = uuid4()
        mock_session = {
            "id": str(session_id),
            "title": "New Test Session",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        mock_service_instance.create_session.return_value = mock_session

        # Act
        response = client.post(
            "/api/v1/chat/sessions",
            params={"title": "New Test Session"},
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == str(session_id)
        assert data["title"] == "New Test Session"
        mock_service_instance.create_session.assert_called_once()

    def test_get_session_messages(self, client: TestClient, mock_chat_service):
        """Test getting messages from a session."""
        # Arrange
        session_id = uuid4()
        mock_service_instance = mock_chat_service
        mock_messages = [
            {
                "id": 1,
                "content": "Hello",
                "role": "user",
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
            {
                "id": 2,
                "content": "Hi there!",
                "role": "assistant",
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        ]
        mock_service_instance.get_messages.return_value = mock_messages

        # Act
        response = client.get(
            f"/api/v1/chat/sessions/{session_id}/messages",
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 2
        assert data[0]["role"] == "user"
        assert data[1]["role"] == "assistant"
        mock_service_instance.get_messages.assert_called_once()

    def test_delete_session_endpoint(self, client: TestClient, mock_chat_service):
        """Test deleting a chat session."""
        # Arrange
        session_id = uuid4()
        mock_service_instance = mock_chat_service
        mock_service_instance.delete_session.return_value = True

        # Act
        response = client.delete(
            f"/api/v1/chat/sessions/{session_id}",
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["message"] == "Session deleted successfully"
        mock_service_instance.delete_session.assert_called_once()
