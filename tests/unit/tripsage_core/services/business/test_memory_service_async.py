"""
Comprehensive tests for the async-optimized memory service.

Tests cover:
- Native async operations
- Connection pooling
- DragonflyDB caching
- Batch operations
- Cache invalidation
- Performance improvements
"""

import asyncio
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch

import asyncpg
import pytest

from tripsage_core.exceptions import CoreServiceError
from tripsage_core.services.business.memory_service_async import (
    AsyncMemoryService,
    ConversationMemoryRequest,
    MemorySearchRequest,
    MemorySearchResult,
    PreferencesUpdateRequest,
    UserContextResponse,
    get_async_memory_service,
)

@pytest.fixture
async def mock_database_service():
    """Mock database service."""
    service = AsyncMock()
    service.execute_sql = AsyncMock(return_value=[])
    return service

@pytest.fixture
async def mock_cache_service():
    """Mock DragonflyDB cache service."""
    service = AsyncMock()
    service.get_json = AsyncMock(return_value=None)
    service.set_json = AsyncMock(return_value=True)
    service.mget = AsyncMock(return_value=[None] * 10)
    service.delete = AsyncMock(return_value=1)
    service.delete_pattern = AsyncMock(return_value=5)
    return service

@pytest.fixture
async def mock_pg_pool():
    """Mock asyncpg connection pool."""
    pool = AsyncMock(spec=asyncpg.Pool)
    conn = AsyncMock()
    pool.acquire = AsyncMock(
        return_value=AsyncMock(__aenter__=AsyncMock(return_value=conn))
    )
    return pool

@pytest.fixture
async def memory_service(mock_database_service, mock_cache_service, mock_pg_pool):
    """Create memory service with mocked dependencies."""
    with patch(
        "tripsage_core.services.business.memory_service_async.get_cache_service"
    ) as mock_get_cache:
        mock_get_cache.return_value = mock_cache_service

        service = AsyncMemoryService(
            database_service=mock_database_service,
            cache_ttl=300,
        )

        # Mock the asyncpg pool initialization
        with patch.object(service, "_init_pg_pool", return_value=mock_pg_pool):
            # Mock memory backend
            service.memory = Mock()
            service.memory.add = Mock(
                return_value={
                    "results": [{"id": "test-memory"}],
                    "usage": {"total_tokens": 100},
                }
            )
            service.memory.search = Mock(
                return_value={
                    "results": [
                        {
                            "id": "mem1",
                            "memory": "I love visiting Japan",
                            "metadata": {"type": "preference"},
                            "categories": ["travel", "destination"],
                            "score": 0.95,
                            "created_at": datetime.now(timezone.utc).isoformat(),
                        }
                    ]
                }
            )
            service.memory.get_all = Mock(return_value={"results": []})
            service.memory.delete = Mock()

            yield service

