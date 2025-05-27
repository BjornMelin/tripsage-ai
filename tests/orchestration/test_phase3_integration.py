"""
Integration test suite for Phase 3 LangGraph migration components.

This module tests the complete integration of all Phase 3 components:
- LangGraph-MCP Bridge
- Session Memory Bridge
- Checkpoint Manager
- Handoff Coordinator
- Updated Graph orchestration
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tripsage.orchestration.checkpoint_manager import get_checkpoint_manager
from tripsage.orchestration.graph import TripSageOrchestrator
from tripsage.orchestration.handoff_coordinator import (
    get_handoff_coordinator,
)
from tripsage.orchestration.mcp_bridge import get_mcp_bridge
from tripsage.orchestration.memory_bridge import get_memory_bridge


class TestPhase3Integration:
    """Integration tests for all Phase 3 components."""

    @pytest.fixture
    def mock_dependencies(self):
        """Mock all external dependencies."""
        with (
            patch.multiple("tripsage.mcp_abstraction.manager", MCPManager=MagicMock()),
            patch.multiple(
                "tripsage.utils.session_memory", SessionMemoryUtil=MagicMock()
            ),
            patch.multiple("asyncpg", create_pool=AsyncMock()),
            patch.multiple("tripsage.config.app_settings", get_settings=MagicMock()),
        ):
            yield

    @pytest.fixture
    async def orchestrator(self, mock_dependencies):
        """Create fully integrated orchestrator."""
        orchestrator = TripSageOrchestrator()
        await orchestrator.initialize()
        return orchestrator

    @pytest.mark.asyncio
    async def test_full_integration_initialization(self, orchestrator):
        """Test that all Phase 3 components initialize correctly together."""
        # Verify orchestrator is initialized
        assert orchestrator._initialized is True
        assert orchestrator.compiled_graph is not None

        # Verify Phase 3 components are available
        assert orchestrator.memory_bridge is not None
        assert orchestrator.handoff_coordinator is not None

        # Verify singletons work correctly
        assert get_mcp_bridge() is not None
        assert get_memory_bridge() is not None
        assert get_checkpoint_manager() is not None
        assert get_handoff_coordinator() is not None

    @pytest.mark.asyncio
    async def test_end_to_end_conversation_flow(self, orchestrator, mock_dependencies):
        """Test complete conversation flow through all components."""
        user_id = "integration_test_user"

        # Mock MCP responses
        with patch("tripsage.mcp_abstraction.manager.MCPManager") as mock_mcp:
            mock_mcp_instance = MagicMock()
            mock_mcp_instance.invoke.return_value = {
                "destinations": [{"name": "Paris", "country": "France"}]
            }
            mock_mcp.return_value = mock_mcp_instance

            # Mock memory responses
            with patch(
                "tripsage.utils.session_memory.SessionMemoryUtil"
            ) as mock_memory:
                mock_memory_instance = MagicMock()
                mock_memory_instance.get_user_context.return_value = {
                    "preferences": {"budget": "moderate"}
                }
                mock_memory_instance.update_user_context = AsyncMock()
                mock_memory_instance.add_conversation_insight = AsyncMock()
                mock_memory.return_value = mock_memory_instance

                # Process message through full system
                result = await orchestrator.process_message(
                    user_id, "I want to plan a trip to Paris for my vacation"
                )

                # Verify successful processing
                assert "response" in result
                assert "session_id" in result
                assert result["session_id"].startswith("session_")
                assert isinstance(result["response"], str)
                assert len(result["response"]) > 0

    @pytest.mark.asyncio
    async def test_agent_handoff_integration(self, orchestrator, mock_dependencies):
        """Test agent handoff integration in full system."""
        user_id = "handoff_test_user"
        session_id = "test_session_handoff"

        with patch("tripsage.mcp_abstraction.manager.MCPManager") as mock_mcp:
            mock_mcp_instance = MagicMock()
            mock_mcp_instance.invoke.return_value = {"results": "success"}
            mock_mcp.return_value = mock_mcp_instance

            # First message - destination research
            result1 = await orchestrator.process_message(
                user_id, "Tell me about Paris attractions", session_id
            )

            # Second message - should trigger handoff to flight agent
            result2 = await orchestrator.process_message(
                user_id, "Now I need flights from NYC to Paris", session_id
            )

            # Verify both messages processed successfully
            assert result1["session_id"] == session_id
            assert result2["session_id"] == session_id
            assert "response" in result1
            assert "response" in result2

    @pytest.mark.asyncio
    async def test_memory_bridge_state_hydration(self, orchestrator, mock_dependencies):
        """Test memory bridge state hydration integration."""
        user_id = "memory_test_user"

        # Mock user context in memory
        with patch("tripsage.utils.session_memory.SessionMemoryUtil") as mock_memory:
            mock_memory_instance = MagicMock()
            mock_memory_instance.get_user_context.return_value = {
                "preferences": {
                    "budget_range": "1000-2000",
                    "preferred_airlines": ["Delta", "American"],
                    "travel_style": "leisure",
                },
                "travel_history": [{"destination": "London", "rating": 5}],
            }
            mock_memory_instance.update_user_context = AsyncMock()
            mock_memory_instance.add_conversation_insight = AsyncMock()
            mock_memory.return_value = mock_memory_instance

            # Process message
            result = await orchestrator.process_message(user_id, "Plan a trip to Tokyo")

            # Verify state was hydrated with user context
            assert "response" in result
            assert "state" in result

            # Memory bridge should have been called
            mock_memory_instance.get_user_context.assert_called()

    @pytest.mark.asyncio
    async def test_checkpoint_persistence_integration(
        self, orchestrator, mock_dependencies
    ):
        """Test checkpoint persistence integration."""
        user_id = "checkpoint_test_user"
        session_id = "persistent_session_123"

        # Mock PostgreSQL checkpointer
        with patch(
            "langgraph.checkpoint.postgres.aio.AsyncPostgresSaver"
        ) as mock_saver:
            mock_saver_instance = MagicMock()
            mock_saver_instance.aput = AsyncMock()
            mock_saver_instance.aget = AsyncMock()
            mock_saver.return_value = mock_saver_instance

            # Process multiple messages in same session
            message1 = "I want to visit Tokyo"
            message2 = "What's the weather like there?"

            result1 = await orchestrator.process_message(user_id, message1, session_id)
            result2 = await orchestrator.process_message(user_id, message2, session_id)

            # Both should use same session
            assert result1["session_id"] == session_id
            assert result2["session_id"] == session_id

            # Checkpointer should have been used
            # (In real integration, state would persist between calls)

    @pytest.mark.asyncio
    async def test_mcp_bridge_tool_integration(self, orchestrator, mock_dependencies):
        """Test MCP bridge tool integration."""
        user_id = "mcp_test_user"

        # Mock MCP services and tools
        with patch("tripsage.mcp_abstraction.manager.MCPManager") as mock_mcp:
            mock_mcp_instance = MagicMock()
            mock_mcp_instance.services = {
                "flights": MagicMock(),
                "accommodations": MagicMock(),
                "google_maps": MagicMock(),
            }
            mock_mcp_instance.invoke.return_value = {
                "flights": [{"id": "FL123", "price": 500}]
            }
            # Mock get_tools for each service
            for service in mock_mcp_instance.services.values():
                service.get_tools.return_value = [
                    {"name": "search", "description": "Search function"}
                ]
            mock_mcp_instance.is_service_available.return_value = True
            mock_mcp.return_value = mock_mcp_instance

            # Process flight search message
            result = await orchestrator.process_message(
                user_id, "Find flights from NYC to LAX for July 15th"
            )

            # Verify successful processing
            assert "response" in result
            assert isinstance(result["response"], str)

    @pytest.mark.asyncio
    async def test_error_handling_across_components(
        self, orchestrator, mock_dependencies
    ):
        """Test error handling across all Phase 3 components."""
        user_id = "error_test_user"

        # Mock various failures
        with patch("tripsage.mcp_abstraction.manager.MCPManager") as mock_mcp:
            mock_mcp.side_effect = Exception("MCP service unavailable")

            # System should handle errors gracefully
            result = await orchestrator.process_message(user_id, "Find flights")

            # Should return error response but not crash
            assert "response" in result
            assert "error" in result or "apologize" in result["response"].lower()

    @pytest.mark.asyncio
    async def test_concurrent_session_handling(self, orchestrator, mock_dependencies):
        """Test handling of concurrent sessions."""

        # Create multiple concurrent sessions
        async def process_session(user_id: str, session_id: str, message: str):
            return await orchestrator.process_message(user_id, message, session_id)

        # Mock dependencies
        with patch("tripsage.mcp_abstraction.manager.MCPManager") as mock_mcp:
            mock_mcp_instance = MagicMock()
            mock_mcp_instance.invoke.return_value = {"result": "success"}
            mock_mcp.return_value = mock_mcp_instance

            # Create concurrent tasks
            tasks = [
                process_session(f"user_{i}", f"session_{i}", f"Message from user {i}")
                for i in range(5)
            ]

            # Execute concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # All should succeed
            assert len(results) == 5
            for result in results:
                assert not isinstance(result, Exception)
                assert "response" in result
                assert "session_id" in result

    @pytest.mark.asyncio
    async def test_performance_with_all_components(
        self, orchestrator, mock_dependencies
    ):
        """Test performance with all Phase 3 components active."""
        import time

        user_id = "performance_test_user"

        # Mock fast responses
        with patch("tripsage.mcp_abstraction.manager.MCPManager") as mock_mcp:
            mock_mcp_instance = MagicMock()
            mock_mcp_instance.invoke.return_value = {"quick": "response"}
            mock_mcp.return_value = mock_mcp_instance

            start_time = time.time()

            # Process multiple messages
            tasks = []
            for i in range(10):
                task = orchestrator.process_message(user_id, f"Quick message {i}")
                tasks.append(task)

            results = await asyncio.gather(*tasks)

            end_time = time.time()
            total_time = end_time - start_time

            # Should complete reasonably quickly
            assert total_time < 5.0  # Less than 5 seconds for 10 messages
            assert len(results) == 10

            # All should be successful
            for result in results:
                assert "response" in result
                assert "session_id" in result

    @pytest.mark.asyncio
    async def test_state_consistency_across_handoffs(
        self, orchestrator, mock_dependencies
    ):
        """Test that state remains consistent across agent handoffs."""
        user_id = "consistency_test_user"
        session_id = "consistency_session"

        with patch("tripsage.mcp_abstraction.manager.MCPManager") as mock_mcp:
            mock_mcp_instance = MagicMock()
            mock_mcp_instance.invoke.return_value = {"data": "consistent"}
            mock_mcp.return_value = mock_mcp_instance

            # Simulate conversation that should trigger handoffs
            messages = [
                "Research Paris attractions",
                "Find flights to Paris",
                "Look for hotels in Paris",
                "Create an itinerary for my Paris trip",
            ]

            results = []
            for message in messages:
                result = await orchestrator.process_message(
                    user_id, message, session_id
                )
                results.append(result)

            # All should use same session
            for result in results:
                assert result["session_id"] == session_id
                assert "response" in result

            # State should be preserved across handoffs
            assert len(set(r["session_id"] for r in results)) == 1

    @pytest.mark.asyncio
    async def test_memory_persistence_integration(
        self, orchestrator, mock_dependencies
    ):
        """Test memory persistence across multiple interactions."""
        user_id = "memory_persistence_user"

        # Mock memory with accumulating insights
        insights_storage = {}

        def mock_add_insight(user_id, insight):
            if user_id not in insights_storage:
                insights_storage[user_id] = []
            insights_storage[user_id].append(insight)

        with patch("tripsage.utils.session_memory.SessionMemoryUtil") as mock_memory:
            mock_memory_instance = MagicMock()
            mock_memory_instance.get_user_context.return_value = {"preferences": {}}
            mock_memory_instance.update_user_context = AsyncMock()
            mock_memory_instance.add_conversation_insight = AsyncMock(
                side_effect=mock_add_insight
            )
            mock_memory.return_value = mock_memory_instance

            # Process multiple messages
            messages = [
                "I prefer budget accommodations",
                "I like cultural activities",
                "I want to visit museums",
            ]

            for message in messages:
                await orchestrator.process_message(user_id, message)

            # Memory should have been updated
            assert mock_memory_instance.add_conversation_insight.call_count >= len(
                messages
            )

    @pytest.mark.asyncio
    async def test_component_isolation_on_failure(
        self, orchestrator, mock_dependencies
    ):
        """Test that component failures don't cascade."""
        user_id = "isolation_test_user"

        # Mock memory bridge failure
        with patch.object(
            orchestrator.memory_bridge,
            "hydrate_state",
            side_effect=Exception("Memory error"),
        ):
            # System should still work without memory hydration
            result = await orchestrator.process_message(
                user_id, "Plan a trip despite memory issues"
            )

            # Should complete successfully despite memory failure
            assert "response" in result
            assert result["response"]  # Should have content

            # Error should be logged but not crash system
            assert "session_id" in result

    @pytest.mark.asyncio
    async def test_full_workflow_simulation(self, orchestrator, mock_dependencies):
        """Test a complete travel planning workflow."""
        user_id = "workflow_test_user"
        session_id = "workflow_session"

        # Mock comprehensive responses
        with patch("tripsage.mcp_abstraction.manager.MCPManager") as mock_mcp:
            mock_mcp_instance = MagicMock()

            # Different responses for different agent calls
            def mock_invoke(service, method, params):
                if "destination" in method or "research" in method:
                    return {"attractions": ["Eiffel Tower", "Louvre"]}
                elif "flight" in method:
                    return {"flights": [{"price": 500, "airline": "Air France"}]}
                elif "accommodation" in method:
                    return {"hotels": [{"name": "Hotel Paris", "price": 200}]}
                else:
                    return {"result": "success"}

            mock_mcp_instance.invoke.side_effect = mock_invoke
            mock_mcp.return_value = mock_mcp_instance

            # Simulate complete workflow
            workflow_messages = [
                "I want to plan a trip to Paris",
                "Research Paris attractions and culture",
                "Find flights from NYC to Paris for July 15-22",
                "Look for hotels near the Eiffel Tower",
                "My budget is $3000 total",
                "Create a 7-day itinerary",
            ]

            results = []
            for message in workflow_messages:
                result = await orchestrator.process_message(
                    user_id, message, session_id
                )
                results.append(result)

                # Small delay to simulate real usage
                await asyncio.sleep(0.1)

            # All steps should succeed
            assert len(results) == len(workflow_messages)
            for result in results:
                assert "response" in result
                assert result["session_id"] == session_id

            # Verify consistent session throughout
            session_ids = [r["session_id"] for r in results]
            assert len(set(session_ids)) == 1
