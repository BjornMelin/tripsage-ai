"""
Comprehensive tests for async tool implementations.

This module tests the async tool implementations that were refactored
to use proper async/await patterns for all I/O operations.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestAsyncToolsPattern:
    """Test async patterns in tool implementations."""

    @pytest.mark.asyncio
    async def test_accommodations_tools_async_pattern(self):
        """Test accommodations tools use proper async patterns."""
        from tripsage.tools.accommodations_tools import search_accommodations_tool

        # Mock service registry
        mock_registry = MagicMock()
        mock_service = AsyncMock()
        mock_service.search_accommodations = AsyncMock(
            return_value={
                "status": "success",
                "accommodations": [
                    {
                        "id": "hotel_123",
                        "name": "Test Hotel",
                        "price_per_night": 150.0,
                        "rating": 4.5,
                    }
                ],
            }
        )
        mock_registry.get_service.return_value = mock_service

        # Test async execution
        result = await search_accommodations_tool(
            location="Paris",
            checkin="2024-06-01",
            checkout="2024-06-05",
            guests=2,
            service_registry=mock_registry,
        )

        # Verify async call was made
        mock_service.search_accommodations.assert_called_once()
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_memory_tools_async_pattern(self):
        """Test memory tools use proper async patterns."""
        from tripsage.tools.memory_tools import search_memory_tool

        # Mock service registry
        mock_registry = MagicMock()
        mock_service = AsyncMock()
        mock_service.search_memories = AsyncMock(
            return_value={
                "memories": [
                    {
                        "id": "memory_123",
                        "content": "User prefers boutique hotels",
                        "relevance": 0.95,
                    }
                ]
            }
        )
        mock_registry.get_service.return_value = mock_service

        # Test async execution
        result = await search_memory_tool(
            query="hotel preferences", service_registry=mock_registry
        )

        # Verify async call was made
        mock_service.search_memories.assert_called_once()
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_web_crawl_tools_async_pattern(self):
        """Test web crawl tools use proper async patterns."""
        from tripsage.tools.webcrawl_tools import crawl_website_content_tool

        # Mock service registry
        mock_registry = MagicMock()
        mock_service = AsyncMock()
        mock_service.crawl_url = AsyncMock(
            return_value={
                "status": "success",
                "content": "Travel guide content",
                "metadata": {"title": "Paris Travel Guide"},
            }
        )
        mock_registry.get_service.return_value = mock_service

        # Test async execution
        result = await crawl_website_content_tool(
            url="https://example.com/paris-guide", service_registry=mock_registry
        )

        # Verify async call was made
        mock_service.crawl_url.assert_called_once()
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_planning_tools_async_pattern(self):
        """Test planning tools use proper async patterns."""
        from tripsage.tools.planning_tools import create_travel_plan

        # Test that function is properly async
        params = {
            "user_id": "test_user",
            "title": "Paris Vacation",
            "destinations": ["Paris"],
            "start_date": "2024-06-01",
            "end_date": "2024-06-05",
            "travelers": 2,
        }

        with (
            patch("tripsage.tools.planning_tools.redis_cache") as mock_cache,
            patch("tripsage.tools.planning_tools.MemoryService") as mock_memory_service,
        ):
            mock_cache.set = AsyncMock()
            mock_memory_instance = AsyncMock()
            mock_memory_instance.connect = AsyncMock()
            mock_memory_instance.add_conversation_memory = AsyncMock()
            mock_memory_service.return_value = mock_memory_instance

            # Test async execution
            result = await create_travel_plan(params)

            # Verify async calls were made
            mock_cache.set.assert_called_once()
            mock_memory_instance.connect.assert_called_once()
            mock_memory_instance.add_conversation_memory.assert_called_once()
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_concurrent_tool_execution(self):
        """Test tools can execute concurrently."""
        from tripsage.tools.accommodations_tools import search_accommodations_tool
        from tripsage.tools.memory_tools import search_memory_tool

        # Setup mock registries
        accommodation_registry = MagicMock()
        accommodation_service = AsyncMock()
        accommodation_service.search_accommodations = AsyncMock(
            return_value={"status": "success", "accommodations": []}
        )
        accommodation_registry.get_service.return_value = accommodation_service

        memory_registry = MagicMock()
        memory_service = AsyncMock()
        memory_service.search_memories = AsyncMock(return_value={"memories": []})
        memory_registry.get_service.return_value = memory_service

        # Execute tools concurrently
        start_time = asyncio.get_event_loop().time()
        results = await asyncio.gather(
            search_accommodations_tool(
                location="Paris",
                checkin="2024-06-01",
                checkout="2024-06-05",
                guests=2,
                service_registry=accommodation_registry,
            ),
            search_memory_tool(
                query="travel preferences", service_registry=memory_registry
            ),
        )
        end_time = asyncio.get_event_loop().time()

        # Verify both completed
        assert len(results) == 2
        assert isinstance(results[0], dict)
        assert isinstance(results[1], dict)

        # Verify concurrent execution
        total_time = end_time - start_time
        assert total_time < 1.0  # Should complete quickly with mocks


class TestToolErrorHandling:
    """Test error handling in async tools."""

    @pytest.mark.asyncio
    async def test_tool_service_error_handling(self):
        """Test tool handles service errors gracefully."""
        from tripsage.tools.accommodations_tools import search_accommodations_tool

        # Mock service that raises an error
        mock_registry = MagicMock()
        mock_service = AsyncMock()
        mock_service.search_accommodations = AsyncMock(
            side_effect=Exception("Service unavailable")
        )
        mock_registry.get_service.return_value = mock_service

        # Test error handling
        result = await search_accommodations_tool(
            location="Paris",
            checkin="2024-06-01",
            checkout="2024-06-05",
            guests=2,
            service_registry=mock_registry,
        )

        # Verify error is handled gracefully
        assert isinstance(result, dict)
        # Should not raise exception

    @pytest.mark.asyncio
    async def test_tool_timeout_handling(self):
        """Test tool handles timeouts gracefully."""
        from tripsage.tools.memory_tools import search_memory_tool

        # Mock service with timeout
        mock_registry = MagicMock()
        mock_service = AsyncMock()

        async def slow_search(*args, **kwargs):
            await asyncio.sleep(2)  # Simulate slow service
            return {"memories": []}

        mock_service.search_memories = slow_search
        mock_registry.get_service.return_value = mock_service

        # Test with timeout
        start_time = asyncio.get_event_loop().time()
        try:
            await asyncio.wait_for(
                search_memory_tool(query="test query", service_registry=mock_registry),
                timeout=1.0,
            )
        except asyncio.TimeoutError:
            # Expected timeout
            pass
        end_time = asyncio.get_event_loop().time()

        # Verify timeout occurred
        assert (end_time - start_time) < 1.5


class TestToolServiceIntegration:
    """Test tool integration with services."""

    @pytest.mark.asyncio
    async def test_tool_service_registry_integration(self):
        """Test tools properly integrate with service registry."""
        from tripsage.tools.accommodations_tools import search_accommodations_tool

        # Mock comprehensive service registry
        mock_registry = MagicMock()
        mock_accommodation_service = AsyncMock()
        mock_memory_service = AsyncMock()

        def get_service(service_name):
            if "accommodation" in service_name:
                return mock_accommodation_service
            elif "memory" in service_name:
                return mock_memory_service
            return AsyncMock()

        mock_registry.get_service.side_effect = get_service
        mock_accommodation_service.search_accommodations = AsyncMock(
            return_value={"status": "success", "accommodations": [{"id": "hotel_123"}]}
        )

        # Execute tool
        result = await search_accommodations_tool(
            location="Paris",
            checkin="2024-06-01",
            checkout="2024-06-05",
            guests=2,
            service_registry=mock_registry,
        )

        # Verify service registry interaction
        mock_registry.get_service.assert_called()
        mock_accommodation_service.search_accommodations.assert_called_once()
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_tool_dependency_injection(self):
        """Test tools properly handle dependency injection."""
        from tripsage.tools.memory_tools import add_memory_tool

        # Mock all required services
        mock_registry = MagicMock()
        mock_memory_service = AsyncMock()
        mock_cache_service = AsyncMock()

        def get_service(service_name):
            if "memory" in service_name:
                return mock_memory_service
            elif "cache" in service_name:
                return mock_cache_service
            return AsyncMock()

        mock_registry.get_service.side_effect = get_service
        mock_memory_service.add_conversation_memory = AsyncMock(
            return_value={"status": "success", "memory_id": "memory_456"}
        )

        # Execute tool
        result = await add_memory_tool(
            content="User prefers luxury hotels",
            user_id="test_user",
            service_registry=mock_registry,
        )

        # Verify dependency injection worked
        mock_registry.get_service.assert_called()
        mock_memory_service.add_conversation_memory.assert_called_once()
        assert isinstance(result, dict)


@pytest.mark.integration
class TestToolsIntegrationScenarios:
    """Integration tests for tool scenarios."""

    @pytest.mark.asyncio
    async def test_travel_planning_tool_workflow(self):
        """Test complete travel planning tool workflow."""
        from tripsage.tools.planning_tools import create_travel_plan, update_travel_plan

        # Mock dependencies
        with (
            patch("tripsage.tools.planning_tools.redis_cache") as mock_cache,
            patch("tripsage.tools.planning_tools.MemoryService") as mock_memory_service,
        ):
            mock_cache.set = AsyncMock()
            mock_cache.get = AsyncMock()
            mock_memory_instance = AsyncMock()
            mock_memory_instance.connect = AsyncMock()
            mock_memory_instance.add_conversation_memory = AsyncMock()
            mock_memory_service.return_value = mock_memory_instance

            # Create travel plan
            create_params = {
                "user_id": "traveler_123",
                "title": "European Adventure",
                "destinations": ["Paris", "Rome"],
                "start_date": "2024-06-01",
                "end_date": "2024-06-15",
                "travelers": 2,
                "budget": 5000.0,
            }

            create_result = await create_travel_plan(create_params)
            assert create_result["success"] is True

            plan_id = create_result["plan_id"]

            # Update travel plan
            mock_cache.get.return_value = {
                "plan_id": plan_id,
                "user_id": "traveler_123",
                "title": "European Adventure",
                "destinations": ["Paris", "Rome"],
                "budget": 5000.0,
            }

            update_params = {
                "plan_id": plan_id,
                "user_id": "traveler_123",
                "updates": {"budget": 6000.0},
            }

            update_result = await update_travel_plan(update_params)
            assert update_result["success"] is True

            # Verify workflow
            assert mock_cache.set.call_count >= 2  # Create and update
            assert mock_memory_instance.add_conversation_memory.call_count >= 2

    @pytest.mark.asyncio
    async def test_multi_tool_accommodation_search_workflow(self):
        """Test workflow using multiple accommodation-related tools."""
        from tripsage.tools.accommodations_tools import (
            book_accommodation_tool,
            search_accommodations_tool,
        )

        # Setup mock services
        mock_registry = MagicMock()
        mock_service = AsyncMock()

        # Mock search results
        mock_service.search_accommodations = AsyncMock(
            return_value={
                "status": "success",
                "accommodations": [
                    {
                        "id": "hotel_123",
                        "name": "Paris Boutique Hotel",
                        "price_per_night": 200.0,
                        "rating": 4.8,
                        "availability": True,
                    }
                ],
            }
        )

        # Mock booking
        mock_service.book_accommodation = AsyncMock(
            return_value={
                "status": "success",
                "booking_id": "booking_456",
                "confirmation_code": "CONF789",
            }
        )

        mock_registry.get_service.return_value = mock_service

        # Execute search workflow
        search_result = await search_accommodations_tool(
            location="Paris, France",
            checkin="2024-06-01",
            checkout="2024-06-05",
            guests=2,
            service_registry=mock_registry,
        )

        # Execute booking workflow
        if search_result:  # Assuming search returns results
            await book_accommodation_tool(
                accommodation_id="hotel_123",
                checkin="2024-06-01",
                checkout="2024-06-05",
                guests=2,
                service_registry=mock_registry,
            )

        # Verify workflow
        mock_service.search_accommodations.assert_called_once()
        mock_service.book_accommodation.assert_called_once()


class TestToolPerformanceCharacteristics:
    """Test performance characteristics of async tools."""

    @pytest.mark.asyncio
    async def test_tool_concurrent_performance(self):
        """Test tool performance under concurrent load."""
        from tripsage.tools.memory_tools import search_memory_tool

        # Setup mock service with simulated delay
        mock_registry = MagicMock()
        mock_service = AsyncMock()

        async def simulated_search(*args, **kwargs):
            await asyncio.sleep(0.1)  # Simulate processing time
            return {
                "memories": [{"id": f"memory_{hash(str(args) + str(kwargs)) % 1000}"}]
            }

        mock_service.search_memories = simulated_search
        mock_registry.get_service.return_value = mock_service

        # Execute multiple concurrent searches
        search_tasks = [
            search_memory_tool(query=f"query_{i}", service_registry=mock_registry)
            for i in range(10)
        ]

        start_time = asyncio.get_event_loop().time()
        results = await asyncio.gather(*search_tasks)
        end_time = asyncio.get_event_loop().time()

        # Verify concurrent execution performance
        total_time = end_time - start_time
        # Should be much faster than 10 * 0.1 = 1.0 second if truly concurrent
        assert total_time < 0.5
        assert len(results) == 10
        assert all(isinstance(result, dict) for result in results)

    @pytest.mark.asyncio
    async def test_tool_resource_efficiency(self):
        """Test tool resource efficiency with async patterns."""
        from tripsage.tools.accommodations_tools import search_accommodations_tool

        # Setup mock service that tracks calls
        mock_registry = MagicMock()
        mock_service = AsyncMock()
        call_count = 0

        async def tracked_search(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.05)  # Simulate work
            return {"accommodations": [{"id": f"hotel_{call_count}"}]}

        mock_service.search_accommodations = tracked_search
        mock_registry.get_service.return_value = mock_service

        # Execute rapid successive calls
        tasks = []
        for i in range(5):
            task = search_accommodations_tool(
                location=f"City_{i}",
                checkin="2024-06-01",
                checkout="2024-06-05",
                guests=2,
                service_registry=mock_registry,
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks)

        # Verify efficient execution
        assert call_count == 5
        assert len(results) == 5
        assert all(isinstance(result, dict) for result in results)
