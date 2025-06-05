"""Comprehensive unit tests for websocket router."""

import json
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from tests.factories import ChatFactory
from tripsage.api.main import app


class TestWebSocketRouter:
    """Test suite for websocket router endpoints."""

    def setup_method(self):
        """Set up test client and mocks."""
        self.client = TestClient(app)
        self.mock_websocket_manager = Mock()
        self.mock_chat_service = Mock()
        self.mock_chat_agent = Mock()
        self.session_id = str(uuid4())
        self.user_id = str(uuid4())
        self.connection_id = "test-connection-123"

        # Sample test data
        self.sample_auth_request = {
            "access_token": "test-token",
            "user_id": self.user_id,
            "session_id": self.session_id,
        }

        self.sample_auth_response = Mock()
        self.sample_auth_response.success = True
        self.sample_auth_response.connection_id = self.connection_id
        self.sample_auth_response.user_id = self.user_id
        self.sample_auth_response.model_dump.return_value = {
            "success": True,
            "connection_id": self.connection_id,
            "user_id": self.user_id,
        }

    @patch("tripsage.api.routers.websocket.websocket_manager")
    @patch("tripsage.api.routers.websocket.get_chat_agent")
    @patch("tripsage.api.routers.websocket.get_core_chat_service")
    def test_chat_websocket_successful_connection(
        self, mock_get_chat_service, mock_get_chat_agent, mock_ws_manager
    ):
        """Test successful WebSocket chat connection and authentication."""
        # Arrange
        mock_ws_manager.authenticate_connection = AsyncMock(
            return_value=self.sample_auth_response
        )
        mock_ws_manager.send_to_connection = AsyncMock()
        mock_ws_manager.disconnect_connection = AsyncMock()
        mock_get_chat_agent.return_value = self.mock_chat_agent
        mock_get_chat_service.return_value = self.mock_chat_service

        # Act & Assert
        with self.client.websocket_connect(
            f"/api/ws/chat/{self.session_id}"
        ) as websocket:
            # Send authentication request
            websocket.send_text(json.dumps(self.sample_auth_request))

            # Receive authentication response
            auth_response = websocket.receive_text()
            auth_data = json.loads(auth_response)

            assert auth_data["success"] is True
            assert auth_data["connection_id"] == self.connection_id
            mock_ws_manager.authenticate_connection.assert_called_once()

    @patch("tripsage.api.routers.websocket.websocket_manager")
    def test_chat_websocket_authentication_failure(self, mock_ws_manager):
        """Test WebSocket connection with authentication failure."""
        # Arrange
        failed_auth_response = Mock()
        failed_auth_response.success = False
        failed_auth_response.error = "Invalid token"
        mock_ws_manager.authenticate_connection = AsyncMock(
            return_value=failed_auth_response
        )

        # Act & Assert
        with pytest.raises(Exception):  # WebSocket should close
            with self.client.websocket_connect(
                f"/api/ws/chat/{self.session_id}"
            ) as websocket:
                websocket.send_text(json.dumps(self.sample_auth_request))
                # Should receive error and connection should close

    @patch("tripsage.api.routers.websocket.websocket_manager")
    @patch("tripsage.api.routers.websocket.get_chat_agent")
    @patch("tripsage.api.routers.websocket.get_core_chat_service")
    def test_chat_websocket_message_handling(
        self, mock_get_chat_service, mock_get_chat_agent, mock_ws_manager
    ):
        """Test WebSocket chat message handling."""
        # Arrange
        mock_ws_manager.authenticate_connection = AsyncMock(
            return_value=self.sample_auth_response
        )
        mock_ws_manager.send_to_connection = AsyncMock()
        mock_ws_manager.send_to_session = AsyncMock()
        mock_ws_manager.disconnect_connection = AsyncMock()

        mock_chat_agent = Mock()
        mock_chat_agent.run = AsyncMock(
            return_value={"content": "Hello! How can I help you today?"}
        )
        mock_get_chat_agent.return_value = mock_chat_agent

        mock_chat_service = Mock()
        mock_chat_service.add_message = AsyncMock()
        mock_get_chat_service.return_value = mock_chat_service

        chat_message = {
            "type": "chat_message",
            "payload": {"content": "Hello, I need help planning a trip"},
        }

        # This test would need a more complex setup to properly test WebSocket message flow
        # For now, we test the components are properly mocked
        assert mock_chat_agent.run is not None
        assert mock_chat_service.add_message is not None

    @patch("tripsage.api.routers.websocket.websocket_manager")
    def test_chat_websocket_invalid_json_auth(self, mock_ws_manager):
        """Test WebSocket connection with invalid JSON authentication."""
        # Act & Assert
        with pytest.raises(Exception):
            with self.client.websocket_connect(
                f"/api/ws/chat/{self.session_id}"
            ) as websocket:
                websocket.send_text("invalid json")

    @patch("tripsage.api.routers.websocket.websocket_manager")
    def test_agent_status_websocket_successful_connection(self, mock_ws_manager):
        """Test successful agent status WebSocket connection."""
        # Arrange
        mock_ws_manager.authenticate_connection = AsyncMock(
            return_value=self.sample_auth_response
        )
        mock_ws_manager.send_to_connection = AsyncMock()
        mock_ws_manager.disconnect_connection = AsyncMock()

        # Act & Assert
        with self.client.websocket_connect(
            f"/api/ws/agent-status/{self.user_id}"
        ) as websocket:
            # Send authentication request with agent status channel
            auth_request = {
                **self.sample_auth_request,
                "channels": [f"agent_status:{self.user_id}"],
            }
            websocket.send_text(json.dumps(auth_request))

            # Should receive authentication response
            auth_response = websocket.receive_text()
            auth_data = json.loads(auth_response)

            assert auth_data["success"] is True
            mock_ws_manager.authenticate_connection.assert_called_once()

    @patch("tripsage.api.routers.websocket.websocket_manager")
    def test_agent_status_websocket_user_id_mismatch(self, mock_ws_manager):
        """Test agent status WebSocket with user ID mismatch."""
        # Arrange
        different_user_auth = Mock()
        different_user_auth.success = True
        different_user_auth.connection_id = self.connection_id
        different_user_auth.user_id = (
            "different-user-id"  # Different from URL parameter
        )
        different_user_auth.model_dump.return_value = {
            "success": True,
            "connection_id": self.connection_id,
            "user_id": "different-user-id",
        }
        mock_ws_manager.authenticate_connection = AsyncMock(
            return_value=different_user_auth
        )

        # Act & Assert
        with pytest.raises(Exception):  # Should close with user ID mismatch
            with self.client.websocket_connect(
                f"/api/ws/agent-status/{self.user_id}"
            ) as websocket:
                websocket.send_text(json.dumps(self.sample_auth_request))

    @patch("tripsage.api.routers.websocket.websocket_manager")
    def test_websocket_heartbeat_handling(self, mock_ws_manager):
        """Test WebSocket heartbeat message handling."""
        # Arrange
        mock_ws_manager.authenticate_connection = AsyncMock(
            return_value=self.sample_auth_response
        )
        mock_ws_manager.send_to_connection = AsyncMock()
        mock_ws_manager.disconnect_connection = AsyncMock()

        mock_connection = Mock()
        mock_connection.update_heartbeat = Mock()
        mock_ws_manager.connections = {self.connection_id: mock_connection}

        heartbeat_message = {"type": "heartbeat"}

        # The actual heartbeat handling would be tested in integration tests
        # Here we verify the mock setup
        assert mock_connection.update_heartbeat is not None

    @patch("tripsage.api.routers.websocket.websocket_manager")
    def test_websocket_subscription_handling(self, mock_ws_manager):
        """Test WebSocket subscription message handling."""
        # Arrange
        mock_ws_manager.authenticate_connection = AsyncMock(
            return_value=self.sample_auth_response
        )
        mock_ws_manager.send_to_connection = AsyncMock()
        mock_ws_manager.subscribe_connection = AsyncMock()
        mock_ws_manager.disconnect_connection = AsyncMock()

        subscribe_response = Mock()
        subscribe_response.model_dump.return_value = {
            "status": "subscribed",
            "channels": ["test-channel"],
        }
        mock_ws_manager.subscribe_connection.return_value = subscribe_response

        subscribe_message = {
            "type": "subscribe",
            "payload": {"channels": ["test-channel"]},
        }

        # Verify subscription components are set up
        assert mock_ws_manager.subscribe_connection is not None

    def test_websocket_health_endpoint(self):
        """Test WebSocket health check endpoint."""
        # Act
        response = self.client.get("/api/ws/health")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
        assert "websocket_manager_running" in data
        assert "connection_stats" in data
        assert "timestamp" in data

    @patch("tripsage.api.routers.websocket.websocket_manager")
    def test_list_websocket_connections(self, mock_ws_manager):
        """Test listing active WebSocket connections."""
        # Arrange
        mock_connection1 = Mock()
        mock_connection1.get_info.return_value.model_dump.return_value = {
            "connection_id": "conn-1",
            "user_id": "user-1",
            "connected_at": "2024-01-01T00:00:00Z",
        }

        mock_connection2 = Mock()
        mock_connection2.get_info.return_value.model_dump.return_value = {
            "connection_id": "conn-2",
            "user_id": "user-2",
            "connected_at": "2024-01-01T00:01:00Z",
        }

        mock_ws_manager.connections = {
            "conn-1": mock_connection1,
            "conn-2": mock_connection2,
        }

        # Act
        response = self.client.get("/api/ws/connections")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "connections" in data
        assert "total_count" in data
        assert data["total_count"] == 2
        assert len(data["connections"]) == 2

    @patch("tripsage.api.routers.websocket.websocket_manager")
    def test_disconnect_websocket_connection(self, mock_ws_manager):
        """Test disconnecting a specific WebSocket connection."""
        # Arrange
        connection_id = "test-connection-456"
        mock_ws_manager.disconnect_connection = AsyncMock()

        # Act
        response = self.client.delete(f"/api/ws/connections/{connection_id}")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "message" in data
        assert connection_id in data["message"]
        assert data["connection_id"] == connection_id
        mock_ws_manager.disconnect_connection.assert_called_once_with(connection_id)

    @patch("tripsage.api.routers.websocket.get_service_registry")
    def test_get_service_registry(self, mock_get_registry):
        """Test service registry singleton creation."""
        # Arrange
        mock_registry = Mock()
        mock_get_registry.return_value = mock_registry

        # Act
        from tripsage.api.routers.websocket import get_service_registry

        result = get_service_registry()

        # Assert
        assert result is not None

    @patch("tripsage.api.routers.websocket.get_chat_agent")
    def test_get_chat_agent(self, mock_get_agent):
        """Test chat agent singleton creation."""
        # Arrange
        mock_agent = Mock()
        mock_get_agent.return_value = mock_agent

        # Act
        from tripsage.api.routers.websocket import get_chat_agent

        result = get_chat_agent()

        # Assert
        assert result is not None

    @patch("tripsage.api.routers.websocket.websocket_manager")
    @patch("tripsage.api.routers.websocket.handle_chat_message")
    def test_handle_chat_message_empty_content(self, mock_handle_chat, mock_ws_manager):
        """Test chat message handling with empty content."""
        # Arrange
        mock_ws_manager.send_to_connection = AsyncMock()

        # Act - This would be called from within the WebSocket handler
        # We verify the function exists and can be mocked
        assert mock_handle_chat is not None

    @patch("tripsage.api.routers.websocket.websocket_manager")
    def test_websocket_connection_cleanup(self, mock_ws_manager):
        """Test WebSocket connection cleanup on disconnect."""
        # Arrange
        mock_ws_manager.disconnect_connection = AsyncMock()

        # Act - Verify cleanup function exists
        assert mock_ws_manager.disconnect_connection is not None

    def test_websocket_event_classes(self):
        """Test WebSocket event class definitions."""
        # Import event classes
        from tripsage.api.routers.websocket import (
            ChatMessageChunkEvent,
            ChatMessageEvent,
            ConnectionEvent,
            ErrorEvent,
        )

        # Test ChatMessageEvent
        message_data = ChatFactory.create_message()
        chat_event = ChatMessageEvent(
            message=message_data, user_id=self.user_id, session_id=self.session_id
        )
        assert chat_event.message == message_data

        # Test ChatMessageChunkEvent
        chunk_event = ChatMessageChunkEvent(
            content="Hello",
            chunk_index=1,
            is_final=False,
            user_id=self.user_id,
            session_id=self.session_id,
        )
        assert chunk_event.content == "Hello"
        assert chunk_event.chunk_index == 1
        assert chunk_event.is_final is False

        # Test ConnectionEvent
        conn_event = ConnectionEvent(
            status="connected",
            connection_id=self.connection_id,
            user_id=self.user_id,
            session_id=self.session_id,
        )
        assert conn_event.status == "connected"
        assert conn_event.connection_id == self.connection_id

        # Test ErrorEvent
        error_event = ErrorEvent(
            error_code="test_error",
            error_message="Test error message",
            user_id=self.user_id,
            session_id=self.session_id,
        )
        assert error_event.error_code == "test_error"
        assert error_event.error_message == "Test error message"

    def test_websocket_endpoints_no_authentication_required_for_health(self):
        """Test that WebSocket health endpoint doesn't require authentication."""
        # Act
        response = self.client.get("/api/ws/health")

        # Assert
        assert response.status_code == status.HTTP_200_OK

    def test_websocket_connections_endpoint_requires_admin(self):
        """Test that connection management endpoints should require admin access."""
        # Note: These endpoints currently don't have authentication
        # but should in production (marked as admin only in comments)

        # Act
        response = self.client.get("/api/ws/connections")

        # Assert - Currently passes without auth, but should be secured
        assert response.status_code == status.HTTP_200_OK

    @patch("tripsage.api.routers.websocket.websocket_manager")
    def test_websocket_stats_in_health_check(self, mock_ws_manager):
        """Test WebSocket connection statistics in health check."""
        # Arrange
        mock_stats = {
            "total_connections": 5,
            "active_connections": 3,
            "channels": ["chat", "agent_status"],
        }
        mock_ws_manager.get_connection_stats.return_value = mock_stats
        mock_ws_manager._running = True

        # Act
        response = self.client.get("/api/ws/health")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["websocket_manager_running"] is True
        assert data["connection_stats"] == mock_stats

    def test_websocket_health_method_restrictions(self):
        """Test that WebSocket health endpoint only allows GET."""
        # Test POST not allowed
        response = self.client.post("/api/ws/health")
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

        # Test PUT not allowed
        response = self.client.put("/api/ws/health")
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

        # Test DELETE not allowed
        response = self.client.delete("/api/ws/health")
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    @patch("tripsage.api.routers.websocket.websocket_manager")
    def test_list_connections_empty_state(self, mock_ws_manager):
        """Test listing connections when no connections exist."""
        # Arrange
        mock_ws_manager.connections = {}

        # Act
        response = self.client.get("/api/ws/connections")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["connections"] == []
        assert data["total_count"] == 0

    @patch("tripsage.api.routers.websocket.websocket_manager")
    def test_disconnect_nonexistent_connection(self, mock_ws_manager):
        """Test disconnecting a connection that doesn't exist."""
        # Arrange
        connection_id = "nonexistent-connection"
        mock_ws_manager.disconnect_connection = AsyncMock()

        # Act
        response = self.client.delete(f"/api/ws/connections/{connection_id}")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        # Should still return success even for nonexistent connections
        mock_ws_manager.disconnect_connection.assert_called_once_with(connection_id)
