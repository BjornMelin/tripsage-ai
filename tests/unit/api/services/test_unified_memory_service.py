"""
Tests for unified MemoryService API adapter.

This module tests the unified MemoryService that acts as a thin adaptation 
layer between API requests and core memory business logic.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from tripsage.api.services.memory import MemoryService
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
        mock_response = {"memory_id": str(uuid4()), "success": True}
        mock_core_memory_service.add_conversation_memory.return_value = mock_response

        result = await memory_service.add_conversation_memory(
            user_id, messages, session_id
        )

        # Verify core service was called
        mock_core_memory_service.add_conversation_memory.assert_called_once_with(
            user_id=user_id, messages=messages, session_id=session_id
        )
        assert result == mock_response

    @pytest.mark.asyncio
    async def test_search_memories_delegates_to_core_service(
        self, memory_service, mock_core_memory_service
    ):
        """Test that search_memories delegates to core service."""
        user_id = str(uuid4())
        query = "travel plans"
        limit = 10

        # Mock core service response
        mock_memories = [
            {"id": str(uuid4()), "content": "Travel to Paris"},
            {"id": str(uuid4()), "content": "Book hotel in Rome"},
        ]
        mock_core_memory_service.search_memories.return_value = mock_memories

        result = await memory_service.search_memories(user_id, query, limit)

        # Verify core service was called
        mock_core_memory_service.search_memories.assert_called_once_with(
            user_id=user_id, query=query, limit=limit
        )
        assert result == mock_memories

    @pytest.mark.asyncio
    async def test_get_user_context_delegates_to_core_service(
        self, memory_service, mock_core_memory_service
    ):
        """Test that get_user_context delegates to core service."""
        user_id = str(uuid4())

        # Mock core service response
        mock_context = {
            "preferences": {"travel_style": "luxury"},
            "recent_searches": ["Paris", "Tokyo"],
            "profile_summary": "Business traveler",
        }
        mock_core_memory_service.get_user_context.return_value = mock_context

        result = await memory_service.get_user_context(user_id)

        # Verify core service was called
        mock_core_memory_service.get_user_context.assert_called_once_with(
            user_id=user_id
        )
        assert result == mock_context

    @pytest.mark.asyncio
    async def test_update_user_preferences_delegates_to_core_service(
        self, memory_service, mock_core_memory_service
    ):
        """Test that update_user_preferences delegates to core service."""
        user_id = str(uuid4())
        preferences = {"budget_range": "$1000-$2000", "travel_style": "adventure"}

        # Mock core service response
        mock_response = {"updated": True, "preferences": preferences}
        mock_core_memory_service.update_user_preferences.return_value = mock_response

        result = await memory_service.update_user_preferences(user_id, preferences)

        # Verify core service was called
        mock_core_memory_service.update_user_preferences.assert_called_once_with(
            user_id=user_id, preferences=preferences
        )
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

        # Mock core service response
        mock_response = {"preference_id": str(uuid4()), "created": True}
        mock_core_memory_service.add_user_preference.return_value = mock_response

        result = await memory_service.add_user_preference(user_id, key, value, category)

        # Verify core service was called
        mock_core_memory_service.add_user_preference.assert_called_once_with(
            user_id=user_id, key=key, value=value, category=category
        )
        assert result == mock_response

    @pytest.mark.asyncio
    async def test_delete_memory_delegates_to_core_service(
        self, memory_service, mock_core_memory_service
    ):
        """Test that delete_memory delegates to core service."""
        user_id = str(uuid4())
        memory_id = str(uuid4())

        # Mock core service response
        mock_core_memory_service.delete_memory.return_value = True

        result = await memory_service.delete_memory(user_id, memory_id)

        # Verify core service was called
        mock_core_memory_service.delete_memory.assert_called_once_with(
            user_id=user_id, memory_id=memory_id
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_get_memory_stats_delegates_to_core_service(
        self, memory_service, mock_core_memory_service
    ):
        """Test that get_memory_stats delegates to core service."""
        user_id = str(uuid4())

        # Mock core service response
        mock_stats = {
            "total_memories": 15,
            "conversation_memories": 10,
            "preference_count": 5,
            "last_activity": "2024-01-01T12:00:00Z",
        }
        mock_core_memory_service.get_memory_stats.return_value = mock_stats

        result = await memory_service.get_memory_stats(user_id)

        # Verify core service was called
        mock_core_memory_service.get_memory_stats.assert_called_once_with(
            user_id=user_id
        )
        assert result == mock_stats

    @pytest.mark.asyncio
    async def test_clear_user_memory_delegates_to_core_service(
        self, memory_service, mock_core_memory_service
    ):
        """Test that clear_user_memory delegates to core service."""
        user_id = str(uuid4())
        confirm = True

        # Mock core service response
        mock_response = {"cleared": True, "count": 15}
        mock_core_memory_service.clear_user_memory.return_value = mock_response

        result = await memory_service.clear_user_memory(user_id, confirm)

        # Verify core service was called
        mock_core_memory_service.clear_user_memory.assert_called_once_with(
            user_id=user_id, confirm=confirm
        )
        assert result == mock_response


class TestMemoryServiceDependencyInjection:
    """Test MemoryService dependency injection functionality."""

    @pytest.mark.asyncio
    async def test_get_memory_service_creates_instance(self):
        """Test that get_memory_service creates MemoryService with proper dependencies."""
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

        # Mock core service to return False (not found)
        memory_service.core_memory_service.delete_memory.return_value = False

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
            "success": False,
            "error": "No messages to store",
        }

        result = await memory_service.add_conversation_memory(user_id, messages, None)

        # Verify core service was still called (validation happens at core level)
        memory_service.core_memory_service.add_conversation_memory.assert_called_once_with(
            user_id=user_id, messages=messages, session_id=None
        )

    @pytest.mark.asyncio
    async def test_empty_query_handled_correctly(self, memory_service):
        """Test that empty search query is handled correctly."""
        user_id = str(uuid4())
        query = ""

        # Mock core service response
        memory_service.core_memory_service.search_memories.return_value = []

        result = await memory_service.search_memories(user_id, query, 10)

        # Verify core service was called (validation happens at core level)
        memory_service.core_memory_service.search_memories.assert_called_once_with(
            user_id=user_id, query=query, limit=10
        )
        assert result == []