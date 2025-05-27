"""
Comprehensive test suite to target specific coverage areas for 90% coverage goal.

This file focuses on testing edge cases, error paths, and internal methods
that weren't covered in the main test suite.
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from tripsage.services.memory_service import (
    ConversationMemory,
    MemorySearchResult,
    TripSageMemoryService,
)


class TestMemoryServiceCoverage:
    """Test specific code paths to achieve 90% coverage."""

    @pytest.fixture
    def service_with_mocks(self):
        """Service with comprehensive mocks for internal methods."""
        service = TripSageMemoryService()
        service.memory = MagicMock()
        service._connected = True

        # Mock all memory operations
        service.memory.add.return_value = {
            "results": [{"memory_id": "test-123"}],
            "usage": {"total_tokens": 100},
        }
        service.memory.search.return_value = {
            "results": [
                {
                    "id": "mem-1",
                    "memory": "Test memory content",
                    "metadata": {"category": "test"},
                    "categories": ["travel"],
                    "score": 0.8,
                    "created_at": datetime.now(datetime.UTC).isoformat(),
                }
            ]
        }
        service.memory.get_all.return_value = {
            "results": [
                {
                    "id": "mem-1",
                    "memory": "User prefers luxury hotels",
                    "metadata": {"category": "accommodation"},
                    "categories": ["travel", "accommodation"],
                    "created_at": datetime.now(datetime.UTC).isoformat(),
                },
                {
                    "id": "mem-2",
                    "memory": "Budget range is $2000-3000",
                    "metadata": {"category": "budget"},
                    "categories": ["travel", "budget"],
                    "created_at": datetime.now(datetime.UTC).isoformat(),
                },
                {
                    "id": "mem-3",
                    "memory": "Visited Japan 3 times",
                    "metadata": {"category": "destination"},
                    "categories": ["travel", "destination"],
                    "created_at": datetime.now(datetime.UTC).isoformat(),
                },
            ]
        }
        service.memory.update.return_value = {"success": True}
        service.memory.delete.return_value = {"success": True}

        return service

    @pytest.mark.asyncio
    async def test_cache_mechanisms(self, service_with_mocks):
        """Test cache get, set, and invalidation mechanisms."""
        # Test cache miss
        cache_key = "user_123:test_query:5:123456"
        result = service_with_mocks._get_cached_result(cache_key)
        assert result is None

        # Test cache set
        test_results = [
            MemorySearchResult(
                id="test-1",
                memory="Cached memory",
                metadata={},
                categories=["test"],
                similarity=0.9,
                created_at=datetime.now(datetime.UTC),
                user_id="user_123",
            )
        ]
        service_with_mocks._cache_result(cache_key, test_results)

        # Test cache hit
        cached = service_with_mocks._get_cached_result(cache_key)
        assert cached is not None
        assert len(cached) == 1
        assert cached[0].memory == "Cached memory"

        # Test cache invalidation
        service_with_mocks._invalidate_user_cache("user_123")
        invalidated = service_with_mocks._get_cached_result(cache_key)
        assert invalidated is None

    @pytest.mark.asyncio
    async def test_travel_insights_analysis(self, service_with_mocks):
        """Test the travel insights generation methods."""
        # Test context analysis with realistic data
        context = {
            "preferences": [
                {"content": "luxury hotels", "category": "accommodation"},
                {"content": "business class flights", "category": "transportation"},
            ],
            "past_trips": [
                {"content": "Visited Japan in spring", "category": "destination"},
                {"content": "Stayed in Tokyo for 7 days", "category": "duration"},
                {"content": "Budget was $3000", "category": "budget"},
            ],
            "saved_destinations": [
                {"content": "Want to visit Korea next", "category": "destination"},
                {"content": "Interested in European cities", "category": "destination"},
            ],
            "budget_patterns": [
                {"content": "$2000-3000 per trip", "category": "budget"},
                {"content": "Willing to spend more for luxury", "category": "budget"},
            ],
        }

        # Test destination analysis
        destinations = service_with_mocks._analyze_destinations(context)
        assert "most_visited" in destinations
        assert "destination_count" in destinations

        # Test budget analysis
        budgets = service_with_mocks._analyze_budgets(context)
        assert "budget_info" in budgets

        # Test frequency analysis
        frequency = service_with_mocks._analyze_frequency(context)
        assert "total_trips" in frequency
        assert "estimated_frequency" in frequency

        # Test activity analysis
        activities = service_with_mocks._analyze_activities(context)
        assert "preferred_activities" in activities
        assert "activity_style" in activities

        # Test travel style analysis
        travel_style = service_with_mocks._analyze_travel_style(context)
        assert "travel_styles" in travel_style
        assert "primary_style" in travel_style

    @pytest.mark.asyncio
    async def test_context_summary_generation(self, service_with_mocks):
        """Test context summary generation with various scenarios."""
        # Test with comprehensive context
        full_context = {
            "preferences": [{"content": "luxury", "category": "accommodation"}],
            "past_trips": [{"content": "Japan", "category": "destination"}],
            "insights": {
                "preferred_destinations": {"destination_count": 5},
                "travel_frequency": {"total_trips": 3},
                "budget_range": {"budget_info": "$2000-3000"},
            },
        }

        summary = service_with_mocks._generate_context_summary(full_context)
        assert isinstance(summary, str)
        assert len(summary) > 0

        # Test with minimal context
        minimal_context = {
            "preferences": [],
            "past_trips": [],
            "insights": {
                "preferred_destinations": {"destination_count": 0},
                "travel_frequency": {"total_trips": 0},
            },
        }

        minimal_summary = service_with_mocks._generate_context_summary(minimal_context)
        assert "limited" in minimal_summary.lower() or "new" in minimal_summary.lower()

    @pytest.mark.asyncio
    async def test_memory_enrichment(self, service_with_mocks):
        """Test travel memory enrichment functionality."""
        # Create test memory results
        raw_results = [
            MemorySearchResult(
                id="mem-1",
                memory="User prefers beach destinations",
                metadata={"category": "travel_preference"},
                categories=["travel"],
                similarity=0.85,
                created_at=datetime.now(datetime.UTC),
                user_id="user_123",
            )
        ]

        # Test enrichment
        enriched = await service_with_mocks._enrich_travel_memories(raw_results)
        assert len(enriched) == len(raw_results)
        assert enriched[0].memory == raw_results[0].memory

    @pytest.mark.asyncio
    async def test_error_handling_paths(self, service_with_mocks):
        """Test various error handling scenarios."""
        # Test search with connection error
        service_with_mocks.memory.search.side_effect = Exception("Network error")

        results = await service_with_mocks.search_memories("test", "user_123")
        assert isinstance(results, list)
        assert len(results) == 0

        # Reset side effect
        service_with_mocks.memory.search.side_effect = None
        service_with_mocks.memory.search.return_value = {"results": []}

    @pytest.mark.asyncio
    async def test_memory_deletion_edge_cases(self, service_with_mocks):
        """Test memory deletion with various scenarios."""
        # Test deletion with specific memory IDs
        memory_ids = ["mem-1", "mem-2"]
        result = await service_with_mocks.delete_user_memories("user_123", memory_ids)

        assert "deleted_count" in result
        assert "success" in result
        assert result["success"] is True

        # Test deletion with partial failures
        service_with_mocks.memory.delete.side_effect = [
            None,
            Exception("Delete failed"),
        ]

        result = await service_with_mocks.delete_user_memories(
            "user_123", ["mem-1", "mem-2"]
        )
        assert "deleted_count" in result

    @pytest.mark.asyncio
    async def test_preference_update_scenarios(self, service_with_mocks):
        """Test user preference updates with different data types."""
        # Test with complex preference structure
        complex_prefs = {
            "accommodation": {
                "type": "luxury_hotel",
                "amenities": ["spa", "gym", "pool"],
                "budget_range": "$300-500",
            },
            "transportation": {
                "flight_class": "business",
                "airline_preferences": ["Singapore Airlines", "Emirates"],
            },
            "activities": ["cultural_tours", "fine_dining", "shopping"],
        }

        result = await service_with_mocks.update_user_preferences(
            "user_123", complex_prefs
        )
        assert "success" in result or "results" in result

    @pytest.mark.asyncio
    async def test_connection_state_management(self):
        """Test connection state handling."""
        service = TripSageMemoryService()

        # Test is_connected property
        assert not service.is_connected

        # Test auto-connect on method calls
        with patch.object(service, "connect") as mock_connect:
            mock_connect.return_value = None
            service._connected = False

            # This should trigger auto-connect
            service.memory = MagicMock()
            service.memory.search.return_value = {"results": []}

            await service.search_memories("test", "user_123")
            mock_connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_feature_flag_integration(self, service_with_mocks):
        """Test feature flag switching between MCP and direct SDK."""
        # Test direct SDK path (default)
        with patch("tripsage.services.memory_service.feature_flags") as mock_flags:
            from tripsage.config.feature_flags import IntegrationMode

            mock_flags.get_integration_mode.return_value = IntegrationMode.DIRECT

            results = await service_with_mocks.search_memories("test", "user_123")
            assert isinstance(results, list)

            # Verify direct memory search was called
            service_with_mocks.memory.search.assert_called()

    @pytest.mark.asyncio
    async def test_metadata_enhancement(self, service_with_mocks):
        """Test metadata enhancement for memory storage."""
        messages = [
            {"role": "user", "content": "I'm planning a luxury trip to Japan"},
            {
                "role": "assistant",
                "content": "Great! I can help with luxury accommodations.",
            },
        ]

        await service_with_mocks.add_conversation_memory(
            messages=messages,
            user_id="user_123",
            session_id="session_456",
            metadata={"trip_type": "luxury", "destination": "Japan"},
        )

        # Verify memory.add was called with enhanced metadata
        call_args = service_with_mocks.memory.add.call_args
        assert call_args is not None
        assert "metadata" in call_args.kwargs

        metadata = call_args.kwargs["metadata"]
        assert "session_id" in metadata
        assert "timestamp" in metadata
        assert "trip_type" in metadata

    def test_memory_result_model_edge_cases(self):
        """Test MemorySearchResult with edge case data."""
        # Test with minimal data
        result = MemorySearchResult(
            id="test",
            memory="minimal memory",
            created_at=datetime.now(datetime.UTC),
            user_id="test_user",
        )
        assert result.metadata == {}
        assert result.categories == []
        assert result.similarity == 0.0

        # Test with maximum data
        result = MemorySearchResult(
            id="test",
            memory="detailed memory",
            metadata={"key1": "value1", "key2": ["item1", "item2"]},
            categories=["travel", "accommodation", "luxury"],
            similarity=0.99,
            created_at=datetime.now(datetime.UTC),
            user_id="test_user",
        )
        assert len(result.metadata) == 2
        assert len(result.categories) == 3
        assert result.similarity == 0.99

    @pytest.mark.asyncio
    async def test_conversation_memory_model(self):
        """Test ConversationMemory model validation."""
        # Test valid conversation
        conv = ConversationMemory(
            messages=[
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there!"},
            ],
            user_id="test_user",
        )
        assert len(conv.messages) == 2
        assert conv.session_id is None
        assert conv.metadata is None

        # Test with full data
        conv = ConversationMemory(
            messages=[{"role": "user", "content": "Test"}],
            user_id="test_user",
            session_id="session_123",
            metadata={"source": "chat_ui"},
        )
        assert conv.session_id == "session_123"
        assert conv.metadata["source"] == "chat_ui"


class TestMemoryServiceAdapter:
    """Test the memory service adapter pattern."""

    @pytest.mark.asyncio
    async def test_service_adapter_interface(self):
        """Test that memory service implements ServiceProtocol correctly."""
        service = TripSageMemoryService()

        # Test that required methods exist
        assert hasattr(service, "health_check")
        assert hasattr(service, "close")
        assert hasattr(service, "is_connected")

        # Test health check returns boolean
        with patch.object(service, "memory", MagicMock()):
            service._connected = True
            service.memory.search.return_value = {"results": []}
            result = await service.health_check()
            assert isinstance(result, bool)


class TestPerformanceAndScaling:
    """Test performance characteristics and scaling behavior."""

    @pytest.mark.asyncio
    async def test_large_memory_batch_operations(self):
        """Test handling of large batches of memories."""
        service = TripSageMemoryService()
        service.memory = MagicMock()
        service._connected = True

        # Mock large result set
        large_results = {
            "results": [
                {
                    "id": f"mem-{i}",
                    "memory": f"Memory content {i}",
                    "metadata": {"index": i},
                    "categories": ["test"],
                    "score": 0.8,
                    "created_at": datetime.now(datetime.UTC).isoformat(),
                }
                for i in range(100)  # 100 memories
            ]
        }
        service.memory.search.return_value = large_results

        results = await service.search_memories("test query", "user_123", limit=100)
        assert len(results) == 100
        assert all(isinstance(r, MemorySearchResult) for r in results)

    @pytest.mark.asyncio
    async def test_cache_performance_with_large_datasets(self):
        """Test cache performance with large result sets."""
        service = TripSageMemoryService()

        # Create large result set
        large_results = [
            MemorySearchResult(
                id=f"mem-{i}",
                memory=f"Large memory content {i}",
                metadata={"index": i},
                categories=["performance_test"],
                similarity=0.8,
                created_at=datetime.now(datetime.UTC),
                user_id="performance_user",
            )
            for i in range(50)
        ]

        # Test cache operations with large dataset
        cache_key = "performance_test_key"

        start_time = datetime.now(datetime.UTC)
        service._cache_result(cache_key, large_results)
        cache_time = (datetime.now(datetime.UTC) - start_time).total_seconds()

        start_time = datetime.now(datetime.UTC)
        cached_results = service._get_cached_result(cache_key)
        retrieve_time = (datetime.now(datetime.UTC) - start_time).total_seconds()

        # Verify performance is reasonable
        assert cache_time < 1.0  # Should cache in under 1 second
        assert retrieve_time < 0.1  # Should retrieve in under 100ms
        assert len(cached_results) == 50
        assert cached_results[0].memory == "Large memory content 0"
