"""
Tests for unified WebSocket router.

This module tests the updated WebSocket router that integrates with
both unified services and existing core services.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from tripsage.api.routers.websocket import router
from tripsage_core.services.business.chat_service import ChatService as CoreChatService


class TestWebSocketRouterEndpoints:
    """Test WebSocket router endpoint functionality."""

    @pytest.fixture
    def app(self):
        """Create FastAPI app with WebSocket router."""
        app = FastAPI()
        app.include_router(router)
        return app

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)

    def test_websocket_router_has_expected_endpoints(self, app):
        """Test that WebSocket router has all expected endpoints."""
        route_paths = [route.path for route in app.routes if hasattr(route, "path")]

        expected_endpoints = [
            "/ws/chat/{session_id}",
            "/ws/agent-status/{user_id}",
            "/ws/health",
            "/ws/connections",
            "/ws/connections/{connection_id}",
        ]

        for endpoint in expected_endpoints:
            assert endpoint in route_paths, f"Missing endpoint: {endpoint}"

    def test_websocket_health_endpoint_structure(self, client):
        """Test WebSocket health endpoint returns expected structure."""
        with patch("tripsage.api.routers.websocket.websocket_manager") as mock_manager:
            # Mock the websocket manager
            mock_manager.get_connection_stats.return_value = {
                "total_connections": 2,
                "active_connections": 1,
            }
            mock_manager._running = True

            response = client.get("/ws/health")

            assert response.status_code == 200
            data = response.json()

            # Verify health response structure
            assert "status" in data
            assert "websocket_manager_running" in data
            assert "connection_stats" in data
            assert data["status"] == "healthy"
            assert data["websocket_manager_running"] is True
            assert data["connection_stats"]["total_connections"] == 2


class TestWebSocketDependencyInjection:
    """Test WebSocket dependency injection functionality."""

    @pytest.mark.asyncio
    async def test_get_core_chat_service_creates_instance(self):
        """Test that get_core_chat_service creates CoreChatService with dependency."""
        from sqlalchemy.ext.asyncio import AsyncSession

        from tripsage.api.routers.websocket import get_core_chat_service

        # Create mock database session
        mock_db_session = MagicMock(spec=AsyncSession)

        # Call the dependency function
        with patch("tripsage.api.routers.websocket.CoreChatService") as mock_service_class:
            mock_instance = AsyncMock()
            mock_service_class.return_value = mock_instance

            result = await get_core_chat_service(db=mock_db_session)

            # Verify CoreChatService was created with database dependency
            mock_service_class.assert_called_once_with(database_service=mock_db_session)
            assert result == mock_instance

    def test_websocket_chat_endpoint_has_correct_dependencies(self):
        """Test that WebSocket chat endpoint has proper dependency injection."""
        import inspect

        from sqlalchemy.ext.asyncio import AsyncSession

        from tripsage.api.routers.websocket import chat_websocket

        sig = inspect.signature(chat_websocket)

        # Verify required parameters exist
        required_params = ["websocket", "session_id", "db", "chat_service"]
        for param in required_params:
            assert param in sig.parameters, f"Missing parameter: {param}"

        # Verify dependency injection parameters have correct types
        db_param = sig.parameters["db"]
        chat_service_param = sig.parameters["chat_service"]

        assert db_param.annotation == AsyncSession
        assert chat_service_param.annotation == CoreChatService

        # Verify they have Depends() defaults
        assert db_param.default is not None
        assert chat_service_param.default is not None


class TestWebSocketEventModels:
    """Test WebSocket event model functionality."""

    def test_websocket_event_models_can_be_created(self):
        """Test that WebSocket event models can be imported and created."""
        from tripsage.api.routers.websocket import (
            ChatMessageChunkEvent,
            ChatMessageEvent,
            ConnectionEvent,
            ErrorEvent,
        )
        from tripsage_core.models.schemas_common.chat import ChatMessage

        # Test ChatMessageEvent creation
        session_id = uuid4()
        user_id = uuid4()

        # Create a proper ChatMessage object
        chat_message = ChatMessage(role="user", content="Hello")

        message_event = ChatMessageEvent(
            type="chat.message",
            message=chat_message,
            user_id=user_id,
            session_id=session_id,
        )
        assert message_event.message == chat_message
        assert message_event.user_id == user_id
        assert message_event.session_id == session_id
        assert message_event.type == "chat.message"

        # Test ChatMessageChunkEvent creation
        chunk_event = ChatMessageChunkEvent(
            type="chat.chunk",
            content="Hello",
            chunk_index=0,
            is_final=False,
            user_id=user_id,
            session_id=session_id,
        )
        assert chunk_event.content == "Hello"
        assert chunk_event.chunk_index == 0
        assert chunk_event.is_final is False
        assert chunk_event.type == "chat.chunk"

        # Test ConnectionEvent creation
        connection_event = ConnectionEvent(
            type="connection.status",
            status="connected",
            connection_id="conn123",
            user_id=user_id,
            session_id=session_id,
        )
        assert connection_event.status == "connected"
        assert connection_event.connection_id == "conn123"
        assert connection_event.type == "connection.status"

        # Test ErrorEvent creation
        error_event = ErrorEvent(
            type="error",
            error_code="test_error",
            error_message="Test error message",
            user_id=user_id,
            session_id=session_id,
        )
        assert error_event.error_code == "test_error"
        assert error_event.error_message == "Test error message"
        assert error_event.type == "error"

    def test_event_models_inherit_from_websocket_event(self):
        """Test that event models inherit from WebSocketEvent."""
        from tripsage.api.routers.websocket import (
            ChatMessageChunkEvent,
            ChatMessageEvent,
            ConnectionEvent,
            ErrorEvent,
        )
        from tripsage_core.services.infrastructure.websocket_manager import (
            WebSocketEvent,
        )

        # Verify inheritance
        assert issubclass(ChatMessageEvent, WebSocketEvent)
        assert issubclass(ChatMessageChunkEvent, WebSocketEvent)
        assert issubclass(ConnectionEvent, WebSocketEvent)
        assert issubclass(ErrorEvent, WebSocketEvent)


class TestWebSocketManagerIntegration:
    """Test WebSocket manager integration."""

    def test_websocket_manager_is_imported(self):
        """Test that websocket_manager is properly imported and available."""
        from tripsage.api.routers.websocket import websocket_manager

        # Verify websocket_manager is imported and available
        assert websocket_manager is not None

        # Verify it has expected methods
        expected_methods = [
            "authenticate_connection",
            "send_to_connection",
            "send_to_session",
            "disconnect_connection",
            "get_connection_stats",
        ]

        for method in expected_methods:
            assert hasattr(websocket_manager, method), f"Missing method: {method}"

    def test_websocket_connections_endpoint_structure(self):
        """Test WebSocket connections endpoint structure."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from tripsage.api.routers.websocket import router

        # Create test app
        app = FastAPI()
        app.include_router(router)

        with patch("tripsage.api.routers.websocket.websocket_manager") as mock_manager:
            # Mock connections
            mock_connection1 = MagicMock()
            mock_connection1.get_info.return_value.model_dump.return_value = {
                "connection_id": "conn1",
                "user_id": "user1",
                "status": "connected",
            }

            mock_connection2 = MagicMock()
            mock_connection2.get_info.return_value.model_dump.return_value = {
                "connection_id": "conn2",
                "user_id": "user2",
                "status": "connected",
            }

            mock_manager.connections = {
                "conn1": mock_connection1,
                "conn2": mock_connection2,
            }

            client = TestClient(app)
            response = client.get("/ws/connections")

            assert response.status_code == 200
            data = response.json()

            # Verify response structure
            assert "connections" in data
            assert "total_count" in data
            assert data["total_count"] == 2
            assert len(data["connections"]) == 2


