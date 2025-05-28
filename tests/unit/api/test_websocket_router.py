"""
Tests for WebSocket router endpoints.

This module tests the FastAPI WebSocket router endpoints for chat and agent status,
including authentication, message handling, and error scenarios.
"""

import os
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from tripsage.api.main import app

# Test constants
TEST_JWT_TOKEN = os.getenv("TEST_JWT_TOKEN", "mock-valid-jwt-token-for-router")


@pytest.fixture
def test_client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def mock_websocket_manager():
    """Create a mock WebSocket manager."""
    manager = MagicMock()
    manager.authenticate_connection = AsyncMock()
    manager.add_connection = AsyncMock()
    manager.remove_connection = AsyncMock()
    manager.send_to_session = AsyncMock()
    manager.send_to_user = AsyncMock()
    manager.health_check_connections = AsyncMock()
    manager.get_connection_stats = MagicMock(
        return_value={"total_connections": 0, "unique_users": 0, "active_sessions": 0}
    )
    return manager


@pytest.fixture
def mock_websocket_broadcaster():
    """Create a mock WebSocket broadcaster."""
    broadcaster = MagicMock()
    broadcaster.broadcast_to_session = AsyncMock()
    broadcaster.broadcast_to_user = AsyncMock()
    broadcaster.store_message_history = AsyncMock()
    broadcaster.get_message_history = AsyncMock(return_value=[])
    return broadcaster


