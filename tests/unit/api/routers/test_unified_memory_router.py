"""
Tests for unified Memory router.

This module tests the updated memory router that uses the unified MemoryService
adapter for clean separation of concerns.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from fastapi import HTTPException
from fastapi.testclient import TestClient
from fastapi import FastAPI

from tripsage.api.routers.memory import router
from tripsage.api.services.memory import MemoryService
from tripsage.api.middlewares.authentication import Principal


class TestMemoryRouterEndpoints:
    """Test memory router endpoint functionality."""

    @pytest.fixture
    def app(self):
        """Create FastAPI app with memory router."""
        app = FastAPI()
        app.include_router(router)
        return app

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)

    def test_memory_router_has_expected_endpoints(self, app):
        """Test that memory router has all expected endpoints."""
        route_paths = [route.path for route in app.routes if hasattr(route, "path")]

        expected_endpoints = [
            "/memory/conversation",
            "/memory/context",
            "/memory/search",
            "/memory/preferences",
            "/memory/preference",
            "/memory/memory/{memory_id}",
            "/memory/stats",
            "/memory/clear",
        ]

        for endpoint in expected_endpoints:
            assert endpoint in route_paths, f"Missing endpoint: {endpoint}"

    def test_memory_router_endpoints_have_correct_methods(self, app):
        """Test that endpoints have correct HTTP methods."""
        routes = {route.path: route for route in app.routes if hasattr(route, "path")}

        # Verify HTTP methods for each endpoint
        assert "POST" in routes["/memory/conversation"].methods
        assert "GET" in routes["/memory/context"].methods
        assert "POST" in routes["/memory/search"].methods
        assert "PUT" in routes["/memory/preferences"].methods
        assert "POST" in routes["/memory/preference"].methods
        assert "DELETE" in routes["/memory/memory/{memory_id}"].methods
        assert "GET" in routes["/memory/stats"].methods
        assert "DELETE" in routes["/memory/clear"].methods


class TestConversationMemoryEndpoint:
    """Test conversation memory endpoint."""

    @pytest.mark.asyncio
    async def test_add_conversation_memory_delegates_to_service(self):
        """Test that add_conversation_memory endpoint delegates to MemoryService."""
        from tripsage.api.routers.memory import add_conversation_memory, ConversationMemoryRequest

        # Create mocks
        mock_principal = MagicMock(spec=Principal)
        mock_principal.id = str(uuid4())
        mock_memory_service = AsyncMock(spec=MemoryService)
        
        # Mock service response
        mock_response = {"memory_id": str(uuid4()), "success": True}
        mock_memory_service.add_conversation_memory.return_value = mock_response

        # Create request
        request = ConversationMemoryRequest(
            messages=[
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there!"},
            ],
            session_id=str(uuid4()),
        )

        # Call endpoint
        with patch("tripsage.api.routers.memory.get_principal_id") as mock_get_id:
            mock_get_id.return_value = mock_principal.id
            
            result = await add_conversation_memory(
                request=request,
                principal=mock_principal,
                memory_service=mock_memory_service,
            )

        # Verify service was called correctly
        mock_memory_service.add_conversation_memory.assert_called_once_with(
            mock_principal.id, request.messages, request.session_id
        )
        assert result == mock_response

    @pytest.mark.asyncio
    async def test_add_conversation_memory_handles_errors(self):
        """Test that add_conversation_memory handles service errors."""
        from tripsage.api.routers.memory import add_conversation_memory, ConversationMemoryRequest

        # Create mocks
        mock_principal = MagicMock(spec=Principal)
        mock_principal.id = str(uuid4())
        mock_memory_service = AsyncMock(spec=MemoryService)
        
        # Mock service to raise an error
        mock_memory_service.add_conversation_memory.side_effect = Exception("Storage failed")

        # Create request
        request = ConversationMemoryRequest(
            messages=[{"role": "user", "content": "Hello"}],
        )

        # Call endpoint and expect HTTPException
        with patch("tripsage.api.routers.memory.get_principal_id") as mock_get_id:
            mock_get_id.return_value = mock_principal.id
            
            with pytest.raises(HTTPException) as exc_info:
                await add_conversation_memory(
                    request=request,
                    principal=mock_principal,
                    memory_service=mock_memory_service,
                )

        assert exc_info.value.status_code == 500
        assert "Failed to add conversation memory" in exc_info.value.detail


class TestUserContextEndpoint:
    """Test user context endpoint."""

    @pytest.mark.asyncio
    async def test_get_user_context_delegates_to_service(self):
        """Test that get_user_context endpoint delegates to MemoryService."""
        from tripsage.api.routers.memory import get_user_context

        # Create mocks
        mock_principal = MagicMock(spec=Principal)
        mock_principal.id = str(uuid4())
        mock_memory_service = AsyncMock(spec=MemoryService)
        
        # Mock service response
        mock_context = {
            "preferences": {"travel_style": "luxury"},
            "recent_searches": ["Paris", "Tokyo"],
        }
        mock_memory_service.get_user_context.return_value = mock_context

        # Call endpoint
        with patch("tripsage.api.routers.memory.get_principal_id") as mock_get_id:
            mock_get_id.return_value = mock_principal.id
            
            result = await get_user_context(
                principal=mock_principal,
                memory_service=mock_memory_service,
            )

        # Verify service was called correctly
        mock_memory_service.get_user_context.assert_called_once_with(mock_principal.id)
        assert result == mock_context

    @pytest.mark.asyncio
    async def test_get_user_context_handles_errors(self):
        """Test that get_user_context handles service errors."""
        from tripsage.api.routers.memory import get_user_context

        # Create mocks
        mock_principal = MagicMock(spec=Principal)
        mock_memory_service = AsyncMock(spec=MemoryService)
        
        # Mock service to raise an error
        mock_memory_service.get_user_context.side_effect = Exception("Context fetch failed")

        # Call endpoint and expect HTTPException
        with patch("tripsage.api.routers.memory.get_principal_id") as mock_get_id:
            mock_get_id.return_value = "user123"
            
            with pytest.raises(HTTPException) as exc_info:
                await get_user_context(
                    principal=mock_principal,
                    memory_service=mock_memory_service,
                )

        assert exc_info.value.status_code == 500
        assert "Failed to get user context" in exc_info.value.detail


class TestSearchMemoriesEndpoint:
    """Test search memories endpoint."""

    @pytest.mark.asyncio
    async def test_search_memories_delegates_to_service(self):
        """Test that search_memories endpoint delegates to MemoryService."""
        from tripsage.api.routers.memory import search_memories, SearchMemoryRequest

        # Create mocks
        mock_principal = MagicMock(spec=Principal)
        mock_principal.id = str(uuid4())
        mock_memory_service = AsyncMock(spec=MemoryService)
        
        # Mock service response
        mock_memories = [
            {"id": str(uuid4()), "content": "Travel to Paris"},
            {"id": str(uuid4()), "content": "Book hotel in Rome"},
        ]
        mock_memory_service.search_memories.return_value = mock_memories

        # Create request
        request = SearchMemoryRequest(query="travel plans", limit=10)

        # Call endpoint
        with patch("tripsage.api.routers.memory.get_principal_id") as mock_get_id:
            mock_get_id.return_value = mock_principal.id
            
            result = await search_memories(
                request=request,
                principal=mock_principal,
                memory_service=mock_memory_service,
            )

        # Verify service was called correctly
        mock_memory_service.search_memories.assert_called_once_with(
            mock_principal.id, request.query, request.limit
        )
        assert result == {"memories": mock_memories, "count": len(mock_memories)}

    @pytest.mark.asyncio
    async def test_search_memories_handles_errors(self):
        """Test that search_memories handles service errors."""
        from tripsage.api.routers.memory import search_memories, SearchMemoryRequest

        # Create mocks
        mock_principal = MagicMock(spec=Principal)
        mock_memory_service = AsyncMock(spec=MemoryService)
        
        # Mock service to raise an error
        mock_memory_service.search_memories.side_effect = Exception("Search failed")

        # Create request
        request = SearchMemoryRequest(query="test")

        # Call endpoint and expect HTTPException
        with patch("tripsage.api.routers.memory.get_principal_id") as mock_get_id:
            mock_get_id.return_value = "user123"
            
            with pytest.raises(HTTPException) as exc_info:
                await search_memories(
                    request=request,
                    principal=mock_principal,
                    memory_service=mock_memory_service,
                )

        assert exc_info.value.status_code == 500
        assert "Failed to search memories" in exc_info.value.detail


class TestPreferencesEndpoints:
    """Test preference management endpoints."""

    @pytest.mark.asyncio
    async def test_update_preferences_delegates_to_service(self):
        """Test that update_preferences endpoint delegates to MemoryService."""
        from tripsage.api.routers.memory import update_preferences, UpdatePreferencesRequest

        # Create mocks
        mock_principal = MagicMock(spec=Principal)
        mock_principal.id = str(uuid4())
        mock_memory_service = AsyncMock(spec=MemoryService)
        
        # Mock service response
        mock_response = {"updated": True, "preferences": {"budget": "$1000"}}
        mock_memory_service.update_user_preferences.return_value = mock_response

        # Create request
        request = UpdatePreferencesRequest(preferences={"budget": "$1000"})

        # Call endpoint
        with patch("tripsage.api.routers.memory.get_principal_id") as mock_get_id:
            mock_get_id.return_value = mock_principal.id
            
            result = await update_preferences(
                request=request,
                principal=mock_principal,
                memory_service=mock_memory_service,
            )

        # Verify service was called correctly
        mock_memory_service.update_user_preferences.assert_called_once_with(
            mock_principal.id, request.preferences
        )
        assert result == mock_response

    @pytest.mark.asyncio
    async def test_add_preference_delegates_to_service(self):
        """Test that add_preference endpoint delegates to MemoryService."""
        from tripsage.api.routers.memory import add_preference

        # Create mocks
        mock_principal = MagicMock(spec=Principal)
        mock_principal.id = str(uuid4())
        mock_memory_service = AsyncMock(spec=MemoryService)
        
        # Mock service response
        mock_response = {"preference_id": str(uuid4()), "created": True}
        mock_memory_service.add_user_preference.return_value = mock_response

        # Call endpoint
        with patch("tripsage.api.routers.memory.get_principal_id") as mock_get_id:
            mock_get_id.return_value = mock_principal.id
            
            result = await add_preference(
                key="favorite_airline",
                value="Delta",
                category="travel",
                principal=mock_principal,
                memory_service=mock_memory_service,
            )

        # Verify service was called correctly
        mock_memory_service.add_user_preference.assert_called_once_with(
            mock_principal.id, "favorite_airline", "Delta", "travel"
        )
        assert result == mock_response


class TestMemoryManagementEndpoints:
    """Test memory management endpoints."""

    @pytest.mark.asyncio
    async def test_delete_memory_delegates_to_service(self):
        """Test that delete_memory endpoint delegates to MemoryService."""
        from tripsage.api.routers.memory import delete_memory

        # Create mocks
        mock_principal = MagicMock(spec=Principal)
        mock_principal.id = str(uuid4())
        mock_memory_service = AsyncMock(spec=MemoryService)
        memory_id = str(uuid4())
        
        # Mock service response
        mock_memory_service.delete_memory.return_value = True

        # Call endpoint
        with patch("tripsage.api.routers.memory.get_principal_id") as mock_get_id:
            mock_get_id.return_value = mock_principal.id
            
            result = await delete_memory(
                memory_id=memory_id,
                principal=mock_principal,
                memory_service=mock_memory_service,
            )

        # Verify service was called correctly
        mock_memory_service.delete_memory.assert_called_once_with(
            mock_principal.id, memory_id
        )
        assert result == {"message": "Memory deleted successfully"}

    @pytest.mark.asyncio
    async def test_delete_memory_handles_not_found(self):
        """Test that delete_memory handles not found cases."""
        from tripsage.api.routers.memory import delete_memory

        # Create mocks
        mock_principal = MagicMock(spec=Principal)
        mock_memory_service = AsyncMock(spec=MemoryService)
        memory_id = str(uuid4())
        
        # Mock service to return False (not found)
        mock_memory_service.delete_memory.return_value = False

        # Call endpoint and expect HTTPException
        with patch("tripsage.api.routers.memory.get_principal_id") as mock_get_id:
            mock_get_id.return_value = "user123"
            
            with pytest.raises(HTTPException) as exc_info:
                await delete_memory(
                    memory_id=memory_id,
                    principal=mock_principal,
                    memory_service=mock_memory_service,
                )

        assert exc_info.value.status_code == 404
        assert "Memory not found" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_memory_stats_delegates_to_service(self):
        """Test that get_memory_stats endpoint delegates to MemoryService."""
        from tripsage.api.routers.memory import get_memory_stats

        # Create mocks
        mock_principal = MagicMock(spec=Principal)
        mock_principal.id = str(uuid4())
        mock_memory_service = AsyncMock(spec=MemoryService)
        
        # Mock service response
        mock_stats = {
            "total_memories": 15,
            "conversation_memories": 10,
            "preference_count": 5,
        }
        mock_memory_service.get_memory_stats.return_value = mock_stats

        # Call endpoint
        with patch("tripsage.api.routers.memory.get_principal_id") as mock_get_id:
            mock_get_id.return_value = mock_principal.id
            
            result = await get_memory_stats(
                principal=mock_principal,
                memory_service=mock_memory_service,
            )

        # Verify service was called correctly
        mock_memory_service.get_memory_stats.assert_called_once_with(mock_principal.id)
        assert result == mock_stats

    @pytest.mark.asyncio
    async def test_clear_user_memory_delegates_to_service(self):
        """Test that clear_user_memory endpoint delegates to MemoryService."""
        from tripsage.api.routers.memory import clear_user_memory

        # Create mocks
        mock_principal = MagicMock(spec=Principal)
        mock_principal.id = str(uuid4())
        mock_memory_service = AsyncMock(spec=MemoryService)
        
        # Mock service response
        mock_response = {"cleared": True, "count": 15}
        mock_memory_service.clear_user_memory.return_value = mock_response

        # Call endpoint
        with patch("tripsage.api.routers.memory.get_principal_id") as mock_get_id:
            mock_get_id.return_value = mock_principal.id
            
            result = await clear_user_memory(
                confirm=True,
                principal=mock_principal,
                memory_service=mock_memory_service,
            )

        # Verify service was called correctly
        mock_memory_service.clear_user_memory.assert_called_once_with(
            mock_principal.id, True
        )
        assert result == mock_response


class TestMemoryRouterDependencyInjection:
    """Test dependency injection in memory router."""

    def test_memory_router_uses_principal_authentication(self):
        """Test that memory router uses Principal-based authentication."""
        import inspect
        from tripsage.api.routers.memory import add_conversation_memory

        sig = inspect.signature(add_conversation_memory)
        
        # Verify principal parameter exists with correct type
        assert "principal" in sig.parameters
        principal_param = sig.parameters["principal"]
        assert principal_param.annotation == Principal

    def test_memory_router_uses_unified_memory_service(self):
        """Test that memory router uses unified MemoryService."""
        import inspect
        from tripsage.api.routers.memory import add_conversation_memory

        sig = inspect.signature(add_conversation_memory)
        
        # Verify memory_service parameter exists with correct type
        assert "memory_service" in sig.parameters
        memory_service_param = sig.parameters["memory_service"]
        assert memory_service_param.annotation == MemoryService

        # Verify it has a Depends() default
        assert memory_service_param.default is not None
        assert str(type(memory_service_param.default)) == "<class 'fastapi.params.Depends'>"


class TestMemoryRouterErrorHandling:
    """Test error handling in memory router."""

    @pytest.mark.asyncio
    async def test_all_endpoints_handle_errors_consistently(self):
        """Test that all memory endpoints handle errors consistently."""
        from tripsage.api.routers.memory import (
            add_conversation_memory,
            get_user_context,
            search_memories,
            ConversationMemoryRequest,
            SearchMemoryRequest,
        )

        mock_principal = MagicMock(spec=Principal)
        mock_memory_service = AsyncMock(spec=MemoryService)
        
        # Test multiple endpoints for consistent error handling
        endpoints_to_test = [
            (
                add_conversation_memory,
                {"request": ConversationMemoryRequest(messages=[])},
                "add_conversation_memory",
            ),
            (
                get_user_context,
                {},
                "get_user_context",
            ),
            (
                search_memories,
                {"request": SearchMemoryRequest(query="test")},
                "search_memories",
            ),
        ]

        for endpoint_func, extra_kwargs, service_method in endpoints_to_test:
            # Mock service method to raise an error
            getattr(mock_memory_service, service_method).side_effect = Exception("Service error")
            
            with patch("tripsage.api.routers.memory.get_principal_id") as mock_get_id:
                mock_get_id.return_value = "user123"
                
                with pytest.raises(HTTPException) as exc_info:
                    await endpoint_func(
                        principal=mock_principal,
                        memory_service=mock_memory_service,
                        **extra_kwargs,
                    )
                
                # Verify all endpoints return 500 status code for service errors
                assert exc_info.value.status_code == 500
                assert "Failed to" in exc_info.value.detail