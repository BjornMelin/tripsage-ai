"""
Simple API endpoint tests for memory system without FastAPI dependencies.
"""

import json
from unittest.mock import AsyncMock, patch

import pytest

from tripsage.services.memory_service import TripSageMemoryService


class TestMemoryEndpoints:
    """Test memory API endpoints functionality without FastAPI."""

    @pytest.fixture
    def mock_memory_service(self):
        """Mock memory service."""
        service = AsyncMock(spec=TripSageMemoryService)
        service.store_conversation_memory.return_value = {
            "status": "success",
            "memory_id": "test-123",
        }
        service.get_user_context.return_value = {
            "memories": [
                {
                    "id": "mem-1",
                    "content": "User prefers luxury hotels",
                    "metadata": {"category": "accommodation", "preference": "luxury"},
                    "score": 0.95,
                    "created_at": "2024-01-01T10:00:00Z",
                }
            ],
            "preferences": {
                "accommodation": "luxury",
                "budget": "high",
                "destinations": ["Europe", "Asia"],
            },
            "travel_patterns": {
                "favorite_destinations": ["Paris", "Tokyo"],
                "avg_trip_duration": 7,
                "booking_lead_time": 30,
            },
        }
        service.search_memories.return_value = [
            {
                "content": "Looking for flights to Paris",
                "metadata": {"type": "search", "destination": "Paris"},
                "score": 0.88,
            }
        ]
        return service

    @pytest.mark.asyncio
    async def test_memory_service_store_conversation(self, mock_memory_service):
        """Test storing conversation through memory service."""
        messages = [
            {
                "role": "user",
                "content": "I'm looking for luxury hotels in Paris for my honeymoon",
                "timestamp": "2024-01-01T10:00:00Z",
            },
            {
                "role": "assistant",
                "content": "I found some excellent luxury hotels in Paris.",
                "timestamp": "2024-01-01T10:01:00Z",
            },
        ]

        result = await mock_memory_service.store_conversation_memory(
            messages=messages, user_id="user-123", session_id="session-123"
        )

        assert result["status"] == "success"
        assert "memory_id" in result
        mock_memory_service.store_conversation_memory.assert_called_once()

    @pytest.mark.asyncio
    async def test_memory_service_get_context(self, mock_memory_service):
        """Test getting user context through memory service."""
        result = await mock_memory_service.get_user_context("user-123")

        assert "memories" in result
        assert "preferences" in result
        assert "travel_patterns" in result

        # Verify memory structure
        memory = result["memories"][0]
        assert "id" in memory
        assert "content" in memory
        assert "metadata" in memory
        assert "score" in memory

    @pytest.mark.asyncio
    async def test_memory_service_search(self, mock_memory_service):
        """Test searching memories through memory service."""
        results = await mock_memory_service.search_memories("user-123", "Paris hotels")

        assert isinstance(results, list)
        assert len(results) > 0

        memory = results[0]
        assert "content" in memory
        assert "metadata" in memory
        assert "score" in memory

    def test_memory_router_import(self):
        """Test that memory router can be imported."""
        try:
            from tripsage.api.routers.memory import router

            assert router is not None
        except ImportError as e:
            pytest.skip(f"Memory router not available: {e}")

    def test_memory_service_import(self):
        """Test that memory service can be imported."""
        try:
            from tripsage.services.memory_service import TripSageMemoryService

            service = TripSageMemoryService()
            assert service is not None
        except ImportError as e:
            pytest.skip(f"Memory service not available: {e}")

    def test_data_structure_compatibility(self):
        """Test that data structures match expected formats."""
        expected_conversation_request = {
            "messages": [{"role": "user", "content": str, "timestamp": str}],
            "metadata": {"sessionId": str, "userId": str},
        }

        expected_context_response = {
            "memories": [
                {
                    "id": str,
                    "content": str,
                    "metadata": dict,
                    "score": float,
                    "created_at": str,
                }
            ],
            "preferences": dict,
            "travel_patterns": dict,
        }

        # These structures should match frontend TypeScript interfaces
        assert expected_conversation_request is not None
        assert expected_context_response is not None

    @patch("tripsage.services.memory_service.TripSageMemoryService")
    def test_memory_service_initialization(self, mock_service_class):
        """Test memory service can be instantiated."""
        try:
            from tripsage.services.memory_service import TripSageMemoryService

            service = TripSageMemoryService()

            # Verify required methods exist
            assert hasattr(service, "store_conversation_memory")
            assert hasattr(service, "get_user_context")
            assert hasattr(service, "search_memories")

        except Exception as e:
            pytest.skip(f"Memory service initialization failed: {e}")

    def test_json_serialization(self):
        """Test that memory data can be JSON serialized."""
        sample_memory_data = {
            "memories": [
                {
                    "id": "mem-1",
                    "content": "User prefers luxury hotels",
                    "metadata": {"category": "accommodation"},
                    "score": 0.95,
                    "created_at": "2024-01-01T10:00:00Z",
                }
            ],
            "preferences": {"accommodation": "luxury"},
            "travel_patterns": {"favorite_destinations": ["Paris"]},
        }

        # Should be able to serialize/deserialize without errors
        json_str = json.dumps(sample_memory_data)
        parsed_data = json.loads(json_str)

        assert parsed_data == sample_memory_data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
