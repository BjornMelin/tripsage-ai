"""
Comprehensive tests for MemoryService.

This module provides full test coverage for memory management operations
including memory storage, retrieval, search, and AI-powered contextual understanding.
Tests use actual domain models with proper mocking and async patterns.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from tripsage_core.services.business.memory_service import (
    ConversationMemoryRequest,
    MemorySearchRequest,
    MemoryService,
    PreferencesUpdateRequest,
    UserContextResponse,
    get_memory_service,
)


class TestMemoryService:
    """Test suite for MemoryService."""

    @pytest.fixture
    def mock_database_service(self):
        """Mock database service with comprehensive memory operations."""
        db = AsyncMock()
        # Set up default return values
        db.create_memory = AsyncMock()
        db.get_memory_by_id = AsyncMock()
        db.get_memories_by_filters = AsyncMock(return_value=[])
        db.update_memory = AsyncMock()
        db.delete_memory = AsyncMock(return_value=True)
        db.get_user_memory_stats = AsyncMock(
            return_value={
                "total_memories": 0,
                "memory_types": {},
            }
        )
        return db

    @pytest.fixture
    def mock_mem0_client(self):
        """Mock Mem0 client."""
        mem0 = MagicMock()
        mem0.add = MagicMock()
        mem0.search = MagicMock(return_value=[])
        mem0.update = MagicMock()
        mem0.delete = MagicMock()
        mem0.get = MagicMock()
        return mem0

    @pytest.fixture
    def memory_service(self, mock_mem0_client):
        """Create MemoryService instance with mocked dependencies."""
        service = MemoryService()
        service.memory = mock_mem0_client
        service._connected = True
        return service

    @pytest.fixture
    def sample_conversation_request(self):
        """Sample conversation memory request."""
        return ConversationMemoryRequest(
            messages=[
                {
                    "role": "user",
                    "content": "I prefer boutique hotels in historic city centers",
                },
                {
                    "role": "assistant",
                    "content": (
                        "I'll remember your preference for boutique hotels "
                        "in historic areas."
                    ),
                },
            ],
            session_id=str(uuid4()),
            trip_id=str(uuid4()),
            metadata={
                "location": "Europe",
                "category": "accommodation",
                "tags": ["hotels", "boutique", "historic", "preferences"],
            },
        )

    @pytest.mark.asyncio
    async def test_add_conversation_memory_success(
        self,
        memory_service,
        mock_mem0_client,
        sample_conversation_request,
    ):
        """Test successful conversation memory addition."""
        user_id = str(uuid4())

        # Mock Mem0 response
        mock_mem0_client.add.return_value = {
            "results": [
                {
                    "id": "mem0_abc123",
                    "memory": "User prefers boutique hotels in historic city centers",
                    "metadata": {
                        "domain": "travel_planning",
                        "session_id": sample_conversation_request.session_id,
                    },
                }
            ],
            "usage": {"total_tokens": 150},
        }

        result = await memory_service.add_conversation_memory(
            user_id, sample_conversation_request
        )

        # Assertions
        assert "results" in result
        assert len(result["results"]) == 1
        assert result["results"][0]["id"] == "mem0_abc123"
        assert "boutique hotels" in result["results"][0]["memory"]

        # Verify service calls
        mock_mem0_client.add.assert_called_once()
        call_args = mock_mem0_client.add.call_args
        assert call_args[1]["user_id"] == user_id
        assert call_args[1]["messages"] == sample_conversation_request.messages

    @pytest.mark.asyncio
    async def test_search_memories_success(self, memory_service, mock_mem0_client):
        """Test successful memory search."""
        user_id = str(uuid4())

        search_request = MemorySearchRequest(
            query="hotel preferences",
            limit=10,
        )

        # Mock Mem0 search response
        mock_mem0_client.search.return_value = [
            {
                "id": "mem0_123",
                "memory": "User prefers boutique hotels",
                "metadata": {
                    "categories": ["accommodation", "preferences"],
                    "created_at": datetime.now(timezone.utc).isoformat(),
                },
                "similarity": 0.92,
            }
        ]

        results = await memory_service.search_memories(user_id, search_request)

        assert len(results) == 1
        assert results[0].id == "mem0_123"
        assert results[0].similarity == 0.92
        assert "boutique hotels" in results[0].memory

        mock_mem0_client.search.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_context_success(self, memory_service, mock_mem0_client):
        """Test successful user context retrieval."""
        user_id = str(uuid4())

        # Mock comprehensive memory search
        mock_mem0_client.search.side_effect = [
            # Preferences
            [
                {
                    "memory": "Prefers boutique hotels",
                    "metadata": {"category": "accommodation"},
                }
            ],
            # Past trips
            [
                {
                    "memory": "Visited Tokyo in 2023",
                    "metadata": {"trip_date": "2023-05"},
                }
            ],
            # Other categories
            [],  # saved destinations
            [],  # budget patterns
            [],  # travel style
            [],  # dietary
            [],  # accommodation prefs
            [],  # activity prefs
        ]

        result = await memory_service.get_user_context(user_id)

        assert isinstance(result, UserContextResponse)
        assert len(result.preferences) == 1
        assert len(result.past_trips) == 1
        assert "Travel Context Summary" in result.summary

        # Verify multiple search calls were made
        assert mock_mem0_client.search.call_count >= 2

    @pytest.mark.asyncio
    async def test_update_preferences_success(self, memory_service, mock_mem0_client):
        """Test successful preferences update."""
        user_id = str(uuid4())

        update_request = PreferencesUpdateRequest(
            preferences={
                "accommodation_type": "boutique_hotel",
                "budget_range": "medium",
                "travel_style": "cultural",
            },
            category="travel_preferences",
        )

        # Mock existing preferences search
        mock_mem0_client.search.return_value = [
            {
                "id": "mem0_pref_123",
                "memory": "Old preferences",
                "metadata": {"category": "travel_preferences"},
            }
        ]

        # Mock update
        mock_mem0_client.update.return_value = {"success": True}

        # Mock add for new preference
        mock_mem0_client.add.return_value = {
            "results": [{"id": "mem0_new_pref", "memory": "Updated preferences"}]
        }

        result = await memory_service.update_preferences(user_id, update_request)

        assert result["success"] is True
        assert "preferences_updated" in result

    @pytest.mark.asyncio
    async def test_memory_service_connection_failure(self, mock_mem0_client):
        """Test memory service connection failure handling."""
        memory_service = MemoryService()
        memory_service.memory = mock_mem0_client

        # Mock connection failure
        mock_mem0_client.search.side_effect = Exception("Connection failed")

        # Should handle connection failure gracefully
        await memory_service.connect()
        assert not memory_service._connected

    @pytest.mark.asyncio
    async def test_cache_invalidation(
        self, memory_service, mock_mem0_client, sample_conversation_request
    ):
        """Test cache invalidation after memory updates."""
        user_id = str(uuid4())

        # First search (should cache)
        search_request = MemorySearchRequest(query="hotels", limit=5)
        mock_mem0_client.search.return_value = [
            {"id": "mem0_1", "memory": "Old hotel preference"}
        ]

        results1 = await memory_service.search_memories(user_id, search_request)
        assert len(results1) == 1

        # Add new memory (should invalidate cache)
        mock_mem0_client.add.return_value = {"results": [{"id": "mem0_2"}]}
        await memory_service.add_conversation_memory(
            user_id, sample_conversation_request
        )

        # Second search (should not use cache)
        mock_mem0_client.search.return_value = [
            {"id": "mem0_1", "memory": "Old hotel preference"},
            {"id": "mem0_2", "memory": "New hotel preference"},
        ]

        results2 = await memory_service.search_memories(user_id, search_request)
        assert len(results2) == 2

        # Verify search was called twice (not cached second time)
        assert mock_mem0_client.search.call_count == 2

    @pytest.mark.asyncio
    async def test_memory_extraction_error_handling(
        self, memory_service, mock_mem0_client, sample_conversation_request
    ):
        """Test error handling in memory extraction."""
        user_id = str(uuid4())

        # Mock extraction failure
        mock_mem0_client.add.side_effect = Exception("Extraction failed")

        result = await memory_service.add_conversation_memory(
            user_id, sample_conversation_request
        )

        assert "error" in result
        assert result["results"] == []
        assert "Extraction failed" in result["error"]

    @pytest.mark.asyncio
    async def test_get_memory_service_dependency(self):
        """Test the dependency injection function."""
        with patch(
            "tripsage_core.services.business.memory_service.MemoryService"
        ) as MockMemoryService:
            mock_instance = MagicMock()
            MockMemoryService.return_value = mock_instance

            service = await get_memory_service()
            assert service == mock_instance

    @pytest.mark.asyncio
    async def test_search_with_filters(self, memory_service, mock_mem0_client):
        """Test memory search with various filters."""
        user_id = str(uuid4())

        search_request = MemorySearchRequest(
            query="travel preferences",
            limit=20,
            filters={
                "categories": ["preferences", "travel"],
                "date_range": {
                    "start": (
                        datetime.now(timezone.utc) - timedelta(days=30)
                    ).isoformat(),
                    "end": datetime.now(timezone.utc).isoformat(),
                },
            },
            similarity_threshold=0.8,
        )

        mock_mem0_client.search.return_value = []

        results = await memory_service.search_memories(user_id, search_request)

        assert results == []

        # Verify filters were passed
        call_args = mock_mem0_client.search.call_args
        assert call_args[1]["query"] == "travel preferences"
        assert call_args[1]["limit"] == 20

    @pytest.mark.asyncio
    async def test_memory_service_not_connected(self, memory_service):
        """Test operations when memory service is not connected."""
        memory_service._connected = False

        user_id = str(uuid4())
        search_request = MemorySearchRequest(query="test")

        # Should return empty results when not connected
        results = await memory_service.search_memories(user_id, search_request)
        assert results == []

        # Should return error in conversation memory
        conversation_request = ConversationMemoryRequest(messages=[])
        result = await memory_service.add_conversation_memory(
            user_id, conversation_request
        )
        assert result["error"] == "Memory service not available"

    @pytest.mark.asyncio
    async def test_travel_context_enrichment(self, memory_service, mock_mem0_client):
        """Test travel-specific context enrichment."""
        user_id = str(uuid4())

        # Search with travel context
        mock_mem0_client.search.return_value = [
            {
                "id": "mem0_travel_1",
                "memory": "Loves exploring local markets",
                "metadata": {
                    "travel_context": {
                        "destinations": ["Bangkok", "Marrakech"],
                        "activity_type": "cultural",
                    }
                },
                "similarity": 0.85,
            }
        ]

        results = await memory_service.search_memories(
            user_id, MemorySearchRequest(query="market experiences")
        )

        assert len(results) == 1
        assert "travel_context" in results[0].metadata
        assert "Bangkok" in results[0].metadata["travel_context"]["destinations"]
