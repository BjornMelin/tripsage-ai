"""Comprehensive unit tests for chat router."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from tests.factories import ChatFactory
from tripsage.api.main import app


class TestChatRouter:
    """Test suite for chat router endpoints."""

    def setup_method(self):
        """Set up test client and mocks."""
        self.client = TestClient(app)
        self.mock_service = Mock()
        self.sample_chat_response = ChatFactory.create_response()

    @patch("tripsage.api.routers.chat.get_chat_service_dep")
    @patch("tripsage.api.routers.chat.require_principal_dep")
    def test_chat_success(self, mock_auth, mock_service_dep):
        """Test successful chat interaction."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")
        mock_service_dep.return_value = self.mock_service
        self.mock_service.process_message = AsyncMock(
            return_value=self.sample_chat_response
        )

        chat_request = {
            "message": "Help me plan a trip to Tokyo",
            "session_id": "test-session-id",
            "context": {"user_preferences": {"budget": "medium"}},
        }

        # Act
        response = self.client.post(
            "/api/chat/",
            json=chat_request,
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "response" in data
        assert "session_id" in data
        assert data["session_id"] == "test-session-id"

    @patch("tripsage.api.routers.chat.get_chat_service_dep")
    @patch("tripsage.api.routers.chat.require_principal_dep")
    def test_chat_empty_message(self, mock_auth, mock_service_dep):
        """Test chat with empty message."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")
        mock_service_dep.return_value = self.mock_service

        chat_request = {"message": "", "session_id": "test-session-id"}

        # Act
        response = self.client.post(
            "/api/chat/",
            json=chat_request,
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @patch("tripsage.api.routers.chat.get_chat_service_dep")
    @patch("tripsage.api.routers.chat.require_principal_dep")
    def test_chat_service_error(self, mock_auth, mock_service_dep):
        """Test chat with service error."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")
        mock_service_dep.return_value = self.mock_service
        self.mock_service.process_message = AsyncMock(
            side_effect=Exception("AI service unavailable")
        )

        chat_request = {
            "message": "Help me plan a trip",
            "session_id": "test-session-id",
        }

        # Act
        response = self.client.post(
            "/api/chat/",
            json=chat_request,
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    def test_chat_unauthorized(self):
        """Test chat without authentication."""
        chat_request = {
            "message": "Help me plan a trip",
            "session_id": "test-session-id",
        }

        response = self.client.post("/api/chat/", json=chat_request)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @patch("tripsage.api.routers.chat.get_chat_service_dep")
    @patch("tripsage.api.routers.chat.require_principal_dep")
    def test_chat_with_tool_calls(self, mock_auth, mock_service_dep):
        """Test chat response with tool calls."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")
        mock_service_dep.return_value = self.mock_service
        response_with_tools = {
            **self.sample_chat_response,
            "tool_calls": [
                {
                    "function": "search_flights",
                    "arguments": {"destination": "Tokyo", "date": "2024-03-15"},
                }
            ],
        }
        self.mock_service.process_message = AsyncMock(return_value=response_with_tools)

        chat_request = {
            "message": "Find flights to Tokyo for March 15th",
            "session_id": "test-session-id",
        }

        # Act
        response = self.client.post(
            "/api/chat/",
            json=chat_request,
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "tool_calls" in data
        assert len(data["tool_calls"]) == 1
        assert data["tool_calls"][0]["function"] == "search_flights"

    @pytest.mark.parametrize("message_length", [5001, 10000])
    def test_chat_message_too_long(self, message_length):
        """Test chat with excessively long message."""
        chat_request = {
            "message": "x" * message_length,
            "session_id": "test-session-id",
        }

        response = self.client.post(
            "/api/chat/",
            json=chat_request,
            headers={"Authorization": "Bearer test-token"},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @patch("tripsage.api.routers.chat.get_chat_service_dep")
    @patch("tripsage.api.routers.chat.require_principal_dep")
    def test_chat_with_memory_context(self, mock_auth, mock_service_dep):
        """Test chat with memory context retrieval."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")
        mock_service_dep.return_value = self.mock_service
        response_with_memory = {
            **self.sample_chat_response,
            "memory_context": {
                "previous_destinations": ["Paris", "London"],
                "travel_preferences": {"budget": "luxury"},
            },
        }
        self.mock_service.process_message = AsyncMock(return_value=response_with_memory)

        chat_request = {
            "message": "What about another trip similar to my last one?",
            "session_id": "test-session-id",
            "use_memory": True,
        }

        # Act
        response = self.client.post(
            "/api/chat/",
            json=chat_request,
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "memory_context" in data
        assert "previous_destinations" in data["memory_context"]

    @patch("tripsage.api.routers.chat.get_chat_service_dep")
    @patch("tripsage.api.routers.chat.require_principal_dep")
    def test_chat_streaming_response(self, mock_auth, mock_service_dep):
        """Test chat with streaming response."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")
        mock_service_dep.return_value = self.mock_service
        streaming_response = {
            **self.sample_chat_response,
            "streaming": True,
            "stream_id": "stream-123",
        }
        self.mock_service.process_message = AsyncMock(return_value=streaming_response)

        chat_request = {
            "message": "Plan a detailed itinerary for Tokyo",
            "session_id": "test-session-id",
            "stream": True,
        }

        # Act
        response = self.client.post(
            "/api/chat/",
            json=chat_request,
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["streaming"] is True
        assert "stream_id" in data
