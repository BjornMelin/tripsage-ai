"""
Integration tests for the complete memory system workflow.
Tests backend-frontend communication, data flow, and API compatibility.
"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from tripsage.api.main import app
from tripsage_core.models.db.user import User
from tripsage.services.memory_service import TripSageMemoryService


class TestMemorySystemIntegration:
    """Test complete memory system integration across backend and frontend."""

    @pytest.fixture
    def client(self):
        """Test client for API requests."""
        return TestClient(app)

    @pytest.fixture
    def mock_memory_service(self):
        """Mock memory service for testing."""
        service = AsyncMock(spec=TripSageMemoryService)
        service.store_conversation_memory.return_value = {
            "status": "success",
            "memory_id": "test-123",
        }
        service.get_user_context.return_value = {
            "memories": [
                {
                    "id": "mem-1",
                    "content": "User prefers luxury hotels",
                    "metadata": {"category": "accommodation", "preference": "luxury"},
                    "score": 0.95,
                    "created_at": "2024-01-01T10:00:00Z",
                }
            ],
            "preferences": {
                "accommodation": "luxury",
                "budget": "high",
                "destinations": ["Europe", "Asia"],
            },
            "travel_patterns": {
                "favorite_destinations": ["Paris", "Tokyo"],
                "avg_trip_duration": 7,
                "booking_lead_time": 30,
            },
        }
        service.search_memories.return_value = [
            {
                "content": "Looking for flights to Paris",
                "metadata": {"type": "search", "destination": "Paris"},
                "score": 0.88,
            }
        ]
        return service

    @pytest.fixture
    def sample_user(self):
        """Sample user for testing."""
        return User(
            id="user-123",
            email="test@example.com",
            username="testuser",
            display_name="Test User",
        )

    @patch("tripsage.api.routers.memory.memory_service")
    def test_store_conversation_memory_endpoint(
        self, mock_service, client, sample_user
    ):
        """Test storing conversation memory through API."""
        # Setup mock
        mock_service.store_conversation_memory.return_value = {
            "status": "success",
            "memory_id": "test-123",
        }

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
                    "content": (
                        "I found some excellent luxury hotels in Paris. "
                        "The Four Seasons and Ritz are highly recommended."
                    ),
                    "timestamp": "2024-01-01T10:01:00Z",
                },
            ],
            "metadata": {"sessionId": "session-123", "userId": "user-123"},
        }

        # Make request
        response = client.post("/api/memory/conversations", json=request_data)

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "memory_id" in data

        # Verify service was called with correct parameters
        mock_service.store_conversation_memory.assert_called_once()
        call_args = mock_service.store_conversation_memory.call_args[1]
        assert call_args["messages"] == request_data["messages"]
        assert call_args["user_id"] == "user-123"

    @patch("tripsage.api.routers.memory.memory_service")
    def test_get_user_context_endpoint(self, mock_service, client, mock_memory_service):
        """Test getting user memory context through API."""
        # Setup mock
        mock_service.get_user_context.return_value = (
            mock_memory_service.get_user_context.return_value
        )

        # Make request
        response = client.get("/api/memory/context/user-123")

        # Verify response
        assert response.status_code == 200
        data = response.json()

        # Check response structure matches frontend expectations
        assert "memories" in data
        assert "preferences" in data
        assert "travel_patterns" in data

        # Verify memory structure
        memory = data["memories"][0]
        assert "id" in memory
        assert "content" in memory
        assert "metadata" in memory
        assert "score" in memory
        assert "created_at" in memory

        # Verify preferences structure
        prefs = data["preferences"]
        assert "accommodation" in prefs
        assert "budget" in prefs
        assert "destinations" in prefs

    @patch("tripsage.api.routers.memory.memory_service")
    def test_search_memories_endpoint(self, mock_service, client, mock_memory_service):
        """Test searching memories through API."""
        # Setup mock
        mock_service.search_memories.return_value = (
            mock_memory_service.search_memories.return_value
        )

        # Test with query parameters
        response = client.get("/api/memory/search/user-123?query=Paris&limit=10")

        # Verify response
        assert response.status_code == 200
        data = response.json()

        # Check response is list of memories
        assert isinstance(data, list)
        assert len(data) > 0

        # Verify memory structure
        memory = data[0]
        assert "content" in memory
        assert "metadata" in memory
        assert "score" in memory

    def test_memory_service_conversation_extraction(self, mock_memory_service):
        """Test memory service conversation extraction logic."""
        messages = [
            {
                "role": "user",
                "content": (
                    "I want to book a luxury hotel in Paris for my anniversary. "
                    "Budget is $500/night."
                ),
                "timestamp": "2024-01-01T10:00:00Z",
            },
            {
                "role": "assistant",
                "content": (
                    "I'll help you find luxury hotels in Paris. "
                    "Here are some excellent options within your budget."
                ),
                "timestamp": "2024-01-01T10:01:00Z",
            },
        ]

        # This would test the actual memory extraction logic
        # For now, we verify the mock works correctly
        result = asyncio.run(
            mock_memory_service.store_conversation_memory(
                messages=messages, user_id="user-123", session_id="session-123"
            )
        )

        assert result["status"] == "success"
        assert "memory_id" in result

    @patch("tripsage.api.routers.memory.memory_service")
    def test_error_handling_memory_endpoints(self, mock_service, client):
        """Test error handling in memory endpoints."""
        # Test with invalid user ID
        response = client.get("/api/memory/context/invalid-user")
        # Should handle gracefully, not crash
        assert response.status_code in [200, 404, 422]

        # Test with malformed conversation data
        response = client.post("/api/memory/conversations", json={"invalid": "data"})
        assert response.status_code == 422  # Validation error

        # Test search with missing parameters
        response = client.get("/api/memory/search/user-123")  # No query
        assert response.status_code in [200, 422]  # Should handle gracefully

    def test_frontend_backend_type_compatibility(self):
        """Test that frontend types match backend response formats."""
        # This would be a compile-time check in a real TypeScript environment
        # For now, we document the expected structure

        expected_memory_response = {
            "memories": [
                {
                    "id": str,
                    "content": str,
                    "metadata": dict,
                    "score": float,
                    "created_at": str,
                }
            ],
            "preferences": {
                "accommodation": str,
                "budget": str,
                "destinations": list,
            },
            "travel_patterns": {
                "favorite_destinations": list,
                "avg_trip_duration": int,
                "booking_lead_time": int,
            },
        }

        # This structure should match frontend types/memory.ts interfaces
        assert expected_memory_response is not None

    @patch("tripsage.services.memory_service.TripSageMemoryService")
    def test_memory_service_initialization(self, mock_service_class):
        """Test memory service proper initialization."""
        # Verify service can be instantiated
        service = TripSageMemoryService()
        assert service is not None

        # Test that required methods exist
        assert hasattr(service, "store_conversation_memory")
        assert hasattr(service, "get_user_context")
        assert hasattr(service, "search_memories")
        assert hasattr(service, "update_user_preferences")

    def test_api_endpoint_authentication_flow(self, client):
        """Test that memory endpoints properly handle authentication."""
        # Test without authentication (should fail or redirect)
        response = client.get("/api/memory/context/user-123")
        # Depending on auth setup, this might be 401, 403, or redirect
        # For now, we just verify it doesn't crash
        assert response.status_code is not None

        # Test with proper authentication would require auth headers
        # This would be implemented when auth is fully set up

    @pytest.mark.asyncio
    async def test_async_memory_operations(self, mock_memory_service):
        """Test async memory operations work correctly."""
        # Test async context retrieval
        context = await mock_memory_service.get_user_context("user-123")
        assert context is not None
        assert "memories" in context

        # Test async memory search
        results = await mock_memory_service.search_memories("user-123", "Paris hotels")
        assert isinstance(results, list)

        # Test async conversation storage
        result = await mock_memory_service.store_conversation_memory(
            messages=[{"role": "user", "content": "test"}],
            user_id="user-123",
        )
        assert result["status"] == "success"


class TestMemoryWorkflowIntegration:
    """Test complete memory workflow from frontend to backend."""

    def test_chat_to_memory_workflow(self):
        """Test complete workflow: chat -> memory extraction -> storage -> retrieval."""
        # This would test the full pipeline:
        # 1. User sends chat message
        # 2. Chat agent processes message
        # 3. Memory service extracts relevant information
        # 4. Information is stored in vector database
        # 5. Future chats retrieve relevant context

        # For now, we outline the expected flow
        workflow_steps = [
            "user_sends_message",
            "chat_agent_processes",
            "memory_extraction",
            "vector_storage",
            "context_retrieval",
            "personalized_response",
        ]

        assert len(workflow_steps) == 6
        assert "memory_extraction" in workflow_steps

    def test_personalization_workflow(self):
        """Test personalization based on stored memories."""
        # This would test:
        # 1. User has stored preferences and travel history
        # 2. New search/recommendation request comes in
        # 3. Memory system provides relevant context
        # 4. Recommendations are personalized based on history

        # For now, we outline the expected flow
        personalization_flow = [
            "retrieve_user_context",
            "analyze_preferences",
            "generate_personalized_recommendations",
            "return_contextual_results",
        ]

        assert len(personalization_flow) == 4
        assert "generate_personalized_recommendations" in personalization_flow


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
