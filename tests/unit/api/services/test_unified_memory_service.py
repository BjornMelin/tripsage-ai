"""
Tests for unified MemoryService API adapter.

This module tests the unified MemoryService that acts as a thin adaptation
layer between API requests and core memory business logic.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from tripsage.api.services.memory import MemoryService
from tripsage_core.services.business.memory_service import (
    ConversationMemoryRequest,
    MemorySearchRequest,
    MemorySearchResult,
    PreferencesUpdateRequest,
    UserContextResponse,
)
from tripsage_core.services.business.memory_service import (
    MemoryService as CoreMemoryService,
)


class TestMemoryServiceAdapter:
    """Test the unified MemoryService adapter functionality."""

    @pytest.fixture
    def mock_core_memory_service(self):
        """Mock core memory service."""
        return AsyncMock(spec=CoreMemoryService)

    @pytest.fixture
    def memory_service(self, mock_core_memory_service):
        """Create MemoryService instance with mocked dependencies."""
        return MemoryService(core_memory_service=mock_core_memory_service)

    @pytest.mark.asyncio
    async def test_add_conversation_memory_delegates_to_core_service(
        self, memory_service, mock_core_memory_service
    ):
        """Test that add_conversation_memory delegates to core service."""
        user_id = str(uuid4())
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]
        session_id = str(uuid4())

        # Mock core service response
        mock_response = {
            "results": [{"id": str(uuid4()), "memory": "Stored memory"}],
            "success": True,
        }
        mock_core_memory_service.add_conversation_memory.return_value = mock_response

        result = await memory_service.add_conversation_memory(
            user_id, messages, session_id
        )

        # Verify core service was called with ConversationMemoryRequest
        mock_core_memory_service.add_conversation_memory.assert_called_once()
        call_args = mock_core_memory_service.add_conversation_memory.call_args
        assert call_args.kwargs["user_id"] == user_id

        # Verify the request is a ConversationMemoryRequest
        memory_request = call_args.kwargs["memory_request"]
        assert isinstance(memory_request, ConversationMemoryRequest)
        assert memory_request.messages == messages
        assert memory_request.session_id == session_id

        assert result == mock_response

    @pytest.mark.asyncio
    async def test_search_memories_delegates_to_core_service(
        self, memory_service, mock_core_memory_service
    ):
        """Test that search_memories delegates to core service."""
        user_id = str(uuid4())
        query = "travel plans"
        limit = 10

        # Mock core service response with MemorySearchResult objects
        mock_memory_results = [
            MemorySearchResult(
                id=str(uuid4()),
                memory="Travel to Paris",
                metadata={"category": "destinations"},
                categories=["travel", "destinations"],
                similarity=0.8,
                created_at=datetime.now(timezone.utc),
                user_id=user_id,
            ),
            MemorySearchResult(
                id=str(uuid4()),
                memory="Book hotel in Rome",
                metadata={"category": "accommodations"},
                categories=["travel", "accommodations"],
                similarity=0.7,
                created_at=datetime.now(timezone.utc),
                user_id=user_id,
            ),
        ]
        mock_core_memory_service.search_memories.return_value = mock_memory_results

        result = await memory_service.search_memories(user_id, query, limit)

        # Verify core service was called with MemorySearchRequest
        mock_core_memory_service.search_memories.assert_called_once()
        call_args = mock_core_memory_service.search_memories.call_args
        assert call_args.kwargs["user_id"] == user_id

        # Verify the request is a MemorySearchRequest
        search_request = call_args.kwargs["search_request"]
        assert isinstance(search_request, MemorySearchRequest)
        assert search_request.query == query
        assert search_request.limit == limit

        # Verify result is converted to dictionaries
        expected_result = [memory.model_dump() for memory in mock_memory_results]
        assert result == expected_result

    @pytest.mark.asyncio
    async def test_get_user_context_delegates_to_core_service(
        self, memory_service, mock_core_memory_service
    ):
        """Test that get_user_context delegates to core service."""
        user_id = str(uuid4())

        # Mock core service response with UserContextResponse
        mock_context_response = UserContextResponse(
            preferences=[{"travel_style": "luxury", "budget": "$1000-$2000"}],
            past_trips=[{"destination": "Paris", "year": "2023"}],
            saved_destinations=[{"name": "Tokyo", "country": "Japan"}],
            budget_patterns=[{"avg_budget": 1500, "category": "international"}],
            travel_style=[{"style": "luxury", "frequency": "high"}],
            dietary_restrictions=[{"type": "vegetarian"}],
            accommodation_preferences=[{"type": "hotel", "stars": "4+"}],
            activity_preferences=[{"type": "cultural", "preference": "museums"}],
            insights={
                "preferred_destinations": {"most_visited": ["Paris", "Tokyo"]},
                "travel_style": {"primary_style": "luxury"},
            },
            summary="Luxury traveler with preference for cultural destinations",
        )
        mock_core_memory_service.get_user_context.return_value = mock_context_response

        result = await memory_service.get_user_context(user_id)

        # Verify core service was called
        mock_core_memory_service.get_user_context.assert_called_once_with(
            user_id=user_id
        )

        # Verify result is converted to dictionary
        expected_result = mock_context_response.model_dump()
        assert result == expected_result

    @pytest.mark.asyncio
    async def test_update_user_preferences_delegates_to_core_service(
        self, memory_service, mock_core_memory_service
    ):
        """Test that update_user_preferences delegates to core service."""
        user_id = str(uuid4())
        preferences = {"budget_range": "$1000-$2000", "travel_style": "adventure"}

        # Mock core service response
        mock_response = {
            "results": [{"id": str(uuid4()), "memory": "User preferences updated"}],
            "success": True,
        }
        mock_core_memory_service.update_user_preferences.return_value = mock_response

        result = await memory_service.update_user_preferences(user_id, preferences)

        # Verify core service was called with PreferencesUpdateRequest
        mock_core_memory_service.update_user_preferences.assert_called_once()
        call_args = mock_core_memory_service.update_user_preferences.call_args
        assert call_args.kwargs["user_id"] == user_id

        # Verify the request is a PreferencesUpdateRequest
        preferences_request = call_args.kwargs["preferences_request"]
        assert isinstance(preferences_request, PreferencesUpdateRequest)
        assert preferences_request.preferences == preferences

        assert result == mock_response

    @pytest.mark.asyncio
    async def test_add_user_preference_delegates_to_core_service(
        self, memory_service, mock_core_memory_service
    ):
        """Test that add_user_preference delegates to core service."""
        user_id = str(uuid4())
        key = "favorite_airline"
        value = "Delta"
        category = "travel"

        # Mock core service response (add_user_preference uses
        # update_user_preferences internally)
        mock_response = {
            "results": [{"id": str(uuid4()), "memory": "User preference added"}],
            "success": True,
        }
        mock_core_memory_service.update_user_preferences.return_value = mock_response

        result = await memory_service.add_user_preference(user_id, key, value, category)

        # Verify core service was called with update_user_preferences
        mock_core_memory_service.update_user_preferences.assert_called_once()
        call_args = mock_core_memory_service.update_user_preferences.call_args
        assert call_args.kwargs["user_id"] == user_id

        # Verify the request is a PreferencesUpdateRequest with single preference
        preferences_request = call_args.kwargs["preferences_request"]
        assert isinstance(preferences_request, PreferencesUpdateRequest)
        assert preferences_request.preferences == {key: value}
        assert preferences_request.category == category

        assert result == mock_response

    @pytest.mark.asyncio
    async def test_delete_memory_delegates_to_core_service(
        self, memory_service, mock_core_memory_service
    ):
        """Test that delete_memory delegates to core service."""
        user_id = str(uuid4())
        memory_id = str(uuid4())

        # Mock core service response (delete_memory uses
        # delete_user_memories internally)
        mock_response = {"deleted_count": 1, "success": True}
        mock_core_memory_service.delete_user_memories.return_value = mock_response

        result = await memory_service.delete_memory(user_id, memory_id)

        # Verify core service was called with delete_user_memories
        mock_core_memory_service.delete_user_memories.assert_called_once_with(
            user_id=user_id, memory_ids=[memory_id]
        )

        # Verify result is extracted from response
        assert result == mock_response.get("success", False)

    @pytest.mark.asyncio
    async def test_get_memory_stats_delegates_to_core_service(
        self, memory_service, mock_core_memory_service
    ):
        """Test that get_memory_stats derives stats from user context."""
        user_id = str(uuid4())

        # Mock core service response (get_memory_stats uses get_user_context internally)
        mock_context_response = UserContextResponse(
            preferences=[{"travel_style": "luxury"}, {"budget": "$1000-$2000"}],
            past_trips=[{"destination": "Paris"}, {"destination": "Tokyo"}],
            saved_destinations=[{"name": "Rome"}],
            budget_patterns=[{"avg_budget": 1500}],
            travel_style=[{"style": "luxury"}],
            dietary_restrictions=[],
            accommodation_preferences=[{"type": "hotel"}],
            activity_preferences=[],
            insights={},
            summary="Test user summary",
        )
        mock_core_memory_service.get_user_context.return_value = mock_context_response

        result = await memory_service.get_memory_stats(user_id)

        # Verify core service was called with get_user_context
        mock_core_memory_service.get_user_context.assert_called_once_with(
            user_id=user_id
        )

        # Verify stats are derived correctly (based on actual implementation)
        expected_stats = {
            "total_memories": 4,  # preferences(2) + past_trips(2) only
            "conversation_memories": 2,  # past_trips
            "preference_count": 2,  # preferences
            "last_activity": "unknown",
        }
        assert result == expected_stats

    @pytest.mark.asyncio
    async def test_clear_user_memory_delegates_to_core_service(
        self, memory_service, mock_core_memory_service
    ):
        """Test that clear_user_memory delegates to core service."""
        user_id = str(uuid4())
        confirm = True

        # Mock core service response (clear_user_memory uses
        # delete_user_memories internally)
        mock_response = {"deleted_count": 15, "success": True}
        mock_core_memory_service.delete_user_memories.return_value = mock_response

        result = await memory_service.clear_user_memory(user_id, confirm)

        # Verify core service was called with delete_user_memories
        # (no memory_ids = delete all)
        mock_core_memory_service.delete_user_memories.assert_called_once_with(
            user_id=user_id
        )

        # Verify response is formatted correctly
        expected_result = {
            "cleared": mock_response.get("success", False),
            "count": mock_response.get("deleted_count", 0),
        }
        assert result == expected_result


class TestMemoryServiceDependencyInjection:
    """Test MemoryService dependency injection functionality."""

    @pytest.mark.asyncio
    async def test_get_memory_service_creates_instance(self):
        """Test that get_memory_service creates MemoryService with proper
        dependencies."""
        with patch(
            "tripsage.api.services.memory.get_core_memory_service"
        ) as mock_get_core:
            mock_core_memory = AsyncMock()
            mock_get_core.return_value = mock_core_memory

            from tripsage.api.services.memory import get_memory_service

            result = await get_memory_service()

            # Verify dependency was retrieved
            mock_get_core.assert_called_once()

            # Verify MemoryService was created with proper dependency
            assert isinstance(result, MemoryService)
            assert result.core_memory_service == mock_core_memory


class TestMemoryServiceErrorHandling:
    """Test error handling in MemoryService adapter."""

    @pytest.fixture
    def memory_service(self):
        """Create MemoryService with error-prone mocks."""
        mock_core_memory = AsyncMock()
        return MemoryService(core_memory_service=mock_core_memory)

    @pytest.mark.asyncio
    async def test_add_conversation_memory_propagates_errors(self, memory_service):
        """Test that add_conversation_memory propagates core service errors."""
        user_id = str(uuid4())
        messages = [{"role": "user", "content": "Hello"}]

        # Mock core service to raise an error
        memory_service.core_memory_service.add_conversation_memory.side_effect = (
            Exception("Memory storage failed")
        )

        with pytest.raises(Exception) as exc_info:
            await memory_service.add_conversation_memory(user_id, messages, None)

        assert "Memory storage failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_search_memories_propagates_errors(self, memory_service):
        """Test that search_memories propagates core service errors."""
        user_id = str(uuid4())
        query = "test query"

        # Mock core service to raise an error
        memory_service.core_memory_service.search_memories.side_effect = Exception(
            "Search failed"
        )

        with pytest.raises(Exception) as exc_info:
            await memory_service.search_memories(user_id, query, 10)

        assert "Search failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_delete_memory_handles_not_found(self, memory_service):
        """Test that delete_memory handles not found cases."""
        user_id = str(uuid4())
        memory_id = str(uuid4())

        # Mock core service to return unsuccessful response (not found)
        memory_service.core_memory_service.delete_user_memories.return_value = {
            "deleted_count": 0,
            "success": False,
        }

        result = await memory_service.delete_memory(user_id, memory_id)

        assert result is False


class TestMemoryServiceValidation:
    """Test input validation in MemoryService adapter."""

    @pytest.fixture
    def memory_service(self):
        """Create MemoryService with mocked dependencies."""
        mock_core_memory = AsyncMock()
        return MemoryService(core_memory_service=mock_core_memory)

    @pytest.mark.asyncio
    async def test_empty_messages_handled_correctly(self, memory_service):
        """Test that empty messages list is handled correctly."""
        user_id = str(uuid4())
        messages = []

        # Mock core service response
        memory_service.core_memory_service.add_conversation_memory.return_value = {
            "results": [],
            "error": "No messages to store",
        }

        await memory_service.add_conversation_memory(user_id, messages, None)

        # Verify core service was still called (validation happens at core level)
        memory_service.core_memory_service.add_conversation_memory.assert_called_once()
        call_args = memory_service.core_memory_service.add_conversation_memory.call_args
        assert call_args.kwargs["user_id"] == user_id

        # Verify the request is a ConversationMemoryRequest
        memory_request = call_args.kwargs["memory_request"]
        assert isinstance(memory_request, ConversationMemoryRequest)
        assert memory_request.messages == messages
        assert memory_request.session_id is None

    @pytest.mark.asyncio
    async def test_empty_query_handled_correctly(self, memory_service):
        """Test that empty search query raises validation error."""
        user_id = str(uuid4())
        query = ""

        # Empty query should raise ValidationError due to Pydantic validation
        from pydantic import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            await memory_service.search_memories(user_id, query, 10)

        # Verify the error is about query length validation
        assert "String should have at least 1 character" in str(exc_info.value)
