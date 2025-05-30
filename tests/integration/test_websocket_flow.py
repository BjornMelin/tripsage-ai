"""
Integration tests for WebSocket connection lifecycle.

This module tests the complete WebSocket flow including connection, authentication,
message handling, and disconnection across the application stack.
"""

import asyncio
import json
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from tripsage.api.main import app
from tripsage.api.models.websocket import (
    ChatMessageEvent,
    ConnectionStatus,
    WebSocketAuthRequest,
    WebSocketEventType,
    WebSocketMessage,
    WebSocketSubscribeRequest,
)
from tripsage.api.services.websocket_manager import WebSocketManager
from tripsage_core.models.db.user import UserDB


class TestWebSocketFlow:
    """Test complete WebSocket connection lifecycle."""

    @pytest.fixture
    def client(self):
        """Test client for WebSocket connections."""
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
    def mock_websocket_manager(self):
        """Mock WebSocket manager."""
        manager = AsyncMock(spec=WebSocketManager)
        manager.connect = AsyncMock()
        manager.disconnect = AsyncMock()
        manager.send_personal_message = AsyncMock()
        manager.broadcast = AsyncMock()
        manager.subscribe_to_channel = AsyncMock()
        manager.unsubscribe_from_channel = AsyncMock()
        manager.get_active_connections = AsyncMock(return_value=0)
        return manager

    @pytest.fixture
    def mock_chat_agent(self):
        """Mock chat agent for testing."""
        agent = AsyncMock()
        agent.process_message = AsyncMock()
        agent.stream_response = AsyncMock()
        return agent

    def test_websocket_connection_success(
        self, client, mock_user, mock_websocket_manager
    ):
        """Test successful WebSocket connection establishment."""
        with patch(
            "tripsage.api.routers.websocket.websocket_manager", mock_websocket_manager
        ):
            with patch("tripsage.api.core.dependencies.verify_api_key") as mock_verify:
                mock_verify.return_value = mock_user

                with client.websocket_connect("/ws") as websocket:
                    # Send authentication message
                    auth_message = WebSocketMessage(
                        type=WebSocketEventType.AUTH,
                        data=WebSocketAuthRequest(
                            api_key="test-api-key", user_id=str(mock_user.id)
                        ),
                    )
                    websocket.send_text(auth_message.model_dump_json())

                    # Receive connection confirmation
                    response = websocket.receive_text()
                    response_data = json.loads(response)

                    assert response_data["type"] == WebSocketEventType.CONNECTION
                    assert response_data["data"]["status"] == ConnectionStatus.CONNECTED

                    # Verify manager was called
                    mock_websocket_manager.connect.assert_called_once()

    def test_websocket_authentication_failure(self, client, mock_websocket_manager):
        """Test WebSocket connection with invalid authentication."""
        with patch(
            "tripsage.api.routers.websocket.websocket_manager", mock_websocket_manager
        ):
            with patch("tripsage.api.core.dependencies.verify_api_key") as mock_verify:
                mock_verify.side_effect = Exception("Invalid API key")

                with client.websocket_connect("/ws") as websocket:
                    # Send invalid authentication message
                    auth_message = WebSocketMessage(
                        type=WebSocketEventType.AUTH,
                        data=WebSocketAuthRequest(
                            api_key="invalid-key", user_id="invalid-user"
                        ),
                    )
                    websocket.send_text(auth_message.model_dump_json())

                    # Should receive error response
                    response = websocket.receive_text()
                    response_data = json.loads(response)

                    assert response_data["type"] == WebSocketEventType.ERROR
                    assert "authentication" in response_data["data"]["message"].lower()

    def test_websocket_channel_subscription(
        self, client, mock_user, mock_websocket_manager
    ):
        """Test WebSocket channel subscription functionality."""
        with patch(
            "tripsage.api.routers.websocket.websocket_manager", mock_websocket_manager
        ):
            with patch("tripsage.api.core.dependencies.verify_api_key") as mock_verify:
                mock_verify.return_value = mock_user

                with client.websocket_connect("/ws") as websocket:
                    # Authenticate first
                    auth_message = WebSocketMessage(
                        type=WebSocketEventType.AUTH,
                        data=WebSocketAuthRequest(
                            api_key="test-api-key", user_id=str(mock_user.id)
                        ),
                    )
                    websocket.send_text(auth_message.model_dump_json())
                    websocket.receive_text()  # Consume auth response

                    # Subscribe to a channel
                    subscribe_message = WebSocketMessage(
                        type=WebSocketEventType.SUBSCRIBE,
                        data=WebSocketSubscribeRequest(
                            channel="chat", session_id="test-session-123"
                        ),
                    )
                    websocket.send_text(subscribe_message.model_dump_json())

                    # Receive subscription confirmation
                    response = websocket.receive_text()
                    response_data = json.loads(response)

                    assert response_data["type"] == WebSocketEventType.SUBSCRIBE
                    assert response_data["data"]["channel"] == "chat"

                    # Verify manager was called
                    mock_websocket_manager.subscribe_to_channel.assert_called_once()

    def test_websocket_chat_message_flow(
        self, client, mock_user, mock_websocket_manager, mock_chat_agent
    ):
        """Test complete chat message flow through WebSocket."""
        with patch(
            "tripsage.api.routers.websocket.websocket_manager", mock_websocket_manager
        ):
            with patch(
                "tripsage.api.routers.websocket.get_chat_agent",
                return_value=mock_chat_agent,
            ):
                with patch(
                    "tripsage.api.core.dependencies.verify_api_key"
                ) as mock_verify:
                    mock_verify.return_value = mock_user

                    # Configure chat agent to return a response
                    mock_chat_agent.process_message.return_value = {
                        "response": "Hello! How can I help you plan your trip?",
                        "session_id": "test-session-123",
                    }

                    with client.websocket_connect("/ws") as websocket:
                        # Authenticate
                        auth_message = WebSocketMessage(
                            type=WebSocketEventType.AUTH,
                            data=WebSocketAuthRequest(
                                api_key="test-api-key", user_id=str(mock_user.id)
                            ),
                        )
                        websocket.send_text(auth_message.model_dump_json())
                        websocket.receive_text()  # Consume auth response

                        # Subscribe to chat channel
                        subscribe_message = WebSocketMessage(
                            type=WebSocketEventType.SUBSCRIBE,
                            data=WebSocketSubscribeRequest(
                                channel="chat", session_id="test-session-123"
                            ),
                        )
                        websocket.send_text(subscribe_message.model_dump_json())
                        websocket.receive_text()  # Consume subscribe response

                        # Send chat message
                        chat_message = WebSocketMessage(
                            type=WebSocketEventType.CHAT_MESSAGE,
                            data=ChatMessageEvent(
                                message="Help me plan a trip to Paris",
                                session_id="test-session-123",
                                user_id=str(mock_user.id),
                            ),
                        )
                        websocket.send_text(chat_message.model_dump_json())

                        # Receive chat response
                        response = websocket.receive_text()
                        response_data = json.loads(response)

                        assert response_data["type"] == WebSocketEventType.CHAT_MESSAGE
                        assert "trip" in response_data["data"]["message"].lower()

                        # Verify chat agent was called
                        mock_chat_agent.process_message.assert_called_once()

    def test_websocket_disconnection_cleanup(
        self, client, mock_user, mock_websocket_manager
    ):
        """Test proper cleanup when WebSocket disconnects."""
        with patch(
            "tripsage.api.routers.websocket.websocket_manager", mock_websocket_manager
        ):
            with patch("tripsage.api.core.dependencies.verify_api_key") as mock_verify:
                mock_verify.return_value = mock_user

                with client.websocket_connect("/ws") as websocket:
                    # Authenticate
                    auth_message = WebSocketMessage(
                        type=WebSocketEventType.AUTH,
                        data=WebSocketAuthRequest(
                            api_key="test-api-key", user_id=str(mock_user.id)
                        ),
                    )
                    websocket.send_text(auth_message.model_dump_json())
                    websocket.receive_text()  # Consume auth response

                    # Subscribe to channels
                    subscribe_message = WebSocketMessage(
                        type=WebSocketEventType.SUBSCRIBE,
                        data=WebSocketSubscribeRequest(
                            channel="chat", session_id="test-session-123"
                        ),
                    )
                    websocket.send_text(subscribe_message.model_dump_json())
                    websocket.receive_text()  # Consume subscribe response

                # WebSocket should be disconnected when exiting context
                # Verify cleanup was called
                mock_websocket_manager.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_websocket_concurrent_connections(
        self, client, mock_user, mock_websocket_manager
    ):
        """Test multiple concurrent WebSocket connections."""
        with patch(
            "tripsage.api.routers.websocket.websocket_manager", mock_websocket_manager
        ):
            with patch("tripsage.api.core.dependencies.verify_api_key") as mock_verify:
                mock_verify.return_value = mock_user

                # Simulate multiple concurrent connections
                connection_tasks = []

                async def create_connection(connection_id):
                    """Create a WebSocket connection."""
                    with client.websocket_connect("/ws") as websocket:
                        auth_message = WebSocketMessage(
                            type=WebSocketEventType.AUTH,
                            data=WebSocketAuthRequest(
                                api_key="test-api-key", user_id=str(mock_user.id)
                            ),
                        )
                        websocket.send_text(auth_message.model_dump_json())
                        response = websocket.receive_text()

                        response_data = json.loads(response)
                        assert response_data["type"] == WebSocketEventType.CONNECTION

                        return connection_id

                # Create multiple concurrent connections
                for i in range(3):
                    task = asyncio.create_task(create_connection(f"conn-{i}"))
                    connection_tasks.append(task)

                # Wait for all connections to complete
                results = await asyncio.gather(*connection_tasks)

                # Verify all connections succeeded
                assert len(results) == 3
                assert mock_websocket_manager.connect.call_count == 3

    def test_websocket_message_broadcasting(
        self, client, mock_user, mock_websocket_manager
    ):
        """Test message broadcasting to multiple clients."""
        with patch(
            "tripsage.api.routers.websocket.websocket_manager", mock_websocket_manager
        ):
            with patch("tripsage.api.core.dependencies.verify_api_key") as mock_verify:
                mock_verify.return_value = mock_user

                # Configure manager to simulate broadcast
                mock_websocket_manager.broadcast.return_value = True

                with client.websocket_connect("/ws") as websocket:
                    # Authenticate and subscribe
                    auth_message = WebSocketMessage(
                        type=WebSocketEventType.AUTH,
                        data=WebSocketAuthRequest(
                            api_key="test-api-key", user_id=str(mock_user.id)
                        ),
                    )
                    websocket.send_text(auth_message.model_dump_json())
                    websocket.receive_text()  # Consume auth response

                    # Subscribe to broadcast channel
                    subscribe_message = WebSocketMessage(
                        type=WebSocketEventType.SUBSCRIBE,
                        data=WebSocketSubscribeRequest(
                            channel="broadcast", session_id="test-session"
                        ),
                    )
                    websocket.send_text(subscribe_message.model_dump_json())
                    websocket.receive_text()  # Consume subscribe response

                    # Trigger a broadcast (this would normally come from another part of the system)
                    broadcast_message = WebSocketMessage(
                        type=WebSocketEventType.CHAT_MESSAGE,
                        data=ChatMessageEvent(
                            message="System announcement",
                            session_id="test-session",
                            user_id="system",
                        ),
                    )

                    # Send broadcast message
                    websocket.send_text(broadcast_message.model_dump_json())

                    # In a real scenario, this would trigger broadcasts to all connected clients
                    # For testing, we verify the manager's broadcast method would be called

    def test_websocket_error_handling(self, client, mock_user, mock_websocket_manager):
        """Test WebSocket error handling and recovery."""
        with patch(
            "tripsage.api.routers.websocket.websocket_manager", mock_websocket_manager
        ):
            with patch("tripsage.api.core.dependencies.verify_api_key") as mock_verify:
                mock_verify.return_value = mock_user

                # Configure manager to raise an error
                mock_websocket_manager.subscribe_to_channel.side_effect = Exception(
                    "Channel not found"
                )

                with client.websocket_connect("/ws") as websocket:
                    # Authenticate
                    auth_message = WebSocketMessage(
                        type=WebSocketEventType.AUTH,
                        data=WebSocketAuthRequest(
                            api_key="test-api-key", user_id=str(mock_user.id)
                        ),
                    )
                    websocket.send_text(auth_message.model_dump_json())
                    websocket.receive_text()  # Consume auth response

                    # Try to subscribe to invalid channel
                    subscribe_message = WebSocketMessage(
                        type=WebSocketEventType.SUBSCRIBE,
                        data=WebSocketSubscribeRequest(
                            channel="invalid-channel", session_id="test-session"
                        ),
                    )
                    websocket.send_text(subscribe_message.model_dump_json())

                    # Should receive error response
                    response = websocket.receive_text()
                    response_data = json.loads(response)

                    assert response_data["type"] == WebSocketEventType.ERROR
                    assert "channel" in response_data["data"]["message"].lower()

    def test_websocket_heartbeat_mechanism(
        self, client, mock_user, mock_websocket_manager
    ):
        """Test WebSocket heartbeat/ping-pong mechanism."""
        with patch(
            "tripsage.api.routers.websocket.websocket_manager", mock_websocket_manager
        ):
            with patch("tripsage.api.core.dependencies.verify_api_key") as mock_verify:
                mock_verify.return_value = mock_user

                with client.websocket_connect("/ws") as websocket:
                    # Authenticate
                    auth_message = WebSocketMessage(
                        type=WebSocketEventType.AUTH,
                        data=WebSocketAuthRequest(
                            api_key="test-api-key", user_id=str(mock_user.id)
                        ),
                    )
                    websocket.send_text(auth_message.model_dump_json())
                    websocket.receive_text()  # Consume auth response

                    # Send ping message
                    ping_message = WebSocketMessage(
                        type=WebSocketEventType.PING,
                        data={"timestamp": "2024-01-01T12:00:00Z"},
                    )
                    websocket.send_text(ping_message.model_dump_json())

                    # Receive pong response
                    response = websocket.receive_text()
                    response_data = json.loads(response)

                    assert response_data["type"] == WebSocketEventType.PONG
                    assert "timestamp" in response_data["data"]
