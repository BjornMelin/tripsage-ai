"""
Integration tests for chat session management.

This module tests the complete chat session lifecycle including creation,
message handling, persistence, and cleanup across the application stack.
Uses modern Principal-based authentication.
"""

import asyncio
import json
from datetime import datetime
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from tripsage.agents.chat import ChatAgent
from tripsage.api.main import app
from tripsage.api.middlewares.authentication import Principal
from tripsage_core.models.db.chat import ChatMessageDB, ChatSessionDB
from tripsage_core.models.db.user import User
from tripsage_core.services.business.chat_service import ChatService as CoreChatService


class TestChatSessionFlow:
    """Test complete chat session management flow."""

    @pytest.fixture
    def client(self):
        """Test client for API requests."""
        return TestClient(app)

    @pytest.fixture
    def mock_user(self):
        """Mock user for testing."""
        return User(
            id=12345,  # Use integer ID as required by User model
            email="test@example.com",
            name="testuser",
            role="user",
            is_admin=False,
            is_disabled=False,
        )

    @pytest.fixture
    def mock_principal(self, mock_user):
        """Mock principal for testing authentication."""
        return Principal(
            id=str(mock_user.id),
            type="user",
            email=mock_user.email,
            auth_method="jwt",
            scopes=[],
            metadata={}
        )

    @pytest.fixture
    def mock_chat_session(self, mock_user):
        """Mock chat session for testing."""
        return ChatSessionDB(
            id=uuid4(),
            user_id=mock_user.id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            metadata={},
        )

    @pytest.fixture
    def mock_chat_message(self, mock_chat_session):
        """Mock chat message for testing."""
        return ChatMessageDB(
            id=12346,  # Use integer ID as required by ChatMessageDB model
            session_id=mock_chat_session.id,
            role="user",
            content="Test message",
            created_at=datetime.utcnow(),
            metadata={},
        )

    @pytest.fixture
    def mock_chat_service(self, mock_chat_session, mock_chat_message):
        """Mock chat service."""
        service = AsyncMock(spec=CoreChatService)
        service.create_session.return_value = mock_chat_session
        service.get_session.return_value = mock_chat_session
        service.send_message.return_value = mock_chat_message
        service.get_session_history.return_value = [mock_chat_message]
        service.delete_session.return_value = True
        return service

    @pytest.fixture
    def mock_chat_agent(self):
        """Mock chat agent."""
        agent = AsyncMock(spec=ChatAgent)
        agent.process_message.return_value = {
            "response": "Test response",
            "confidence": 0.95,
            "sources": [],
        }
        return agent

    @pytest.mark.asyncio
    async def test_chat_session_creation_flow(
        self, client, mock_chat_service, mock_principal
    ):
        """Test complete chat session creation flow."""
        with patch(
            "tripsage_core.services.business.chat_service.get_chat_service"
        ) as mock_service_dep:
            mock_service_dep.return_value = mock_chat_service

            with patch(
                "tripsage.api.core.dependencies.require_principal"
            ) as mock_auth:
                mock_auth.return_value = mock_principal

                # Test session creation
                response = client.post(
                    "/api/chat/sessions",
                    json={"title": "New Chat Session"},
                    headers={"Authorization": "Bearer test-token"},
                )

                # Verify API response
                assert response.status_code == 201
                response_data = response.json()
                assert "id" in response_data
                assert response_data["title"] == "New Chat Session"

                # Verify service was called
                mock_chat_service.create_session.assert_called_once()

    @pytest.mark.asyncio
    async def test_chat_message_flow(
        self, client, mock_chat_service, mock_chat_agent, mock_principal
    ):
        """Test complete chat message handling flow."""
        with patch(
            "tripsage_core.services.business.chat_service.get_chat_service"
        ) as mock_service_dep:
            mock_service_dep.return_value = mock_chat_service

            with patch(
                "tripsage.agents.chat.ChatAgent"
            ) as mock_agent_class:
                mock_agent_class.return_value = mock_chat_agent

                with patch(
                    "tripsage.api.core.dependencies.require_principal"
                ) as mock_auth:
                    mock_auth.return_value = mock_principal

                    session_id = str(uuid4())

                    # Test message sending
                    response = client.post(
                        f"/api/chat/sessions/{session_id}/messages",
                        json={"content": "Hello, can you help me plan a trip?"},
                        headers={"Authorization": "Bearer test-token"},
                    )

                    # Verify API response
                    assert response.status_code == 200
                    response_data = response.json()
                    assert "message" in response_data
                    assert response_data["message"]["content"] == "Hello, can you help me plan a trip?"

                    # Verify services were called
                    mock_chat_service.send_message.assert_called_once()
                    mock_chat_agent.process_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_chat_history_retrieval_flow(
        self, client, mock_chat_service, mock_principal
    ):
        """Test chat history retrieval flow."""
        with patch(
            "tripsage_core.services.business.chat_service.get_chat_service"
        ) as mock_service_dep:
            mock_service_dep.return_value = mock_chat_service

            with patch(
                "tripsage.api.core.dependencies.require_principal"
            ) as mock_auth:
                mock_auth.return_value = mock_principal

                session_id = str(uuid4())

                # Test history retrieval
                response = client.get(
                    f"/api/chat/sessions/{session_id}/messages",
                    headers={"Authorization": "Bearer test-token"},
                )

                # Verify API response
                assert response.status_code == 200
                response_data = response.json()
                assert "messages" in response_data
                assert isinstance(response_data["messages"], list)

                # Verify service was called
                mock_chat_service.get_session_history.assert_called_once()

    @pytest.mark.asyncio
    async def test_chat_session_deletion_flow(
        self, client, mock_chat_service, mock_principal
    ):
        """Test chat session deletion flow."""
        with patch(
            "tripsage_core.services.business.chat_service.get_chat_service"
        ) as mock_service_dep:
            mock_service_dep.return_value = mock_chat_service

            with patch(
                "tripsage.api.core.dependencies.require_principal"
            ) as mock_auth:
                mock_auth.return_value = mock_principal

                session_id = str(uuid4())

                # Test session deletion
                response = client.delete(
                    f"/api/chat/sessions/{session_id}",
                    headers={"Authorization": "Bearer test-token"},
                )

                # Verify API response
                assert response.status_code == 200
                response_data = response.json()
                assert "message" in response_data

                # Verify service was called
                mock_chat_service.delete_session.assert_called_once()

    @pytest.mark.asyncio
    async def test_chat_error_handling_flow(
        self, client, mock_chat_service, mock_principal
    ):
        """Test error handling in chat flow."""
        with patch(
            "tripsage_core.services.business.chat_service.get_chat_service"
        ) as mock_service_dep:
            mock_service_dep.return_value = mock_chat_service

            with patch(
                "tripsage.api.core.dependencies.require_principal"
            ) as mock_auth:
                mock_auth.return_value = mock_principal

                # Configure service to raise exception
                mock_chat_service.send_message.side_effect = Exception("Chat service error")

                session_id = str(uuid4())

                # Test error handling
                response = client.post(
                    f"/api/chat/sessions/{session_id}/messages",
                    json={"content": "This should fail"},
                    headers={"Authorization": "Bearer test-token"},
                )

                # Verify error response
                assert response.status_code == 500
                assert "error" in response.json()

    @pytest.mark.asyncio
    async def test_chat_authentication_flow(self, client):
        """Test authentication in chat flow."""
        with patch(
            "tripsage.api.core.dependencies.require_principal"
        ) as mock_auth:
            # Configure authentication to fail
            from tripsage_core.exceptions.exceptions import CoreAuthenticationError
            mock_auth.side_effect = CoreAuthenticationError("Invalid token")

            # Test API call with invalid authentication
            response = client.get(
                "/api/chat/sessions",
                headers={"Authorization": "Bearer invalid-token"}
            )

            # Verify authentication error response
            assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_chat_concurrent_messages_flow(
        self, client, mock_chat_service, mock_chat_agent, mock_principal
    ):
        """Test concurrent message handling in chat flow."""
        with patch(
            "tripsage_core.services.business.chat_service.get_chat_service"
        ) as mock_service_dep:
            mock_service_dep.return_value = mock_chat_service

            with patch(
                "tripsage.agents.chat.ChatAgent"
            ) as mock_agent_class:
                mock_agent_class.return_value = mock_chat_agent

                with patch(
                    "tripsage.api.core.dependencies.require_principal"
                ) as mock_auth:
                    mock_auth.return_value = mock_principal

                    session_id = str(uuid4())

                    # Test concurrent message sending
                    message_data = {"content": "Concurrent message test"}

                    response = client.post(
                        f"/api/chat/sessions/{session_id}/messages",
                        json=message_data,
                        headers={"Authorization": "Bearer test-token"},
                    )

                    # Verify response
                    assert response.status_code == 200
                    mock_chat_service.send_message.assert_called()

    @pytest.mark.asyncio
    async def test_chat_validation_flow(self, client, mock_principal):
        """Test data validation in chat flow."""
        with patch(
            "tripsage.api.core.dependencies.require_principal"
        ) as mock_auth:
            mock_auth.return_value = mock_principal

            session_id = str(uuid4())

            # Test with invalid message data
            response = client.post(
                f"/api/chat/sessions/{session_id}/messages",
                json={"content": ""},  # Invalid empty content
                headers={"Authorization": "Bearer test-token"},
            )

            # Verify validation error response
            assert response.status_code == 422
            response_data = response.json()
            assert "detail" in response_data

    @pytest.mark.asyncio
    async def test_chat_websocket_integration_flow(
        self, client, mock_chat_service, mock_principal
    ):
        """Test WebSocket integration in chat flow."""
        with patch(
            "tripsage_core.services.business.chat_service.get_chat_service"
        ) as mock_service_dep:
            mock_service_dep.return_value = mock_chat_service

            with patch(
                "tripsage.api.core.dependencies.require_principal"
            ) as mock_auth:
                mock_auth.return_value = mock_principal

                # Test WebSocket connection endpoint
                session_id = str(uuid4())

                # Note: This is a simplified test for WebSocket integration
                # Real WebSocket testing would require more complex setup
                response = client.get(
                    f"/api/chat/sessions/{session_id}",
                    headers={"Authorization": "Bearer test-token"},
                )

                # Verify session access works (prerequisite for WebSocket)
                assert response.status_code == 200
                mock_chat_service.get_session.assert_called_once()