class TestWebSocketChatEndpoint:
    """Test WebSocket chat endpoint functionality."""

    @pytest.mark.asyncio
    async def test_chat_websocket_connection(
        self, test_client, mock_websocket_manager, mock_websocket_broadcaster
    ):
        """Test successful WebSocket chat connection."""
        session_id = str(uuid4())

        with (
            patch(
                "tripsage.api.routers.websocket.websocket_manager",
                mock_websocket_manager,
            ),
            patch(
                "tripsage.api.routers.websocket.websocket_broadcaster",
                mock_websocket_broadcaster,
            ),
        ):
            # Mock successful authentication
            mock_websocket_manager.authenticate_connection.return_value.success = True
            mock_websocket_manager.authenticate_connection.return_value.userId = str(
                uuid4()
            )

            with test_client.websocket_connect(f"/ws/chat/{session_id}") as websocket:
                # Send authentication
                auth_request = {
                    "type": "auth",
                    "token": TEST_JWT_TOKEN,
                    "sessionId": session_id,
                }
                websocket.send_json(auth_request)

                # Should receive auth response
                auth_response = websocket.receive_json()
                assert auth_response["type"] == "auth_response"

                # Send a chat message
                chat_message = {
                    "type": "chat_message",
                    "content": "Hello, can you help me plan a trip?",
                    "sessionId": session_id,
                }
                websocket.send_json(chat_message)

                # Verify manager methods were called
                mock_websocket_manager.authenticate_connection.assert_called_once()
                mock_websocket_manager.add_connection.assert_called_once()

    @pytest.mark.asyncio
    async def test_chat_websocket_authentication_failure(
        self, test_client, mock_websocket_manager
    ):
        """Test WebSocket chat connection with authentication failure."""
        session_id = str(uuid4())

        with patch(
            "tripsage.api.routers.websocket.websocket_manager", mock_websocket_manager
        ):
            # Mock failed authentication
            mock_websocket_manager.authenticate_connection.return_value.success = False
            mock_websocket_manager.authenticate_connection.return_value.message = (
                "Invalid token"
            )

            with test_client.websocket_connect(f"/ws/chat/{session_id}") as websocket:
                # Send authentication
                auth_request = {
                    "type": "auth",
                    "token": "invalid-token",
                    "sessionId": session_id,
                }
                websocket.send_json(auth_request)

                # Should receive auth failure response
                auth_response = websocket.receive_json()
                assert auth_response["type"] == "auth_response"
                assert auth_response["success"] is False

    @pytest.mark.asyncio
    async def test_chat_websocket_message_broadcasting(
        self, test_client, mock_websocket_manager, mock_websocket_broadcaster
    ):
        """Test message broadcasting through WebSocket."""
        session_id = str(uuid4())
        user_id = str(uuid4())

        with (
            patch(
                "tripsage.api.routers.websocket.websocket_manager",
                mock_websocket_manager,
            ),
            patch(
                "tripsage.api.routers.websocket.websocket_broadcaster",
                mock_websocket_broadcaster,
            ),
            patch("tripsage.api.routers.websocket.chat_service") as mock_chat_service,
        ):
            # Mock successful authentication
            mock_websocket_manager.authenticate_connection.return_value.success = True
            mock_websocket_manager.authenticate_connection.return_value.userId = user_id

            # Mock chat service response
            mock_chat_service.process_message = AsyncMock(
                return_value={
                    "content": (
                        "I'd be happy to help you plan your trip! "
                        "Where would you like to go?"
                    ),
                    "role": "assistant",
                }
            )

            with test_client.websocket_connect(f"/ws/chat/{session_id}") as websocket:
                # Authenticate
                auth_request = {
                    "type": "auth",
                    "token": TEST_JWT_TOKEN,
                    "sessionId": session_id,
                }
                websocket.send_json(auth_request)
                websocket.receive_json()  # Auth response

                # Send chat message
                chat_message = {
                    "type": "chat_message",
                    "content": "Plan a trip to Japan",
                    "sessionId": session_id,
                }
                websocket.send_json(chat_message)

                # Verify broadcast was called
                mock_websocket_broadcaster.broadcast_to_session.assert_called()

    @pytest.mark.asyncio
    async def test_chat_websocket_streaming_response(
        self, test_client, mock_websocket_manager, mock_websocket_broadcaster
    ):
        """Test streaming chat response through WebSocket."""
        session_id = str(uuid4())
        user_id = str(uuid4())

        with (
            patch(
                "tripsage.api.routers.websocket.websocket_manager",
                mock_websocket_manager,
            ),
            patch(
                "tripsage.api.routers.websocket.websocket_broadcaster",
                mock_websocket_broadcaster,
            ),
            patch("tripsage.api.routers.websocket.chat_service") as mock_chat_service,
        ):
            # Mock successful authentication
            mock_websocket_manager.authenticate_connection.return_value.success = True
            mock_websocket_manager.authenticate_connection.return_value.userId = user_id

            # Mock streaming chat service response
            async def mock_stream_response(message, session_id):
                chunks = ["I'd ", "be happy ", "to help you ", "plan your trip!"]
                for i, chunk in enumerate(chunks):
                    yield {
                        "content": chunk,
                        "isComplete": i == len(chunks) - 1,
                        "messageId": str(uuid4()),
                    }

            mock_chat_service.stream_message = mock_stream_response

            with test_client.websocket_connect(f"/ws/chat/{session_id}") as websocket:
                # Authenticate
                auth_request = {
                    "type": "auth",
                    "token": TEST_JWT_TOKEN,
                    "sessionId": session_id,
                }
                websocket.send_json(auth_request)
                websocket.receive_json()  # Auth response

                # Send streaming chat message
                chat_message = {
                    "type": "chat_message_stream",
                    "content": "Plan a trip to Japan",
                    "sessionId": session_id,
                }
                websocket.send_json(chat_message)

                # Should receive multiple streaming chunks
                # This would be tested with actual streaming implementation

    @pytest.mark.asyncio
    async def test_chat_websocket_typing_indicators(
        self, test_client, mock_websocket_manager, mock_websocket_broadcaster
    ):
        """Test typing indicators through WebSocket."""
        session_id = str(uuid4())
        user_id = str(uuid4())

        with (
            patch(
                "tripsage.api.routers.websocket.websocket_manager",
                mock_websocket_manager,
            ),
            patch(
                "tripsage.api.routers.websocket.websocket_broadcaster",
                mock_websocket_broadcaster,
            ),
        ):
            # Mock successful authentication
            mock_websocket_manager.authenticate_connection.return_value.success = True
            mock_websocket_manager.authenticate_connection.return_value.userId = user_id

            with test_client.websocket_connect(f"/ws/chat/{session_id}") as websocket:
                # Authenticate
                auth_request = {
                    "type": "auth",
                    "token": TEST_JWT_TOKEN,
                    "sessionId": session_id,
                }
                websocket.send_json(auth_request)
                websocket.receive_json()  # Auth response

                # Send typing start
                typing_message = {
                    "type": "user_typing",
                    "sessionId": session_id,
                    "userId": user_id,
                }
                websocket.send_json(typing_message)

                # Send typing stop
                stop_typing_message = {
                    "type": "user_stop_typing",
                    "sessionId": session_id,
                    "userId": user_id,
                }
                websocket.send_json(stop_typing_message)

                # Verify broadcasts were called
                assert mock_websocket_broadcaster.broadcast_to_session.call_count >= 2

    @pytest.mark.asyncio
    async def test_chat_websocket_error_handling(
        self, test_client, mock_websocket_manager
    ):
        """Test error handling in chat WebSocket."""
        session_id = str(uuid4())

        with patch(
            "tripsage.api.routers.websocket.websocket_manager", mock_websocket_manager
        ):
            # Mock authentication to raise an exception
            mock_websocket_manager.authenticate_connection.side_effect = Exception(
                "Auth service down"
            )

            with test_client.websocket_connect(f"/ws/chat/{session_id}") as websocket:
                # Send authentication
                auth_request = {
                    "type": "auth",
                    "token": TEST_JWT_TOKEN,
                    "sessionId": session_id,
                }
                websocket.send_json(auth_request)

                # Should receive error response
                error_response = websocket.receive_json()
                assert error_response["type"] == "error"

    @pytest.mark.asyncio
    async def test_chat_websocket_disconnection_cleanup(
        self, test_client, mock_websocket_manager
    ):
        """Test proper cleanup on WebSocket disconnection."""
        session_id = str(uuid4())
        user_id = str(uuid4())

        with patch(
            "tripsage.api.routers.websocket.websocket_manager", mock_websocket_manager
        ):
            # Mock successful authentication
            mock_websocket_manager.authenticate_connection.return_value.success = True
            mock_websocket_manager.authenticate_connection.return_value.userId = user_id

            with test_client.websocket_connect(f"/ws/chat/{session_id}") as websocket:
                # Authenticate
                auth_request = {
                    "type": "auth",
                    "token": TEST_JWT_TOKEN,
                    "sessionId": session_id,
                }
                websocket.send_json(auth_request)
                websocket.receive_json()  # Auth response

                # Connection gets added
                mock_websocket_manager.add_connection.assert_called_once()

            # After context exit, connection should be removed
            mock_websocket_manager.remove_connection.assert_called_once()


