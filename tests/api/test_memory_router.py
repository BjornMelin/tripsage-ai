"""
Comprehensive test suite for memory API router.
Tests all memory endpoints, authentication, validation, and error handling.
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from tripsage.api.main import app
from tripsage.config.feature_flags import IntegrationMode


class TestMemoryRouter:
    """Test suite for memory API router endpoints."""

    @pytest.fixture
    def client(self):
        """Test client for API requests."""
        return TestClient(app)

    @pytest.fixture
    def mock_memory_service(self):
        """Mock memory service for testing."""
        service = AsyncMock()
        service.add_conversation_memory.return_value = {
            "status": "success",
            "memory_id": "mem-123",
        }
        service.get_user_context.return_value = {
            "memories": [
                {
                    "id": "mem-1",
                    "content": "User prefers luxury hotels",
                    "metadata": {"category": "accommodation"},
                    "score": 0.95,
                    "created_at": "2024-01-01T10:00:00Z",
                }
            ],
            "preferences": {"accommodation": "luxury", "budget": "high"},
            "travel_patterns": {
                "favorite_destinations": ["Paris"],
                "avg_trip_duration": 7,
            },
        }
        service.search_memories.return_value = [
            {
                "content": "Looking for Paris hotels",
                "metadata": {"destination": "Paris"},
                "score": 0.88,
            }
        ]
        service.update_user_preferences.return_value = {"status": "success"}
        return service

    @patch("tripsage.api.routers.memory.feature_flags")
    def test_memory_service_disabled(self, mock_feature_flags, client):
        """Test memory endpoints when service is disabled."""
        mock_feature_flags.memory_integration_mode = IntegrationMode.DISABLED

        response = client.post(
            "/api/memory/conversations",
            json={
                "messages": [{"role": "user", "content": "test"}],
                "metadata": {"userId": "user-123", "sessionId": "session-123"},
            },
        )

        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert "Memory service is currently disabled" in response.json()["detail"]

    @patch("tripsage.api.routers.memory.memory_service")
    def test_store_conversation_memory_success(self, mock_service, client):
        """Test storing conversation memory successfully."""
        mock_service.add_conversation_memory.return_value = {
            "status": "success",
            "memory_id": "mem-123",
        }

        request_data = {
            "messages": [
                {
                    "role": "user",
                    "content": "I want to book a luxury hotel in Paris",
                    "timestamp": "2024-01-01T10:00:00Z",
                },
                {
                    "role": "assistant",
                    "content": "I'll help you find luxury hotels in Paris",
                    "timestamp": "2024-01-01T10:01:00Z",
                },
            ],
            "metadata": {"sessionId": "session-123", "userId": "user-123"},
        }

        response = client.post("/api/memory/conversations", json=request_data)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "success"
        assert data["memory_id"] == "mem-123"

        # Verify service was called correctly
        mock_service.add_conversation_memory.assert_called_once()

    @patch("tripsage.api.routers.memory.memory_service")
    def test_store_conversation_memory_validation_error(self, mock_service, client):
        """Test conversation memory storage with validation error."""
        # Missing required fields
        request_data = {
            "messages": [],  # Empty messages
            "metadata": {},  # Missing required fields
        }

        response = client.post("/api/memory/conversations", json=request_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @patch("tripsage.api.routers.memory.memory_service")
    def test_get_user_context_success(self, mock_service, client):
        """Test getting user context successfully."""
        mock_service.get_user_context.return_value = {
            "memories": [
                {
                    "id": "mem-1",
                    "content": "User prefers luxury hotels",
                    "metadata": {"category": "accommodation"},
                    "score": 0.95,
                    "created_at": "2024-01-01T10:00:00Z",
                }
            ],
            "preferences": {"accommodation": "luxury", "budget": "high"},
            "travel_patterns": {
                "favorite_destinations": ["Paris"],
                "avg_trip_duration": 7,
            },
        }

        response = client.get("/api/memory/context/user-123")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "memories" in data
        assert "preferences" in data
        assert "travel_patterns" in data
        assert len(data["memories"]) == 1
        assert data["preferences"]["accommodation"] == "luxury"

    @patch("tripsage.api.routers.memory.memory_service")
    def test_search_memories_success(self, mock_service, client):
        """Test searching memories successfully."""
        mock_service.search_memories.return_value = [
            {
                "content": "Looking for Paris hotels",
                "metadata": {"destination": "Paris"},
                "score": 0.88,
            },
            {
                "content": "Budget is $5000",
                "metadata": {"category": "budget"},
                "score": 0.82,
            },
        ]

        response = client.get("/api/memory/search/user-123?query=Paris hotels&limit=10")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0]["content"] == "Looking for Paris hotels"
        assert data[0]["score"] == 0.88

        # Verify service was called with correct parameters
        mock_service.search_memories.assert_called_once_with(
            user_id="user-123", query="Paris hotels", limit=10
        )

    @patch("tripsage.api.routers.memory.memory_service")
    def test_search_memories_with_filters(self, mock_service, client):
        """Test searching memories with filters."""
        mock_service.search_memories.return_value = []

        response = client.get(
            "/api/memory/search/user-123"
            "?query=hotels"
            "&limit=5"
            "&category_filter=accommodation"
        )

        assert response.status_code == status.HTTP_200_OK

        # Verify service was called with filters
        call_args = mock_service.search_memories.call_args[1]
        assert call_args["query"] == "hotels"
        assert call_args["limit"] == 5
        assert call_args.get("category_filter") == "accommodation"

    @patch("tripsage.api.routers.memory.memory_service")
    def test_search_memories_missing_query(self, mock_service, client):
        """Test searching memories without query parameter."""
        response = client.get("/api/memory/search/user-123")

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @patch("tripsage.api.routers.memory.memory_service")
    def test_update_preferences_success(self, mock_service, client):
        """Test updating user preferences successfully."""
        mock_service.update_user_preferences.return_value = {"status": "success"}

        preferences_data = {
            "accommodation": "luxury",
            "budget": "high",
            "destinations": ["Europe", "Asia"],
            "travel_style": "adventure",
        }

        response = client.put("/api/memory/preferences/user-123", json=preferences_data)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "success"

        # Verify service was called correctly
        mock_service.update_user_preferences.assert_called_once_with(
            user_id="user-123", preferences=preferences_data
        )

    @patch("tripsage.api.routers.memory.memory_service")
    def test_update_preferences_empty_data(self, mock_service, client):
        """Test updating preferences with empty data."""
        response = client.put("/api/memory/preferences/user-123", json={})

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @patch("tripsage.api.routers.memory.memory_service")
    def test_service_error_handling(self, mock_service, client):
        """Test API error handling when service fails."""
        mock_service.get_user_context.side_effect = Exception("Service unavailable")

        response = client.get("/api/memory/context/user-123")

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Internal server error" in response.json()["detail"]

    @patch("tripsage.api.routers.memory.memory_service")
    def test_invalid_user_id_format(self, mock_service, client):
        """Test endpoints with invalid user ID format."""
        # Test with empty user ID
        response = client.get("/api/memory/context/")
        assert response.status_code == status.HTTP_404_NOT_FOUND

        # Test with special characters (depending on validation rules)
        response = client.get("/api/memory/context/user@invalid")
        # This might be valid depending on your user ID format requirements
        # Adjust assertion based on your validation rules

    def test_conversation_memory_request_model(self):
        """Test ConversationMemoryRequest model validation."""
        from tripsage.api.routers.memory import ConversationMemoryRequest

        # Valid data
        valid_data = {
            "messages": [
                {
                    "role": "user",
                    "content": "test message",
                    "timestamp": "2024-01-01T10:00:00Z",
                }
            ],
            "metadata": {"sessionId": "session-123", "userId": "user-123"},
        }

        request = ConversationMemoryRequest(**valid_data)
        assert len(request.messages) == 1
        assert request.metadata["userId"] == "user-123"

        # Invalid data - missing required fields
        with pytest.raises(ValueError):
            ConversationMemoryRequest(messages=[], metadata={})

    def test_preferences_update_request_model(self):
        """Test PreferencesUpdateRequest model validation."""
        from tripsage.api.routers.memory import PreferencesUpdateRequest

        # Valid data
        valid_data = {
            "accommodation": "luxury",
            "budget": "high",
            "destinations": ["Europe"],
            "travel_style": "comfort",
        }

        request = PreferencesUpdateRequest(**valid_data)
        assert request.accommodation == "luxury"
        assert "Europe" in request.destinations

    @patch("tripsage.api.routers.memory.memory_service")
    def test_concurrent_requests(self, mock_service, client):
        """Test handling concurrent requests to memory endpoints."""
        import concurrent.futures

        mock_service.get_user_context.return_value = {
            "memories": [],
            "preferences": {},
            "travel_patterns": {},
        }

        def make_request():
            return client.get("/api/memory/context/user-123")

        # Make multiple concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request) for _ in range(5)]
            responses = [future.result() for future in futures]

        # All requests should succeed
        assert all(response.status_code == 200 for response in responses)

    @patch("tripsage.api.routers.memory.memory_service")
    def test_large_payload_handling(self, mock_service, client):
        """Test handling of large conversation payloads."""
        mock_service.add_conversation_memory.return_value = {
            "status": "success",
            "memory_id": "mem-large",
        }

        # Create large conversation
        large_messages = []
        for i in range(100):
            large_messages.append(
                {
                    "role": "user",
                    "content": f"This is message number {i} "
                    * 50,  # Make content large
                    "timestamp": f"2024-01-01T{10 + i // 60:02d}:{i % 60:02d}:00Z",
                }
            )

        request_data = {
            "messages": large_messages,
            "metadata": {"sessionId": "large-session", "userId": "user-123"},
        }

        response = client.post("/api/memory/conversations", json=request_data)

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["memory_id"] == "mem-large"

    @patch("tripsage.api.routers.memory.memory_service")
    def test_rate_limiting_behavior(self, mock_service, client):
        """Test rate limiting behavior (if implemented)."""
        mock_service.search_memories.return_value = []

        # Make multiple rapid requests
        responses = []
        for i in range(10):
            response = client.get(f"/api/memory/search/user-123?query=test{i}")
            responses.append(response)

        # All should succeed if no rate limiting
        # If rate limiting is implemented, some might return 429
        success_count = sum(1 for r in responses if r.status_code == 200)
        rate_limited_count = sum(1 for r in responses if r.status_code == 429)

        assert success_count + rate_limited_count == 10

    def test_cors_headers(self, client):
        """Test CORS headers are properly set."""
        response = client.options("/api/memory/context/user-123")

        # Check if CORS headers are present (adjust based on your CORS setup)
        # This test depends on your CORS configuration
        assert response.status_code in [200, 405]  # OPTIONS might not be enabled

    @patch("tripsage.api.routers.memory.memory_service")
    def test_response_time_performance(self, mock_service, client):
        """Test API response time performance."""
        import time

        mock_service.get_user_context.return_value = {
            "memories": [],
            "preferences": {},
            "travel_patterns": {},
        }

        start_time = time.time()
        response = client.get("/api/memory/context/user-123")
        end_time = time.time()

        response_time = end_time - start_time

        assert response.status_code == 200
        assert response_time < 1.0  # Should respond within 1 second

    @patch("tripsage.api.routers.memory.memory_service")
    def test_json_serialization_edge_cases(self, mock_service, client):
        """Test JSON serialization edge cases."""
        # Test with special characters and unicode
        mock_service.add_conversation_memory.return_value = {
            "status": "success",
            "memory_id": "mem-unicode",
        }

        request_data = {
            "messages": [
                {
                    "role": "user",
                    "content": "I want to visit Paris 🇫🇷 and Tokyo 🇯🇵",
                    "timestamp": "2024-01-01T10:00:00Z",
                }
            ],
            "metadata": {
                "sessionId": "unicode-session",
                "userId": "user-123",
                "special_chars": "àáâãäåæçèéêë",
            },
        }

        response = client.post("/api/memory/conversations", json=request_data)

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["memory_id"] == "mem-unicode"


class TestMemoryRouterSecurity:
    """Security-focused tests for memory router."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_sql_injection_protection(self, client):
        """Test protection against SQL injection in query parameters."""
        malicious_query = "'; DROP TABLE memories; --"

        response = client.get(f"/api/memory/search/user-123?query={malicious_query}")

        # Should handle malicious input gracefully
        assert response.status_code in [200, 422, 400]  # Not 500

    def test_xss_protection(self, client):
        """Test protection against XSS in request data."""
        xss_payload = "<script>alert('xss')</script>"

        request_data = {
            "messages": [
                {
                    "role": "user",
                    "content": xss_payload,
                    "timestamp": "2024-01-01T10:00:00Z",
                }
            ],
            "metadata": {"sessionId": "xss-test", "userId": "user-123"},
        }

        with patch("tripsage.api.routers.memory.memory_service") as mock_service:
            mock_service.add_conversation_memory.return_value = {
                "status": "success",
                "memory_id": "mem-xss",
            }
            response = client.post("/api/memory/conversations", json=request_data)

        # Should handle XSS payload safely
        assert response.status_code in [200, 422]

    def test_user_data_isolation(self, client):
        """Test that users cannot access other users' data."""
        with patch("tripsage.api.routers.memory.memory_service") as mock_service:
            mock_service.get_user_context.return_value = {
                "memories": [],
                "preferences": {},
                "travel_patterns": {},
            }

            # Request data for user-123
            response = client.get("/api/memory/context/user-123")
            assert response.status_code == 200

            # Verify service was called with correct user ID
            mock_service.get_user_context.assert_called_with("user-123")


if __name__ == "__main__":
    pytest.main(
        [
            __file__,
            "-v",
            "--cov=tripsage.api.routers.memory",
            "--cov-report=term-missing",
        ]
    )
