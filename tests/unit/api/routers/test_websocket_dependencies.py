"""
Tests for WebSocket router dependency injection.

This module tests the refactored WebSocket router's dependency injection
functionality for database sessions and CoreChatService.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from tripsage.api.routers.websocket import get_core_chat_service
from tripsage_core.services.business.chat_service import ChatService as CoreChatService


class TestWebSocketDependencies:
    """Test WebSocket dependency injection."""

    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        session = MagicMock(spec=AsyncSession)
        return session

    @pytest.mark.asyncio
    async def test_get_core_chat_service_dependency(self, mock_db_session):
        """Test that get_core_chat_service creates CoreChatService with db dependency."""
        with patch(
            "tripsage.api.routers.websocket.CoreChatService"
        ) as mock_service_class:
            mock_instance = AsyncMock()
            mock_service_class.return_value = mock_instance

            result = await get_core_chat_service(db=mock_db_session)

            mock_service_class.assert_called_once_with(database_service=mock_db_session)
            assert result == mock_instance

    @pytest.mark.asyncio
    async def test_get_core_chat_service_returns_core_service_instance(
        self, mock_db_session
    ):
        """Test that get_core_chat_service returns a CoreChatService instance."""
        # Test with real CoreChatService instantiation (mocked internally)
        with patch(
            "tripsage.api.routers.websocket.CoreChatService"
        ) as mock_service_class:
            # Create a mock that behaves like CoreChatService
            mock_instance = AsyncMock()
            mock_instance.add_message = AsyncMock()
            mock_instance.get_session = AsyncMock()
            mock_service_class.return_value = mock_instance

            result = await get_core_chat_service(db=mock_db_session)

            # Verify the service was created with the database dependency
            mock_service_class.assert_called_once_with(database_service=mock_db_session)
            assert result == mock_instance

            # Verify the returned object has the expected CoreChatService methods
            assert hasattr(result, "add_message")
            assert hasattr(result, "get_session")

    def test_dependency_function_signature(self):
        """Test that dependency functions have correct signatures for FastAPI."""
        import inspect

        # Test get_core_chat_service signature
        sig = inspect.signature(get_core_chat_service)

        # Should have 'db' parameter with AsyncSession annotation
        assert "db" in sig.parameters
        db_param = sig.parameters["db"]
        assert db_param.annotation == AsyncSession

        # Should have Depends() as default
        assert db_param.default is not None
        assert str(type(db_param.default)) == "<class 'fastapi.params.Depends'>"


class TestWebSocketRouterSetup:
    """Test WebSocket router configuration."""

    def test_websocket_router_exists(self):
        """Test that WebSocket router is properly configured."""
        from fastapi import APIRouter

        from tripsage.api.routers.websocket import router

        assert isinstance(router, APIRouter)

    def test_websocket_endpoints_exist(self):
        """Test that expected WebSocket endpoints are configured."""
        from fastapi import FastAPI

        from tripsage.api.routers.websocket import router

        # Create a test app to inspect routes
        app = FastAPI()
        app.include_router(router)

        # Get all route paths
        route_paths = [route.path for route in app.routes if hasattr(route, "path")]

        # Verify key WebSocket endpoints exist
        expected_endpoints = [
            "/ws/chat/{session_id}",
            "/ws/agent-status/{user_id}",
            "/ws/health",
            "/ws/connections",
            "/ws/connections/{connection_id}",
        ]

        for endpoint in expected_endpoints:
            assert endpoint in route_paths, f"Missing endpoint: {endpoint}"

    def test_websocket_endpoint_has_dependency_injection(self):
        """Test that WebSocket chat endpoint has proper dependency injection."""
        import inspect

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
    """Test WebSocket event model creation."""

    @pytest.mark.asyncio
    async def test_websocket_event_models_can_be_imported(self):
        """Test that WebSocket event models can be imported and created."""
        # Import the event models
        from tripsage.api.routers.websocket import (
            ChatMessageChunkEvent,
            ChatMessageEvent,
            ConnectionEvent,
            ErrorEvent,
        )

        # Verify they're all classes
        assert callable(ChatMessageEvent)
        assert callable(ChatMessageChunkEvent)
        assert callable(ConnectionEvent)
        assert callable(ErrorEvent)

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


class TestWebSocketHealthEndpoint:
    """Test WebSocket health check functionality."""

    def test_websocket_health_endpoint_returns_status(self):
        """Test that health endpoint returns proper status."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from tripsage.api.routers.websocket import router

        # Create test app
        app = FastAPI()
        app.include_router(router)

        with patch("tripsage.api.routers.websocket.websocket_manager") as mock_manager:
            # Mock the websocket manager
            mock_manager.get_connection_stats.return_value = {
                "total_connections": 0,
                "active_connections": 0,
            }
            mock_manager._running = True

            client = TestClient(app)
            response = client.get("/ws/health")

            assert response.status_code == 200
            data = response.json()

            # Verify health response structure
            assert "status" in data
            assert "websocket_manager_running" in data
            assert "connection_stats" in data
            assert data["status"] == "healthy"
            assert data["websocket_manager_running"] is True


class TestWebSocketIntegration:
    """Test WebSocket integration with other components."""

    @pytest.mark.asyncio
    async def test_websocket_manager_integration(self):
        """Test that WebSocket router integrates with websocket_manager."""
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

    def test_websocket_imports_core_services(self):
        """Test that WebSocket router properly imports core services."""
        # Verify CoreChatService import
        from tripsage.api.routers.websocket import CoreChatService

        assert CoreChatService is not None

        # Verify WebSocket models import
        from tripsage.api.routers.websocket import (
            MessageCreateRequest,
            MessageRole,
        )

        assert MessageCreateRequest is not None
        assert MessageRole is not None

    def test_websocket_uses_proper_dependencies(self):
        """Test that WebSocket router uses proper dependency injection."""
        from tripsage.api.core.dependencies import get_db as core_get_db
        from tripsage.api.routers.websocket import get_db

        # Verify it's using the core dependency function
        assert get_db == core_get_db
