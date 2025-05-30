"""
Comprehensive tests for TripSageMemoryService.

This module provides extensive testing for the Mem0-based memory service
including all methods, error handling, caching, and edge cases.
"""

import time
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from tripsage_core.services.core.memory_service import (
    ConversationMemory,
    MemorySearchResult,
    MemoryServiceAdapter,
    TripSageMemoryService,
    create_memory_hash,
    get_memory_service,
)


class TestTripSageMemoryService:
    """Comprehensive tests for TripSageMemoryService."""

    @pytest.fixture
    def mock_mem0_memory(self):
        """Mock Mem0 Memory client."""
        mock = MagicMock()
        mock.add = Mock()
        mock.search = Mock()
        mock.get_all = Mock()
        mock.delete = Mock()
        return mock

    @pytest.fixture
    def service(self, mock_mem0_memory):
        """Create a TripSageMemoryService instance with mocked dependencies."""
        with patch("tripsage.services.core.memory_service.Memory") as mock_memory_cls:
            mock_memory_cls.from_config.return_value = mock_mem0_memory

            service = TripSageMemoryService()
            service.memory = mock_mem0_memory
            service._connected = True
            return service

    @pytest.fixture
    def sample_messages(self):
        """Sample conversation messages for testing."""
        return [
            {"role": "user", "content": "I want to plan a trip to Japan"},
            {
                "role": "assistant",
                "content": "I'd love to help you plan your Japan trip! What's your budget and preferred travel dates?",
            },
            {
                "role": "user",
                "content": "My budget is around $3000 and I want to go in spring for cherry blossoms",
            },
        ]

    @pytest.fixture
    def sample_memory_results(self):
        """Sample memory search results."""
        return {
            "results": [
                {
                    "id": "mem_1",
                    "memory": "User prefers spring travel to see cherry blossoms",
                    "metadata": {"type": "preference", "location": "Japan"},
                    "categories": ["travel_preferences"],
                    "score": 0.95,
                    "created_at": "2024-01-15T10:00:00Z",
                },
                {
                    "id": "mem_2",
                    "memory": "User has a budget around $3000 for international trips",
                    "metadata": {"type": "budget", "amount": 3000},
                    "categories": ["budget_patterns"],
                    "score": 0.87,
                    "created_at": "2024-01-15T10:05:00Z",
                },
            ]
        }

    def test_initialization_default_config(self):
        """Test service initialization with default configuration."""
        service = TripSageMemoryService()
        assert service.config is not None
        assert service.config["vector_store"]["provider"] == "pgvector"
        assert service.config["llm"]["provider"] == "openai"
        assert service.config["embedder"]["provider"] == "openai"
        assert not service._connected
        assert service._cache == {}
        assert service._cache_ttl == 300

    def test_initialization_custom_config(self):
        """Test service initialization with custom configuration."""
        custom_config = {
            "vector_store": {"provider": "custom"},
            "llm": {"provider": "custom"},
            "embedder": {"provider": "custom"},
        }
        service = TripSageMemoryService(config=custom_config)
        assert service.config == custom_config

    def test_get_default_config(self):
        """Test default configuration generation."""
        service = TripSageMemoryService()
        config = service._get_default_config()

        assert config["vector_store"]["provider"] == "pgvector"
        assert config["vector_store"]["config"]["collection_name"] == "memories"
        assert config["llm"]["config"]["model"] == "gpt-4o-mini"
        assert config["embedder"]["config"]["model"] == "text-embedding-3-small"
        assert config["version"] == "v1.1"

    @pytest.mark.asyncio
    async def test_connect_success(self, mock_mem0_memory):
        """Test successful service connection."""
        with patch("tripsage.services.core.memory_service.Memory") as mock_memory_cls:
            mock_memory_cls.from_config.return_value = mock_mem0_memory

            service = TripSageMemoryService()
            await service.connect()

            assert service._connected
            assert service.memory == mock_mem0_memory
            mock_memory_cls.from_config.assert_called_once_with(service.config)

    @pytest.mark.asyncio
    async def test_connect_already_connected(self, service):
        """Test connection when already connected."""
        # Service is already connected from fixture
        assert service._connected

        # Should not reconnect
        with patch("tripsage.services.core.memory_service.Memory") as mock_memory_cls:
            await service.connect()
            mock_memory_cls.from_config.assert_not_called()

    @pytest.mark.asyncio
    async def test_connect_failure(self):
        """Test connection failure handling."""
        with patch("tripsage.services.core.memory_service.Memory") as mock_memory_cls:
            mock_memory_cls.from_config.side_effect = Exception("Connection failed")

            service = TripSageMemoryService()

            with pytest.raises(Exception, match="Connection failed"):
                await service.connect()

            assert not service._connected

    @pytest.mark.asyncio
    async def test_close_success(self, service):
        """Test successful service closure."""
        await service.close()

        assert not service._connected
        assert service._cache == {}

    @pytest.mark.asyncio
    async def test_close_not_connected(self):
        """Test closure when not connected."""
        service = TripSageMemoryService()
        assert not service._connected

        # Should not raise error
        await service.close()
        assert not service._connected

    def test_is_connected_property(self, service):
        """Test is_connected property."""
        assert service.is_connected

        service._connected = False
        assert not service.is_connected

    @pytest.mark.asyncio
    async def test_health_check_success(self, service):
        """Test successful health check."""
        service.memory.search.return_value = {"results": []}

        with patch("asyncio.to_thread") as mock_to_thread:
            mock_to_thread.return_value = {"results": []}

            result = await service.health_check()
            assert result is True
            mock_to_thread.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_check_not_connected(self, mock_mem0_memory):
        """Test health check when not connected."""
        with patch("tripsage.services.core.memory_service.Memory") as mock_memory_cls:
            mock_memory_cls.from_config.return_value = mock_mem0_memory

            service = TripSageMemoryService()
            assert not service._connected

            with patch("asyncio.to_thread") as mock_to_thread:
                mock_to_thread.return_value = {"results": []}

                result = await service.health_check()
                assert result is True
                assert service._connected

    @pytest.mark.asyncio
    async def test_health_check_failure(self, service):
        """Test health check failure."""
        with patch("asyncio.to_thread") as mock_to_thread:
            mock_to_thread.side_effect = Exception("Health check failed")

            result = await service.health_check()
            assert result is False

    @pytest.mark.asyncio
    async def test_add_conversation_memory_success(self, service, sample_messages):
        """Test successful conversation memory addition."""
        mock_result = {
            "results": [{"id": "mem_1", "memory": "Test memory"}],
            "usage": {"total_tokens": 150},
        }

        with patch("asyncio.to_thread") as mock_to_thread:
            mock_to_thread.return_value = mock_result

            result = await service.add_conversation_memory(
                messages=sample_messages,
                user_id="user_123",
                session_id="session_456",
                metadata={"test": "data"},
            )

            assert result == mock_result
            mock_to_thread.assert_called_once()

            # Verify the call arguments
            call_args = mock_to_thread.call_args
            assert call_args[0][0] == service.memory.add
            assert call_args[1]["messages"] == sample_messages
            assert call_args[1]["user_id"] == "user_123"

            # Check metadata enhancement
            metadata = call_args[1]["metadata"]
            assert metadata["domain"] == "travel_planning"
            assert metadata["session_id"] == "session_456"
            assert metadata["test"] == "data"

    @pytest.mark.asyncio
    async def test_add_conversation_memory_not_connected(self, sample_messages):
        """Test conversation memory addition when not connected."""
        service = TripSageMemoryService()

        with patch.object(service, "connect") as mock_connect:
            with patch("asyncio.to_thread") as mock_to_thread:
                mock_to_thread.return_value = {"results": []}

                await service.add_conversation_memory(
                    messages=sample_messages, user_id="user_123"
                )

                mock_connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_conversation_memory_failure(self, service, sample_messages):
        """Test conversation memory addition failure."""
        with patch("asyncio.to_thread") as mock_to_thread:
            mock_to_thread.side_effect = Exception("Memory add failed")

            result = await service.add_conversation_memory(
                messages=sample_messages, user_id="user_123"
            )

            assert result["results"] == []
            assert "error" in result
            assert "Memory add failed" in result["error"]

    @pytest.mark.asyncio
    async def test_search_memories_success(self, service, sample_memory_results):
        """Test successful memory search."""
        with patch("asyncio.to_thread") as mock_to_thread:
            mock_to_thread.return_value = sample_memory_results

            results = await service.search_memories(
                query="Japan travel",
                user_id="user_123",
                limit=5,
                similarity_threshold=0.3,
            )

            assert len(results) == 2
            assert all(isinstance(r, MemorySearchResult) for r in results)

            # Check first result
            first_result = results[0]
            assert first_result.id == "mem_1"
            assert (
                first_result.memory
                == "User prefers spring travel to see cherry blossoms"
            )
            assert first_result.similarity == 0.95
            assert first_result.user_id == "user_123"

    @pytest.mark.asyncio
    async def test_search_memories_with_caching(self, service, sample_memory_results):
        """Test memory search with caching."""
        # First search - should call the service
        with patch("asyncio.to_thread") as mock_to_thread:
            mock_to_thread.return_value = sample_memory_results

            results1 = await service.search_memories(
                query="Japan travel", user_id="user_123", limit=5
            )

            assert len(results1) == 2
            assert mock_to_thread.call_count == 1

            # Second search with same parameters - should use cache
            results2 = await service.search_memories(
                query="Japan travel", user_id="user_123", limit=5
            )

            assert len(results2) == 2
            # Should not call the service again
            assert mock_to_thread.call_count == 1

    @pytest.mark.asyncio
    async def test_search_memories_similarity_filtering(self, service):
        """Test memory search with similarity threshold filtering."""
        mock_results = {
            "results": [
                {
                    "id": "mem_1",
                    "memory": "High similarity result",
                    "metadata": {},
                    "categories": [],
                    "score": 0.9,
                    "created_at": "2024-01-15T10:00:00Z",
                },
                {
                    "id": "mem_2",
                    "memory": "Low similarity result",
                    "metadata": {},
                    "categories": [],
                    "score": 0.2,
                    "created_at": "2024-01-15T10:00:00Z",
                },
            ]
        }

        with patch("asyncio.to_thread") as mock_to_thread:
            mock_to_thread.return_value = mock_results

            results = await service.search_memories(
                query="test", user_id="user_123", similarity_threshold=0.5
            )

            # Only high similarity result should be returned
            assert len(results) == 1
            assert results[0].similarity == 0.9

    @pytest.mark.asyncio
    async def test_search_memories_mcp_fallback(self, service):
        """Test memory search with MCP fallback."""
        with patch("tripsage.services.core.memory_service.feature_flags") as mock_flags:
            mock_flags.get_integration_mode.return_value = "mcp"

            with patch.object(service, "_search_via_mcp") as mock_mcp_search:
                mock_mcp_search.return_value = []

                results = await service.search_memories(
                    query="test", user_id="user_123"
                )

                mock_mcp_search.assert_called_once()
                assert results == []

    @pytest.mark.asyncio
    async def test_search_memories_failure(self, service):
        """Test memory search failure handling."""
        with patch("asyncio.to_thread") as mock_to_thread:
            mock_to_thread.side_effect = Exception("Search failed")

            results = await service.search_memories(query="test", user_id="user_123")

            assert results == []

    @pytest.mark.asyncio
    async def test_get_user_context_success(self, service):
        """Test successful user context retrieval."""
        mock_memories = {
            "results": [
                {
                    "memory": "I prefer luxury hotels in Japan",
                    "categories": ["preferences"],
                    "metadata": {"type": "accommodation"},
                },
                {
                    "memory": "My budget for trips is usually $5000",
                    "categories": ["budget_patterns"],
                    "metadata": {"type": "budget"},
                },
                {
                    "memory": "I visited France last year",
                    "categories": ["past_trips"],
                    "metadata": {"destination": "France"},
                },
            ]
        }

        with patch("asyncio.to_thread") as mock_to_thread:
            mock_to_thread.return_value = mock_memories

            context = await service.get_user_context("user_123", limit=50)

            assert "preferences" in context
            assert "past_trips" in context
            assert "budget_patterns" in context
            assert "insights" in context
            assert "summary" in context

            # Check categorization
            assert len(context["preferences"]) >= 1
            assert len(context["budget_patterns"]) >= 1
            assert len(context["past_trips"]) >= 1

    @pytest.mark.asyncio
    async def test_get_user_context_failure(self, service):
        """Test user context retrieval failure."""
        with patch("asyncio.to_thread") as mock_to_thread:
            mock_to_thread.side_effect = Exception("Context retrieval failed")

            context = await service.get_user_context("user_123")

            # Should return default context structure
            assert "preferences" in context
            assert context["preferences"] == []
            assert "insights" in context
            assert context["summary"] == "New user with limited travel history"

    @pytest.mark.asyncio
    async def test_update_user_preferences_success(self, service):
        """Test successful user preferences update."""
        preferences = {
            "accommodation_type": "hotel",
            "budget_range": "luxury",
            "travel_style": "leisure",
        }

        mock_result = {"results": [{"id": "pref_1"}]}

        with patch.object(service, "add_conversation_memory") as mock_add:
            mock_add.return_value = mock_result

            result = await service.update_user_preferences("user_123", preferences)

            assert result == mock_result
            mock_add.assert_called_once()

            # Check the call arguments
            call_args = mock_add.call_args
            assert call_args[1]["user_id"] == "user_123"
            assert "preferences" in call_args[0][0][1]["content"]

    @pytest.mark.asyncio
    async def test_update_user_preferences_failure(self, service):
        """Test user preferences update failure."""
        with patch.object(service, "add_conversation_memory") as mock_add:
            mock_add.side_effect = Exception("Preferences update failed")

            result = await service.update_user_preferences("user_123", {})

            assert "error" in result
            assert "Preferences update failed" in result["error"]

    @pytest.mark.asyncio
    async def test_delete_user_memories_specific_ids(self, service):
        """Test deletion of specific memory IDs."""
        memory_ids = ["mem_1", "mem_2", "mem_3"]

        with patch("asyncio.to_thread") as mock_to_thread:
            mock_to_thread.return_value = None  # delete returns None

            result = await service.delete_user_memories("user_123", memory_ids)

            assert result["success"] is True
            assert result["deleted_count"] == 3
            assert mock_to_thread.call_count == 3

    @pytest.mark.asyncio
    async def test_delete_user_memories_all(self, service):
        """Test deletion of all user memories."""
        mock_all_memories = {"results": [{"id": "mem_1"}, {"id": "mem_2"}]}

        with patch("asyncio.to_thread") as mock_to_thread:
            # First call for get_all, then calls for delete
            mock_to_thread.side_effect = [mock_all_memories, None, None]

            result = await service.delete_user_memories("user_123")

            assert result["success"] is True
            assert result["deleted_count"] == 2
            assert mock_to_thread.call_count == 3

    @pytest.mark.asyncio
    async def test_delete_user_memories_failure(self, service):
        """Test memory deletion failure."""
        with patch("asyncio.to_thread") as mock_to_thread:
            mock_to_thread.side_effect = Exception("Deletion failed")

            result = await service.delete_user_memories("user_123", ["mem_1"])

            assert result["success"] is False
            assert "error" in result

    def test_cache_management(self, service):
        """Test cache management functionality."""
        # Test cache storage
        results = [
            MemorySearchResult(
                id="test_1",
                memory="test memory",
                similarity=0.9,
                created_at=datetime.now(timezone.utc),
                user_id="user_123",
            )
        ]

        cache_key = "test_key"
        service._cache_result(cache_key, results)

        # Test cache retrieval
        cached_result = service._get_cached_result(cache_key)
        assert cached_result == results

        # Test cache expiration
        service._cache[cache_key] = (results, time.time() - 400)  # Expired
        cached_result = service._get_cached_result(cache_key)
        assert cached_result is None
        assert cache_key not in service._cache

    def test_cache_size_management(self, service):
        """Test cache size management."""
        # Fill cache with many entries
        for i in range(1200):
            key = f"key_{i}"
            service._cache[key] = ([], time.time())

        # Add one more to trigger cleanup
        service._cache_result("final_key", [])

        # Should have removed 200 oldest entries
        assert len(service._cache) <= 1001

    def test_invalidate_user_cache(self, service):
        """Test user-specific cache invalidation."""
        # Add cache entries for different users
        service._cache["user_123:query1"] = ([], time.time())
        service._cache["user_123:query2"] = ([], time.time())
        service._cache["user_456:query1"] = ([], time.time())

        # Invalidate user_123's cache
        service._invalidate_user_cache("user_123")

        # Only user_456's cache should remain
        assert "user_123:query1" not in service._cache
        assert "user_123:query2" not in service._cache
        assert "user_456:query1" in service._cache

    @pytest.mark.asyncio
    async def test_enrich_travel_memories(self, service):
        """Test travel memory enrichment."""
        memories = [
            MemorySearchResult(
                id="mem_1",
                memory="I visited Tokyo, Japan last year and loved the hotels",
                metadata={},
                similarity=0.9,
                created_at=datetime.now(timezone.utc),
                user_id="user_123",
            ),
            MemorySearchResult(
                id="mem_2",
                memory="My budget for the trip was $3000",
                metadata={},
                similarity=0.8,
                created_at=datetime.now(timezone.utc),
                user_id="user_123",
            ),
        ]

        enriched = await service._enrich_travel_memories(memories)

        # Check enrichment flags
        assert enriched[0].metadata["has_location"] is True
        assert enriched[0].metadata["has_accommodation"] is True
        assert enriched[1].metadata["has_budget"] is True

    @pytest.mark.asyncio
    async def test_derive_travel_insights(self, service):
        """Test travel insights derivation."""
        context = {
            "past_trips": [
                {"memory": "I visited Japan last year"},
                {"memory": "France was amazing"},
            ],
            "budget_patterns": [
                {"memory": "I spent $5000 on my trip"},
                {"memory": "My budget is usually $3000"},
            ],
            "activity_preferences": [
                {"memory": "I love museums and cultural sites"},
                {"memory": "Beach activities are my favorite"},
            ],
        }

        insights = await service._derive_travel_insights(context)

        assert "preferred_destinations" in insights
        assert "budget_range" in insights
        assert "travel_frequency" in insights
        assert "preferred_activities" in insights
        assert "travel_style" in insights

    def test_analyze_destinations(self, service):
        """Test destination analysis."""
        context = {
            "past_trips": [
                {"memory": "I visited Japan last year"},
                {"memory": "France was amazing"},
            ],
            "saved_destinations": [{"memory": "I want to visit Italy next"}],
        }

        result = service._analyze_destinations(context)

        assert "most_visited" in result
        assert "destination_count" in result
        assert "Japan" in result["most_visited"]
        assert "France" in result["most_visited"]
        assert "Italy" in result["most_visited"]

    def test_analyze_budgets(self, service):
        """Test budget analysis."""
        context = {
            "budget_patterns": [
                {"memory": "I spent $5000 on my trip"},
                {"memory": "My budget is usually $3000"},
            ]
        }

        result = service._analyze_budgets(context)

        assert "average_budget" in result
        assert "max_budget" in result
        assert "min_budget" in result
        assert result["average_budget"] == 4000
        assert result["max_budget"] == 5000
        assert result["min_budget"] == 3000

    def test_analyze_budgets_no_data(self, service):
        """Test budget analysis with no data."""
        context = {"budget_patterns": []}

        result = service._analyze_budgets(context)

        assert result["budget_info"] == "No budget data available"

    def test_analyze_frequency(self, service):
        """Test travel frequency analysis."""
        context = {"past_trips": [{"memory": f"Trip {i}"} for i in range(6)]}

        result = service._analyze_frequency(context)

        assert result["total_trips"] == 6
        assert result["estimated_frequency"] == "Regular"

    def test_analyze_activities(self, service):
        """Test activity analysis."""
        context = {
            "activity_preferences": [
                {"memory": "I love museum visits"},
                {"memory": "Beach activities are fun"},
            ],
            "preferences": [{"memory": "Cultural experiences are important"}],
        }

        result = service._analyze_activities(context)

        assert "preferred_activities" in result
        assert "activity_style" in result
        assert "museum" in result["preferred_activities"]
        assert "beach" in result["preferred_activities"]
        assert result["activity_style"] == "Cultural"

    def test_analyze_travel_style(self, service):
        """Test travel style analysis."""
        context = {
            "preferences": [
                {"memory": "I prefer luxury hotels and expensive restaurants"},
                {"memory": "I usually travel with my family"},
            ]
        }

        result = service._analyze_travel_style(context)

        assert "travel_styles" in result
        assert "primary_style" in result
        assert "luxury" in result["travel_styles"]
        assert "family" in result["travel_styles"]
        assert result["primary_style"] == "luxury"

    def test_generate_context_summary(self, service):
        """Test context summary generation."""
        context = {
            "insights": {
                "preferred_destinations": {"most_visited": ["Japan", "France"]},
                "travel_style": {"primary_style": "luxury"},
                "budget_range": {"average_budget": 4500},
                "preferred_activities": {"preferred_activities": ["museum", "dining"]},
            }
        }

        summary = service._generate_context_summary(context)

        assert "Japan" in summary
        assert "luxury" in summary
        assert "$4500" in summary or "4500" in summary
        assert "museum" in summary

    def test_generate_context_summary_minimal(self, service):
        """Test context summary for new user."""
        context = {"insights": {}}

        summary = service._generate_context_summary(context)

        assert summary == "New user with limited travel history"

    @pytest.mark.asyncio
    async def test_search_via_mcp_placeholder(self, service):
        """Test MCP search fallback placeholder."""
        results = await service._search_via_mcp("test", "user_123", {}, 5)

        assert results == []


