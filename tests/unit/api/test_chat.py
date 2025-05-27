"""Test chat API endpoints."""

from uuid import uuid4

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from tripsage.api.main import app

client = TestClient(app)


class TestChatAPI:
    """Test chat API endpoints."""

    @pytest.fixture
    def auth_headers(self):
        """Mock authentication headers."""
        return {"Authorization": "Bearer test-token"}

    @pytest.fixture
    def chat_request(self):
        """Sample chat request."""
        return {
            "messages": [{"role": "user", "content": "Help me plan a trip to Paris"}],
            "stream": False,  # Non-streaming for easier testing
        }

    def test_chat_endpoint(self, auth_headers, chat_request, monkeypatch):
        """Test basic chat endpoint."""

        # Mock the authentication dependency
        def mock_get_current_user():
            return "test-user-id"

        monkeypatch.setattr(
            "tripsage.api.routers.chat.get_current_user",
            lambda: mock_get_current_user(),
        )

        # Mock the agent run method
        async def mock_run(self, user_input, context=None):
            return {
                "content": "I'd be happy to help you plan a trip to Paris!",
                "tool_calls": [],
                "status": "success",
            }

        monkeypatch.setattr(
            "tripsage.agents.travel.TravelPlanningAgent.run",
            mock_run,
        )

        # Make request
        response = client.post(
            "/api/v1/chat/",
            json=chat_request,
            headers=auth_headers,
        )

        # Verify response
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "content" in data
        assert "id" in data
        assert data["finish_reason"] == "stop"

    def test_chat_streaming(self, auth_headers, monkeypatch):
        """Test streaming chat endpoint."""

        # Mock dependencies
        def mock_get_current_user():
            return "test-user-id"

        monkeypatch.setattr(
            "tripsage.api.routers.chat.get_current_user",
            lambda: mock_get_current_user(),
        )

        async def mock_run(self, user_input, context=None):
            return {
                "content": "Streaming response test",
                "tool_calls": [],
                "status": "success",
            }

        monkeypatch.setattr(
            "tripsage.agents.travel.TravelPlanningAgent.run",
            mock_run,
        )

        # Request with streaming enabled
        request_data = {
            "messages": [{"role": "user", "content": "Test streaming"}],
            "stream": True,
        }

        response = client.post(
            "/api/v1/chat/",
            json=request_data,
            headers=auth_headers,
        )

        # Verify streaming response
        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
        assert response.headers.get("x-vercel-ai-data-stream") == "v1"

    def test_chat_without_messages(self, auth_headers, monkeypatch):
        """Test chat endpoint without messages."""

        # Mock authentication
        def mock_get_current_user():
            return "test-user-id"

        monkeypatch.setattr(
            "tripsage.api.routers.chat.get_current_user",
            lambda: mock_get_current_user(),
        )

        # Request without messages
        response = client.post(
            "/api/v1/chat/",
            json={"messages": [], "stream": False},
            headers=auth_headers,
        )

        # Should return bad request
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "No messages provided" in response.json()["detail"]

    def test_chat_invalid_role(self, auth_headers, monkeypatch):
        """Test chat endpoint with invalid last message role."""

        # Mock authentication
        def mock_get_current_user():
            return "test-user-id"

        monkeypatch.setattr(
            "tripsage.api.routers.chat.get_current_user",
            lambda: mock_get_current_user(),
        )

        # Request with assistant as last message
        request_data = {
            "messages": [{"role": "assistant", "content": "This is wrong"}],
            "stream": False,
        }

        response = client.post(
            "/api/v1/chat/",
            json=request_data,
            headers=auth_headers,
        )

        # Should return bad request
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Last message must be from user" in response.json()["detail"]

    def test_continue_session(self, auth_headers, chat_request, monkeypatch):
        """Test continuing an existing session."""

        # Mock dependencies
        def mock_get_current_user():
            return "test-user-id"

        monkeypatch.setattr(
            "tripsage.api.routers.chat.get_current_user",
            lambda: mock_get_current_user(),
        )

        async def mock_run(self, user_input, context=None):
            return {
                "content": "Continuing the conversation...",
                "tool_calls": [],
                "status": "success",
            }

        monkeypatch.setattr(
            "tripsage.agents.travel.TravelPlanningAgent.run",
            mock_run,
        )

        # Continue session
        session_id = str(uuid4())
        response = client.post(
            f"/api/v1/chat/sessions/{session_id}/continue",
            json=chat_request,
            headers=auth_headers,
        )

        # Verify response
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "content" in data

    def test_get_session_history(self, auth_headers, monkeypatch):
        """Test getting session history."""

        # Mock authentication
        def mock_get_current_user():
            return "test-user-id"

        monkeypatch.setattr(
            "tripsage.api.routers.chat.get_current_user",
            lambda: mock_get_current_user(),
        )

        # Get session history
        session_id = str(uuid4())
        response = client.get(
            f"/api/v1/chat/sessions/{session_id}/history",
            headers=auth_headers,
        )

        # Verify response
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["session_id"] == session_id
        assert "messages" in data
        assert isinstance(data["messages"], list)
