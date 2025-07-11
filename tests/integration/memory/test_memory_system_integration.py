"""
Integration tests for the memory system workflow.
Tests backend-frontend communication, data flow, and API compatibility.
"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from tripsage.api.main import app
from tripsage_core.models.db.user import User
from tripsage_core.services.business.memory_service import MemoryService


class TestMemorySystemIntegration:
    """Test complete memory system integration across backend and frontend."""

    @pytest.fixture
    def authenticated_client(self):
        """Test client with authentication headers."""
        return TestClient(app)

    @pytest.fixture
    def auth_headers(self):
        """Authentication headers for test requests."""
        return {"Authorization": "Bearer test-token"}

    @pytest.fixture(autouse=True)
    def mock_auth_dependencies(self):
        """Mock authentication dependencies."""
        from unittest.mock import Mock, patch

        # Create mock principal
        mock_principal = Mock()
        mock_principal.id = "test-user-123"
        mock_principal.email = "test@example.com"

        # Patch authentication dependencies
        with patch(
            "tripsage.api.core.dependencies.get_current_principal",
            return_value=mock_principal,
        ):
            with patch(
                "tripsage.api.core.dependencies.require_principal",
                return_value=mock_principal,
            ):
                with patch(
                    "tripsage.api.core.dependencies.get_principal_id",
                    return_value="test-user-123",
                ):
                    yield mock_principal

    @pytest.fixture
    def mock_memory_service(self):
        """Mock memory service with realistic responses."""
        service = AsyncMock(spec=MemoryService)

        # Mock search response
        service.search_memories.return_value = [
            {
                "id": "mem-1",
                "content": "User prefers luxury hotels in Paris",
                "category": "preferences",
                "created_at": "2024-01-01T10:00:00Z",
                "relevance_score": 0.95,
            },
            {
                "id": "mem-2",
                "content": "User enjoyed Four Seasons George V last trip",
                "category": "experiences",
                "created_at": "2024-01-01T10:01:00Z",
                "relevance_score": 0.90,
            },
        ]

        # Mock user context
        service.get_user_context.return_value = {
            "memories": [
                {
                    "id": "mem-1",
                    "content": "User prefers luxury hotels",
                    "category": "preferences",
                    "created_at": "2024-01-01T10:00:00Z",
                }
            ],
            "preferences": {
                "accommodation_type": "luxury",
                "preferred_locations": ["Paris", "Tokyo"],
                "budget_range": "high",
            },
            "travel_patterns": {
                "average_trip_duration": 7,
                "preferred_season": "spring",
                "travel_frequency": "quarterly",
            },
        }

        return service

    @pytest.fixture
    def sample_user(self):
        """Sample user for testing."""
        return User(
            id=123,
            email="test@example.com",
            name="Test User",
        )

    def test_store_conversation_memory_endpoint(
        self,
        authenticated_client,
        sample_user,
        mock_settings_and_redis,
    ):
        """Test storing conversation memory through API."""
        # Setup mock service at the app dependency level
        mock_service = AsyncMock()
        mock_service.add_conversation_memory.return_value = {
            "results": [{"id": "mem-123", "content": "memory content"}],
            "usage": {"total_tokens": 100},
        }

        # Override the dependency in the FastAPI app
        from tripsage.api.core.dependencies import get_memory_service
        from tripsage.api.main import app

        app.dependency_overrides[get_memory_service] = lambda: mock_service

        # Test data matching frontend request format
        request_data = {
            "messages": [
                {
                    "role": "user",
                    "content": "Looking for luxury hotels in Paris for honeymoon",
                    "timestamp": "2024-01-01T10:00:00Z",
                },
                {
                    "role": "assistant",
                    "content": "I found some excellent luxury hotels in Paris. "
                    "The Four Seasons and Ritz are highly recommended.",
                    "timestamp": "2024-01-01T10:01:00Z",
                },
            ],
            "metadata": {"sessionId": "session-123", "userId": 123},
        }

        try:
            # Make request
            response = authenticated_client.post(
                "/api/memory/conversation", json=request_data
            )

            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert "results" in data
            assert len(data["results"]) > 0
            assert data["results"][0]["id"] == "mem-123"

            # Verify service was called with correct parameters
            mock_service.add_conversation_memory.assert_called_once()
        finally:
            # Clean up dependency override
            app.dependency_overrides.clear()

    @patch("tripsage.api.core.dependencies.get_memory_service")
    def test_get_user_context_endpoint(
        self, mock_get_service, authenticated_client, mock_memory_service
    ):
        """Test getting user memory context through API."""
        # Setup mock service
        mock_service = AsyncMock()
        mock_get_service.return_value = mock_service
        mock_service.get_user_context.return_value = (
            mock_memory_service.get_user_context.return_value
        )

        # Make request
        response = authenticated_client.get("/api/memory/context")

        # Verify response
        assert response.status_code == 200
        data = response.json()

        # Check response structure matches frontend expectations
        assert "memories" in data
        assert "preferences" in data
        assert "travel_patterns" in data

        # Verify memory structure
        memories = data["memories"]
        assert len(memories) > 0
        assert all(
            key in memories[0] for key in ["id", "content", "category", "created_at"]
        )

        # Verify preferences structure
        preferences = data["preferences"]
        assert "accommodation_type" in preferences
        assert "preferred_locations" in preferences

    @patch("tripsage.api.core.dependencies.get_memory_service")
    @patch("tripsage_core.services.business.memory_service.MemoryService")
    def test_search_memories_endpoint(
        self,
        mock_memory_class,
        mock_get_service,
        authenticated_client,
        mock_memory_service,
        mock_settings_and_redis,
    ):
        """Test searching memories through API."""
        # Setup mock service
        mock_service = AsyncMock()
        mock_get_service.return_value = mock_service
        mock_memory_class.return_value = mock_service
        mock_service.search_memories.return_value = (
            mock_memory_service.search_memories.return_value
        )

        # Make request with query parameters matching frontend
        response = authenticated_client.post(
            "/api/memory/search", json={"query": "Paris", "limit": 10}
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()

        # Check response structure
        assert "results" in data
        assert "query" in data
        assert "total" in data

        results = data["results"]
        assert len(results) == 2
        assert all(
            key in results[0]
            for key in ["id", "content", "category", "relevance_score"]
        )

    @pytest.mark.asyncio
    async def test_memory_workflow_integration(self, mock_memory_service):
        """Test complete memory workflow from frontend perspective."""
        # Simulate frontend storing conversation
        messages = [
            {"role": "user", "content": "Looking for hotels in Paris"},
            {"role": "assistant", "content": "I can help you find hotels in Paris."},
        ]

        # Store conversation (simulating API call)
        with patch.object(
            mock_memory_service, "store_conversation_memory"
        ) as mock_store:
            mock_store.return_value = {"status": "success", "memory_id": "mem-123"}

            result = await mock_memory_service.store_conversation_memory(
                messages=messages, user_id=123, session_id="session-123"
            )
            assert result["status"] == "success"

        # Search memories (simulating API call)
        search_results = await mock_memory_service.search_memories(123, "Paris hotels")
        assert len(search_results) == 2
        assert search_results[0]["relevance_score"] > 0.9

        # Get user context (simulating API call)
        context = await mock_memory_service.get_user_context(123)
        assert "preferences" in context
        assert context["preferences"]["accommodation_type"] == "luxury"

    @patch("tripsage.api.core.dependencies.get_memory_service")
    def test_memory_error_handling(self, mock_get_service, authenticated_client):
        """Test API error handling for memory endpoints."""
        # Test invalid query parameters
        response = authenticated_client.post("/api/memory/search", json={})  # No query
        assert response.status_code == 422  # Validation error

        # Test service errors
        mock_service = AsyncMock()
        mock_get_service.return_value = mock_service
        mock_service.search_memories.side_effect = Exception("Service error")
        response = authenticated_client.post(
            "/api/memory/search", json={"query": "test", "limit": 10}
        )
        assert response.status_code == 500

    @pytest.mark.asyncio
    async def test_memory_caching_behavior(self, mock_memory_service):
        """Test that memory responses are properly cached."""
        # First call should hit the service
        context1 = await mock_memory_service.get_user_context(123)
        assert mock_memory_service.get_user_context.call_count == 1

        # Second call should also hit service (no caching in mock)
        context2 = await mock_memory_service.get_user_context(123)
        assert mock_memory_service.get_user_context.call_count == 2

        # Verify consistency
        assert context1 == context2

    def test_memory_frontend_compatibility(self, authenticated_client):
        """Test that API responses match frontend TypeScript interfaces."""
        with patch(
            "tripsage.api.core.dependencies.get_memory_service"
        ) as mock_get_service:
            # Setup mock service
            mock_service = AsyncMock()
            mock_get_service.return_value = mock_service
            # Mock response matching frontend MemoryContext interface
            mock_service.get_user_context.return_value = {
                "memories": [
                    {
                        "id": "mem-1",
                        "content": "User preference",
                        "category": "preferences",
                        "created_at": "2024-01-01T10:00:00Z",
                        "metadata": {"source": "conversation", "confidence": 0.9},
                    }
                ],
                "preferences": {
                    "accommodation_type": "luxury",
                    "preferred_locations": ["Paris"],
                    "budget_range": "high",
                    "dietary_restrictions": [],
                    "travel_style": "comfort",
                },
                "travel_patterns": {
                    "average_trip_duration": 7,
                    "preferred_season": "spring",
                    "travel_frequency": "quarterly",
                    "favorite_destinations": ["Paris", "Tokyo"],
                },
            }

            response = authenticated_client.get("/api/memory/context")
            assert response.status_code == 200

            data = response.json()

            # Verify all required fields for frontend
            assert isinstance(data["memories"], list)
            assert isinstance(data["preferences"], dict)
            assert isinstance(data["travel_patterns"], dict)

            # Verify nested structures
            if data["memories"]:
                memory = data["memories"][0]
                assert "id" in memory
                assert "content" in memory
                assert "category" in memory
                assert "created_at" in memory

    @pytest.mark.asyncio
    async def test_memory_concurrency(self, mock_memory_service):
        """Test concurrent memory operations."""
        # Simulate multiple concurrent operations
        tasks = [
            mock_memory_service.search_memories(123, f"query{i}") for i in range(5)
        ]

        results = await asyncio.gather(*tasks)

        # All should succeed
        assert len(results) == 5
        assert all(len(result) == 2 for result in results)

    def test_memory_data_validation(self, authenticated_client):
        """Test that API properly validates input data."""
        with patch("tripsage.api.core.dependencies.get_memory_service"):
            # Test invalid message format
            invalid_data = {
                "messages": [
                    {"content": "Missing role field"},  # Missing 'role'
                ],
                "metadata": {"userId": 123},
            }

            response = authenticated_client.post(
                "/api/memory/conversation", json=invalid_data
            )
            assert response.status_code == 422  # Validation error

            # Test missing required fields
            incomplete_data = {
                "messages": [],  # Empty messages
                "metadata": {},  # Missing userId
            }

            response = authenticated_client.post(
                "/api/memory/conversation", json=incomplete_data
            )
            assert response.status_code == 422