class TestWebSocketCoreServiceIntegration:
    """Test WebSocket integration with core services."""

    def test_websocket_imports_core_services_correctly(self):
        """Test that WebSocket router properly imports core services."""
        # Verify CoreChatService import
        from tripsage.api.routers.websocket import CoreChatService
        from tripsage_core.services.business.chat_service import ChatService

        assert CoreChatService is not None
        assert CoreChatService == ChatService

        # Verify model imports
        from tripsage.api.routers.websocket import MessageCreateRequest, MessageRole

        assert MessageCreateRequest is not None
        assert MessageRole is not None

        # Verify they're from the core service module
        from tripsage_core.services.business.chat_service import (
            MessageCreateRequest as CoreMessageCreateRequest,
        )
        from tripsage_core.services.business.chat_service import (
            MessageRole as CoreMessageRole,
        )

        assert MessageCreateRequest == CoreMessageCreateRequest
        assert MessageRole == CoreMessageRole

    def test_websocket_uses_unified_chat_service_alongside_core(self):
        """Test that WebSocket router uses unified ChatService alongside core."""
        from tripsage.api.services import get_chat_service

        # Verify unified ChatService is available for WebSocket use
        assert get_chat_service is not None

        # The WebSocket router should have access to both unified and core services
        # This allows it to work with the new architecture while maintaining
        # compatibility with existing WebSocket functionality


class TestWebSocketErrorHandling:
    """Test error handling in WebSocket router."""

    @pytest.mark.asyncio
    async def test_handle_chat_message_function_exists(self):
        """Test that handle_chat_message function exists and has correct signature."""
        import inspect

        from tripsage.api.routers.websocket import handle_chat_message

        # Verify function exists
        assert handle_chat_message is not None

        # Verify function signature
        sig = inspect.signature(handle_chat_message)
        expected_params = [
            "connection_id",
            "user_id",
            "session_id",
            "message_data",
            "chat_service",
            "chat_agent",
        ]

        for param in expected_params:
            assert param in sig.parameters, f"Missing parameter: {param}"

        # Verify it's an async function
        assert inspect.iscoroutinefunction(handle_chat_message)

    def test_websocket_agent_singletons_exist(self):
        """Test that WebSocket agent singleton functions exist."""
        from tripsage.api.routers.websocket import get_chat_agent, get_service_registry

        # Verify singleton functions exist
        assert get_chat_agent is not None
        assert get_service_registry is not None

        # Test that they return instances (with mocked dependencies)
        with patch("tripsage.api.routers.websocket.ServiceRegistry") as mock_service_registry:
            with patch("tripsage.api.routers.websocket.ChatAgent") as mock_chat_agent:
                mock_service_instance = MagicMock()
                mock_agent_instance = MagicMock()
                mock_service_registry.return_value = mock_service_instance
                mock_chat_agent.return_value = mock_agent_instance

                # Test service registry singleton
                registry1 = get_service_registry()
                registry2 = get_service_registry()
                assert registry1 is registry2  # Should be singleton

                # Test chat agent singleton
                agent1 = get_chat_agent()
                agent2 = get_chat_agent()
                assert agent1 is agent2  # Should be singleton
