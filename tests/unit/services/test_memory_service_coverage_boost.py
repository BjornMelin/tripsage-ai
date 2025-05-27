"""
Targeted tests to boost coverage to 90%+ by testing specific missing lines.

Based on coverage report, targeting lines:
116, 129, 136-137, 186, 221-223, 259, 324, 353, 362-363,
371-374, 409, 437-439, 457, 488-489, 497-499, 530-532, 566,
569, 602-603, 621, 672, 695, 700, 705-706, 735-736, 743-744, 754-758
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tripsage.services.memory_service import (
    MemorySearchResult,
    MemoryServiceAdapter,
    TripSageMemoryService,
)


class TestSpecificCoverageLines:
    """Target specific lines missing from coverage."""

    @pytest.mark.asyncio
    async def test_connect_early_return(self):
        """Test connect method early return when already connected."""
        service = TripSageMemoryService()
        service._connected = True
        service.memory = MagicMock()

        # Should return early without calling Memory.from_config
        with patch("tripsage.services.memory_service.Memory") as mock_memory:
            await service.connect()
            mock_memory.from_config.assert_not_called()

    @pytest.mark.asyncio
    async def test_close_early_return(self):
        """Test close method early return when not connected."""
        service = TripSageMemoryService()
        service._connected = False

        # Should return early
        await service.close()
        assert not service._connected

    @pytest.mark.asyncio
    async def test_close_with_exception(self):
        """Test close method with exception during cleanup."""
        service = TripSageMemoryService()
        service._connected = True
        service._cache = {"test": "data"}

        # Mock an exception during cleanup
        with patch.object(
            service._cache, "clear", side_effect=Exception("Cleanup error")
        ):
            await service.close()
            # Should still set _connected to False despite exception
            assert not service._connected

    @pytest.mark.asyncio
    async def test_add_conversation_early_return(self):
        """Test add_conversation_memory early return when not connected."""
        service = TripSageMemoryService()
        service._connected = False

        with patch.object(service, "connect") as mock_connect:
            mock_connect.return_value = None
            service.memory = MagicMock()
            service.memory.add.return_value = {"results": []}

            await service.add_conversation_memory(
                messages=[{"role": "user", "content": "test"}], user_id="user_123"
            )

            mock_connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_memories_early_return(self):
        """Test search_memories early return when not connected."""
        service = TripSageMemoryService()
        service._connected = False

        with patch.object(service, "connect") as mock_connect:
            mock_connect.return_value = None
            service.memory = MagicMock()
            service.memory.search.return_value = {"results": []}

            await service.search_memories("test", "user_123")
            mock_connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_context_early_return(self):
        """Test get_user_context early return when not connected."""
        service = TripSageMemoryService()
        service._connected = False

        with patch.object(service, "connect") as mock_connect:
            mock_connect.return_value = None
            service.memory = MagicMock()
            service.memory.get_all.return_value = {"results": []}

            await service.get_user_context("user_123")
            mock_connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_with_mcp_fallback(self):
        """Test MCP fallback path in search_memories."""
        service = TripSageMemoryService()
        service._connected = True
        service.memory = MagicMock()

        # Mock MCP fallback method
        service._search_via_mcp = AsyncMock(return_value=[])

        with patch("tripsage.services.memory_service.feature_flags") as mock_flags:
            from tripsage.config.feature_flags import IntegrationMode

            mock_flags.get_integration_mode.return_value = IntegrationMode.MCP

            await service.search_memories("test", "user_123")
            service._search_via_mcp.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_memories_with_ids(self):
        """Test delete_user_memories with specific memory IDs."""
        service = TripSageMemoryService()
        service._connected = True
        service.memory = MagicMock()
        service.memory.delete.return_value = {"success": True}

        result = await service.delete_user_memories("user_123", ["mem-1", "mem-2"])

        assert "deleted_count" in result
        assert result["success"] is True
        # Should call delete twice for two memory IDs
        assert service.memory.delete.call_count == 2

    @pytest.mark.asyncio
    async def test_delete_memories_all_user_memories(self):
        """Test delete_user_memories without specific IDs (delete all)."""
        service = TripSageMemoryService()
        service._connected = True
        service.memory = MagicMock()

        # Mock get_all to return some memories
        service.memory.get_all.return_value = {
            "results": [
                {"id": "mem-1", "memory": "test1"},
                {"id": "mem-2", "memory": "test2"},
            ]
        }
        service.memory.delete.return_value = {"success": True}

        result = await service.delete_user_memories("user_123")

        assert "deleted_count" in result
        # Should call get_all once and delete twice
        service.memory.get_all.assert_called_once()
        assert service.memory.delete.call_count == 2

    @pytest.mark.asyncio
    async def test_delete_with_partial_failures(self):
        """Test deletion with some failures."""
        service = TripSageMemoryService()
        service._connected = True
        service.memory = MagicMock()

        # First delete succeeds, second fails
        service.memory.delete.side_effect = [
            {"success": True},
            Exception("Delete failed"),
        ]

        result = await service.delete_user_memories("user_123", ["mem-1", "mem-2"])

        assert "deleted_count" in result
        assert result["deleted_count"] == 1  # Only one succeeded

    def test_cache_expiration_logic(self):
        """Test cache expiration logic in _get_cached_result."""
        service = TripSageMemoryService()

        # Create expired cache entry
        import time

        cache_key = "test_key"
        test_results = [
            MemorySearchResult(
                id="test",
                memory="test memory",
                created_at=datetime.now(timezone.utc),
                user_id="test_user",
            )
        ]

        # Set short TTL and add to cache
        service._cache_ttl = 0.1
        service._cache[cache_key] = (test_results, time.time() - 1)  # Already expired

        # Should return None for expired cache
        result = service._get_cached_result(cache_key)
        assert result is None
        assert cache_key not in service._cache  # Should be cleaned up

    @pytest.mark.asyncio
    async def test_memory_service_adapter_get_mcp_client(self):
        """Test MemoryServiceAdapter MCP client retrieval."""
        adapter = MemoryServiceAdapter()

        # Mock the MCP client retrieval
        with patch("tripsage.services.memory_service.get_memory_service") as mock_get:
            mock_service = MagicMock()
            mock_get.return_value = mock_service

            client = await adapter.get_mcp_client()
            assert client is mock_service

    @pytest.mark.asyncio
    async def test_memory_service_adapter_get_direct_service(self):
        """Test MemoryServiceAdapter direct service retrieval."""
        adapter = MemoryServiceAdapter()

        service = await adapter.get_direct_service()
        assert isinstance(service, TripSageMemoryService)

    def test_analysis_methods_with_empty_data(self):
        """Test analysis methods with empty context data."""
        service = TripSageMemoryService()

        empty_context = {
            "preferences": [],
            "past_trips": [],
            "saved_destinations": [],
            "budget_patterns": [],
            "travel_style": [],
            "dietary_restrictions": [],
            "accommodation_preferences": [],
            "activity_preferences": [],
        }

        # Test all analysis methods with empty data
        destinations = service._analyze_destinations(empty_context)
        assert destinations["destination_count"] == 0

        budgets = service._analyze_budgets(empty_context)
        assert "budget_info" in budgets

        frequency = service._analyze_frequency(empty_context)
        assert frequency["total_trips"] == 0

        activities = service._analyze_activities(empty_context)
        assert isinstance(activities["preferred_activities"], list)

        travel_style = service._analyze_travel_style(empty_context)
        assert isinstance(travel_style["travel_styles"], list)

    def test_analysis_methods_with_rich_data(self):
        """Test analysis methods with rich context data."""
        service = TripSageMemoryService()

        rich_context = {
            "preferences": [
                {"content": "luxury hotels", "category": "accommodation"},
                {"content": "business class", "category": "transportation"},
            ],
            "past_trips": [
                {"content": "Japan trip", "category": "destination"},
                {"content": "Europe tour", "category": "destination"},
                {"content": "$3000 budget", "category": "budget"},
            ],
            "saved_destinations": [
                {"content": "Korea", "category": "destination"},
                {"content": "Thailand", "category": "destination"},
            ],
            "budget_patterns": [
                {"content": "$2000-3000", "category": "budget"},
                {"content": "luxury spending", "category": "budget"},
            ],
            "travel_style": [
                {"content": "luxury travel", "category": "style"},
                {"content": "cultural tours", "category": "activity"},
            ],
            "activity_preferences": [
                {"content": "museums", "category": "cultural"},
                {"content": "fine dining", "category": "food"},
            ],
        }

        # Test all analysis methods with rich data
        destinations = service._analyze_destinations(rich_context)
        assert destinations["destination_count"] > 0

        budgets = service._analyze_budgets(rich_context)
        assert "budget_info" in budgets

        frequency = service._analyze_frequency(rich_context)
        assert frequency["total_trips"] > 0

        activities = service._analyze_activities(rich_context)
        assert len(activities["preferred_activities"]) > 0

        travel_style = service._analyze_travel_style(rich_context)
        assert len(travel_style["travel_styles"]) > 0

    @pytest.mark.asyncio
    async def test_enrich_travel_memories_with_data(self):
        """Test memory enrichment with actual data."""
        service = TripSageMemoryService()

        # Create test memories with travel-related content
        memories = [
            MemorySearchResult(
                id="mem-1",
                memory="User loves visiting temples and museums in Japan",
                metadata={"category": "activity_preference"},
                categories=["travel", "activity"],
                similarity=0.9,
                created_at=datetime.now(timezone.utc),
                user_id="test_user",
            ),
            MemorySearchResult(
                id="mem-2",
                memory="Prefers luxury accommodations with spa facilities",
                metadata={"category": "accommodation"},
                categories=["travel", "accommodation"],
                similarity=0.85,
                created_at=datetime.now(timezone.utc),
                user_id="test_user",
            ),
        ]

        enriched = await service._enrich_travel_memories(memories)
        assert len(enriched) == len(memories)
        assert all(isinstance(m, MemorySearchResult) for m in enriched)

    def test_context_summary_generation_variations(self):
        """Test context summary with different context variations."""
        service = TripSageMemoryService()

        # Test high-activity user context
        active_context = {
            "preferences": [{"content": "luxury"}, {"content": "adventure"}],
            "past_trips": [{"content": "Japan"}, {"content": "Europe"}],
            "insights": {
                "preferred_destinations": {"destination_count": 15},
                "travel_frequency": {"total_trips": 10},
                "budget_range": {"budget_info": "$5000+"},
            },
        }

        active_summary = service._generate_context_summary(active_context)
        assert (
            "experienced" in active_summary.lower()
            or "frequent" in active_summary.lower()
        )

        # Test moderate user context
        moderate_context = {
            "preferences": [{"content": "comfort"}],
            "past_trips": [{"content": "domestic"}],
            "insights": {
                "preferred_destinations": {"destination_count": 3},
                "travel_frequency": {"total_trips": 2},
                "budget_range": {"budget_info": "$1000-2000"},
            },
        }

        moderate_summary = service._generate_context_summary(moderate_context)
        assert isinstance(moderate_summary, str)
        assert len(moderate_summary) > 0
