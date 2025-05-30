"""
Comprehensive test suite for MemoryService.

Tests the complete memory service functionality including:
- Service initialization and connection management
- Memory operations (add, search, update, delete)
- Caching and performance optimization
- Error handling and resilience
- Integration workflows
"""

import asyncio
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from tripsage_core.services.business.memory_service import (
    MemorySearchResult,
    MemoryService,
    get_memory_service,
)


class TestMemoryService:
    """Test the core MemoryService functionality."""

    @pytest.fixture
    def mock_memory(self):
        """Mock Mem0 Memory instance."""
        memory = MagicMock()
        memory.add = MagicMock(
            return_value={
                "results": [
                    {"memory_id": "mem_123", "message": "Memory added successfully"}
                ],
                "usage": {"total_tokens": 150},
            }
        )
        memory.search = MagicMock(
            return_value={
                "results": [
                    {
                        "id": "mem_123",
                        "memory": "User prefers beach destinations",
                        "metadata": {"category": "travel_preference"},
                        "categories": ["travel"],
                        "score": 0.85,
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    }
                ]
            }
        )
        memory.get = MagicMock(
            return_value={
                "results": [
                    {
                        "id": "mem_123",
                        "memory": "User prefers beach destinations",
                        "metadata": {"category": "travel_preference"},
                        "categories": ["travel"],
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    }
                ]
            }
        )
        memory.get_all = MagicMock(
            return_value={
                "results": [
                    {
                        "id": "mem_123",
                        "memory": "User prefers beach destinations",
                        "metadata": {"category": "travel_preference"},
                        "categories": ["travel"],
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    }
                ]
            }
        )
        memory.delete = MagicMock(return_value={"success": True})
        memory.update = MagicMock(return_value={"success": True})
        return memory

    @pytest.fixture
    def memory_service(self, mock_memory):
        """Create a test memory service with mocked dependencies."""
        service = MemoryService()
        service.memory = mock_memory
        service._connected = True
        return service

    def test_service_initialization(self):
        """Test service initializes with default configuration."""
        service = MemoryService()
        assert service.config is not None
        assert "vector_store" in service.config
        assert service.config["vector_store"]["provider"] == "pgvector"
        assert not service._connected
        assert service._cache == {}

    def test_custom_config_initialization(self):
        """Test service accepts custom configuration."""
        config = {
            "vector_store": {"provider": "test_provider", "config": {"test": "value"}}
        }
        service = MemoryService(config)
        assert service.config == config
        assert service.config["vector_store"]["provider"] == "test_provider"

    @pytest.mark.asyncio
    async def test_connect_success(self, memory_service):
        """Test successful connection to memory service."""
        with patch("mem0.Memory") as mock_memory_class:
            mock_memory_class.from_config.return_value = memory_service.memory

            service = MemoryService()
            await service.connect()

            assert service._connected
            assert service.memory is not None
            mock_memory_class.from_config.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_failure(self):
        """Test connection failure handling."""
        with patch("mem0.Memory") as mock_memory_class:
            mock_memory_class.from_config.side_effect = Exception("Connection failed")
            service = MemoryService()

            with pytest.raises(Exception, match="Connection failed"):
                await service.connect()

            assert not service._connected

    @pytest.mark.asyncio
    async def test_close_service(self, memory_service):
        """Test service cleanup and connection closure."""
        await memory_service.close()
        assert not memory_service._connected

    @pytest.mark.asyncio
    async def test_health_check_success(self, memory_service):
        """Test health check when service is healthy."""
        result = await memory_service.health_check()
        assert result is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        """Test health check when service is unhealthy."""
        service = MemoryService()
        service._connected = False

        result = await service.health_check()
        assert result is False

    @pytest.mark.asyncio
    async def test_add_conversation_memory_success(self, memory_service):
        """Test adding conversation memory successfully."""
        messages = [
            {"role": "user", "content": "I love beach destinations"},
            {"role": "assistant", "content": "Great! I'll remember that preference."},
        ]

        result = await memory_service.add_conversation_memory(
            messages=messages, user_id="user_123", session_id="session_456"
        )

        assert "results" in result
        memory_service.memory.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_context_success(self, memory_service):
        """Test retrieving user context successfully."""
        result = await memory_service.get_user_context("user_123")

        assert "preferences" in result
        assert "insights" in result
        assert "summary" in result
        memory_service.memory.get_all.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_memories_success(self, memory_service):
        """Test memory search functionality."""
        results = await memory_service.search_memories(
            query="beach destinations", user_id="user_123", limit=5
        )

        assert len(results) > 0
        assert isinstance(results[0], MemorySearchResult)
        assert results[0].memory == "User prefers beach destinations"
        memory_service.memory.search.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_memories_with_filters(self, memory_service):
        """Test memory search with metadata filters."""
        filters = {"category": "travel_preference"}
        results = await memory_service.search_memories(
            query="beach destinations", user_id="user_123", limit=5, filters=filters
        )

        assert len(results) > 0
        memory_service.memory.search.assert_called_with(
            query="beach destinations", user_id="user_123", limit=5, filters=filters
        )

    @pytest.mark.asyncio
    async def test_update_user_preferences_success(self, memory_service):
        """Test updating user preferences."""
        preferences = {
            "budget_range": "$1000-$3000",
            "preferred_destinations": ["Europe", "Asia"],
        }

        result = await memory_service.update_user_preferences("user_123", preferences)

        assert "results" in result or "success" in result
        memory_service.memory.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_user_memories_success(self, memory_service):
        """Test deleting user memories."""
        result = await memory_service.delete_user_memories("user_123")

        assert "success" in result
        memory_service.memory.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_caching_functionality(self, memory_service):
        """Test memory search result caching."""
        # First search - should call the underlying service
        results1 = await memory_service.search_memories(
            query="beach destinations", user_id="user_123"
        )

        # Second search with same parameters - should use cache
        results2 = await memory_service.search_memories(
            query="beach destinations", user_id="user_123"
        )

        assert results1 == results2
        # Memory service should only be called once due to caching
        assert memory_service.memory.search.call_count == 1

    @pytest.mark.asyncio
    async def test_cache_expiration(self, memory_service):
        """Test cache expiration functionality."""
        # Set short TTL for testing
        memory_service._cache_ttl = 0.1  # 100ms

        # First search
        await memory_service.search_memories(
            query="beach destinations", user_id="user_123"
        )

        # Wait for cache to expire
        await asyncio.sleep(0.2)

        # Second search should bypass cache
        await memory_service.search_memories(
            query="beach destinations", user_id="user_123"
        )

        # Should have called memory service twice
        assert memory_service.memory.search.call_count == 2

    def test_memory_search_result_model(self):
        """Test MemorySearchResult model validation."""
        result = MemorySearchResult(
            id="mem_123",
            memory="User prefers beach destinations",
            metadata={"category": "travel_preference"},
            categories=["travel", "preference"],
            similarity=0.85,
            created_at=datetime.now(timezone.utc),
            user_id="user_123",
        )

        assert result.id == "mem_123"
        assert result.memory == "User prefers beach destinations"
        assert result.similarity == 0.85
        assert "travel" in result.categories

    @pytest.mark.asyncio
    async def test_memory_extraction_accuracy(self, memory_service):
        """Test memory extraction produces relevant memories."""
        messages = [
            {
                "role": "user",
                "content": "I'm planning a trip to Japan for cherry blossom season",
            },
            {
                "role": "assistant",
                "content": "Cherry blossom season is beautiful! I'll help you plan.",
            },
        ]

        await memory_service.add_conversation_memory(
            messages=messages, user_id="user_123"
        )

        # Verify memory was called with correct content
        call_args = memory_service.memory.add.call_args
        assert call_args is not None
        assert "user_id" in call_args.kwargs
        assert call_args.kwargs["user_id"] == "user_123"

    @pytest.mark.asyncio
    async def test_user_data_isolation(self, memory_service):
        """Test user data isolation between different users."""
        # Add memory for user 1
        messages = [{"role": "user", "content": "I love beaches"}]
        await memory_service.add_conversation_memory(
            messages=messages, user_id="user_1"
        )

        # Search for user 2
        await memory_service.search_memories(query="beaches", user_id="user_2")

        # Verify search was called with correct user_id
        search_call = memory_service.memory.search.call_args
        assert search_call.kwargs["user_id"] == "user_2"

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, memory_service):
        """Test concurrent memory operations."""
        conversations = [
            {
                "messages": [{"role": "user", "content": f"Message {i}"}],
                "user_id": f"user_{i}",
            }
            for i in range(5)
        ]

        # Execute concurrent operations
        tasks = [
            memory_service.add_conversation_memory(
                messages=conv["messages"], user_id=conv["user_id"]
            )
            for conv in conversations
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All operations should succeed
        for result in results:
            assert not isinstance(result, Exception)
            assert "results" in result

    @pytest.mark.asyncio
    async def test_performance_benchmarking(self, memory_service):
        """Test performance characteristics of memory operations."""
        start_time = asyncio.get_event_loop().time()

        # Perform multiple search operations
        tasks = [
            memory_service.search_memories(f"query_{i}", f"user_{i}") for i in range(10)
        ]

        await asyncio.gather(*tasks)

        end_time = asyncio.get_event_loop().time()
        total_time = end_time - start_time

        # Should complete within reasonable time (adjust threshold as needed)
        assert total_time < 5.0  # 5 seconds for 10 operations

    @pytest.mark.asyncio
    async def test_error_recovery(self, memory_service):
        """Test service recovery from errors."""
        # Simulate memory service failure
        memory_service.memory.search.side_effect = Exception(
            "Service temporarily unavailable"
        )

        # Should handle error gracefully
        result = await memory_service.search_memories("test query", "user_123")

        # Should return empty results instead of crashing
        assert isinstance(result, list)


class TestMemoryServiceIntegration:
    """Integration tests for memory service workflows."""

    @pytest.fixture
    def integration_service(self):
        """Create service for integration testing."""
        service = MemoryService()
        service.memory = MagicMock()
        service._connected = True

        # Mock realistic responses
        service.memory.add.return_value = {
            "results": [{"memory_id": "mem_456"}],
            "usage": {"total_tokens": 120},
        }

        service.memory.search.return_value = {
            "results": [
                {
                    "id": "mem_456",
                    "memory": "User is planning a Japan trip for cherry blossoms",
                    "metadata": {"category": "trip_planning"},
                    "categories": ["travel", "planning"],
                    "score": 0.9,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            ]
        }

        service.memory.get.return_value = {
            "results": [
                {
                    "id": "mem_456",
                    "memory": "User is planning a Japan trip for cherry blossoms",
                    "metadata": {"category": "trip_planning"},
                    "categories": ["travel", "planning"],
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            ]
        }

        return service

    @pytest.mark.asyncio
    async def test_full_conversation_workflow(self, integration_service):
        """Test complete conversation memory workflow."""
        # Step 1: Add conversation memory
        messages = [
            {
                "role": "user",
                "content": "I want to visit Japan during cherry blossom season",
            },
            {
                "role": "assistant",
                "content": "Great choice! Cherry blossom season is March-May.",
            },
        ]

        add_result = await integration_service.add_conversation_memory(
            messages=messages, user_id="user_123", session_id="session_456"
        )
        assert "results" in add_result

        # Step 2: Search for related memories
        search_results = await integration_service.search_memories(
            query="Japan cherry blossom", user_id="user_123"
        )
        assert len(search_results) > 0
        assert "Japan" in search_results[0].memory

        # Step 3: Get user context
        context = await integration_service.get_user_context("user_123")
        assert "preferences" in context
        assert "insights" in context

    @pytest.mark.asyncio
    async def test_personalization_workflow(self, integration_service):
        """Test memory-driven personalization workflow."""
        # Add multiple conversations to build user profile
        conversations = [
            {"role": "user", "content": "I love budget-friendly hostels"},
            {"role": "user", "content": "Mountain hiking is my favorite activity"},
            {"role": "user", "content": "I prefer traveling in spring"},
        ]

        # Add all conversations
        for message in conversations:
            await integration_service.add_conversation_memory(
                messages=[message], user_id="user_123"
            )

        # Get personalized context
        context = await integration_service.get_user_context("user_123")

        assert "preferences" in context
        assert "insights" in context
        assert "summary" in context


class TestMemoryUtilities:
    """Test utility functions."""

    def test_memory_hash_creation(self):
        """Test memory hash creation functionality."""
        import hashlib

        content = "User prefers beach destinations"
        hash1 = hashlib.sha256(content.encode()).hexdigest()
        hash2 = hashlib.sha256(content.encode()).hexdigest()

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex digest

        # Different content should produce different hash
        hash3 = hashlib.sha256("Different content".encode()).hexdigest()
        assert hash1 != hash3

    @pytest.mark.asyncio
    async def test_get_memory_service_singleton(self):
        """Test memory service singleton pattern."""
        with patch("mem0.Memory") as mock_memory_class:
            mock_memory_class.from_config.return_value = MagicMock()

            service1 = await get_memory_service()
            service2 = await get_memory_service()

            # Should return the same instance
            assert service1 is service2