class TestAsyncMemoryService:
    """Test suite for AsyncMemoryService."""

    @pytest.mark.asyncio
    async def test_connect_initializes_resources(
        self, memory_service, mock_pg_pool, mock_cache_service
    ):
        """Test that connect properly initializes all resources."""
        # Act
        await memory_service.connect()

        # Assert
        assert memory_service._connected is True
        assert memory_service._pg_pool is not None
        assert memory_service._cache_service is not None

    @pytest.mark.asyncio
    async def test_close_releases_resources(self, memory_service, mock_pg_pool):
        """Test that close properly releases all resources."""
        # Arrange
        await memory_service.connect()
        memory_service._cache_keys = {"key1", "key2", "key3"}

        # Act
        await memory_service.close()

        # Assert
        assert memory_service._connected is False
        assert memory_service._pg_pool is None
        assert len(memory_service._cache_keys) == 0
        mock_pg_pool.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_conversation_memory_with_caching(self, memory_service):
        """Test adding conversation memory with cache invalidation."""
        # Arrange
        user_id = "test-user"
        memory_request = ConversationMemoryRequest(
            messages=[
                {"role": "user", "content": "I want to visit Tokyo"},
                {"role": "assistant", "content": "Tokyo is a great destination!"},
            ],
            session_id="test-session",
            trip_id="test-trip",
        )

        # Act
        result = await memory_service.add_conversation_memory(user_id, memory_request)

        # Assert
        assert result["results"][0]["id"] == "test-memory"
        assert result["usage"]["total_tokens"] == 100
        memory_service.memory.add.assert_called_once()

        # Verify metadata was enhanced
        call_args = memory_service.memory.add.call_args
        assert call_args[1]["metadata"]["domain"] == "travel_planning"
        assert call_args[1]["metadata"]["session_id"] == "test-session"
        assert call_args[1]["metadata"]["trip_id"] == "test-trip"

    @pytest.mark.asyncio
    async def test_search_memories_with_cache_hit(
        self, memory_service, mock_cache_service
    ):
        """Test memory search with DragonflyDB cache hit."""
        # Arrange
        user_id = "test-user"
        search_request = MemorySearchRequest(
            query="Japan travel", limit=10, similarity_threshold=0.8
        )

        cached_data = [
            {
                "id": "cached-mem1",
                "memory": "Cached memory about Japan",
                "metadata": {},
                "categories": ["travel"],
                "similarity": 0.9,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "user_id": user_id,
            }
        ]
        mock_cache_service.get_json.return_value = cached_data

        # Act
        results = await memory_service.search_memories(user_id, search_request)

        # Assert
        assert len(results) == 1
        assert results[0].id == "cached-mem1"
        assert results[0].memory == "Cached memory about Japan"
        # Should not call the memory backend
        memory_service.memory.search.assert_not_called()

    @pytest.mark.asyncio
    async def test_search_memories_with_cache_miss(
        self, memory_service, mock_cache_service
    ):
        """Test memory search with cache miss and DragonflyDB storage."""
        # Arrange
        user_id = "test-user"
        search_request = MemorySearchRequest(
            query="Tokyo restaurants", limit=5, similarity_threshold=0.7
        )
        mock_cache_service.get_json.return_value = None  # Cache miss

        # Act
        results = await memory_service.search_memories(user_id, search_request)

        # Assert
        assert len(results) == 1
        assert results[0].id == "mem1"
        assert results[0].memory == "I love visiting Japan"
        assert results[0].similarity == 0.95

        # Verify caching
        mock_cache_service.set_json.assert_called_once()
        cache_call = mock_cache_service.set_json.call_args
        assert cache_call[0][1][0]["id"] == "mem1"  # Cached result
        assert cache_call[1]["ttl"] == 300  # Cache TTL

    @pytest.mark.asyncio
    async def test_search_memories_batch(self, memory_service, mock_cache_service):
        """Test batch memory search with mixed cache hits/misses."""
        # Arrange
        user_queries = [
            ("user1", MemorySearchRequest(query="Tokyo", limit=5)),
            ("user2", MemorySearchRequest(query="Paris", limit=5)),
            ("user3", MemorySearchRequest(query="London", limit=5)),
        ]

        # Mock cache responses: user1 hit, user2 and user3 miss
        mock_cache_service.mget.return_value = [
            json.dumps(
                [
                    {
                        "id": "cached1",
                        "memory": "Tokyo trip",
                        "metadata": {},
                        "categories": [],
                        "similarity": 0.9,
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "user_id": "user1",
                    }
                ]
            ),
            None,
            None,
        ]

        # Act
        results = await memory_service.search_memories_batch(user_queries)

        # Assert
        assert len(results) == 3
        assert len(results["user1"]) == 1
        assert results["user1"][0].id == "cached1"
        assert len(results["user2"]) == 1  # From memory backend
        assert len(results["user3"]) == 1  # From memory backend

    @pytest.mark.asyncio
    async def test_get_user_context_with_caching(
        self, memory_service, mock_cache_service
    ):
        """Test getting user context with DragonflyDB caching."""
        # Arrange
        user_id = "test-user"
        memory_service.memory.get_all.return_value = {
            "results": [
                {
                    "id": "pref1",
                    "memory": "I prefer luxury hotels",
                    "categories": ["accommodation_preferences"],
                },
                {
                    "id": "budget1",
                    "memory": "My budget is usually $3000",
                    "categories": ["budget_patterns"],
                },
            ]
        }

        # Act
        context = await memory_service.get_user_context(user_id)

        # Assert
        assert isinstance(context, UserContextResponse)
        assert len(context.accommodation_preferences) == 1
        assert len(context.budget_patterns) == 1
        assert "Average budget: $3000" in context.summary

        # Verify caching
        mock_cache_service.set_json.assert_called()
        cache_call = mock_cache_service.set_json.call_args
        assert cache_call[0][0] == f"user_context:{user_id}:all"
        assert cache_call[1]["ttl"] == 600  # Double TTL for context

    @pytest.mark.asyncio
    async def test_delete_user_memories_batch(self, memory_service):
        """Test batch deletion of user memories."""
        # Arrange
        user_id = "test-user"
        memory_ids = ["mem1", "mem2", "mem3", "mem4", "mem5"]

        # Mock all deletions as successful
        memory_service.memory.delete.return_value = None

        # Act
        result = await memory_service.delete_user_memories(user_id, memory_ids)

        # Assert
        assert result["success"] is True
        assert result["deleted_count"] == 5
        assert memory_service.memory.delete.call_count == 5

    @pytest.mark.asyncio
    async def test_cache_key_generation_optimization(self, memory_service):
        """Test optimized cache key generation."""
        # Arrange
        user_id = "test-user-123"
        search_request = MemorySearchRequest(
            query="Tokyo travel tips",
            limit=10,
            similarity_threshold=0.8,
            filters={"category": "travel", "year": 2024},
        )

        # Act
        key1 = memory_service._generate_cache_key(user_id, search_request)
        key2 = memory_service._generate_cache_key(user_id, search_request)

        # Same request should generate same key
        assert key1 == key2
        assert key1.startswith("mem:")
        assert len(key1) == 20  # "mem:" + 16 chars

        # Different filter should generate different key
        search_request.filters["year"] = 2025
        key3 = memory_service._generate_cache_key(user_id, search_request)
        assert key3 != key1

    @pytest.mark.asyncio
    async def test_async_cache_invalidation(self, memory_service, mock_cache_service):
        """Test async cache invalidation for user."""
        # Arrange
        user_id = "test-user"
        memory_service._cache_keys = {
            "mem:abc123",
            "mem:def456",
            f"mem:user-{user_id}-search1",
            f"mem:user-{user_id}-search2",
            "mem:other-user-search",
        }

        # Act
        await memory_service._invalidate_user_cache_async(user_id)

        # Assert
        # Should only delete user-specific keys
        assert len(memory_service._cache_keys) == 3  # Other keys remain
        assert f"mem:user-{user_id}-search1" not in memory_service._cache_keys
        assert f"mem:user-{user_id}-search2" not in memory_service._cache_keys

        # Should also delete user context pattern
        mock_cache_service.delete_pattern.assert_called_with(
            f"user_context:{user_id}:*"
        )

    @pytest.mark.asyncio
    async def test_connection_pool_reuse(self, memory_service, mock_pg_pool):
        """Test that connection pool is reused across operations."""
        # Arrange
        await memory_service.connect()

        # Act
        pool1 = await memory_service._init_pg_pool()
        pool2 = await memory_service._init_pg_pool()

        # Assert
        assert pool1 is pool2  # Same instance
        assert pool1 is mock_pg_pool

    @pytest.mark.asyncio
    async def test_memory_enrichment(self, memory_service):
        """Test travel memory enrichment."""
        # Arrange
        memories = [
            MemorySearchResult(
                id="1",
                memory="I want to visit Tokyo and stay at a luxury hotel",
                metadata={},
                categories=[],
                similarity=0.9,
                created_at=datetime.now(timezone.utc),
                user_id="test",
            ),
            MemorySearchResult(
                id="2",
                memory="My budget for the trip is $5000",
                metadata={},
                categories=[],
                similarity=0.8,
                created_at=datetime.now(timezone.utc),
                user_id="test",
            ),
        ]

        # Act
        enriched = await memory_service._enrich_travel_memories(memories)

        # Assert
        assert enriched[0].metadata["has_location"] is True
        assert enriched[0].metadata["has_accommodation"] is True
        assert enriched[1].metadata["has_budget"] is True

    @pytest.mark.asyncio
    async def test_error_handling_with_fallback(self, memory_service):
        """Test error handling with fallback to direct implementation."""
        # Arrange
        user_id = "test-user"
        memory_service.memory = None  # No Mem0 available

        search_request = MemorySearchRequest(query="test", limit=5)

        # Act
        results = await memory_service.search_memories(user_id, search_request)

        # Assert
        assert isinstance(results, list)
        # Should use direct implementation (currently returns empty)
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_performance_improvements(self, memory_service, mock_cache_service):
        """Test that async operations provide performance improvements."""
        import time

        # Arrange
        user_id = "perf-test-user"
        search_requests = [
            MemorySearchRequest(query=f"query-{i}", limit=5) for i in range(10)
        ]

        # Ensure all are cache misses
        mock_cache_service.get_json.return_value = None

        # Mock memory.search to be "slow"
        async def slow_search(*args, **kwargs):
            await asyncio.sleep(0.1)  # Simulate 100ms latency
            return {
                "results": [
                    {
                        "id": f"mem-{kwargs.get('query', 'test')}",
                        "memory": "Test memory",
                        "metadata": {},
                        "categories": [],
                        "score": 0.9,
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    }
                ]
            }

        # Replace with async mock
        memory_service.memory.search = AsyncMock(side_effect=slow_search)

        # Act - Parallel execution
        start_time = time.time()
        tasks = [
            memory_service.search_memories(user_id, req) for req in search_requests
        ]
        results = await asyncio.gather(*tasks)
        parallel_time = time.time() - start_time

        # Assert
        assert len(results) == 10
        # Parallel execution should take ~100ms (not 1000ms)
        assert parallel_time < 0.5  # Allow some overhead

    @pytest.mark.asyncio
    async def test_connection_failure_handling(self, memory_service):
        """Test graceful handling of connection failures."""
        # Arrange
        memory_service._init_pg_pool = AsyncMock(
            side_effect=asyncpg.PostgresError("Connection failed")
        )

        # Act & Assert
        with pytest.raises(CoreServiceError) as exc_info:
            await memory_service.connect()

        assert "Failed to connect async memory service" in str(exc_info.value)
        assert not memory_service._connected

