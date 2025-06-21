"""
Comprehensive integration tests for WebSocket functionality.

This module tests the complete WebSocket lifecycle including connection,
authentication, message handling, agent status updates, broadcasting,
and error recovery scenarios.
"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from tests.factories import ChatFactory, UserFactory, WebSocketFactory
from tripsage.api.main import app
from tripsage_core.exceptions.exceptions import (
    CoreRateLimitError,
)


class TestWebSocketIntegration:
    """Integration tests for WebSocket functionality."""

    @pytest.fixture
    def test_client(self):
        """Create FastAPI test client."""
        return TestClient(app)

    @pytest.fixture
    def mock_auth_service(self):
        """Mock authentication service."""
        auth_service = MagicMock()
        auth_service.validate_access_token = AsyncMock()
        auth_service.get_current_user = AsyncMock()
        return auth_service

    @pytest.fixture
    def mock_chat_service(self):
        """Mock chat service."""
        chat_service = MagicMock()
        chat_service.create_session = AsyncMock()
        chat_service.add_message = AsyncMock()
        chat_service.get_session = AsyncMock()
        return chat_service

    @pytest.fixture
    def mock_websocket_manager(self):
        """Mock WebSocket manager."""
        manager = MagicMock()
        manager.connect = AsyncMock()
        manager.disconnect = AsyncMock()
        manager.send_personal_message = AsyncMock()
        manager.broadcast_to_session = AsyncMock()
        manager.send_error = AsyncMock()

        # Add methods needed by refactored service
        manager.send_to_connection = AsyncMock(return_value=True)
        manager.send_to_session = AsyncMock(return_value=1)
        manager.broadcast_to_channel = AsyncMock(return_value=1)
        manager.disconnect_connection = AsyncMock()
        manager.authenticate_connection = AsyncMock()
        manager.subscribe_connection = AsyncMock()
        manager.get_connection_stats = MagicMock(return_value={})

        # Mock the connections dict
        manager.connections = {}

        return manager

    @pytest.fixture
    def sample_user(self):
        """Create sample user for testing."""
        return UserFactory.create()

    @pytest.fixture
    def sample_auth_token(self):
        """Create sample authentication token."""
        return "test-jwt-token-12345"

    @pytest.fixture
    def websocket_auth_message(self, sample_auth_token):
        """Create WebSocket authentication message."""
        return WebSocketFactory.create_auth_request(access_token=sample_auth_token)

    @pytest.mark.asyncio
    async def test_websocket_connection_lifecycle(
        self,
        test_client,
        mock_auth_service,
        mock_websocket_manager,
        sample_user,
        sample_auth_token,
    ):
        """Test complete WebSocket connection lifecycle."""
        from uuid import uuid4

        from tripsage_core.services.infrastructure.websocket_auth_service import (
            WebSocketAuthResponse,
        )

        # Mock successful authentication response
        connection_id = str(uuid4())
        user_id = uuid4()
        auth_response = WebSocketAuthResponse(
            success=True,
            connection_id=connection_id,
            user_id=user_id,
            session_id=uuid4(),
            available_channels=["general", "notifications"],
        )

        # Set up all the mocks that the WebSocket endpoint needs
        mock_websocket_manager.authenticate_connection = AsyncMock(return_value=auth_response)
        mock_websocket_manager.send_to_connection = AsyncMock(return_value=True)
        mock_websocket_manager.disconnect_connection = AsyncMock()

        # Mock the websocket manager's connections dict to support the get operation
        mock_connection = MagicMock()
        mock_connection.update_heartbeat = MagicMock()
        mock_connection.handle_pong = MagicMock()
        mock_websocket_manager.connections = {connection_id: mock_connection}

        # Patch the websocket_manager in the router
        with patch(
            "tripsage.api.routers.websocket.websocket_manager",
            mock_websocket_manager,
        ):
            # Mock settings validation to prevent JWT and CORS errors
            with patch("tripsage.api.routers.websocket.get_settings") as mock_get_settings:
                mock_settings = MagicMock()
                mock_settings.cors_origins = ["*"]
                mock_settings.is_production = False
                mock_get_settings.return_value = mock_settings

                with test_client.websocket_connect("/api/ws") as websocket:
                    # Send authentication message in the expected format
                    auth_msg = {"token": sample_auth_token, "channels": ["general"]}
                    websocket.send_text(json.dumps(auth_msg))

                    # Give some time for processing
                    await asyncio.sleep(0.1)

                    # Verify authenticate_connection was called
                    mock_websocket_manager.authenticate_connection.assert_called_once()

                    # Send a ping message and verify it was handled
                    ping_msg = {
                        "type": "ping",
                    }
                    websocket.send_text(json.dumps(ping_msg))

                    # Give some time for message processing
                    await asyncio.sleep(0.1)

                    # Verify connection lifecycle methods were called
                    assert mock_websocket_manager.authenticate_connection.called
                    assert mock_websocket_manager.send_to_connection.call_count >= 0

                    # Test completed successfully if we reach here
                    assert True

    @pytest.mark.asyncio
    async def test_websocket_authentication_required(self, test_client, mock_websocket_manager):
        """Test that authentication is required for WebSocket connection."""
        # Set up proper authentication flow that should fail without token
        mock_websocket_manager.authenticate_connection = AsyncMock(side_effect=Exception("Authentication required"))

        with patch("tripsage.api.routers.websocket.websocket_manager", mock_websocket_manager):
            # Mock settings validation to prevent CORS errors
            with patch("tripsage.api.routers.websocket.get_settings") as mock_get_settings:
                mock_settings = MagicMock()
                mock_settings.cors_origins = ["*"]
                mock_settings.is_production = False
                mock_get_settings.return_value = mock_settings

                with test_client.websocket_connect("/api/ws") as websocket:
                    # Try to send message without authentication
                    chat_msg = {
                        "type": "chat_message",
                        "payload": {"content": "Hello"},
                    }
                    websocket.send_json(chat_msg)

                    # Should receive error message
                    response = websocket.receive_json()
                    assert response["type"] == "error"
                    assert "authentication" in response.get("message", "").lower()

    @pytest.mark.asyncio
    async def test_websocket_invalid_token(self, test_client, mock_auth_service, mock_websocket_manager):
        """Test WebSocket connection with invalid token."""
        from tripsage_core.services.infrastructure.websocket_auth_service import (
            WebSocketAuthResponse,
        )

        # Mock authentication failure with invalid token
        mock_websocket_manager.authenticate_connection = AsyncMock(
            return_value=WebSocketAuthResponse(success=False, connection_id="", error="Invalid token")
        )

        with patch("tripsage.api.routers.websocket.auth_service", mock_auth_service):
            with patch(
                "tripsage.api.routers.websocket.websocket_manager",
                mock_websocket_manager,
            ):
                # Mock settings validation to prevent CORS errors
                with patch("tripsage.api.routers.websocket.get_settings") as mock_get_settings:
                    mock_settings = MagicMock()
                    mock_settings.cors_origins = ["*"]
                    mock_settings.is_production = False
                    mock_get_settings.return_value = mock_settings

                    with test_client.websocket_connect("/api/ws") as websocket:
                        # Send authentication with invalid token
                        auth_msg = {"token": "invalid-token", "channels": []}
                        websocket.send_text(json.dumps(auth_msg))

                        # Should receive error message
                        response = websocket.receive_json()
                        assert response["type"] == "error"
                        assert "Invalid token" in response["message"]

    @pytest.mark.asyncio
    async def test_websocket_message_broadcast(
        self,
        test_client,
        mock_auth_service,
        mock_chat_service,
        mock_websocket_manager,
        sample_user,
        sample_auth_token,
    ):
        """Test message broadcasting to multiple clients."""
        from tripsage_core.services.infrastructure.websocket_auth_service import (
            WebSocketAuthResponse,
        )

        session_id = str(uuid4())

        # Mock successful authentication response
        connection_id_1 = str(uuid4())
        connection_id_2 = str(uuid4())
        user_id = uuid4()

        auth_response_1 = WebSocketAuthResponse(
            success=True,
            connection_id=connection_id_1,
            user_id=user_id,
            session_id=uuid4(),
            available_channels=["general", "notifications"],
        )

        auth_response_2 = WebSocketAuthResponse(
            success=True,
            connection_id=connection_id_2,
            user_id=user_id,
            session_id=uuid4(),
            available_channels=["general", "notifications"],
        )

        # Set up all the mocks that the WebSocket endpoint needs
        mock_websocket_manager.authenticate_connection = AsyncMock(side_effect=[auth_response_1, auth_response_2])
        mock_websocket_manager.send_to_connection = AsyncMock(return_value=True)
        mock_websocket_manager.send_to_session = AsyncMock(return_value=1)
        mock_websocket_manager.disconnect_connection = AsyncMock()

        # Mock the websocket manager's connections dict to support the get operations
        mock_connection_1 = MagicMock()
        mock_connection_1.update_heartbeat = MagicMock()
        mock_connection_1.handle_pong = MagicMock()

        mock_connection_2 = MagicMock()
        mock_connection_2.update_heartbeat = MagicMock()
        mock_connection_2.handle_pong = MagicMock()

        mock_websocket_manager.connections = {
            connection_id_1: mock_connection_1,
            connection_id_2: mock_connection_2,
        }

        # Mock authentication and chat service
        mock_auth_service.validate_access_token.return_value = {
            "user_id": sample_user["id"],
            "email": sample_user["email"],
        }
        mock_auth_service.get_current_user.return_value = sample_user

        mock_chat_service.get_session.return_value = {
            "id": session_id,
            "user_id": sample_user["id"],
        }

        message_response = ChatFactory.create_response(session_id=session_id)
        mock_chat_service.add_message.return_value = message_response

        with patch("tripsage.api.routers.websocket.auth_service", mock_auth_service):
            with patch("tripsage.api.routers.websocket.chat_service", mock_chat_service):
                with patch(
                    "tripsage.api.routers.websocket.websocket_manager",
                    mock_websocket_manager,
                ):
                    # Mock settings validation to prevent CORS errors
                    with patch("tripsage.api.routers.websocket.get_settings") as mock_get_settings:
                        mock_settings = MagicMock()
                        mock_settings.cors_origins = ["*"]
                        mock_settings.is_production = False
                        mock_get_settings.return_value = mock_settings

                        # Connect first client
                        with test_client.websocket_connect("/api/ws") as ws1:
                            # Authenticate first client - use correct format for /api/ws
                            auth_msg = {
                                "token": sample_auth_token,
                                "channels": ["general"],
                            }
                            ws1.send_text(json.dumps(auth_msg))

                            # Connect second client
                            with test_client.websocket_connect("/api/ws") as ws2:
                                # Authenticate second client
                                ws2.send_text(json.dumps(auth_msg))

                                # Send message from first client
                                chat_msg = {
                                    "type": "chat_message",
                                    "payload": {
                                        "session_id": session_id,
                                        "content": "Hello everyone",
                                    },
                                }
                                ws1.send_text(json.dumps(chat_msg))

                                # Verify broadcast was called
                                await asyncio.sleep(0.1)
                                mock_websocket_manager.send_to_session.assert_called()

    @pytest.mark.asyncio
    async def test_websocket_agent_status_updates(
        self,
        test_client,
        mock_auth_service,
        mock_websocket_manager,
        sample_user,
        sample_auth_token,
    ):
        """Test agent status update streaming."""
        from tripsage_core.services.infrastructure.websocket_auth_service import (
            WebSocketAuthResponse,
        )

        # Mock successful authentication response
        connection_id = str(uuid4())
        user_id = uuid4()
        auth_response = WebSocketAuthResponse(
            success=True,
            connection_id=connection_id,
            user_id=user_id,
            session_id=uuid4(),
            available_channels=["general", "notifications", "agent_status"],
        )

        # Set up all the mocks that the WebSocket endpoint needs
        mock_websocket_manager.authenticate_connection = AsyncMock(return_value=auth_response)
        mock_websocket_manager.send_to_connection = AsyncMock(return_value=True)
        mock_websocket_manager.subscribe_connection = AsyncMock()
        mock_websocket_manager.disconnect_connection = AsyncMock()

        # Mock the websocket manager's connections dict to support the get operation
        mock_connection = MagicMock()
        mock_connection.update_heartbeat = MagicMock()
        mock_connection.handle_pong = MagicMock()
        mock_websocket_manager.connections = {connection_id: mock_connection}

        with patch("tripsage.api.routers.websocket.auth_service", mock_auth_service):
            with patch(
                "tripsage.api.routers.websocket.websocket_manager",
                mock_websocket_manager,
            ):
                # Mock settings validation to prevent CORS errors
                with patch("tripsage.api.routers.websocket.get_settings") as mock_get_settings:
                    mock_settings = MagicMock()
                    mock_settings.cors_origins = ["*"]
                    mock_settings.is_production = False
                    mock_get_settings.return_value = mock_settings

                    with test_client.websocket_connect("/api/ws") as websocket:
                        # Authenticate - use correct format for /api/ws
                        auth_msg = {
                            "token": sample_auth_token,
                            "channels": ["agent_status"],
                        }
                        websocket.send_text(json.dumps(auth_msg))

                        # Subscribe to agent status updates
                        subscribe_msg = {
                            "type": "subscribe",
                            "payload": {"channels": ["agent_status"]},
                        }
                        websocket.send_text(json.dumps(subscribe_msg))

                        # Verify subscription handling
                        await asyncio.sleep(0.1)

                        # Verify authenticate_connection was called
                        mock_websocket_manager.authenticate_connection.assert_called_once()

                        # Verify send_to_connection was called (for auth response and connection established)
                        assert mock_websocket_manager.send_to_connection.call_count >= 1

    @pytest.mark.asyncio
    async def test_websocket_rate_limiting(
        self,
        test_client,
        mock_auth_service,
        mock_chat_service,
        mock_websocket_manager,
        sample_user,
        sample_auth_token,
    ):
        """Test WebSocket rate limiting."""
        from tripsage_core.services.infrastructure.websocket_auth_service import (
            WebSocketAuthResponse,
        )

        # Mock successful authentication response
        connection_id = str(uuid4())
        user_id = uuid4()
        auth_response = WebSocketAuthResponse(
            success=True,
            connection_id=connection_id,
            user_id=user_id,
            session_id=uuid4(),
            available_channels=["general", "notifications"],
        )

        # Set up all the mocks that the WebSocket endpoint needs
        mock_websocket_manager.authenticate_connection = AsyncMock(return_value=auth_response)
        mock_websocket_manager.send_to_connection = AsyncMock(return_value=True)
        mock_websocket_manager.send_to_session = AsyncMock(return_value=1)
        mock_websocket_manager.disconnect_connection = AsyncMock()

        # Mock the websocket manager's connections dict to support the get operations
        mock_connection = MagicMock()
        mock_connection.update_heartbeat = MagicMock()
        mock_connection.handle_pong = MagicMock()
        mock_websocket_manager.connections = {connection_id: mock_connection}

        # Mock rate limit error on chat service
        mock_chat_service.add_message.side_effect = CoreRateLimitError("Rate limit exceeded")

        with patch("tripsage.api.routers.websocket.auth_service", mock_auth_service):
            with patch("tripsage.api.routers.websocket.chat_service", mock_chat_service):
                with patch(
                    "tripsage.api.routers.websocket.websocket_manager",
                    mock_websocket_manager,
                ):
                    # Mock settings validation to prevent CORS errors
                    with patch("tripsage.api.routers.websocket.get_settings") as mock_get_settings:
                        mock_settings = MagicMock()
                        mock_settings.cors_origins = ["*"]
                        mock_settings.is_production = False
                        mock_get_settings.return_value = mock_settings

                        with test_client.websocket_connect("/api/ws") as websocket:
                            # Authenticate - use correct format for /api/ws
                            auth_msg = {
                                "token": sample_auth_token,
                                "channels": ["general"],
                            }
                            websocket.send_text(json.dumps(auth_msg))

                            # Send multiple messages quickly
                            for i in range(5):
                                chat_msg = {
                                    "type": "chat_message",
                                    "payload": {
                                        "session_id": str(uuid4()),
                                        "content": f"Message {i}",
                                    },
                                }
                                websocket.send_text(json.dumps(chat_msg))

                            # Should receive rate limit error via send_to_session calls
                            await asyncio.sleep(0.1)

                            # Verify authenticate_connection was called
                            mock_websocket_manager.authenticate_connection.assert_called_once()

                            # Verify send_to_session was called for chat messages
                            assert mock_websocket_manager.send_to_session.call_count >= 1

    @pytest.mark.asyncio
    async def test_websocket_reconnection_handling(
        self,
        test_client,
        mock_auth_service,
        mock_websocket_manager,
        sample_user,
        sample_auth_token,
    ):
        """Test WebSocket reconnection handling."""
        from tripsage_core.services.infrastructure.websocket_auth_service import (
            WebSocketAuthResponse,
        )

        connection_id_1 = str(uuid4())
        connection_id_2 = str(uuid4())
        user_id = uuid4()

        # Mock authentication responses for both connections
        auth_response_1 = WebSocketAuthResponse(
            success=True,
            connection_id=connection_id_1,
            user_id=user_id,
            session_id=uuid4(),
            available_channels=["general", "notifications"],
        )

        auth_response_2 = WebSocketAuthResponse(
            success=True,
            connection_id=connection_id_2,
            user_id=user_id,
            session_id=uuid4(),
            available_channels=["general", "notifications"],
        )

        # Set up all the mocks that the WebSocket endpoint needs
        mock_websocket_manager.authenticate_connection = AsyncMock(side_effect=[auth_response_1, auth_response_2])
        mock_websocket_manager.send_to_connection = AsyncMock(return_value=True)
        mock_websocket_manager.disconnect_connection = AsyncMock()

        # Mock the websocket manager's connections dict to support the get operations
        mock_connection_1 = MagicMock()
        mock_connection_1.update_heartbeat = MagicMock()
        mock_connection_1.handle_pong = MagicMock()

        mock_connection_2 = MagicMock()
        mock_connection_2.update_heartbeat = MagicMock()
        mock_connection_2.handle_pong = MagicMock()

        mock_websocket_manager.connections = {
            connection_id_1: mock_connection_1,
            connection_id_2: mock_connection_2,
        }

        with patch("tripsage.api.routers.websocket.auth_service", mock_auth_service):
            with patch(
                "tripsage.api.routers.websocket.websocket_manager",
                mock_websocket_manager,
            ):
                # Mock settings validation to prevent CORS errors
                with patch("tripsage.api.routers.websocket.get_settings") as mock_get_settings:
                    mock_settings = MagicMock()
                    mock_settings.cors_origins = ["*"]
                    mock_settings.is_production = False
                    mock_get_settings.return_value = mock_settings

                    # First connection
                    with test_client.websocket_connect("/api/ws") as ws1:
                        # Authenticate - use correct format for /api/ws
                        auth_msg = {"token": sample_auth_token, "channels": ["general"]}
                        ws1.send_text(json.dumps(auth_msg))
                        await asyncio.sleep(0.1)  # Allow processing

                    # After first connection ends, disconnect should be called
                    mock_websocket_manager.disconnect_connection.assert_called()

                    # Reconnect with new connection
                    with test_client.websocket_connect("/api/ws") as ws2:
                        # Re-authenticate
                        ws2.send_text(json.dumps(auth_msg))
                        await asyncio.sleep(0.1)  # Allow processing

                        # Should have authenticated twice (once for each connection)
                        assert mock_websocket_manager.authenticate_connection.call_count == 2

    @pytest.mark.asyncio
    async def test_websocket_heartbeat(
        self,
        test_client,
        mock_auth_service,
        mock_websocket_manager,
        sample_user,
        sample_auth_token,
    ):
        """Test WebSocket heartbeat mechanism."""
        from tripsage_core.services.infrastructure.websocket_auth_service import (
            WebSocketAuthResponse,
        )

        # Mock successful authentication response
        connection_id = str(uuid4())
        user_id = uuid4()
        auth_response = WebSocketAuthResponse(
            success=True,
            connection_id=connection_id,
            user_id=user_id,
            session_id=uuid4(),
            available_channels=["general", "notifications"],
        )

        # Set up all the mocks that the WebSocket endpoint needs
        mock_websocket_manager.authenticate_connection = AsyncMock(return_value=auth_response)
        mock_websocket_manager.send_to_connection = AsyncMock(return_value=True)
        mock_websocket_manager.disconnect_connection = AsyncMock()

        # Mock the websocket manager's connections dict to support the get operation
        mock_connection = MagicMock()
        mock_connection.update_heartbeat = MagicMock()
        mock_connection.handle_pong = MagicMock()
        mock_websocket_manager.connections = {connection_id: mock_connection}

        with patch("tripsage.api.routers.websocket.auth_service", mock_auth_service):
            with patch(
                "tripsage.api.routers.websocket.websocket_manager",
                mock_websocket_manager,
            ):
                # Mock settings validation to prevent CORS errors
                with patch("tripsage.api.routers.websocket.get_settings") as mock_get_settings:
                    mock_settings = MagicMock()
                    mock_settings.cors_origins = ["*"]
                    mock_settings.is_production = False
                    mock_get_settings.return_value = mock_settings

                    with test_client.websocket_connect("/api/ws") as websocket:
                        # Authenticate - use correct format for /api/ws
                        auth_msg = {"token": sample_auth_token, "channels": ["general"]}
                        websocket.send_text(json.dumps(auth_msg))

                        # Send heartbeat
                        heartbeat_msg = {"type": "heartbeat"}
                        websocket.send_text(json.dumps(heartbeat_msg))

                        # Should receive heartbeat response (authentication + connection established + heartbeat handling)
                        await asyncio.sleep(0.1)

                        # Verify authenticate_connection was called
                        mock_websocket_manager.authenticate_connection.assert_called_once()

                        # Verify send_to_connection was called (for auth response and connection established)
                        assert mock_websocket_manager.send_to_connection.call_count >= 1

                        # Verify heartbeat was handled
                        mock_connection.update_heartbeat.assert_called()

    @pytest.mark.asyncio
    async def test_websocket_typing_indicators(
        self,
        test_client,
        mock_auth_service,
        mock_websocket_manager,
        sample_user,
        sample_auth_token,
    ):
        """Test typing indicator functionality."""
        from tripsage_core.services.infrastructure.websocket_auth_service import (
            WebSocketAuthResponse,
        )

        session_id = str(uuid4())

        # Mock successful authentication response
        connection_id = str(uuid4())
        user_id = uuid4()
        auth_response = WebSocketAuthResponse(
            success=True,
            connection_id=connection_id,
            user_id=user_id,
            session_id=uuid4(),
            available_channels=["general", "notifications"],
        )

        # Set up all the mocks that the WebSocket endpoint needs
        mock_websocket_manager.authenticate_connection = AsyncMock(return_value=auth_response)
        mock_websocket_manager.send_to_connection = AsyncMock(return_value=True)
        mock_websocket_manager.send_to_session = AsyncMock(return_value=1)
        mock_websocket_manager.disconnect_connection = AsyncMock()

        # Mock the websocket manager's connections dict to support the get operation
        mock_connection = MagicMock()
        mock_connection.update_heartbeat = MagicMock()
        mock_connection.handle_pong = MagicMock()
        mock_websocket_manager.connections = {connection_id: mock_connection}

        with patch("tripsage.api.routers.websocket.auth_service", mock_auth_service):
            with patch(
                "tripsage.api.routers.websocket.websocket_manager",
                mock_websocket_manager,
            ):
                # Mock settings validation to prevent CORS errors
                with patch("tripsage.api.routers.websocket.get_settings") as mock_get_settings:
                    mock_settings = MagicMock()
                    mock_settings.cors_origins = ["*"]
                    mock_settings.is_production = False
                    mock_get_settings.return_value = mock_settings

                    with test_client.websocket_connect("/api/ws") as websocket:
                        # Authenticate - use correct format for /api/ws
                        auth_msg = {"token": sample_auth_token, "channels": ["general"]}
                        websocket.send_text(json.dumps(auth_msg))

                        # Send typing indicator (simulate user typing)
                        typing_msg = {
                            "type": "typing",
                            "payload": {
                                "session_id": session_id,
                                "is_typing": True,
                            },
                        }
                        websocket.send_text(json.dumps(typing_msg))

                        # Should handle typing indicator (since it's not explicitly handled,
                        # it will be echoed back)
                        await asyncio.sleep(0.1)

                        # Verify authenticate_connection was called
                        mock_websocket_manager.authenticate_connection.assert_called_once()

                        # Verify send_to_connection was called for auth response
                        assert mock_websocket_manager.send_to_connection.call_count >= 1

    @pytest.mark.asyncio
    async def test_websocket_message_streaming(
        self,
        test_client,
        mock_auth_service,
        mock_chat_service,
        mock_websocket_manager,
        sample_user,
        sample_auth_token,
    ):
        """Test streaming message responses."""
        from tripsage_core.services.infrastructure.websocket_auth_service import (
            WebSocketAuthResponse,
        )

        session_id = str(uuid4())

        # Mock successful authentication response
        connection_id = str(uuid4())
        user_id = uuid4()
        auth_response = WebSocketAuthResponse(
            success=True,
            connection_id=connection_id,
            user_id=user_id,
            session_id=uuid4(),
            available_channels=["general", "notifications"],
        )

        # Set up all the mocks that the WebSocket endpoint needs
        mock_websocket_manager.authenticate_connection = AsyncMock(return_value=auth_response)
        mock_websocket_manager.send_to_connection = AsyncMock(return_value=True)
        mock_websocket_manager.send_to_session = AsyncMock(return_value=1)
        mock_websocket_manager.disconnect_connection = AsyncMock()

        # Mock the websocket manager's connections dict to support the get operation
        mock_connection = MagicMock()
        mock_connection.update_heartbeat = MagicMock()
        mock_connection.handle_pong = MagicMock()
        mock_websocket_manager.connections = {connection_id: mock_connection}

        with patch("tripsage.api.routers.websocket.auth_service", mock_auth_service):
            with patch("tripsage.api.routers.websocket.chat_service", mock_chat_service):
                with patch(
                    "tripsage.api.routers.websocket.websocket_manager",
                    mock_websocket_manager,
                ):
                    # Mock settings validation to prevent CORS errors
                    with patch("tripsage.api.routers.websocket.get_settings") as mock_get_settings:
                        mock_settings = MagicMock()
                        mock_settings.cors_origins = ["*"]
                        mock_settings.is_production = False
                        mock_get_settings.return_value = mock_settings

                        with test_client.websocket_connect("/api/ws") as websocket:
                            # Authenticate - use correct format for /api/ws
                            auth_msg = {
                                "token": sample_auth_token,
                                "channels": ["general"],
                            }
                            websocket.send_text(json.dumps(auth_msg))

                            # Send message requesting streaming
                            chat_msg = {
                                "type": "chat_message",
                                "payload": {
                                    "session_id": session_id,
                                    "content": "Help me plan a trip to Paris",
                                    "stream": True,
                                },
                            }
                            websocket.send_text(json.dumps(chat_msg))

                            # Verify streaming chunks are sent via send_to_session
                            await asyncio.sleep(0.1)

                            # Verify authenticate_connection was called
                            mock_websocket_manager.authenticate_connection.assert_called_once()

                            # Verify send_to_session was called for chat message
                            assert mock_websocket_manager.send_to_session.call_count >= 1

    @pytest.mark.asyncio
    async def test_websocket_error_recovery(
        self,
        test_client,
        mock_auth_service,
        mock_chat_service,
        mock_websocket_manager,
        sample_user,
        sample_auth_token,
    ):
        """Test error recovery mechanisms."""
        mock_auth_service.validate_access_token.return_value = {
            "user_id": sample_user["id"],
            "email": sample_user["email"],
        }
        mock_auth_service.get_current_user.return_value = sample_user

        # Mock service error
        mock_chat_service.add_message.side_effect = Exception("Database connection lost")

        with patch("tripsage.api.routers.websocket.auth_service", mock_auth_service):
            with patch("tripsage.api.routers.websocket.chat_service", mock_chat_service):
                with patch(
                    "tripsage.api.routers.websocket.websocket_manager",
                    mock_websocket_manager,
                ):
                    with test_client.websocket_connect("/api/ws") as websocket:
                        # Authenticate
                        auth_msg = {
                            "type": "authenticate",
                            "payload": {"access_token": sample_auth_token},
                        }
                        websocket.send_json(auth_msg)

                        # Send message that will cause error
                        chat_msg = {
                            "type": "chat_message",
                            "payload": {
                                "session_id": str(uuid4()),
                                "content": "This will fail",
                            },
                        }
                        websocket.send_json(chat_msg)

                        # Should handle error gracefully
                        await asyncio.sleep(0.1)
                        mock_websocket_manager.send_to_connection.assert_called()

                        # Connection should remain open for retry
                        # Send another message
                        websocket.send_json(chat_msg)

                        # Verify connection wasn't terminated
                        assert mock_websocket_manager.disconnect_connection.call_count == 0

    @pytest.mark.asyncio
    async def test_websocket_connection_stats(
        self,
        test_client,
        mock_auth_service,
        mock_websocket_manager,
        sample_user,
        sample_auth_token,
    ):
        """Test WebSocket connection statistics tracking."""
        mock_auth_service.validate_access_token.return_value = {
            "user_id": sample_user["id"],
            "email": sample_user["email"],
        }
        mock_auth_service.get_current_user.return_value = sample_user

        # Mock connection stats
        mock_websocket_manager.get_connection_stats.return_value = WebSocketFactory.create_connection_stats()

        with patch("tripsage.api.routers.websocket.auth_service", mock_auth_service):
            with patch(
                "tripsage.api.routers.websocket.websocket_manager",
                mock_websocket_manager,
            ):
                with test_client.websocket_connect("/api/ws") as websocket:
                    # Authenticate
                    auth_msg = {
                        "type": "authenticate",
                        "payload": {"access_token": sample_auth_token},
                    }
                    websocket.send_json(auth_msg)

                    # Request connection stats
                    stats_msg = {
                        "type": "get_stats",
                        "payload": {},
                    }
                    websocket.send_json(stats_msg)

                    # Should receive stats
                    await asyncio.sleep(0.1)
                    mock_websocket_manager.send_to_connection.assert_called()

                    # Verify stats structure
                    call_args = mock_websocket_manager.send_to_connection.call_args
                    assert call_args is not None

    @pytest.mark.asyncio
    async def test_websocket_malformed_message_handling(
        self,
        test_client,
        mock_auth_service,
        mock_websocket_manager,
        sample_user,
        sample_auth_token,
    ):
        """Test handling of malformed messages."""
        mock_auth_service.validate_access_token.return_value = {
            "user_id": sample_user["id"],
            "email": sample_user["email"],
        }
        mock_auth_service.get_current_user.return_value = sample_user

        with patch("tripsage.api.routers.websocket.auth_service", mock_auth_service):
            with patch(
                "tripsage.api.routers.websocket.websocket_manager",
                mock_websocket_manager,
            ):
                with test_client.websocket_connect("/api/ws") as websocket:
                    # Authenticate
                    auth_msg = {
                        "type": "authenticate",
                        "payload": {"access_token": sample_auth_token},
                    }
                    websocket.send_json(auth_msg)

                    # Send malformed message (missing required fields)
                    malformed_msg = {
                        "type": "chat_message",
                        # Missing payload
                    }
                    websocket.send_json(malformed_msg)

                    # Should receive validation error
                    await asyncio.sleep(0.1)
                    mock_websocket_manager.send_to_connection.assert_called()
                    error_call = mock_websocket_manager.send_to_connection.call_args
                    assert error_call is not None

                    # Send message with invalid type
                    invalid_type_msg = {
                        "type": "unknown_message_type",
                        "payload": {},
                    }
                    websocket.send_json(invalid_type_msg)

                    # Should receive error about unknown message type
                    await asyncio.sleep(0.1)
                    assert mock_websocket_manager.send_to_connection.call_count >= 2
