"""
Integration tests for chat session management.

This module tests the complete chat session lifecycle including creation,
message handling, persistence, and cleanup across the application stack.
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
from tripsage_core.models.db.chat import ChatMessageDB, ChatSessionDB
from tripsage_core.models.db.user import UserDB
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
        return UserDB(
            id=uuid4(),
            email="test@example.com",
            username="testuser",
            first_name="Test",
            last_name="User",
            is_active=True,
            api_keys={"default": "test-api-key"},
        )

    @pytest.fixture
    def mock_chat_session(self):
        """Mock chat session for testing."""
        return ChatSessionDB(
            id=uuid4(),
            user_id=uuid4(),
            title="Trip Planning Session",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            is_active=True,
            metadata={"destination": "Paris", "budget": 2000},
        )

    @pytest.fixture
    def mock_chat_message(self):
        """Mock chat message for testing."""
        return ChatMessageDB(
            id=uuid4(),
            session_id=uuid4(),
            user_id=uuid4(),
            role="user",
            content="Help me plan a trip to Paris",
            timestamp=datetime.utcnow(),
            metadata={},
        )

    @pytest.fixture
    def mock_chat_agent(self):
        """Mock chat agent."""
        agent = AsyncMock(spec=ChatAgent)
        agent.process_message.return_value = {
            "response": (
                "I'd be happy to help you plan your trip to Paris! "
                "What's your budget and preferred travel dates?"
            ),
            "tool_calls": [],
            "session_id": "test-session-123",
        }
        agent.stream_response.return_value = async_generator_mock(
            [
                {"type": "text", "content": "I'd be happy to help"},
                {"type": "text", "content": " you plan your trip to Paris!"},
                {
                    "type": "text",
                    "content": " What's your budget and preferred travel dates?",
                },
            ]
        )
        return agent

    @pytest.fixture
    def mock_chat_service(self, mock_chat_session, mock_chat_message):
        """Mock chat service."""
        service = AsyncMock(spec=CoreChatService)
        service.create_session.return_value = mock_chat_session
        service.get_session.return_value = mock_chat_session
        service.list_user_sessions.return_value = [mock_chat_session]
        service.save_message.return_value = mock_chat_message
        service.get_session_messages.return_value = [mock_chat_message]
        service.update_session.return_value = mock_chat_session
        service.delete_session.return_value = True
        return service

    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        session = AsyncMock(spec=AsyncSession)
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        session.close = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_chat_session_creation_flow(
        self, client, mock_user, mock_chat_service, mock_chat_session
    ):
        """Test complete chat session creation flow."""
        with patch(
            "tripsage.api.services.chat_service.ChatService"
        ) as mock_service_class:
            mock_service_class.return_value = mock_chat_service

            with patch("tripsage.api.core.dependencies.verify_api_key") as mock_verify:
                mock_verify.return_value = mock_user

                # Test session creation
                response = client.post(
                    "/api/chat/sessions",
                    json={
                        "title": "Trip Planning Session",
                        "metadata": {"destination": "Paris", "budget": 2000},
                    },
                    headers={"Authorization": "Bearer test-api-key"},
                )

                # Verify API response
                assert response.status_code == 201
                response_data = response.json()
                assert response_data["title"] == "Trip Planning Session"
                assert response_data["metadata"]["destination"] == "Paris"

                # Verify service was called
                mock_chat_service.create_session.assert_called_once()

    @pytest.mark.asyncio
    async def test_chat_message_processing_flow(
        self, client, mock_user, mock_chat_agent, mock_chat_service
    ):
        """Test complete chat message processing flow."""
        with patch(
            "tripsage.api.routers.chat.get_chat_agent", return_value=mock_chat_agent
        ):
            with patch(
                "tripsage.api.services.chat_service.ChatService"
            ) as mock_service_class:
                mock_service_class.return_value = mock_chat_service

                with patch(
                    "tripsage.api.core.dependencies.verify_api_key"
                ) as mock_verify:
                    mock_verify.return_value = mock_user

                    session_id = str(uuid4())

                    # Test message processing
                    response = client.post(
                        "/api/chat",
                        json={
                            "messages": [
                                {
                                    "role": "user",
                                    "content": "Help me plan a trip to Paris",
                                }
                            ],
                            "session_id": session_id,
                            "stream": False,
                        },
                        headers={"Authorization": "Bearer test-api-key"},
                    )

                    # Verify API response
                    assert response.status_code == 200
                    response_data = response.json()
                    assert "response" in response_data
                    assert "paris" in response_data["response"].lower()

                    # Verify agent was called
                    mock_chat_agent.process_message.assert_called_once()

                    # Verify message was saved
                    mock_chat_service.save_message.assert_called()

    @pytest.mark.asyncio
    async def test_chat_streaming_flow(
        self, client, mock_user, mock_chat_agent, mock_chat_service
    ):
        """Test chat streaming response flow."""
        with patch(
            "tripsage.api.routers.chat.get_chat_agent", return_value=mock_chat_agent
        ):
            with patch(
                "tripsage.api.services.chat_service.ChatService"
            ) as mock_service_class:
                mock_service_class.return_value = mock_chat_service

                with patch(
                    "tripsage.api.core.dependencies.verify_api_key"
                ) as mock_verify:
                    mock_verify.return_value = mock_user

                    session_id = str(uuid4())

                    # Test streaming message processing
                    response = client.post(
                        "/api/chat",
                        json={
                            "messages": [
                                {
                                    "role": "user",
                                    "content": "Help me plan a trip to Paris",
                                }
                            ],
                            "session_id": session_id,
                            "stream": True,
                        },
                        headers={"Authorization": "Bearer test-api-key"},
                    )

                    # Verify streaming response
                    assert response.status_code == 200
                    assert (
                        response.headers["content-type"] == "text/plain; charset=utf-8"
                    )

                    # Read streaming content
                    content = response.content.decode()
                    assert len(content) > 0

                    # Verify agent streaming was called
                    mock_chat_agent.stream_response.assert_called_once()

    @pytest.mark.asyncio
    async def test_chat_session_persistence_flow(
        self, client, mock_user, mock_chat_service, mock_chat_session, mock_chat_message
    ):
        """Test chat session persistence and retrieval."""
        with patch(
            "tripsage.api.services.chat_service.ChatService"
        ) as mock_service_class:
            mock_service_class.return_value = mock_chat_service

            with patch("tripsage.api.core.dependencies.verify_api_key") as mock_verify:
                mock_verify.return_value = mock_user

                session_id = str(mock_chat_session.id)

                # Test session retrieval
                response = client.get(
                    f"/api/chat/sessions/{session_id}",
                    headers={"Authorization": "Bearer test-api-key"},
                )

                # Verify API response
                assert response.status_code == 200
                response_data = response.json()
                assert response_data["title"] == "Trip Planning Session"

                # Test session messages retrieval
                response = client.get(
                    f"/api/chat/sessions/{session_id}/messages",
                    headers={"Authorization": "Bearer test-api-key"},
                )

                # Verify messages response
                assert response.status_code == 200
                response_data = response.json()
                assert isinstance(response_data, list)

                # Verify service was called
                mock_chat_service.get_session.assert_called()
                mock_chat_service.get_session_messages.assert_called()

    @pytest.mark.asyncio
    async def test_chat_tool_calling_flow(
        self, client, mock_user, mock_chat_agent, mock_chat_service
    ):
        """Test chat message with tool calling flow."""
        # Configure agent to return tool calls
        mock_chat_agent.process_message.return_value = {
            "response": "I'll search for flights to Paris for you.",
            "tool_calls": [
                {
                    "id": "tool_123",
                    "function": {
                        "name": "search_flights",
                        "arguments": json.dumps(
                            {
                                "origin": "NYC",
                                "destination": "CDG",
                                "departure_date": "2024-06-01",
                            }
                        ),
                    },
                }
            ],
            "session_id": "test-session-123",
        }

        with patch(
            "tripsage.api.routers.chat.get_chat_agent", return_value=mock_chat_agent
        ):
            with patch(
                "tripsage.api.services.chat_service.ChatService"
            ) as mock_service_class:
                mock_service_class.return_value = mock_chat_service

                with patch(
                    "tripsage.api.core.dependencies.verify_api_key"
                ) as mock_verify:
                    mock_verify.return_value = mock_user

                    session_id = str(uuid4())

                    # Test message with tool calling
                    response = client.post(
                        "/api/chat",
                        json={
                            "messages": [
                                {
                                    "role": "user",
                                    "content": (
                                        "Find flights from NYC to Paris on June 1st"
                                    ),
                                }
                            ],
                            "session_id": session_id,
                            "stream": False,
                        },
                        headers={"Authorization": "Bearer test-api-key"},
                    )

                    # Verify API response includes tool calls
                    assert response.status_code == 200
                    response_data = response.json()
                    assert "tool_calls" in response_data
                    assert len(response_data["tool_calls"]) == 1
                    assert (
                        response_data["tool_calls"][0]["function"]["name"]
                        == "search_flights"
                    )

    @pytest.mark.asyncio
    async def test_chat_session_cleanup_flow(
        self, client, mock_user, mock_chat_service, mock_chat_session
    ):
        """Test chat session cleanup and deletion."""
        with patch(
            "tripsage.api.services.chat_service.ChatService"
        ) as mock_service_class:
            mock_service_class.return_value = mock_chat_service

            with patch("tripsage.api.core.dependencies.verify_api_key") as mock_verify:
                mock_verify.return_value = mock_user

                session_id = str(mock_chat_session.id)

                # Test session deletion
                response = client.delete(
                    f"/api/chat/sessions/{session_id}",
                    headers={"Authorization": "Bearer test-api-key"},
                )

                # Verify deletion response
                assert response.status_code == 204

                # Verify service was called
                mock_chat_service.delete_session.assert_called_once()

    @pytest.mark.asyncio
    async def test_chat_error_handling_flow(
        self, client, mock_user, mock_chat_agent, mock_chat_service
    ):
        """Test chat error handling and recovery."""
        # Configure agent to raise an error
        mock_chat_agent.process_message.side_effect = Exception(
            "AI service unavailable"
        )

        with patch(
            "tripsage.api.routers.chat.get_chat_agent", return_value=mock_chat_agent
        ):
            with patch(
                "tripsage.api.services.chat_service.ChatService"
            ) as mock_service_class:
                mock_service_class.return_value = mock_chat_service

                with patch(
                    "tripsage.api.core.dependencies.verify_api_key"
                ) as mock_verify:
                    mock_verify.return_value = mock_user

                    session_id = str(uuid4())

                    # Test message processing with error
                    response = client.post(
                        "/api/chat",
                        json={
                            "messages": [
                                {"role": "user", "content": "Help me plan a trip"}
                            ],
                            "session_id": session_id,
                            "stream": False,
                        },
                        headers={"Authorization": "Bearer test-api-key"},
                    )

                    # Verify error response
                    assert response.status_code == 500

                    # Verify agent was called (and failed)
                    mock_chat_agent.process_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_chat_concurrent_sessions_flow(
        self, client, mock_user, mock_chat_service, mock_chat_session
    ):
        """Test concurrent chat sessions management."""
        with patch(
            "tripsage.api.services.chat_service.ChatService"
        ) as mock_service_class:
            mock_service_class.return_value = mock_chat_service

            with patch("tripsage.api.core.dependencies.verify_api_key") as mock_verify:
                mock_verify.return_value = mock_user

                # Create multiple concurrent sessions
                tasks = []
                for i in range(3):
                    task = asyncio.create_task(
                        asyncio.to_thread(
                            client.post,
                            "/api/chat/sessions",
                            json={
                                "title": f"Session {i}",
                                "metadata": {"destination": f"City {i}"},
                            },
                            headers={"Authorization": "Bearer test-api-key"},
                        )
                    )
                    tasks.append(task)

                # Wait for all sessions to be created
                responses = await asyncio.gather(*tasks)

                # Verify all sessions were created
                for response in responses:
                    assert response.status_code == 201

                # Verify service was called for each session
                assert mock_chat_service.create_session.call_count == 3

    @pytest.mark.asyncio
    async def test_chat_session_memory_integration(
        self, client, mock_user, mock_chat_agent, mock_chat_service
    ):
        """Test chat session integration with memory service."""
        # Configure agent to use memory
        mock_chat_agent.process_message.return_value = {
            "response": (
                "Based on your previous trips to Europe, I recommend Paris. "
                "Would you like me to find flights?"
            ),
            "tool_calls": [],
            "session_id": "test-session-123",
            "memory_used": True,
        }

        with patch(
            "tripsage.api.routers.chat.get_chat_agent", return_value=mock_chat_agent
        ):
            with patch(
                "tripsage.api.services.chat_service.ChatService"
            ) as mock_service_class:
                mock_service_class.return_value = mock_chat_service

                with patch(
                    "tripsage.api.core.dependencies.get_session_memory"
                ) as mock_memory:
                    mock_memory.return_value = {
                        "preferences": {"destinations": ["Europe"]},
                        "travel_history": ["Spain", "Italy"],
                    }

                    with patch(
                        "tripsage.api.core.dependencies.verify_api_key"
                    ) as mock_verify:
                        mock_verify.return_value = mock_user

                        session_id = str(uuid4())

                        # Test message processing with memory
                        response = client.post(
                            "/api/chat",
                            json={
                                "messages": [
                                    {
                                        "role": "user",
                                        "content": (
                                            "Suggest a destination for my next trip"
                                        ),
                                    }
                                ],
                                "session_id": session_id,
                                "stream": False,
                            },
                            headers={"Authorization": "Bearer test-api-key"},
                        )

                        # Verify response uses memory context
                        assert response.status_code == 200
                        response_data = response.json()
                        assert "previous trips" in response_data["response"].lower()

                        # Verify memory was accessed
                        mock_memory.assert_called_once()


def async_generator_mock(items):
    """Helper to create async generator mock."""

    async def _async_generator():
        for item in items:
            yield item

    return _async_generator()