class TestWebSocketAgentStatusEndpoint:
    """Test WebSocket agent status endpoint functionality."""

    @pytest.mark.asyncio
    async def test_agent_status_websocket_connection(
        self, test_client, mock_websocket_manager
    ):
        """Test successful WebSocket agent status connection."""
        session_id = str(uuid4())

        with patch(
            "tripsage.api.routers.websocket.websocket_manager", mock_websocket_manager
        ):
            # Mock successful authentication
            mock_websocket_manager.authenticate_connection.return_value.success = True
            mock_websocket_manager.authenticate_connection.return_value.userId = str(
                uuid4()
            )

            with test_client.websocket_connect(
                f"/ws/agent-status/{session_id}"
            ) as websocket:
                # Send authentication
                auth_request = {
                    "type": "auth",
                    "token": TEST_JWT_TOKEN,
                    "sessionId": session_id,
                }
                websocket.send_json(auth_request)

                # Should receive auth response
                auth_response = websocket.receive_json()
                assert auth_response["type"] == "auth_response"

    @pytest.mark.asyncio
    async def test_agent_status_updates(
        self, test_client, mock_websocket_manager, mock_websocket_broadcaster
    ):
        """Test agent status updates through WebSocket."""
        session_id = str(uuid4())
        user_id = str(uuid4())

        with (
            patch(
                "tripsage.api.routers.websocket.websocket_manager",
                mock_websocket_manager,
            ),
            patch(
                "tripsage.api.routers.websocket.websocket_broadcaster",
                mock_websocket_broadcaster,
            ),
        ):
            # Mock successful authentication
            mock_websocket_manager.authenticate_connection.return_value.success = True
            mock_websocket_manager.authenticate_connection.return_value.userId = user_id

            with test_client.websocket_connect(
                f"/ws/agent-status/{session_id}"
            ) as websocket:
                # Authenticate
                auth_request = {
                    "type": "auth",
                    "token": TEST_JWT_TOKEN,
                    "sessionId": session_id,
                }
                websocket.send_json(auth_request)
                websocket.receive_json()  # Auth response

                # Send agent status update
                status_update = {
                    "type": "agent_status_update",
                    "sessionId": session_id,
                    "isActive": True,
                    "currentTask": "Searching for flights",
                    "progress": 50,
                    "statusMessage": "Found 10 matching flights",
                }
                websocket.send_json(status_update)

                # Verify broadcast was called
                mock_websocket_broadcaster.broadcast_to_session.assert_called()

    @pytest.mark.asyncio
    async def test_agent_status_subscription(self, test_client, mock_websocket_manager):
        """Test subscribing to agent status updates."""
        session_id = str(uuid4())
        user_id = str(uuid4())

        with patch(
            "tripsage.api.routers.websocket.websocket_manager", mock_websocket_manager
        ):
            # Mock successful authentication
            mock_websocket_manager.authenticate_connection.return_value.success = True
            mock_websocket_manager.authenticate_connection.return_value.userId = user_id

            with test_client.websocket_connect(
                f"/ws/agent-status/{session_id}"
            ) as websocket:
                # Authenticate
                auth_request = {
                    "type": "auth",
                    "token": TEST_JWT_TOKEN,
                    "sessionId": session_id,
                }
                websocket.send_json(auth_request)
                websocket.receive_json()  # Auth response

                # Subscribe to status updates
                subscribe_message = {
                    "type": "subscribe_status",
                    "sessionId": session_id,
                }
                websocket.send_json(subscribe_message)

                # Connection should be added to manager
                mock_websocket_manager.add_connection.assert_called_once()