class TestMemoryServiceAdapter:
    """Tests for MemoryServiceAdapter."""

    @pytest.fixture
    def adapter(self):
        """Create a MemoryServiceAdapter instance."""
        return MemoryServiceAdapter()

    def test_initialization(self, adapter):
        """Test adapter initialization."""
        assert adapter.service_name == "memory"
        assert adapter._memory_service is None

    @pytest.mark.asyncio
    async def test_get_mcp_client_not_implemented(self, adapter):
        """Test that MCP client is not implemented."""
        with pytest.raises(NotImplementedError, match="MCP memory client deprecated"):
            await adapter.get_mcp_client()

    @pytest.mark.asyncio
    async def test_get_direct_service(self, adapter):
        """Test getting direct service instance."""
        with patch(
            "tripsage.services.core.memory_service.TripSageMemoryService"
        ) as mock_service_cls:
            mock_service = MagicMock()
            mock_service.connect = AsyncMock()
            mock_service_cls.return_value = mock_service

            service = await adapter.get_direct_service()

            assert service == mock_service
            mock_service.connect.assert_called_once()

            # Second call should return cached instance
            service2 = await adapter.get_direct_service()
            assert service2 == service
            assert mock_service.connect.call_count == 1


class TestMemoryModels:
    """Tests for memory-related models."""

    def test_memory_search_result_creation(self):
        """Test MemorySearchResult model creation."""
        result = MemorySearchResult(
            id="test_id",
            memory="test memory",
            metadata={"key": "value"},
            categories=["test"],
            similarity=0.95,
            created_at=datetime.now(timezone.utc),
            user_id="user_123",
        )

        assert result.id == "test_id"
        assert result.memory == "test memory"
        assert result.metadata == {"key": "value"}
        assert result.categories == ["test"]
        assert result.similarity == 0.95
        assert result.user_id == "user_123"

    def test_memory_search_result_defaults(self):
        """Test MemorySearchResult default values."""
        result = MemorySearchResult(
            id="test_id",
            memory="test memory",
            created_at=datetime.now(timezone.utc),
            user_id="user_123",
        )

        assert result.metadata == {}
        assert result.categories == []
        assert result.similarity == 0.0

    def test_conversation_memory_creation(self):
        """Test ConversationMemory model creation."""
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]

        conv_memory = ConversationMemory(
            messages=messages,
            user_id="user_123",
            session_id="session_456",
            metadata={"test": "data"},
        )

        assert conv_memory.messages == messages
        assert conv_memory.user_id == "user_123"
        assert conv_memory.session_id == "session_456"
        assert conv_memory.metadata == {"test": "data"}

    def test_conversation_memory_optional_fields(self):
        """Test ConversationMemory with optional fields."""
        messages = [{"role": "user", "content": "Hello"}]

        conv_memory = ConversationMemory(messages=messages, user_id="user_123")

        assert conv_memory.session_id is None
        assert conv_memory.metadata is None