class TestAsyncMemoryServiceIntegration:
    """Integration tests for async memory service."""

    @pytest.mark.asyncio
    async def test_full_memory_lifecycle(self, memory_service, mock_cache_service):
        """Test complete memory lifecycle: add, search, update, delete."""
        user_id = "lifecycle-test-user"

        # 1. Add conversation memory
        conv_request = ConversationMemoryRequest(
            messages=[
                {"role": "user", "content": "I love sushi and want to visit Japan"},
                {"role": "assistant", "content": "Japan is perfect for sushi lovers!"},
            ],
            session_id="session-1",
        )
        add_result = await memory_service.add_conversation_memory(user_id, conv_request)
        assert add_result["results"]

        # 2. Search for memories
        search_request = MemorySearchRequest(query="sushi Japan", limit=5)
        search_results = await memory_service.search_memories(user_id, search_request)
        assert len(search_results) > 0

        # 3. Update preferences
        pref_request = PreferencesUpdateRequest(
            preferences={"cuisine": "Japanese", "accommodation": "Ryokan"},
            category="travel_preferences",
        )
        pref_result = await memory_service.update_user_preferences(
            user_id, pref_request
        )
        assert pref_result.get("results") is not None

        # 4. Get user context
        context = await memory_service.get_user_context(user_id)
        assert isinstance(context, UserContextResponse)

        # 5. Delete memories
        delete_result = await memory_service.delete_user_memories(user_id)
        assert delete_result["success"] is True

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, memory_service):
        """Test handling of concurrent operations."""
        users = [f"concurrent-user-{i}" for i in range(5)]

        # Create tasks for different operations
        tasks = []
        for user in users:
            # Add memory
            tasks.append(
                memory_service.add_conversation_memory(
                    user,
                    ConversationMemoryRequest(
                        messages=[{"role": "user", "content": f"Test for {user}"}]
                    ),
                )
            )
            # Search memory
            tasks.append(
                memory_service.search_memories(
                    user, MemorySearchRequest(query="test", limit=5)
                )
            )
            # Get context
            tasks.append(memory_service.get_user_context(user))

        # Execute all concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Verify no exceptions
        exceptions = [r for r in results if isinstance(r, Exception)]
        assert len(exceptions) == 0

@pytest.mark.asyncio
async def test_get_async_memory_service():
    """Test the dependency injection function."""
    service = await get_async_memory_service()
    assert isinstance(service, AsyncMemoryService)