class TestWebSocketRouterIntegration:
    """Test WebSocket router integration scenarios."""

    @pytest.mark.asyncio
    async def test_multiple_concurrent_connections(
        self, test_client, mock_websocket_manager
    ):
        """Test handling multiple concurrent WebSocket connections."""
        session_id = str(uuid4())

        with patch(
            "tripsage.api.routers.websocket.websocket_manager", mock_websocket_manager
        ):
            # Mock successful authentication
            mock_websocket_manager.authenticate_connection.return_value.success = True
            mock_websocket_manager.authenticate_connection.return_value.userId = str(
                uuid4()
            )

            # Simulate multiple connections (would be more complex in real testing)
            connection_count = 3
            for _ in range(connection_count):
                with test_client.websocket_connect(
                    f"/ws/chat/{session_id}"
                ) as websocket:
                    auth_request = {
                        "type": "auth",
                        "token": TEST_JWT_TOKEN,
                        "sessionId": session_id,
                    }
                    websocket.send_json(auth_request)
                    websocket.receive_json()  # Auth response

            # Each connection should be added
            assert mock_websocket_manager.add_connection.call_count == connection_count

    @pytest.mark.asyncio
    async def test_websocket_health_check_endpoint(
        self, test_client, mock_websocket_manager
    ):
        """Test WebSocket health check endpoint."""
        # Mock connection stats
        mock_websocket_manager.get_connection_stats.return_value = {
            "total_connections": 5,
            "unique_users": 3,
            "active_sessions": 2,
            "uptime_seconds": 3600,
        }

        with patch(
            "tripsage.api.routers.websocket.websocket_manager", mock_websocket_manager
        ):
            response = test_client.get("/ws/health")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["connections"]["total"] == 5
            assert data["connections"]["users"] == 3
            assert data["connections"]["sessions"] == 2

    @pytest.mark.asyncio
    async def test_websocket_metrics_endpoint(
        self, test_client, mock_websocket_manager, mock_websocket_broadcaster
    ):
        """Test WebSocket metrics endpoint."""
        # Mock manager stats
        mock_websocket_manager.get_connection_stats.return_value = {
            "total_connections": 10,
            "unique_users": 7,
            "active_sessions": 5,
        }

        # Mock broadcaster stats
        mock_websocket_broadcaster.get_stats = AsyncMock(
            return_value={
                "messages_sent": 1000,
                "messages_queued": 5,
                "active_sessions": 5,
            }
        )

        with (
            patch(
                "tripsage.api.routers.websocket.websocket_manager",
                mock_websocket_manager,
            ),
            patch(
                "tripsage.api.routers.websocket.websocket_broadcaster",
                mock_websocket_broadcaster,
            ),
        ):
            response = test_client.get("/ws/metrics")

            assert response.status_code == 200
            data = response.json()
            assert "connections" in data
            assert "messages" in data
            assert data["connections"]["total"] == 10
            assert data["messages"]["sent"] == 1000

    @pytest.mark.asyncio
    async def test_websocket_connection_limits(
        self, test_client, mock_websocket_manager
    ):
        """Test WebSocket connection limits and throttling."""
        session_id = str(uuid4())

        # Mock manager to indicate too many connections
        mock_websocket_manager.get_connection_count.return_value = 1000  # Over limit

        with patch(
            "tripsage.api.routers.websocket.websocket_manager", mock_websocket_manager
        ):
            with test_client.websocket_connect(f"/ws/chat/{session_id}") as websocket:
                auth_request = {
                    "type": "auth",
                    "token": TEST_JWT_TOKEN,
                    "sessionId": session_id,
                }
                websocket.send_json(auth_request)

                # Should receive connection limit error
                _ = websocket.receive_json()
                # Implementation would check for rate limiting/connection limits

    @pytest.mark.asyncio
    async def test_websocket_message_validation(
        self, test_client, mock_websocket_manager
    ):
        """Test WebSocket message validation."""
        session_id = str(uuid4())

        with patch(
            "tripsage.api.routers.websocket.websocket_manager", mock_websocket_manager
        ):
            # Mock successful authentication
            mock_websocket_manager.authenticate_connection.return_value.success = True
            mock_websocket_manager.authenticate_connection.return_value.userId = str(
                uuid4()
            )

            with test_client.websocket_connect(f"/ws/chat/{session_id}") as websocket:
                # Authenticate
                auth_request = {
                    "type": "auth",
                    "token": TEST_JWT_TOKEN,
                    "sessionId": session_id,
                }
                websocket.send_json(auth_request)
                websocket.receive_json()  # Auth response

                # Send invalid message (missing required fields)
                invalid_message = {
                    "type": "chat_message"
                    # Missing content and sessionId
                }
                websocket.send_json(invalid_message)

                # Should receive validation error
                error_response = websocket.receive_json()
                assert error_response["type"] == "error"