class TestMemoryUtilities:
    """Tests for memory utility functions."""

    @pytest.mark.asyncio
    async def test_get_memory_service_singleton(self):
        """Test global memory service singleton."""
        with patch(
            "tripsage.services.core.memory_service.TripSageMemoryService"
        ) as mock_service_cls:
            mock_service = MagicMock()
            mock_service.connect = AsyncMock()
            mock_service_cls.return_value = mock_service

            # First call should create instance
            service1 = await get_memory_service()
            assert service1 == mock_service
            mock_service.connect.assert_called_once()

            # Second call should return same instance
            service2 = await get_memory_service()
            assert service2 == service1
            assert mock_service.connect.call_count == 1

    def test_create_memory_hash(self):
        """Test memory content hashing."""
        content1 = "This is test content"
        content2 = "This is different content"

        hash1 = create_memory_hash(content1)
        hash2 = create_memory_hash(content1)  # Same content
        hash3 = create_memory_hash(content2)  # Different content

        # Same content should produce same hash
        assert hash1 == hash2

        # Different content should produce different hash
        assert hash1 != hash3

        # Should be SHA-256 hex string
        assert len(hash1) == 64
        assert all(c in "0123456789abcdef" for c in hash1)


class TestMemoryServiceIntegration:
    """Integration-style tests for memory service functionality."""

    @pytest.fixture
    def configured_service(self):
        """Create a service with realistic configuration for integration tests."""
        config = {
            "vector_store": {
                "provider": "pgvector",
                "config": {
                    "host": "localhost",
                    "port": 5432,
                    "dbname": "test_db",
                    "user": "test_user",
                    "password": "test_pass",
                    "collection_name": "test_memories",
                },
            },
            "llm": {
                "provider": "openai",
                "config": {
                    "model": "gpt-4o-mini",
                    "temperature": 0.1,
                    "max_tokens": 500,
                },
            },
        }

        service = TripSageMemoryService(config=config)
        return service

    @pytest.mark.asyncio
    async def test_full_conversation_workflow(self, configured_service):
        """Test complete conversation memory workflow."""
        # Mock the Mem0 client
        mock_memory = MagicMock()
        configured_service.memory = mock_memory
        configured_service._connected = True

        # Mock conversation memory addition
        mock_memory.add.return_value = {
            "results": [{"id": "conv_mem_1", "memory": "User wants to visit Japan"}],
            "usage": {"total_tokens": 120},
        }

        # Mock memory search
        mock_memory.search.return_value = {
            "results": [
                {
                    "id": "conv_mem_1",
                    "memory": "User wants to visit Japan",
                    "metadata": {"domain": "travel_planning"},
                    "categories": ["preferences"],
                    "score": 0.92,
                    "created_at": "2024-01-15T10:00:00Z",
                }
            ]
        }

        # Mock context retrieval
        mock_memory.get_all.return_value = {
            "results": [
                {
                    "memory": "User wants to visit Japan in spring",
                    "categories": ["preferences"],
                    "metadata": {"season": "spring"},
                }
            ]
        }

        with patch("asyncio.to_thread") as mock_to_thread:
            # Setup side effects for different calls
            mock_to_thread.side_effect = [
                mock_memory.add.return_value,  # add_conversation_memory
                mock_memory.search.return_value,  # search_memories
                mock_memory.get_all.return_value,  # get_user_context
            ]

            # Step 1: Add conversation memory
            messages = [
                {"role": "user", "content": "I want to plan a trip to Japan"},
                {
                    "role": "assistant",
                    "content": "Great! When would you like to visit?",
                },
                {"role": "user", "content": "I prefer spring for cherry blossoms"},
            ]

            add_result = await configured_service.add_conversation_memory(
                messages=messages, user_id="user_123", session_id="session_456"
            )

            assert "results" in add_result
            assert len(add_result["results"]) == 1

            # Step 2: Search for related memories
            search_results = await configured_service.search_memories(
                query="Japan travel preferences", user_id="user_123", limit=5
            )

            assert len(search_results) == 1
            assert search_results[0].memory == "User wants to visit Japan"
            assert search_results[0].similarity == 0.92

            # Step 3: Get user context
            context = await configured_service.get_user_context("user_123")

            assert "preferences" in context
            assert "insights" in context
            assert len(context["preferences"]) == 1

    @pytest.mark.asyncio
    async def test_error_resilience_workflow(self, configured_service):
        """Test service resilience to various error conditions."""
        mock_memory = MagicMock()
        configured_service.memory = mock_memory
        configured_service._connected = True

        # Test partial failures in search
        with patch("asyncio.to_thread") as mock_to_thread:
            mock_to_thread.side_effect = Exception("Temporary search failure")

            # Should return empty results instead of raising
            results = await configured_service.search_memories(
                query="test", user_id="user_123"
            )

            assert results == []

        # Test context retrieval with fallback
        with patch("asyncio.to_thread") as mock_to_thread:
            mock_to_thread.side_effect = Exception("Context retrieval failed")

            # Should return default context structure
            context = await configured_service.get_user_context("user_123")

            assert "preferences" in context
            assert context["preferences"] == []
            assert context["summary"] == "New user with limited travel history"
