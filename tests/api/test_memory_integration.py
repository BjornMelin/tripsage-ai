"""
Integration tests for memory system API endpoints.

Tests the complete integration between frontend and backend memory systems,
including request/response format validation, authentication, and error handling.
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from tripsage.api.main import app
from tripsage.services.memory_service import TripSageMemoryService
from tripsage.tools.memory_tools import ConversationMessage


class TestMemoryAPIIntegration:
    """Test memory API integration and contract compliance."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    def mock_memory_service(self):
        """Mock memory service for testing."""
        service = AsyncMock(spec=TripSageMemoryService)
        service.health_check = AsyncMock(return_value=True)
        service.add_conversation_memory = AsyncMock(
            return_value={
                "results": ["memory_1", "memory_2"],
                "usage": {"total_tokens": 150},
                "processing_time": 0.5,
            }
        )
        service.search_memories = AsyncMock(return_value=[])
        service.get_user_context = AsyncMock(
            return_value={
                "preferences": {"budget_range": "medium"},
                "past_trips": [],
                "insights": {"travel_style": "adventure"},
            }
        )
        service.update_user_preferences = AsyncMock(
            return_value={
                "updated_preferences": {"budget_range": "high"},
                "status": "success",
            }
        )
        service.delete_user_memories = AsyncMock(
            return_value={"deleted_count": 5, "success": True}
        )
        return service

    @pytest.fixture
    def valid_conversation_request(self):
        """Valid conversation memory request payload."""
        return {
            "messages": [
                {"role": "user", "content": "I want to visit Japan"},
                {"role": "assistant", "content": "Japan is a great destination!"},
            ],
            "user_id": "test_user_123",
            "session_id": "session_456",
            "context_type": "travel_planning",
        }

    @pytest.fixture
    def valid_search_request(self):
        """Valid memory search request payload."""
        return {
            "query": "Japan travel preferences",
            "user_id": "test_user_123",
            "limit": 10,
        }

    @pytest.fixture
    def valid_preferences_request(self):
        """Valid preferences update request payload."""
        return {
            "preferences": {
                "budget_range": "high",
                "travel_style": "luxury",
                "destinations": ["Japan", "France"],
            },
            "user_id": "test_user_123",
        }

    @patch("tripsage.api.routers.memory.get_memory_service")
    def test_add_conversation_memory_success(
        self, mock_get_service, client, mock_memory_service, valid_conversation_request
    ):
        """Test successful conversation memory addition."""
        mock_get_service.return_value = mock_memory_service

        response = client.post(
            "/api/memory/conversations", json=valid_conversation_request
        )

        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "usage" in data

        # Verify memory service was called correctly
        mock_memory_service.add_conversation_memory.assert_called_once()
        call_args = mock_memory_service.add_conversation_memory.call_args
        assert call_args[1]["user_id"] == "test_user_123"
        assert call_args[1]["session_id"] == "session_456"
        assert len(call_args[1]["messages"]) == 2

    @patch("tripsage.api.routers.memory.get_memory_service")
    def test_add_conversation_memory_validation_error(
        self, mock_get_service, client, mock_memory_service
    ):
        """Test conversation memory addition with invalid data."""
        mock_get_service.return_value = mock_memory_service

        # Missing required fields
        invalid_request = {
            "messages": [],  # Empty messages
            "user_id": "",  # Empty user_id
        }

        response = client.post("/api/memory/conversations", json=invalid_request)
        assert response.status_code == 422  # Validation error

    @patch("tripsage.api.routers.memory.get_memory_service")
    def test_add_conversation_memory_service_error(
        self, mock_get_service, client, mock_memory_service, valid_conversation_request
    ):
        """Test conversation memory addition with service error."""
        mock_get_service.return_value = mock_memory_service
        mock_memory_service.add_conversation_memory.side_effect = Exception(
            "Service error"
        )

        response = client.post(
            "/api/memory/conversations", json=valid_conversation_request
        )
        assert response.status_code == 500
        data = response.json()
        assert "Failed to add conversation memory" in data["detail"]

    @patch("tripsage.api.routers.memory.get_memory_service")
    def test_get_user_context_success(
        self, mock_get_service, client, mock_memory_service
    ):
        """Test successful user context retrieval."""
        mock_get_service.return_value = mock_memory_service

        response = client.get("/api/memory/context/test_user_123")

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == "test_user_123"
        assert "context" in data
        assert "preferences" in data
        assert data["status"] == "success"

        mock_memory_service.get_user_context.assert_called_once_with("test_user_123")

    @patch("tripsage.api.routers.memory.get_memory_service")
    def test_get_user_context_not_found(
        self, mock_get_service, client, mock_memory_service
    ):
        """Test user context retrieval for non-existent user."""
        mock_get_service.return_value = mock_memory_service
        mock_memory_service.get_user_context.return_value = {
            "status": "error",
            "message": "User context not found",
        }

        response = client.get("/api/memory/context/nonexistent_user")
        assert response.status_code == 404

    @patch("tripsage.api.routers.memory.get_memory_service")
    def test_search_memories_success(
        self, mock_get_service, client, mock_memory_service, valid_search_request
    ):
        """Test successful memory search."""
        mock_get_service.return_value = mock_memory_service
        mock_memory_service.search_memories.return_value = [
            {
                "id": "mem_1",
                "memory": "User likes Japan",
                "similarity": 0.9,
                "metadata": {"category": "preferences"},
            }
        ]

        response = client.post("/api/memory/search", json=valid_search_request)

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == "test_user_123"
        assert len(data["results"]) == 1
        assert data["total_count"] == 1
        assert data["status"] == "success"

    @patch("tripsage.api.routers.memory.get_memory_service")
    def test_search_memories_no_results(
        self, mock_get_service, client, mock_memory_service, valid_search_request
    ):
        """Test memory search with no results."""
        mock_get_service.return_value = mock_memory_service
        mock_memory_service.search_memories.return_value = []

        response = client.post("/api/memory/search", json=valid_search_request)

        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 0
        assert data["results"] == []

    @patch("tripsage.api.routers.memory.get_memory_service")
    def test_update_preferences_success(
        self, mock_get_service, client, mock_memory_service, valid_preferences_request
    ):
        """Test successful preferences update."""
        mock_get_service.return_value = mock_memory_service

        response = client.put(
            "/api/memory/preferences/test_user_123", json=valid_preferences_request
        )

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == "test_user_123"
        assert "updated_preferences" in data
        assert data["status"] == "success"

    @patch("tripsage.api.routers.memory.get_memory_service")
    def test_delete_user_memories_success(
        self, mock_get_service, client, mock_memory_service
    ):
        """Test successful user memory deletion."""
        mock_get_service.return_value = mock_memory_service

        response = client.delete("/api/memory/user/test_user_123")

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == "test_user_123"
        assert data["status"] == "success"
        assert data["deleted_count"] == 5

        mock_memory_service.delete_user_memories.assert_called_once_with(
            "test_user_123"
        )

    @patch("tripsage.api.routers.memory.get_memory_service")
    def test_memory_health_check_healthy(
        self, mock_get_service, client, mock_memory_service
    ):
        """Test memory health check when service is healthy."""
        mock_get_service.return_value = mock_memory_service

        response = client.get("/api/memory/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service_available"]

    @patch("tripsage.api.routers.memory.get_memory_service")
    def test_memory_health_check_unhealthy(
        self, mock_get_service, client, mock_memory_service
    ):
        """Test memory health check when service is unhealthy."""
        mock_get_service.return_value = mock_memory_service
        mock_memory_service.health_check.return_value = False

        response = client.get("/api/memory/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "unhealthy"
        assert not data["service_available"]

    @patch("tripsage.api.routers.memory.get_memory_service")
    def test_memory_service_disabled(self, mock_get_service, client):
        """Test memory endpoints when service is disabled."""
        # Mock disabled service
        from tripsage.config.feature_flags import IntegrationMode

        with patch(
            "tripsage.api.routers.memory.get_memory_integration_mode",
            return_value=IntegrationMode.DISABLED,
        ):
            response = client.get("/api/memory/health")
            assert response.status_code == 503

    def test_request_response_format_compliance(self, client):
        """Test that API request/response formats match frontend expectations."""
        # This test validates the contract between frontend and backend

        # Test conversation memory request format
        frontend_request = {
            "messages": [
                {"role": "user", "content": "I want to visit Japan"},
                {"role": "assistant", "content": "Great choice!"},
            ],
            "user_id": "test_user",  # Frontend uses snake_case for API calls
            "session_id": "session_123",
            "context_type": "travel_planning",
        }

        with patch(
            "tripsage.api.routers.memory.get_memory_service"
        ) as mock_get_service:
            mock_service = AsyncMock()
            mock_service.health_check.return_value = True
            mock_get_service.return_value = mock_service

            # Should not fail validation
            response = client.post("/api/memory/conversations", json=frontend_request)
            assert response.status_code != 422  # Not a validation error

    def test_user_isolation_security(self, client):
        """Test that users can only access their own memories."""
        # This test should verify authentication and user isolation
        # For now, it's a placeholder that demonstrates the security requirement

        with patch(
            "tripsage.api.routers.memory.get_memory_service"
        ) as mock_get_service:
            mock_service = AsyncMock()
            mock_service.health_check.return_value = True
            mock_get_service.return_value = mock_service

            # TODO: Add authentication middleware test
            # TODO: Verify user can only access their own data

            # TODO: Implement proper authentication check
            # response = client.get("/api/memory/context/other_user")
            # assert response.status_code == 403  # Forbidden


class TestMemoryTypeValidation:
    """Test type validation and data transformation."""

    def test_conversation_message_validation(self):
        """Test ConversationMessage model validation."""
        # Valid message
        valid_msg = ConversationMessage(role="user", content="Hello")
        assert valid_msg.role == "user"
        assert valid_msg.content == "Hello"

        # Invalid message - missing content
        with pytest.raises(ValueError):
            ConversationMessage(role="user")

    def test_api_request_validation_edge_cases(self, client):
        """Test API request validation with edge cases."""

        # Empty messages list
        empty_messages_request = {
            "messages": [],
            "user_id": "test_user",
            "session_id": "session_123",
        }

        with patch("tripsage.api.routers.memory.get_memory_service"):
            response = client.post(
                "/api/memory/conversations", json=empty_messages_request
            )
            # Should handle empty messages gracefully
            assert response.status_code in [
                200,
                400,
            ]  # Either success or validation error

        # Very long content
        long_content_request = {
            "messages": [{"role": "user", "content": "x" * 10000}],
            "user_id": "test_user",
        }

        with patch("tripsage.api.routers.memory.get_memory_service"):
            response = client.post(
                "/api/memory/conversations", json=long_content_request
            )
            # Should handle long content appropriately
            assert response.status_code in [
                200,
                400,
                413,
            ]  # Success, validation error, or payload too large


class TestMemoryErrorHandling:
    """Test comprehensive error handling scenarios."""

    @patch("tripsage.api.routers.memory.get_memory_service")
    def test_database_connection_error(self, mock_get_service, client):
        """Test handling of database connection errors."""
        mock_service = AsyncMock()
        mock_service.health_check.side_effect = Exception("Database connection failed")
        mock_get_service.return_value = mock_service

        response = client.get("/api/memory/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "unhealthy"
        assert "error" in data

    @patch("tripsage.api.routers.memory.get_memory_service")
    def test_memory_service_timeout(self, mock_get_service, client):
        """Test handling of service timeout errors."""
        mock_service = AsyncMock()
        mock_service.search_memories.side_effect = TimeoutError("Operation timed out")
        mock_get_service.return_value = mock_service

        search_request = {"query": "test query", "user_id": "test_user", "limit": 10}

        response = client.post("/api/memory/search", json=search_request)
        assert response.status_code == 500

    @patch("tripsage.api.routers.memory.get_memory_service")
    def test_invalid_user_id_format(self, mock_get_service, client):
        """Test handling of invalid user ID formats."""
        mock_service = AsyncMock()
        mock_service.health_check.return_value = True
        mock_get_service.return_value = mock_service

        # Test with potentially malicious user ID
        response = client.get("/api/memory/context/../admin")
        # Should handle path traversal attempts
        assert response.status_code in [400, 404]  # Bad request or not found


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
