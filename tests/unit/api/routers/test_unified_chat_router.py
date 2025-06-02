"""
Tests for unified Chat router.

This module tests the updated chat router that uses the unified ChatService
adapter for clean separation of concerns.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from fastapi import HTTPException
from fastapi.testclient import TestClient
from fastapi import FastAPI

from tripsage.api.routers.chat import router
from tripsage.api.services.chat import ChatService
from tripsage.api.middlewares.authentication import Principal
from tripsage.api.schemas.requests.chat import ChatRequest, SessionCreateRequest


class TestChatRouterEndpoints:
    """Test chat router endpoint functionality."""

    @pytest.fixture
    def app(self):
        """Create FastAPI app with chat router."""
        app = FastAPI()
        app.include_router(router)
        return app

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)

    def test_chat_router_has_expected_endpoints(self, app):
        """Test that chat router has all expected endpoints."""
        route_paths = [route.path for route in app.routes if hasattr(route, "path")]

        expected_endpoints = [
            "/",
            "/sessions",
            "/sessions/{session_id}",
            "/sessions/{session_id}/messages",
        ]

        for endpoint in expected_endpoints:
            assert endpoint in route_paths, f"Missing endpoint: {endpoint}"

    def test_chat_router_endpoints_have_correct_methods(self, app):
        """Test that endpoints have correct HTTP methods."""
        routes = {route.path: route for route in app.routes if hasattr(route, "path")}

        # Verify HTTP methods for each endpoint
        assert "POST" in routes["/"].methods
        assert "POST" in routes["/sessions"].methods
        assert "GET" in routes["/sessions"].methods
        assert "GET" in routes["/sessions/{session_id}"].methods
        assert "DELETE" in routes["/sessions/{session_id}"].methods
        assert "GET" in routes["/sessions/{session_id}/messages"].methods
        assert "POST" in routes["/sessions/{session_id}/messages"].methods


class TestChatEndpoint:
    """Test main chat completion endpoint."""

    @pytest.mark.asyncio
    async def test_chat_endpoint_delegates_to_service(self):
        """Test that chat endpoint delegates to ChatService."""
        from tripsage.api.routers.chat import chat

        # Create mocks
        mock_principal = MagicMock(spec=Principal)
        mock_principal.id = str(uuid4())
        mock_chat_service = AsyncMock(spec=ChatService)
        
        # Mock service response
        mock_response = {
            "content": "Hello back!",
            "session_id": str(uuid4()),
            "finish_reason": "stop",
        }
        mock_chat_service.chat_completion.return_value = mock_response

        # Create request
        request = ChatRequest(
            messages=[{"role": "user", "content": "Hello"}],
            stream=False,
        )

        # Call endpoint
        with patch("tripsage.api.routers.chat.get_principal_id") as mock_get_id:
            mock_get_id.return_value = mock_principal.id
            
            result = await chat(
                request=request,
                principal=mock_principal,
                chat_service=mock_chat_service,
            )

        # Verify service was called correctly
        mock_chat_service.chat_completion.assert_called_once_with(
            mock_principal.id, request
        )
        assert result == mock_response

    @pytest.mark.asyncio
    async def test_chat_endpoint_handles_service_errors(self):
        """Test that chat endpoint handles service errors properly."""
        from tripsage.api.routers.chat import chat

        # Create mocks
        mock_principal = MagicMock(spec=Principal)
        mock_principal.id = str(uuid4())
        mock_chat_service = AsyncMock(spec=ChatService)
        
        # Mock service to raise an error
        mock_chat_service.chat_completion.side_effect = Exception("Service error")

        # Create request
        request = ChatRequest(
            messages=[{"role": "user", "content": "Hello"}],
        )

        # Call endpoint and expect HTTPException
        with patch("tripsage.api.routers.chat.get_principal_id") as mock_get_id:
            mock_get_id.return_value = mock_principal.id
            
            with pytest.raises(HTTPException) as exc_info:
                await chat(
                    request=request,
                    principal=mock_principal,
                    chat_service=mock_chat_service,
                )

        assert exc_info.value.status_code == 500
        assert "Chat request failed" in exc_info.value.detail


class TestSessionEndpoints:
    """Test session management endpoints."""

    @pytest.mark.asyncio
    async def test_create_session_endpoint_delegates_to_service(self):
        """Test that create_session endpoint delegates to ChatService."""
        from tripsage.api.routers.chat import create_session

        # Create mocks
        mock_principal = MagicMock(spec=Principal)
        mock_principal.id = str(uuid4())
        mock_chat_service = AsyncMock(spec=ChatService)
        
        # Mock service response
        mock_session = {
            "id": str(uuid4()),
            "title": "Test Session",
            "user_id": mock_principal.id,
        }
        mock_chat_service.create_session.return_value = mock_session

        # Call endpoint
        with patch("tripsage.api.routers.chat.get_principal_id") as mock_get_id:
            mock_get_id.return_value = mock_principal.id
            
            result = await create_session(
                title="Test Session",
                principal=mock_principal,
                chat_service=mock_chat_service,
            )

        # Verify service was called correctly
        mock_chat_service.create_session.assert_called_once()
        call_args = mock_chat_service.create_session.call_args
        assert call_args[0][0] == mock_principal.id  # user_id
        assert call_args[0][1].title == "Test Session"  # request.title
        assert result == mock_session

    @pytest.mark.asyncio
    async def test_list_sessions_endpoint_delegates_to_service(self):
        """Test that list_sessions endpoint delegates to ChatService."""
        from tripsage.api.routers.chat import list_sessions

        # Create mocks
        mock_principal = MagicMock(spec=Principal)
        mock_principal.id = str(uuid4())
        mock_chat_service = AsyncMock(spec=ChatService)
        
        # Mock service response
        mock_sessions = [
            {"id": str(uuid4()), "title": "Session 1"},
            {"id": str(uuid4()), "title": "Session 2"},
        ]
        mock_chat_service.list_sessions.return_value = mock_sessions

        # Call endpoint
        with patch("tripsage.api.routers.chat.get_principal_id") as mock_get_id:
            mock_get_id.return_value = mock_principal.id
            
            result = await list_sessions(
                principal=mock_principal,
                chat_service=mock_chat_service,
            )

        # Verify service was called correctly
        mock_chat_service.list_sessions.assert_called_once_with(mock_principal.id)
        assert result == mock_sessions

    @pytest.mark.asyncio
    async def test_get_session_endpoint_delegates_to_service(self):
        """Test that get_session endpoint delegates to ChatService."""
        from tripsage.api.routers.chat import get_session

        # Create mocks
        mock_principal = MagicMock(spec=Principal)
        mock_principal.id = str(uuid4())
        mock_chat_service = AsyncMock(spec=ChatService)
        session_id = uuid4()
        
        # Mock service response
        mock_session = {"id": str(session_id), "title": "Test Session"}
        mock_chat_service.get_session.return_value = mock_session

        # Call endpoint
        with patch("tripsage.api.routers.chat.get_principal_id") as mock_get_id:
            mock_get_id.return_value = mock_principal.id
            
            result = await get_session(
                session_id=session_id,
                principal=mock_principal,
                chat_service=mock_chat_service,
            )

        # Verify service was called correctly
        mock_chat_service.get_session.assert_called_once_with(
            mock_principal.id, session_id
        )
        assert result == mock_session

    @pytest.mark.asyncio
    async def test_get_session_handles_not_found(self):
        """Test that get_session handles not found cases."""
        from tripsage.api.routers.chat import get_session

        # Create mocks
        mock_principal = MagicMock(spec=Principal)
        mock_principal.id = str(uuid4())
        mock_chat_service = AsyncMock(spec=ChatService)
        session_id = uuid4()
        
        # Mock service to return None (not found)
        mock_chat_service.get_session.return_value = None

        # Call endpoint and expect HTTPException
        with patch("tripsage.api.routers.chat.get_principal_id") as mock_get_id:
            mock_get_id.return_value = mock_principal.id
            
            with pytest.raises(HTTPException) as exc_info:
                await get_session(
                    session_id=session_id,
                    principal=mock_principal,
                    chat_service=mock_chat_service,
                )

        assert exc_info.value.status_code == 404
        assert "Session not found" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_delete_session_endpoint_delegates_to_service(self):
        """Test that delete_session endpoint delegates to ChatService."""
        from tripsage.api.routers.chat import delete_session

        # Create mocks
        mock_principal = MagicMock(spec=Principal)
        mock_principal.id = str(uuid4())
        mock_chat_service = AsyncMock(spec=ChatService)
        session_id = uuid4()
        
        # Mock service response
        mock_chat_service.delete_session.return_value = True

        # Call endpoint
        with patch("tripsage.api.routers.chat.get_principal_id") as mock_get_id:
            mock_get_id.return_value = mock_principal.id
            
            result = await delete_session(
                session_id=session_id,
                principal=mock_principal,
                chat_service=mock_chat_service,
            )

        # Verify service was called correctly
        mock_chat_service.delete_session.assert_called_once_with(
            mock_principal.id, session_id
        )
        assert result == {"message": "Session deleted successfully"}

    @pytest.mark.asyncio
    async def test_delete_session_handles_not_found(self):
        """Test that delete_session handles not found cases."""
        from tripsage.api.routers.chat import delete_session

        # Create mocks
        mock_principal = MagicMock(spec=Principal)
        mock_principal.id = str(uuid4())
        mock_chat_service = AsyncMock(spec=ChatService)
        session_id = uuid4()
        
        # Mock service to return False (not found)
        mock_chat_service.delete_session.return_value = False

        # Call endpoint and expect HTTPException
        with patch("tripsage.api.routers.chat.get_principal_id") as mock_get_id:
            mock_get_id.return_value = mock_principal.id
            
            with pytest.raises(HTTPException) as exc_info:
                await delete_session(
                    session_id=session_id,
                    principal=mock_principal,
                    chat_service=mock_chat_service,
                )

        assert exc_info.value.status_code == 404
        assert "Session not found" in exc_info.value.detail


class TestMessageEndpoints:
    """Test message management endpoints."""

    @pytest.mark.asyncio
    async def test_get_session_messages_endpoint_delegates_to_service(self):
        """Test that get_session_messages endpoint delegates to ChatService."""
        from tripsage.api.routers.chat import get_session_messages

        # Create mocks
        mock_principal = MagicMock(spec=Principal)
        mock_principal.id = str(uuid4())
        mock_chat_service = AsyncMock(spec=ChatService)
        session_id = uuid4()
        
        # Mock service response
        mock_messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]
        mock_chat_service.get_messages.return_value = mock_messages

        # Call endpoint
        with patch("tripsage.api.routers.chat.get_principal_id") as mock_get_id:
            mock_get_id.return_value = mock_principal.id
            
            result = await get_session_messages(
                session_id=session_id,
                principal=mock_principal,
                chat_service=mock_chat_service,
                limit=50,
            )

        # Verify service was called correctly
        mock_chat_service.get_messages.assert_called_once_with(
            mock_principal.id, session_id, 50
        )
        assert result == mock_messages

    @pytest.mark.asyncio
    async def test_create_message_endpoint_delegates_to_service(self):
        """Test that create_message endpoint delegates to ChatService."""
        from tripsage.api.routers.chat import create_message

        # Create mocks
        mock_principal = MagicMock(spec=Principal)
        mock_principal.id = str(uuid4())
        mock_chat_service = AsyncMock(spec=ChatService)
        session_id = uuid4()
        
        # Mock service response
        mock_message = {
            "id": str(uuid4()),
            "role": "user",
            "content": "Hello",
            "session_id": str(session_id),
        }
        mock_chat_service.create_message.return_value = mock_message

        # Call endpoint
        with patch("tripsage.api.routers.chat.get_principal_id") as mock_get_id:
            mock_get_id.return_value = mock_principal.id
            
            result = await create_message(
                session_id=session_id,
                content="Hello",
                role="user",
                principal=mock_principal,
                chat_service=mock_chat_service,
            )

        # Verify service was called correctly
        mock_chat_service.create_message.assert_called_once()
        call_args = mock_chat_service.create_message.call_args
        assert call_args[0][0] == mock_principal.id  # user_id
        assert call_args[0][1] == session_id  # session_id
        assert call_args[0][2].content == "Hello"  # message_request.content
        assert call_args[0][2].role == "user"  # message_request.role
        assert result == mock_message


class TestChatRouterDependencyInjection:
    """Test dependency injection in chat router."""

    def test_chat_router_uses_principal_authentication(self):
        """Test that chat router uses Principal-based authentication."""
        import inspect
        from tripsage.api.routers.chat import chat

        sig = inspect.signature(chat)
        
        # Verify principal parameter exists with correct type
        assert "principal" in sig.parameters
        principal_param = sig.parameters["principal"]
        assert principal_param.annotation == Principal

    def test_chat_router_uses_unified_chat_service(self):
        """Test that chat router uses unified ChatService."""
        import inspect
        from tripsage.api.routers.chat import chat

        sig = inspect.signature(chat)
        
        # Verify chat_service parameter exists with correct type
        assert "chat_service" in sig.parameters
        chat_service_param = sig.parameters["chat_service"]
        assert chat_service_param.annotation == ChatService

        # Verify it has a Depends() default
        assert chat_service_param.default is not None
        assert str(type(chat_service_param.default)) == "<class 'fastapi.params.Depends'>"


class TestChatRouterErrorHandling:
    """Test error handling in chat router."""

    @pytest.mark.asyncio
    async def test_chat_router_handles_authentication_errors(self):
        """Test that router handles authentication errors properly."""
        from tripsage.api.routers.chat import chat

        # Create mocks
        mock_principal = MagicMock(spec=Principal)
        mock_chat_service = AsyncMock(spec=ChatService)
        
        # Mock get_principal_id to raise an error
        request = ChatRequest(messages=[{"role": "user", "content": "Hello"}])

        with patch("tripsage.api.routers.chat.get_principal_id") as mock_get_id:
            mock_get_id.side_effect = Exception("Authentication failed")
            
            with pytest.raises(HTTPException) as exc_info:
                await chat(
                    request=request,
                    principal=mock_principal,
                    chat_service=mock_chat_service,
                )

        assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_session_endpoints_handle_errors_consistently(self):
        """Test that all session endpoints handle errors consistently."""
        from tripsage.api.routers.chat import create_session, list_sessions

        mock_principal = MagicMock(spec=Principal)
        mock_chat_service = AsyncMock(spec=ChatService)
        
        # Test create_session error handling
        mock_chat_service.create_session.side_effect = Exception("Service error")
        
        with patch("tripsage.api.routers.chat.get_principal_id") as mock_get_id:
            mock_get_id.return_value = "user123"
            
            with pytest.raises(HTTPException) as exc_info:
                await create_session(
                    title="Test",
                    principal=mock_principal,
                    chat_service=mock_chat_service,
                )
            assert exc_info.value.status_code == 500

        # Test list_sessions error handling
        mock_chat_service.list_sessions.side_effect = Exception("Service error")
        
        with patch("tripsage.api.routers.chat.get_principal_id") as mock_get_id:
            mock_get_id.return_value = "user123"
            
            with pytest.raises(HTTPException) as exc_info:
                await list_sessions(
                    principal=mock_principal,
                    chat_service=mock_chat_service,
                )
            assert exc_info.value.status_code == 500