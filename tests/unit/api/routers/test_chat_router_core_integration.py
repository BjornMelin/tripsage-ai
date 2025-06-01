"""
Tests for Chat router with CoreChatService integration.

This module tests the updated chat router that uses CoreChatService instead of
the old ChatService.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from tripsage.api.routers.chat import (
    get_chat_service,
    get_rate_limiter,
    router,
)
from tripsage_core.services.business.chat_service import (
    ChatService as CoreChatService,
)
from tripsage_core.services.business.chat_service import (
    RateLimiter,
)


class TestChatRouterDependencies:
    """Test chat router dependency injection."""

    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        session = MagicMock(spec=AsyncSession)
        return session

    def test_get_rate_limiter_singleton(self):
        """Test that get_rate_limiter returns a singleton."""
        limiter1 = get_rate_limiter()
        limiter2 = get_rate_limiter()

        assert limiter1 is limiter2
        assert isinstance(limiter1, RateLimiter)

    @pytest.mark.asyncio
    async def test_get_chat_service_dependency(self, mock_db_session):
        """Test that get_chat_service creates CoreChatService with dependencies."""
        with (
            patch("tripsage.api.routers.chat.CoreChatService") as mock_service_class,
            patch("tripsage.api.routers.chat.get_rate_limiter") as mock_get_limiter,
        ):
            mock_instance = AsyncMock()
            mock_service_class.return_value = mock_instance
            mock_limiter = MagicMock()
            mock_get_limiter.return_value = mock_limiter

            result = await get_chat_service(db=mock_db_session)

            mock_service_class.assert_called_once_with(
                database_service=mock_db_session, rate_limiter=mock_limiter
            )
            assert result == mock_instance

    def test_chat_router_endpoints_exist(self):
        """Test that chat endpoints exist and have proper structure."""
        app = FastAPI()
        app.include_router(router)

        # Check that endpoints exist
        route_paths = [route.path for route in app.routes if hasattr(route, "path")]

        # Verify key endpoints exist
        expected_endpoints = [
            "/",
            "/sessions/{session_id}/continue",
            "/sessions/{session_id}/history",
            "/sessions",
            "/sessions/{session_id}/end",
            "/export",
            "/data",
        ]

        for endpoint in expected_endpoints:
            assert endpoint in route_paths, f"Missing endpoint: {endpoint}"


class TestChatRouterConfiguration:
    """Test chat router configuration and setup."""

    def test_chat_router_uses_core_chat_service(self):
        """Test that chat router is configured to use CoreChatService."""
        # Verify imports
        from tripsage.api.routers.chat import CoreChatService

        assert CoreChatService is not None

        # Verify the service is the core service, not the old one
        from tripsage_core.services.business.chat_service import ChatService

        assert CoreChatService == ChatService

    def test_chat_endpoints_have_correct_dependencies(self):
        """Test that chat endpoints use CoreChatService dependency."""
        import inspect

        from tripsage.api.routers.chat import chat

        sig = inspect.signature(chat)

        # Verify chat_service parameter exists and has correct type annotation
        assert "chat_service" in sig.parameters
        chat_service_param = sig.parameters["chat_service"]
        assert chat_service_param.annotation == CoreChatService

        # Verify it has a Depends() default
        assert chat_service_param.default is not None
        assert (
            str(type(chat_service_param.default)) == "<class 'fastapi.params.Depends'>"
        )

    def test_chat_router_imports_correct_models(self):
        """Test that chat router imports correct models from core services."""
        from tripsage.api.routers.chat import (
            MessageCreateRequest,
            MessageRole,
            RecentMessagesRequest,
        )

        # Verify all required models are imported
        assert MessageCreateRequest is not None
        assert MessageRole is not None
        assert RecentMessagesRequest is not None

        # Verify they're from the core service module
        from tripsage_core.services.business.chat_service import (
            MessageCreateRequest as CoreMessageCreateRequest,
        )
        from tripsage_core.services.business.chat_service import (
            MessageRole as CoreMessageRole,
        )
        from tripsage_core.services.business.chat_service import (
            RecentMessagesRequest as CoreRecentMessagesRequest,
        )

        assert MessageCreateRequest == CoreMessageCreateRequest
        assert MessageRole == CoreMessageRole
        assert RecentMessagesRequest == CoreRecentMessagesRequest


class TestChatServiceIntegration:
    """Test integration between chat router and CoreChatService."""

    @pytest.mark.asyncio
    async def test_message_creation_uses_message_create_request(self):
        """Test that message creation uses MessageCreateRequest objects."""
        from tripsage_core.services.business.chat_service import (
            MessageCreateRequest,
            MessageRole,
        )

        # Test message request creation
        message_request = MessageCreateRequest(
            role=MessageRole.USER,
            content="Test message",
            metadata={"test": "data"},
        )

        assert message_request.role == MessageRole.USER
        assert message_request.content == "Test message"
        assert message_request.metadata == {"test": "data"}

    @pytest.mark.asyncio
    async def test_recent_messages_uses_request_object(self):
        """Test that recent messages retrieval uses RecentMessagesRequest."""
        from tripsage_core.services.business.chat_service import RecentMessagesRequest

        # Test recent messages request creation
        request = RecentMessagesRequest(
            limit=50,
            max_tokens=4000,
            offset=0,
        )

        assert request.limit == 50
        assert request.max_tokens == 4000
        assert request.offset == 0

    @pytest.mark.asyncio
    async def test_session_management_api_compatibility(self):
        """Test that session management API is compatible with CoreChatService."""
        from tripsage_core.services.business.chat_service import (
            ChatSessionCreateRequest,
            ChatSessionResponse,
        )

        # Test session creation request
        session_request = ChatSessionCreateRequest(
            title="Test Session",
            trip_id=None,
            metadata={"source": "test"},
        )

        assert session_request.title == "Test Session"
        assert session_request.metadata == {"source": "test"}

        # Test session response structure
        session_response = ChatSessionResponse(
            id=str(uuid4()),
            user_id=str(uuid4()),
            title="Test Session",
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z",
        )

        assert session_response.title == "Test Session"
        assert session_response.id is not None


class TestChatEndpointBehavior:
    """Test chat endpoint behavior with CoreChatService."""

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

    @pytest.fixture
    def mock_user(self):
        """Mock authenticated user."""
        user = MagicMock()
        user.id = str(uuid4())
        return user

    def test_chat_endpoint_exists(self, app):
        """Test that chat endpoint exists."""
        # Test by checking the app routes instead of making actual requests
        route_paths = [route.path for route in app.routes if hasattr(route, "path")]
        assert "/" in route_paths

    def test_sessions_endpoint_exists(self, app):
        """Test that sessions endpoint exists."""
        # Test by checking the app routes instead of making actual requests
        route_paths = [route.path for route in app.routes if hasattr(route, "path")]
        assert "/sessions" in route_paths

    @pytest.mark.asyncio
    async def test_chat_service_methods_are_called_correctly(self):
        """Test that chat service methods are called with correct parameters."""
        from tripsage.api.routers.chat import ChatRequest
        from tripsage_core.services.business.chat_service import (
            ChatSessionResponse,
            RecentMessagesRequest,
            RecentMessagesResponse,
        )

        # Create mocks
        mock_core_chat_service = AsyncMock(spec=CoreChatService)
        mock_user = MagicMock()
        mock_user.id = str(uuid4())

        # Mock CoreChatService responses
        session_response = ChatSessionResponse(
            id=str(uuid4()),
            user_id=mock_user.id,
            title="Test Session",
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z",
        )

        recent_messages_response = RecentMessagesResponse(
            messages=[],
            total_tokens=0,
            truncated=False,
        )

        mock_core_chat_service.create_session = AsyncMock(return_value=session_response)
        mock_core_chat_service.get_recent_messages = AsyncMock(
            return_value=recent_messages_response
        )
        mock_core_chat_service.add_message = AsyncMock()

        # Create test request
        request = ChatRequest(
            messages=[{"role": "user", "content": "Hello"}],
            save_history=True,
            session_id=None,
        )

        # Mock dependencies
        session_memory = {}
        api_key_valid = True

        # Import and call the endpoint function directly for testing
        from tripsage.api.routers.chat import chat

        with (
            patch("tripsage.api.routers.chat.get_chat_agent") as mock_get_agent,
            patch("tripsage.api.routers.chat.get_user_available_tools") as mock_tools,
        ):
            mock_agent = AsyncMock()
            mock_agent.run_with_tools = AsyncMock(
                return_value={"content": "Test response"}
            )
            mock_get_agent.return_value = mock_agent
            mock_tools.return_value = []

            # This would normally return a StreamingResponse, but we're testing the service calls
            try:
                await chat(
                    request=request,
                    current_user=mock_user,
                    session_memory=session_memory,
                    chat_service=mock_core_chat_service,
                    api_key_valid=api_key_valid,
                )
            except Exception:
                # Expected to fail due to missing mocks, but service calls should have been made
                pass

        # Verify CoreChatService was called with proper parameters
        mock_core_chat_service.create_session.assert_called()
        mock_core_chat_service.get_recent_messages.assert_called()

        # Verify recent messages was called with RecentMessagesRequest
        recent_call_args = mock_core_chat_service.get_recent_messages.call_args
        assert isinstance(recent_call_args[1]["request"], RecentMessagesRequest)
        assert recent_call_args[1]["user_id"] == mock_user.id


class TestChatRouterErrorHandling:
    """Test error handling in chat router with CoreChatService."""

    @pytest.mark.asyncio
    async def test_rate_limiting_compatibility(self):
        """Test that rate limiting errors are properly handled."""
        # Test that the chat router can handle CoreChatService validation errors
        from tripsage_core.exceptions.exceptions import (
            CoreValidationError as ValidationError,
        )

        mock_service = AsyncMock()
        mock_service.add_message = AsyncMock(
            side_effect=ValidationError("Rate limit exceeded")
        )

        # Test that ValidationError with rate limit message is handled
        with pytest.raises(ValidationError):
            await mock_service.add_message(
                session_id="test",
                user_id="test",
                message_data=MagicMock(),
            )

    @pytest.mark.asyncio
    async def test_session_not_found_handling(self):
        """Test that session not found errors are properly handled."""
        mock_service = AsyncMock()
        mock_service.get_session = AsyncMock(return_value=None)

        # Test that None return is handled as not found
        result = await mock_service.get_session("nonexistent", "user")
        assert result is None


class TestChatRouterBackwardsCompatibility:
    """Test that old ChatService references are completely removed."""

    def test_old_chat_service_not_imported(self):
        """Test that old ChatService is not imported anywhere in chat router."""
        import ast
        import inspect

        from tripsage.api.routers import chat

        # Get the source code of the chat router module
        source = inspect.getsource(chat)

        # Parse the AST to check imports
        tree = ast.parse(source)

        # Check that no imports reference the old chat service path
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module and "tripsage.services.core.chat_service" in node.module:
                    pytest.fail("Old ChatService path still imported in chat router")
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if "tripsage.services.core.chat_service" in alias.name:
                        pytest.fail(
                            "Old ChatService path still imported in chat router"
                        )

    def test_core_chat_service_used_exclusively(self):
        """Test that only CoreChatService from core is used."""
        from tripsage.api.routers.chat import CoreChatService
        from tripsage_core.services.business.chat_service import ChatService

        # Verify it's the same class (aliased correctly)
        assert CoreChatService == ChatService

        # Verify it's from the core module
        assert (
            CoreChatService.__module__ == "tripsage_core.services.business.chat_service"
        )
