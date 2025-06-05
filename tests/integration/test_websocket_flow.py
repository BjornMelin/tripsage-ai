"""
Comprehensive integration tests for WebSocket functionality.

This module tests the complete WebSocket lifecycle including connection,
authentication, message handling, agent status updates, broadcasting,
and error recovery scenarios.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from tests.factories import ChatFactory, UserFactory, WebSocketFactory
from tripsage.api.main import app
from tripsage_core.exceptions.exceptions import (
    CoreAuthenticationError,
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
        # Mock authentication success
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
                with test_client.websocket_connect("/ws") as websocket:
                    # Send authentication message
                    auth_msg = {
                        "type": "authenticate",
                        "payload": {"access_token": sample_auth_token},
                    }
                    websocket.send_json(auth_msg)

                    # Verify connection was established
                    mock_websocket_manager.connect.assert_called_once()

                    # Send a chat message
                    chat_msg = {
                        "type": "chat_message",
                        "payload": {
                            "session_id": str(uuid4()),
                            "content": "Hello, I need help planning a trip",
                        },
                    }
                    websocket.send_json(chat_msg)

                    # Verify message was processed
                    await asyncio.sleep(0.1)  # Give time for async processing

                # Verify disconnection
                mock_websocket_manager.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_websocket_authentication_required(
        self, test_client, mock_websocket_manager
    ):
        """Test that authentication is required for WebSocket connection."""
        with patch(
            "tripsage.api.routers.websocket.websocket_manager", mock_websocket_manager
        ):
            with test_client.websocket_connect("/ws") as websocket:
                # Try to send message without authentication
                chat_msg = {
                    "type": "chat_message",
                    "payload": {"content": "Hello"},
                }
                websocket.send_json(chat_msg)

                # Should receive error message
                response = websocket.receive_json()
                assert response["type"] == "error"
                assert "authentication" in response["error_message"].lower()

    @pytest.mark.asyncio
    async def test_websocket_invalid_token(
        self, test_client, mock_auth_service, mock_websocket_manager
    ):
        """Test WebSocket connection with invalid token."""
        # Mock authentication failure
        mock_auth_service.validate_access_token.side_effect = CoreAuthenticationError(
            "Invalid token"
        )

        with patch("tripsage.api.routers.websocket.auth_service", mock_auth_service):
            with patch(
                "tripsage.api.routers.websocket.websocket_manager",
                mock_websocket_manager,
            ):
                with test_client.websocket_connect("/ws") as websocket:
                    # Send authentication with invalid token
                    auth_msg = {
                        "type": "authenticate",
                        "payload": {"access_token": "invalid-token"},
                    }
                    websocket.send_json(auth_msg)

                    # Should receive error message
                    response = websocket.receive_json()
                    assert response["type"] == "error"
                    assert response["error_code"] == "AUTHENTICATION_ERROR"

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
        session_id = str(uuid4())

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
            with patch(
                "tripsage.api.routers.websocket.chat_service", mock_chat_service
            ):
                with patch(
                    "tripsage.api.routers.websocket.websocket_manager",
                    mock_websocket_manager,
                ):
                    # Connect first client
                    with test_client.websocket_connect("/ws") as ws1:
                        # Authenticate first client
                        auth_msg = {
                            "type": "authenticate",
                            "payload": {"access_token": sample_auth_token},
                        }
                        ws1.send_json(auth_msg)

                        # Connect second client
                        with test_client.websocket_connect("/ws") as ws2:
                            # Authenticate second client
                            ws2.send_json(auth_msg)

                            # Send message from first client
                            chat_msg = {
                                "type": "chat_message",
                                "payload": {
                                    "session_id": session_id,
                                    "content": "Hello everyone",
                                },
                            }
                            ws1.send_json(chat_msg)

                            # Verify broadcast was called
                            await asyncio.sleep(0.1)
                            mock_websocket_manager.broadcast_to_session.assert_called()

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
                with test_client.websocket_connect("/ws") as websocket:
                    # Authenticate
                    auth_msg = {
                        "type": "authenticate",
                        "payload": {"access_token": sample_auth_token},
                    }
                    websocket.send_json(auth_msg)

                    # Subscribe to agent status updates
                    subscribe_msg = {
                        "type": "subscribe",
                        "payload": {"channels": ["agent_status"]},
                    }
                    websocket.send_json(subscribe_msg)

                    # Simulate agent status update
                    _status_update = {
                        "type": "agent_status",
                        "payload": {
                            "agent_id": "flight_agent",
                            "status": "processing",
                            "message": "Searching for flights...",
                            "progress": 0.5,
                        },
                    }

                    # Verify subscription handling
                    await asyncio.sleep(0.1)
                    mock_websocket_manager.send_personal_message.assert_called()

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
        # Mock authentication
        mock_auth_service.validate_access_token.return_value = {
            "user_id": sample_user["id"],
            "email": sample_user["email"],
        }
        mock_auth_service.get_current_user.return_value = sample_user

        # Mock rate limit error on chat service
        mock_chat_service.add_message.side_effect = CoreRateLimitError(
            "Rate limit exceeded"
        )

        with patch("tripsage.api.routers.websocket.auth_service", mock_auth_service):
            with patch(
                "tripsage.api.routers.websocket.chat_service", mock_chat_service
            ):
                with patch(
                    "tripsage.api.routers.websocket.websocket_manager",
                    mock_websocket_manager,
                ):
                    with test_client.websocket_connect("/ws") as websocket:
                        # Authenticate
                        auth_msg = {
                            "type": "authenticate",
                            "payload": {"access_token": sample_auth_token},
                        }
                        websocket.send_json(auth_msg)

                        # Send multiple messages quickly
                        for i in range(5):
                            chat_msg = {
                                "type": "chat_message",
                                "payload": {
                                    "session_id": str(uuid4()),
                                    "content": f"Message {i}",
                                },
                            }
                            websocket.send_json(chat_msg)

                        # Should receive rate limit error
                        await asyncio.sleep(0.1)
                        mock_websocket_manager.send_error.assert_called()
                        error_call = mock_websocket_manager.send_error.call_args
                        assert "rate limit" in str(error_call).lower()

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
        connection_id = str(uuid4())

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
                # First connection
                with test_client.websocket_connect("/ws") as ws1:
                    # Authenticate with connection ID
                    auth_msg = {
                        "type": "authenticate",
                        "payload": {
                            "access_token": sample_auth_token,
                            "connection_id": connection_id,
                        },
                    }
                    ws1.send_json(auth_msg)

                # Simulate disconnection
                mock_websocket_manager.disconnect.assert_called()

                # Reconnect with same connection ID
                with test_client.websocket_connect("/ws") as ws2:
                    # Re-authenticate with same connection ID
                    ws2.send_json(auth_msg)

                    # Should restore session state
                    assert mock_websocket_manager.connect.call_count == 2

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
                with test_client.websocket_connect("/ws") as websocket:
                    # Authenticate
                    auth_msg = {
                        "type": "authenticate",
                        "payload": {"access_token": sample_auth_token},
                    }
                    websocket.send_json(auth_msg)

                    # Send heartbeat
                    heartbeat_msg = WebSocketFactory.create_heartbeat_message()
                    websocket.send_json(heartbeat_msg)

                    # Should receive heartbeat response
                    await asyncio.sleep(0.1)
                    mock_websocket_manager.send_personal_message.assert_called()

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
        session_id = str(uuid4())

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
                with test_client.websocket_connect("/ws") as websocket:
                    # Authenticate
                    auth_msg = {
                        "type": "authenticate",
                        "payload": {"access_token": sample_auth_token},
                    }
                    websocket.send_json(auth_msg)

                    # Send typing indicator
                    typing_msg = WebSocketFactory.create_typing_event(
                        user_id=sample_user["id"],
                        session_id=session_id,
                        is_typing=True,
                    )
                    websocket.send_json(typing_msg)

                    # Should broadcast typing status
                    await asyncio.sleep(0.1)
                    mock_websocket_manager.broadcast_to_session.assert_called()

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
        session_id = str(uuid4())

        mock_auth_service.validate_access_token.return_value = {
            "user_id": sample_user["id"],
            "email": sample_user["email"],
        }
        mock_auth_service.get_current_user.return_value = sample_user

        # Mock streaming response
        async def stream_response():
            chunks = [
                "I can help you ",
                "plan your trip ",
                "to Paris. ",
                "What dates are you considering?",
            ]
            for i, chunk in enumerate(chunks):
                yield WebSocketFactory.create_message_chunk(
                    content=chunk,
                    chunk_index=i,
                    is_final=(i == len(chunks) - 1),
                    session_id=session_id,
                )

        mock_chat_service.add_message.return_value = stream_response()

        with patch("tripsage.api.routers.websocket.auth_service", mock_auth_service):
            with patch(
                "tripsage.api.routers.websocket.chat_service", mock_chat_service
            ):
                with patch(
                    "tripsage.api.routers.websocket.websocket_manager",
                    mock_websocket_manager,
                ):
                    with test_client.websocket_connect("/ws") as websocket:
                        # Authenticate
                        auth_msg = {
                            "type": "authenticate",
                            "payload": {"access_token": sample_auth_token},
                        }
                        websocket.send_json(auth_msg)

                        # Send message requesting streaming
                        chat_msg = {
                            "type": "chat_message",
                            "payload": {
                                "session_id": session_id,
                                "content": "Help me plan a trip to Paris",
                                "stream": True,
                            },
                        }
                        websocket.send_json(chat_msg)

                        # Verify streaming chunks are sent
                        await asyncio.sleep(0.1)
                        assert (
                            mock_websocket_manager.send_personal_message.call_count >= 4
                        )

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
        mock_chat_service.add_message.side_effect = Exception(
            "Database connection lost"
        )

        with patch("tripsage.api.routers.websocket.auth_service", mock_auth_service):
            with patch(
                "tripsage.api.routers.websocket.chat_service", mock_chat_service
            ):
                with patch(
                    "tripsage.api.routers.websocket.websocket_manager",
                    mock_websocket_manager,
                ):
                    with test_client.websocket_connect("/ws") as websocket:
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
                        mock_websocket_manager.send_error.assert_called()

                        # Connection should remain open for retry
                        # Send another message
                        websocket.send_json(chat_msg)

                        # Verify connection wasn't terminated
                        assert mock_websocket_manager.disconnect.call_count == 0

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
        mock_websocket_manager.get_connection_stats.return_value = (
            WebSocketFactory.create_connection_stats()
        )

        with patch("tripsage.api.routers.websocket.auth_service", mock_auth_service):
            with patch(
                "tripsage.api.routers.websocket.websocket_manager",
                mock_websocket_manager,
            ):
                with test_client.websocket_connect("/ws") as websocket:
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
                    mock_websocket_manager.send_personal_message.assert_called()

                    # Verify stats structure
                    call_args = mock_websocket_manager.send_personal_message.call_args
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
                with test_client.websocket_connect("/ws") as websocket:
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
                    mock_websocket_manager.send_error.assert_called()
                    error_call = mock_websocket_manager.send_error.call_args
                    assert "validation" in str(error_call).lower()

                    # Send message with invalid type
                    invalid_type_msg = {
                        "type": "unknown_message_type",
                        "payload": {},
                    }
                    websocket.send_json(invalid_type_msg)

                    # Should receive error about unknown message type
                    await asyncio.sleep(0.1)
                    assert mock_websocket_manager.send_error.call_count >= 2
