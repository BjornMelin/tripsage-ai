"""Comprehensive unit tests for memory router."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from tests.factories import MemoryFactory
from tripsage.api.main import app


class TestMemoryRouter:
    """Test suite for memory router endpoints."""

    def setup_method(self):
        """Set up test client and mocks."""
        self.client = TestClient(app)
        self.mock_service = Mock()
        self.sample_conversation_result = MemoryFactory.create_conversation_result()
        self.sample_user_context = MemoryFactory.create_user_context()
        self.sample_memories = MemoryFactory.create_memories()
        self.sample_preferences = MemoryFactory.create_preferences()
        self.sample_memory_stats = MemoryFactory.create_memory_stats()

    @patch("tripsage.api.routers.memory.get_memory_service_dep")
    @patch("tripsage.api.routers.memory.require_principal_dep")
    def test_add_conversation_memory_success(self, mock_auth, mock_service_dep):
        """Test successful conversation memory addition."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")
        mock_service_dep.return_value = self.mock_service
        self.mock_service.add_conversation_memory = AsyncMock(
            return_value=self.sample_conversation_result
        )

        conversation_request = {
            "messages": [
                {"role": "user", "content": "I want to plan a trip to Tokyo"},
                {
                    "role": "assistant",
                    "content": "I'd be happy to help you plan your Tokyo trip!",
                },
            ],
            "session_id": "test-session-123",
            "context_type": "travel_planning",
        }

        # Act
        response = self.client.post(
            "/api/memory/conversation",
            json=conversation_request,
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "memory_id" in data
        assert data["status"] == "success"
        self.mock_service.add_conversation_memory.assert_called_once()

    @patch("tripsage.api.routers.memory.get_memory_service_dep")
    @patch("tripsage.api.routers.memory.require_principal_dep")
    def test_add_conversation_memory_without_session_id(
        self, mock_auth, mock_service_dep
    ):
        """Test conversation memory addition without session ID."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")
        mock_service_dep.return_value = self.mock_service
        self.mock_service.add_conversation_memory = AsyncMock(
            return_value=self.sample_conversation_result
        )

        conversation_request = {
            "messages": [{"role": "user", "content": "Help me find flights"}],
            "context_type": "travel_planning",
        }

        # Act
        response = self.client.post(
            "/api/memory/conversation",
            json=conversation_request,
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        # Service should be called with None for session_id
        args = self.mock_service.add_conversation_memory.call_args[0]
        assert args[2] is None  # session_id parameter

    @patch("tripsage.api.routers.memory.get_memory_service_dep")
    @patch("tripsage.api.routers.memory.require_principal_dep")
    def test_get_user_context_success(self, mock_auth, mock_service_dep):
        """Test successful user context retrieval."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")
        mock_service_dep.return_value = self.mock_service
        self.mock_service.get_user_context = AsyncMock(
            return_value=self.sample_user_context
        )

        # Act
        response = self.client.get(
            "/api/memory/context", headers={"Authorization": "Bearer test-token"}
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "preferences" in data
        assert "travel_history" in data
        assert "recent_searches" in data
        self.mock_service.get_user_context.assert_called_once_with("test-user-id")

    @patch("tripsage.api.routers.memory.get_memory_service_dep")
    @patch("tripsage.api.routers.memory.require_principal_dep")
    def test_search_memories_success(self, mock_auth, mock_service_dep):
        """Test successful memory search."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")
        mock_service_dep.return_value = self.mock_service
        self.mock_service.search_memories = AsyncMock(return_value=self.sample_memories)

        search_request = {"query": "Tokyo travel preferences", "limit": 5}

        # Act
        response = self.client.post(
            "/api/memory/search",
            json=search_request,
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "memories" in data
        assert "count" in data
        assert data["count"] == len(self.sample_memories)
        assert isinstance(data["memories"], list)
        self.mock_service.search_memories.assert_called_once_with(
            "test-user-id", "Tokyo travel preferences", 5
        )

    @patch("tripsage.api.routers.memory.get_memory_service_dep")
    @patch("tripsage.api.routers.memory.require_principal_dep")
    def test_search_memories_no_results(self, mock_auth, mock_service_dep):
        """Test memory search with no results."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")
        mock_service_dep.return_value = self.mock_service
        self.mock_service.search_memories = AsyncMock(return_value=[])

        search_request = {"query": "nonexistent topic", "limit": 10}

        # Act
        response = self.client.post(
            "/api/memory/search",
            json=search_request,
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["memories"] == []
        assert data["count"] == 0

    @patch("tripsage.api.routers.memory.get_memory_service_dep")
    @patch("tripsage.api.routers.memory.require_principal_dep")
    def test_update_preferences_success(self, mock_auth, mock_service_dep):
        """Test successful preferences update."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")
        mock_service_dep.return_value = self.mock_service
        updated_preferences = {**self.sample_preferences, "budget_range": "luxury"}
        self.mock_service.update_user_preferences = AsyncMock(
            return_value=updated_preferences
        )

        preferences_request = {
            "preferences": {
                "budget_range": "luxury",
                "accommodation_type": "hotel",
                "travel_style": "comfort",
            }
        }

        # Act
        response = self.client.put(
            "/api/memory/preferences",
            json=preferences_request,
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["budget_range"] == "luxury"
        self.mock_service.update_user_preferences.assert_called_once()

    @patch("tripsage.api.routers.memory.get_memory_service_dep")
    @patch("tripsage.api.routers.memory.require_principal_dep")
    def test_add_preference_success(self, mock_auth, mock_service_dep):
        """Test successful single preference addition."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")
        mock_service_dep.return_value = self.mock_service
        new_preference = {
            "key": "dietary_restrictions",
            "value": "vegetarian",
            "category": "food",
        }
        self.mock_service.add_user_preference = AsyncMock(return_value=new_preference)

        # Act
        response = self.client.post(
            "/api/memory/preference?key=dietary_restrictions&value=vegetarian&category=food",
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["key"] == "dietary_restrictions"
        assert data["value"] == "vegetarian"
        assert data["category"] == "food"
        self.mock_service.add_user_preference.assert_called_once_with(
            "test-user-id", "dietary_restrictions", "vegetarian", "food"
        )

    @patch("tripsage.api.routers.memory.get_memory_service_dep")
    @patch("tripsage.api.routers.memory.require_principal_dep")
    def test_add_preference_default_category(self, mock_auth, mock_service_dep):
        """Test preference addition with default category."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")
        mock_service_dep.return_value = self.mock_service
        new_preference = {"key": "language", "value": "english", "category": "general"}
        self.mock_service.add_user_preference = AsyncMock(return_value=new_preference)

        # Act
        response = self.client.post(
            "/api/memory/preference?key=language&value=english",
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        # Should use default category "general"
        self.mock_service.add_user_preference.assert_called_once_with(
            "test-user-id", "language", "english", "general"
        )

    @patch("tripsage.api.routers.memory.get_memory_service_dep")
    @patch("tripsage.api.routers.memory.require_principal_dep")
    def test_delete_memory_success(self, mock_auth, mock_service_dep):
        """Test successful memory deletion."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")
        mock_service_dep.return_value = self.mock_service
        memory_id = "test-memory-id"
        self.mock_service.delete_memory = AsyncMock(return_value=True)

        # Act
        response = self.client.delete(
            f"/api/memory/memory/{memory_id}",
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["message"] == "Memory deleted successfully"
        self.mock_service.delete_memory.assert_called_once_with(
            "test-user-id", memory_id
        )

    @patch("tripsage.api.routers.memory.get_memory_service_dep")
    @patch("tripsage.api.routers.memory.require_principal_dep")
    def test_delete_memory_not_found(self, mock_auth, mock_service_dep):
        """Test deletion of non-existent memory."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")
        mock_service_dep.return_value = self.mock_service
        memory_id = "non-existent-memory"
        self.mock_service.delete_memory = AsyncMock(return_value=False)

        # Act
        response = self.client.delete(
            f"/api/memory/memory/{memory_id}",
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Memory not found" in response.json()["detail"]

    @patch("tripsage.api.routers.memory.get_memory_service_dep")
    @patch("tripsage.api.routers.memory.require_principal_dep")
    def test_get_memory_stats_success(self, mock_auth, mock_service_dep):
        """Test successful memory statistics retrieval."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")
        mock_service_dep.return_value = self.mock_service
        self.mock_service.get_memory_stats = AsyncMock(
            return_value=self.sample_memory_stats
        )

        # Act
        response = self.client.get(
            "/api/memory/stats", headers={"Authorization": "Bearer test-token"}
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "total_memories" in data
        assert "conversation_count" in data
        assert "preference_count" in data
        assert data["total_memories"] == 25
        self.mock_service.get_memory_stats.assert_called_once_with("test-user-id")

    @patch("tripsage.api.routers.memory.get_memory_service_dep")
    @patch("tripsage.api.routers.memory.require_principal_dep")
    def test_clear_user_memory_success(self, mock_auth, mock_service_dep):
        """Test successful memory clearing with confirmation."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")
        mock_service_dep.return_value = self.mock_service
        clear_result = {"status": "success", "deleted_count": 15}
        self.mock_service.clear_user_memory = AsyncMock(return_value=clear_result)

        # Act
        response = self.client.delete(
            "/api/memory/clear?confirm=true",
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "success"
        assert data["deleted_count"] == 15
        self.mock_service.clear_user_memory.assert_called_once_with(
            "test-user-id", True
        )

    @patch("tripsage.api.routers.memory.get_memory_service_dep")
    @patch("tripsage.api.routers.memory.require_principal_dep")
    def test_clear_user_memory_without_confirmation(self, mock_auth, mock_service_dep):
        """Test memory clearing without confirmation."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")
        mock_service_dep.return_value = self.mock_service
        self.mock_service.clear_user_memory = AsyncMock(
            return_value={"status": "confirmation_required"}
        )

        # Act
        response = self.client.delete(
            "/api/memory/clear", headers={"Authorization": "Bearer test-token"}
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        # Should be called with confirm=False (default)
        self.mock_service.clear_user_memory.assert_called_once_with(
            "test-user-id", False
        )

    def test_add_conversation_memory_unauthorized(self):
        """Test conversation memory addition without authentication."""
        conversation_request = {"messages": [{"role": "user", "content": "Hello"}]}

        response = self.client.post(
            "/api/memory/conversation", json=conversation_request
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_user_context_unauthorized(self):
        """Test user context retrieval without authentication."""
        response = self.client.get("/api/memory/context")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @patch("tripsage.api.routers.memory.get_memory_service_dep")
    @patch("tripsage.api.routers.memory.require_principal_dep")
    def test_add_conversation_memory_service_error(self, mock_auth, mock_service_dep):
        """Test conversation memory addition with service error."""
        # Arrange
        mock_auth.return_value = Mock(id="test-user-id")
        mock_service_dep.return_value = self.mock_service
        self.mock_service.add_conversation_memory = AsyncMock(
            side_effect=Exception("Memory service unavailable")
        )

        conversation_request = {
            "messages": [{"role": "user", "content": "Test message"}]
        }

        # Act
        response = self.client.post(
            "/api/memory/conversation",
            json=conversation_request,
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to add conversation memory" in response.json()["detail"]

    @pytest.mark.parametrize("limit", [0, -1, 1001])
    def test_search_memories_invalid_limit(self, limit):
        """Test memory search with invalid limit values."""
        search_request = {"query": "test query", "limit": limit}

        response = self.client.post(
            "/api/memory/search",
            json=search_request,
            headers={"Authorization": "Bearer test-token"},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.parametrize("query", ["", None, " ", "a" * 1001])
    def test_search_memories_invalid_query(self, query):
        """Test memory search with invalid query values."""
        search_request = {"query": query, "limit": 10}

        response = self.client.post(
            "/api/memory/search",
            json=search_request,
            headers={"Authorization": "Bearer test-token"},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_add_conversation_memory_empty_messages(self):
        """Test conversation memory addition with empty messages."""
        conversation_request = {"messages": []}

        response = self.client.post(
            "/api/memory/conversation",
            json=conversation_request,
            headers={"Authorization": "Bearer test-token"},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_update_preferences_missing_preferences(self):
        """Test preferences update with missing preferences field."""
        preferences_request = {}

        response = self.client.put(
            "/api/memory/preferences",
            json=preferences_request,
            headers={"Authorization": "Bearer test-token"},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.parametrize(
        "key,value", [("", "test"), ("test", ""), (None, "test"), ("test", None)]
    )
    def test_add_preference_invalid_parameters(self, key, value):
        """Test preference addition with invalid key/value parameters."""
        params = {}
        if key is not None:
            params["key"] = key
        if value is not None:
            params["value"] = value

        query_string = "&".join([f"{k}={v}" for k, v in params.items()])

        response = self.client.post(
            f"/api/memory/preference?{query_string}",
            headers={"Authorization": "Bearer test-token"},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
