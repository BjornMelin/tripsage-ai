"""
Clean tests for memory router.

Tests the actual implemented memory management functionality.
Follows TripSage standards for focused, actionable testing.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from tripsage.api.middlewares.authentication import Principal
from tripsage.api.routers.memory import (
    ConversationMemoryRequest,
    SearchMemoryRequest,
    UpdatePreferencesRequest,
    add_conversation_memory,
    add_preference,
    clear_user_memory,
    delete_memory,
    get_memory_stats,
    get_user_context,
    search_memories,
    update_preferences,
)
from tripsage_core.services.business.memory_service import MemoryService


class TestMemoryRouter:
    """Test memory router functionality by testing functions directly."""

    @pytest.fixture
    def mock_principal(self):
        """Mock authenticated principal."""
        return Principal(
            id="user123", type="user", email="test@example.com", auth_method="jwt"
        )

    @pytest.fixture
    def mock_memory_service(self):
        """Mock memory service."""
        service = MagicMock(spec=MemoryService)
        # Configure common async methods
        service.add_conversation_memory = AsyncMock()
        service.get_user_context = AsyncMock()
        service.search_memories = AsyncMock()
        service.update_user_preferences = AsyncMock()
        service.add_user_preference = AsyncMock()
        service.delete_memory = AsyncMock()
        service.get_memory_stats = AsyncMock()
        service.clear_user_memory = AsyncMock()
        return service

    @pytest.fixture
    def sample_conversation_request(self):
        """Sample conversation memory request."""
        return ConversationMemoryRequest(
            messages=[
                {"role": "user", "content": "I want to plan a trip to Tokyo"},
                {
                    "role": "assistant",
                    "content": "I'd be happy to help you plan your Tokyo trip!",
                },
            ],
            session_id="test-session-123",
            context_type="travel_planning",
        )

    @pytest.fixture
    def sample_search_request(self):
        """Sample search memory request."""
        return SearchMemoryRequest(query="Tokyo travel preferences", limit=5)

    @pytest.fixture
    def sample_preferences_request(self):
        """Sample preferences update request."""
        return UpdatePreferencesRequest(
            preferences={
                "budget_range": "luxury",
                "accommodation_type": "hotel",
                "travel_style": "comfort",
            }
        )

    async def test_add_conversation_memory_success(
        self, mock_principal, mock_memory_service, sample_conversation_request
    ):
        """Test successful conversation memory addition."""
        # Mock response
        expected_result = {
            "memory_id": "mem123",
            "status": "success",
            "messages_stored": 2,
            "session_id": "test-session-123",
        }
        mock_memory_service.add_conversation_memory.return_value = expected_result

        result = await add_conversation_memory(
            sample_conversation_request, mock_principal, mock_memory_service
        )

        # Verify service call
        mock_memory_service.add_conversation_memory.assert_called_once_with(
            "user123",
            [
                {"role": "user", "content": "I want to plan a trip to Tokyo"},
                {
                    "role": "assistant",
                    "content": "I'd be happy to help you plan your Tokyo trip!",
                },
            ],
            "test-session-123",
        )
        assert result == expected_result

    async def test_add_conversation_memory_without_session_id(
        self, mock_principal, mock_memory_service
    ):
        """Test conversation memory addition without session ID."""
        request = ConversationMemoryRequest(
            messages=[{"role": "user", "content": "Help me find flights"}],
            context_type="travel_planning",
        )

        expected_result = {
            "memory_id": "mem456",
            "status": "success",
            "messages_stored": 1,
        }
        mock_memory_service.add_conversation_memory.return_value = expected_result

        result = await add_conversation_memory(
            request, mock_principal, mock_memory_service
        )

        # Should pass None for session_id
        mock_memory_service.add_conversation_memory.assert_called_once_with(
            "user123", [{"role": "user", "content": "Help me find flights"}], None
        )
        assert result == expected_result

    async def test_add_conversation_memory_service_error(
        self, mock_principal, mock_memory_service, sample_conversation_request
    ):
        """Test conversation memory addition with service error."""
        mock_memory_service.add_conversation_memory.side_effect = Exception(
            "Memory service unavailable"
        )

        with pytest.raises(HTTPException) as exc_info:
            await add_conversation_memory(
                sample_conversation_request, mock_principal, mock_memory_service
            )

        assert exc_info.value.status_code == 500
        assert "Failed to add conversation memory" in str(exc_info.value.detail)

    async def test_get_user_context_success(self, mock_principal, mock_memory_service):
        """Test successful user context retrieval."""
        expected_context = {
            "user_id": "user123",
            "preferences": {
                "budget_range": "medium",
                "accommodation_type": "hotel",
                "travel_style": "balanced",
            },
            "travel_history": [
                {
                    "destination": "Tokyo, Japan",
                    "dates": "2023-05-01 to 2023-05-07",
                    "rating": 5,
                }
            ],
            "recent_searches": [
                {"query": "hotels in Tokyo", "timestamp": "2024-01-01T00:00:00Z"}
            ],
        }
        mock_memory_service.get_user_context.return_value = expected_context

        result = await get_user_context(mock_principal, mock_memory_service)

        mock_memory_service.get_user_context.assert_called_once_with("user123")
        assert result == expected_context
        assert "preferences" in result
        assert "travel_history" in result
        assert "recent_searches" in result

    async def test_get_user_context_service_error(
        self, mock_principal, mock_memory_service
    ):
        """Test user context retrieval with service error."""
        mock_memory_service.get_user_context.side_effect = Exception(
            "Context service error"
        )

        with pytest.raises(HTTPException) as exc_info:
            await get_user_context(mock_principal, mock_memory_service)

        assert exc_info.value.status_code == 500
        assert "Failed to get user context" in str(exc_info.value.detail)

    async def test_search_memories_success(
        self, mock_principal, mock_memory_service, sample_search_request
    ):
        """Test successful memory search."""
        expected_memories = [
            {
                "id": "mem1",
                "content": "Tokyo hotel preferences",
                "type": "conversation",
                "relevance_score": 0.9,
                "created_at": "2024-01-01T00:00:00Z",
            },
            {
                "id": "mem2",
                "content": "Budget discussion for Tokyo trip",
                "type": "preference",
                "relevance_score": 0.8,
                "created_at": "2024-01-02T00:00:00Z",
            },
        ]
        mock_memory_service.search_memories.return_value = expected_memories

        result = await search_memories(
            sample_search_request, mock_principal, mock_memory_service
        )

        mock_memory_service.search_memories.assert_called_once_with(
            "user123", "Tokyo travel preferences", 5
        )
        assert result["memories"] == expected_memories
        assert result["count"] == 2

    async def test_search_memories_no_results(
        self, mock_principal, mock_memory_service
    ):
        """Test memory search with no results."""
        search_request = SearchMemoryRequest(query="nonexistent topic", limit=10)
        mock_memory_service.search_memories.return_value = []

        result = await search_memories(
            search_request, mock_principal, mock_memory_service
        )

        assert result["memories"] == []
        assert result["count"] == 0

    async def test_search_memories_service_error(
        self, mock_principal, mock_memory_service, sample_search_request
    ):
        """Test memory search with service error."""
        mock_memory_service.search_memories.side_effect = Exception(
            "Search service error"
        )

        with pytest.raises(HTTPException) as exc_info:
            await search_memories(
                sample_search_request, mock_principal, mock_memory_service
            )

        assert exc_info.value.status_code == 500
        assert "Failed to search memories" in str(exc_info.value.detail)

    async def test_update_preferences_success(
        self, mock_principal, mock_memory_service, sample_preferences_request
    ):
        """Test successful preferences update."""
        expected_result = {
            "budget_range": "luxury",
            "accommodation_type": "hotel",
            "travel_style": "comfort",
            "updated_at": "2024-01-01T00:00:00Z",
        }
        mock_memory_service.update_user_preferences.return_value = expected_result

        result = await update_preferences(
            sample_preferences_request, mock_principal, mock_memory_service
        )

        mock_memory_service.update_user_preferences.assert_called_once_with(
            "user123",
            {
                "budget_range": "luxury",
                "accommodation_type": "hotel",
                "travel_style": "comfort",
            },
        )
        assert result == expected_result

    async def test_update_preferences_service_error(
        self, mock_principal, mock_memory_service, sample_preferences_request
    ):
        """Test preferences update with service error."""
        mock_memory_service.update_user_preferences.side_effect = Exception(
            "Preferences service error"
        )

        with pytest.raises(HTTPException) as exc_info:
            await update_preferences(
                sample_preferences_request, mock_principal, mock_memory_service
            )

        assert exc_info.value.status_code == 500
        assert "Failed to update preferences" in str(exc_info.value.detail)

    async def test_add_preference_success(self, mock_principal, mock_memory_service):
        """Test successful single preference addition."""
        expected_preference = {
            "key": "dietary_restrictions",
            "value": "vegetarian",
            "category": "food",
            "created_at": "2024-01-01T00:00:00Z",
        }
        mock_memory_service.add_user_preference.return_value = expected_preference

        result = await add_preference(
            "dietary_restrictions",
            "vegetarian",
            "food",
            mock_principal,
            mock_memory_service,
        )

        mock_memory_service.add_user_preference.assert_called_once_with(
            "user123", "dietary_restrictions", "vegetarian", "food"
        )
        assert result == expected_preference

    async def test_add_preference_default_category(
        self, mock_principal, mock_memory_service
    ):
        """Test preference addition with default category."""
        expected_preference = {
            "key": "language",
            "value": "english",
            "category": "general",
            "created_at": "2024-01-01T00:00:00Z",
        }
        mock_memory_service.add_user_preference.return_value = expected_preference

        result = await add_preference(
            "language",
            "english",
            "general",  # Default category
            mock_principal,
            mock_memory_service,
        )

        mock_memory_service.add_user_preference.assert_called_once_with(
            "user123", "language", "english", "general"
        )
        assert result == expected_preference

    async def test_add_preference_service_error(
        self, mock_principal, mock_memory_service
    ):
        """Test preference addition with service error."""
        mock_memory_service.add_user_preference.side_effect = Exception(
            "Preference service error"
        )

        with pytest.raises(HTTPException) as exc_info:
            await add_preference(
                "test_key", "test_value", "general", mock_principal, mock_memory_service
            )

        assert exc_info.value.status_code == 500
        assert "Failed to add preference" in str(exc_info.value.detail)

    async def test_delete_memory_success(self, mock_principal, mock_memory_service):
        """Test successful memory deletion."""
        memory_id = "mem123"
        mock_memory_service.delete_memory.return_value = True

        result = await delete_memory(memory_id, mock_principal, mock_memory_service)

        mock_memory_service.delete_memory.assert_called_once_with("user123", memory_id)
        assert result["message"] == "Memory deleted successfully"

    async def test_delete_memory_not_found(self, mock_principal, mock_memory_service):
        """Test deletion of non-existent memory."""
        memory_id = "nonexistent-memory"
        mock_memory_service.delete_memory.return_value = False

        with pytest.raises(HTTPException) as exc_info:
            await delete_memory(memory_id, mock_principal, mock_memory_service)

        assert exc_info.value.status_code == 404
        assert "Memory not found" in str(exc_info.value.detail)

    async def test_delete_memory_service_error(
        self, mock_principal, mock_memory_service
    ):
        """Test memory deletion with service error."""
        memory_id = "mem123"
        mock_memory_service.delete_memory.side_effect = Exception(
            "Delete service error"
        )

        with pytest.raises(HTTPException) as exc_info:
            await delete_memory(memory_id, mock_principal, mock_memory_service)

        assert exc_info.value.status_code == 500
        assert "Failed to delete memory" in str(exc_info.value.detail)

    async def test_get_memory_stats_success(self, mock_principal, mock_memory_service):
        """Test successful memory statistics retrieval."""
        expected_stats = {
            "total_memories": 25,
            "conversation_count": 15,
            "preference_count": 8,
            "travel_history_count": 2,
            "last_activity": "2024-01-01T00:00:00Z",
            "storage_used_kb": 156.7,
        }
        mock_memory_service.get_memory_stats.return_value = expected_stats

        result = await get_memory_stats(mock_principal, mock_memory_service)

        mock_memory_service.get_memory_stats.assert_called_once_with("user123")
        assert result == expected_stats
        assert "total_memories" in result
        assert "conversation_count" in result
        assert "preference_count" in result

    async def test_get_memory_stats_service_error(
        self, mock_principal, mock_memory_service
    ):
        """Test memory statistics retrieval with service error."""
        mock_memory_service.get_memory_stats.side_effect = Exception(
            "Stats service error"
        )

        with pytest.raises(HTTPException) as exc_info:
            await get_memory_stats(mock_principal, mock_memory_service)

        assert exc_info.value.status_code == 500
        assert "Failed to get memory stats" in str(exc_info.value.detail)

    async def test_clear_user_memory_success(self, mock_principal, mock_memory_service):
        """Test successful memory clearing with confirmation."""
        expected_result = {
            "status": "success",
            "deleted_count": 15,
            "cleared_at": "2024-01-01T00:00:00Z",
        }
        mock_memory_service.clear_user_memory.return_value = expected_result

        result = await clear_user_memory(True, mock_principal, mock_memory_service)

        mock_memory_service.clear_user_memory.assert_called_once_with("user123", True)
        assert result == expected_result

    async def test_clear_user_memory_without_confirmation(
        self, mock_principal, mock_memory_service
    ):
        """Test memory clearing without confirmation."""
        expected_result = {
            "status": "confirmation_required",
            "message": "Confirmation required to clear all memories",
        }
        mock_memory_service.clear_user_memory.return_value = expected_result

        result = await clear_user_memory(False, mock_principal, mock_memory_service)

        mock_memory_service.clear_user_memory.assert_called_once_with("user123", False)
        assert result == expected_result

    async def test_clear_user_memory_service_error(
        self, mock_principal, mock_memory_service
    ):
        """Test memory clearing with service error."""
        mock_memory_service.clear_user_memory.side_effect = Exception(
            "Clear service error"
        )

        with pytest.raises(HTTPException) as exc_info:
            await clear_user_memory(True, mock_principal, mock_memory_service)

        assert exc_info.value.status_code == 500
        assert "Failed to clear memory" in str(exc_info.value.detail)
